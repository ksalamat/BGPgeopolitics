from ipaddress import ip_network, IPv4Network, IPv6Network
from bgpmessage import BGPMessage
import json

class BGPEntryEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BGPMessage):
            return obj.__dict__
        elif isinstance(obj, BGPEntry):
            return obj.__dict__
        elif isinstance(obj, PathEntry):
            return obj.__dict__
        elif isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

class PathEntry:
    def __init__(self, path):
        self.path=path
        self.peerASn=0
        self.risk=0.0
        self.geoPath=[]
        self.nextHop=[]
        self.active=True
        self.lastChange=None

    def __hash__(self):
        return hash(str(self.path))

    def __eq__(self, other):
        return str(self.path)==str(other)

class BGPEntry:
    def __init__(self,prefix):
        self.prefix=prefix
#       a copy of messages is not needed in the BGP table
#        self.msgs=[]
        self.bestPath=None
        self.paths=set()

    def update(self,update):
#       a copy of messages is not needed in the BGP table
#        self.msgs.append(update)
        path=PathEntry(update.fields['asPath'])
        path.peerASn=update.peer['asn']
        path.risk=update.flags['risk']
        path.nextHop=update.fields['nextHop']
        path.geoPath=update.flags['geoPath']
        path.lastChange=update.time
        if path in self.paths:
            self.paths.remove(path)
        self.paths.add(path)
        self.updateBestPath()
        self.bestPath.lastChange=update.time

    def updateBestPath(self):
        for pathe in self.paths:
            if self.bestPath is None:
                self.bestPath=pathe
            elif len(pathe.path)<len(self.bestPath.path) and pathe.risk<self.bestPath.risk:
                self.bestPath=pathe

    def withdraw(self,update):
        withdrawnpaths = [path for path in self.paths if path.peerASn == update.peer['asn']]
        if len(withdrawnpaths) == 1:
            [wpath] = withdrawnpaths
            wpath.active=False
            if (wpath == self.bestPath):
                self.bestpath = None
                self.updateBestPath()
                self.bestpath.lastChange=update.time


class BGPTable:
    def __init__(self):
        self.v4Table = {}
        self.v6Table = {}

    def hasV4Prefix(self, pfx):
        return pfx in self.v4Table.keys()

    def hasV6Prefix(self, pfx):
        return pfx in self.v6Table.keys()
        
    def announceV4(self, update):
        prefix = update.fields['prefix']
        if not self.hasV4Prefix(prefix):
            self.v4Table[prefix] = BGPEntry(prefix)
        self.v4Table[prefix].update(update)


    def announceV6(self, update):
        prefix = update.fields['prefix']
        if not self.hasV6Prefix(prefix):
            self.v6Table[prefix] = BGPEntry(prefix)
        self.v6Table[prefix].update(update)


    def announce(self, update):
        network = ip_network(update.fields['prefix'])
        if network.version == 4:
            self.announceV4(update)
        else:
            self.announceV6(update)

    def withdrawV4(self, update):
        prefix = update.fields['prefix']
        if self.hasV4Prefix(prefix):
            self.v4Table[prefix].withdraw(update)

    def withdrawV6(self, update):
        prefix = update.fields['prefix']
        if self.hasV6Prefix(prefix):
            self.v6Table[prefix].withdraw(update)

    def withdraw(self, update):
        network = ip_network(update.fields['prefix'])
        if network.version == 4:
            self.withdrawV4(update)
        else:
            self.withdrawV6(update)
            
    def update(self, update):
        if update.message == 'announce':
            self.announce(update)
        elif update.message == 'withdrawal':
            self.withdraw(update)
    
    def toJson(self):
        return json.dumps({'IPv4': self.v4Table, 'IPv6': self.v6Table}
                          , cls=BGPEntryEncoder
                          )