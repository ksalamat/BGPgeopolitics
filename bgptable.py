from ipaddress import ip_network
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
    def __init__(self, peerAsn, path):
        self.path = path
        self.peerASn = peerAsn
        self.risk = 0.0
        self.geoPath = []
        self.nextHop = []
        self.active = True
        self.lastChange = None
        self.meanUp = 0
        self.meanDown = 0
        self.coeff = 0.7

    def __hash__(self):
        return hash(str(self.path))

    def __eq__(self, other):
        return str(self.path) == str(other.path)


class BGPEntry:
    def __init__(self, prefix):
        self.prefix = prefix
#       a copy of messages is not needed in the BGP table
#        self.msgs=[]
        self.bestPath = None
        self.paths = set()
        self.AADup = 0
        self.AADiff = 0
        self.WADup = 0
        self.WADiff = 0
        self.WWDup = 0
        self.flaps = 0

    def update(self, update):
        # first obtain all path announced by the
        newPath = False
        prevPath = next((x for x in self.paths if x.path == update.fields['asPath']), None)
        if prevPath is None:
            # this path has never been announced, this is a new one
            path = PathEntry(update.peer['asn'], update.fields['asPath'])
            path.risk = update.flags['risk']
            path.nextHop = update.fields['nextHop']
            path.geoPath = update.flags['geoPath']
            path.lastChange = update.time
            path.active = True
            newPath = True
        if len(self.paths) == 0 and newPath:
            # No previous paths
            self.paths.add(path)
        else:
            # Existing previous paths
            activePath = next((x for x in self.paths if x.active), None)
            if activePath is None:
                # Announcing a path after a withdrawn, explicit withdrawn
                # Let's find the last active
                changeDates = [x.lastChange for x in self.paths]
                lastChange = max(changeDates, default=None)
                lastIndex = changeDates.index(lastChange)
                lastActivePath = self.paths[lastIndex]
                if update.time - lastActivePath.lastChange < 300:
                    # This is a flap
                    if lastActivePath == update.fields['asPath']:
                        self.flaps += 1
                        self.WADup += 1  # explicit withdrawal and replacement with identic
                        update.flags['category'] = 'WADup'
                    else:
                        self.flaps += 1
                        self.WADiff += 1  # explicit withdrawal and replacement with different
                        update.flags['category'] = 'WADiff'
                lastActivePath.meanDown = lastActivePath.coeff * lastActivePath.meanDown + \
                                          (1 - lastActivePath.coeff) * (update.time - lastActivePath.lastChange)
                if newPath:
                    self.paths.add(path)
                else:
                    prevPath.lastChange = update.time
                    prevPath.active = True
            else:
                # this is an implicit withdrawn
                if activePath == update.fields['asPath']:
                    activePath.lastChange = update.time
                    self.AADup += 1
                    update.flags['category'] = 'AADup'
                else:
                    activePath.active = False
                    activePath.meanUp = activePath.coeff * activePath.meanUp + \
                                              (1 - activePath.coeff) * (update.time - activePath.lastChange)
                    activePath.lastChange = update.time
                    self.AADiff += 1
                    update.flags['category'] = 'AADif'
                    if newPath:
                        self.paths.add(path)
                    else:
                        prevPath.lastChange = update.Time
                        prevPath.active = True
        self.updateBestPath()
        self.bestPath.lastChange = update.time

    def withdraw(self, update):
        withdrawnpaths = [path for path in self.paths]
        if len(withdrawnpaths) == 1:
            [wpath] = withdrawnpaths
            if wpath.active:
                wpath.active = False
                wpath.meanUp = wpath.coeff * wpath.meanUp + \
                                          (1 - wpath.coeff) * (update.time - wpath.lastChange)
                wpath.lastChange = update.time
            else:
                # rewithdrawn of an already withdrawn path
                self.WWDup += 1
                update.flags['category'] = 'WWDup'
        if wpath == self.bestPath:
                self.bestPath = None
                self.updateBestPath()
                self.bestPath.lastChange = update.time

    def updateBestPath(self):
        for pathe in self.paths:
            if self.bestPath is None:
                self.bestPath = pathe
            elif len(pathe.path) < len(self.bestPath.path) and pathe.risk < self.bestPath.risk:
                self.bestPath = pathe


class BGPTable:
    def __init__(self):
        self.v4Table = {}
        self.v6Table = {}

    def hasV4peer(self, peer):
        return peer in self.v4Table.keys()

    def hasV6peer(self, peer):
        return peer in self.v6Table.keys()

    def hasV4Prefix(self, peer, pfx):
        return pfx in self.v4Table[peer].keys()

    def hasV6Prefix(self, peer, pfx):
        return pfx in self.v6Table[peer].keys()
        
    def announceV4(self, update):
        peer = update.peer['asn']
        prefix = update.fields['prefix']
        if not self.hasV4peer(peer):
            self.v4Table[peer] = {}
        if not self.hasV4Prefix(peer, prefix):
            self.v4Table[peer][prefix] = BGPEntry(prefix)
        self.v4Table[peer][prefix].update(update)

    def announceV6(self, update):
        peer = update.peer['asn']
        prefix = update.fields['prefix']
        if not self.hasV6peer(peer):
            self.v6Table[peer] = {}
        if not self.hasV6Prefix(peer, prefix):
            self.v6Table[peer][prefix] = BGPEntry(prefix)
        self.v6Table[peer][prefix].update(update)

    def announce(self, update):
        network = ip_network(update.fields['prefix'])
        if network.version == 4:
            self.announceV4(update)
        else:
            self.announceV6(update)

    def withdrawV4(self, update):
        peer = update.peer['asn']
        prefix = update.fields['prefix']
        if not self.hasV4peer(peer):
            self.V4Table[peer] = {}
        if self.hasV4Prefix(peer, prefix):
            self.v4Table[peer][prefix].withdraw(update)

    def withdrawV6(self, update):
        peer = update.peer['asn']
        prefix = update.fields['prefix']
        if not self.hasV6peer(peer):
            self.V6Table[peer] = {}
        if self.hasV6Prefix(peer, prefix):
            self.v6Table[peer][prefix].withdraw(update)

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
