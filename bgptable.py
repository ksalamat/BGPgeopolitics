from ipaddress import ip_network
from bgpmessage import BGPMessage
import json
from sortedcontainers import SortedListWithKey


class BGPEntryEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, dict):
            return obj.__dict__
        if isinstance(obj, BGPMessage):
            return obj.__dict__
        elif isinstance(obj, BGPEntry):
            return obj.__dict__
        elif isinstance(obj, PathEntry):
            return obj.__dict__
        elif isinstance(obj,SortedListWithKey ):
            return obj[0:]
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
        return self.path == str(other)


class BGPEntry:
    def __init__(self, prefix):
        self.prefix = prefix
#       a copy of messages is not needed in the BGP table
#        self.msgs=[]
        self.paths = SortedListWithKey([], key=lambda val : val.lastChange)
        self.AADup = 0
        self.AADiff = 0
        self.WADup = 0
        self.WADiff = 0
        self.WWDup = 0
        self.flaps = 0
        self.announcements = 0

    def update(self, update):
        self.announcements += 1
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
            update.flags['category'] = 'None'
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
                if activePath.path == update.fields['asPath']:
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
                        prevPath.lastChange = update.time
                        prevPath.active = True

    def withdraw(self, update):
        self.announcements += 1
        withdrawnpaths = [path for path in self.paths]
        if len(withdrawnpaths) == 1:
            [wpath] = withdrawnpaths
            if wpath.active:
                wpath.active = False
                wpath.meanUp = wpath.coeff * wpath.meanUp + \
                                          (1 - wpath.coeff) * (update.time - wpath.lastChange)
                wpath.lastChange = update.time
                update.flags['category'] = 'None'
            else:
                # rewithdrawn of an already withdrawn path
                self.WWDup += 1
                update.flags['category'] = 'WWDup'
        else:
            update.flags['category'] = 'UnknownPath'



class BGPTable:
    def __init__(self):
        self.v4Table = {}
        self.v6Table = {}
        self.v4Routing = {}
        self.v6Routing = {}

    def getPrefix(self, peer, pfx):
        if peer in self.v4Table.keys():
            if pfx in self.v4Table[peer]:
                return self.v4Table[peer][pfx]
        if peer in self.v6Table.keys():
            if pfx in self.v6Table[peer]:
                return self.v6Table[peer][pfx]
        return None

    def getV4Prefix(self, peer, pfx):
        if peer not in self.v4Table.keys():
            self.v4Table[peer] = {}
        if pfx not in self.v4Table[peer]:
            self.v4Table[peer][pfx] = BGPEntry(pfx)
        return self.v4Table[peer][pfx]

    def getV6Prefix(self, peer, pfx):
        if peer not in self.v6Table.keys():
            self.v6Table[peer] = {}
        if pfx not in self.v6Table[peer]:
            self.v6Table[peer][pfx] = BGPEntry(pfx)
        return self.v6Table[peer][pfx]
        
    def announceV4(self, update):
        peer = update.peer['asn']
        prefix = update.fields['prefix']
        self.getV4Prefix(peer, prefix).update(update)

    def announceV6(self, update):
        peer = update.peer['asn']
        prefix = update.fields['prefix']
        self.getV6Prefix(peer, prefix).update(update)

    def announce(self, update):
        network = ip_network(update.fields['prefix'])
        if network.version == 4:
            self.announceV4(update)
        else:
            self.announceV6(update)

    def withdrawV4(self, update):
        peer = update.peer['asn']
        prefix = update.fields['prefix']
        if peer in self.v4Table.keys() and prefix in self.v4Table[peer]:
            self.getV4Prefix(peer,prefix).withdraw(update)
            if prefix in self.v4Routing.keys():
                bestPath = self.v4Routing[prefix]
                if not bestPath == None :
                    if bestPath.peerASn == peer:
                        self.v4Routing[prefix]=None
        else:
            update.flags['category'] = 'UnknowPath'


    def withdrawV6(self, update):
        peer = update.peer['asn']
        prefix = update.fields['prefix']
        if peer in self.v6Table.keys() and prefix in self.v6Table[peer]:
            self.getV6Prefix(peer,prefix).withdraw(update)
            if prefix in self.v6Routing.keys():
                bestPath = self.v6Routing[prefix]
                if not bestPath == None:
                    if bestPath.peerASn == peer:
                        self.v4Routing[prefix]=None
        else:
            update.flags['category'] = 'UnknowPath'

    def update(self, update):
        prefix = update.fields['prefix']
        network = ip_network(prefix)
        if update.message == 'announce':
            if network.version == 4:
                self.announceV4(update)
            else:
                self.announceV6(update)
        elif update.message == 'withdrawal':
            if network.version == 4:
                self.withdrawV4(update)
            else:
                self.withdrawV6(update)
        self.updateBestPath(update.fields['prefix'], network.version)

    def updateBestPath(self, pfx, version):
        if version == 4:
            if pfx not in self.v4Routing.keys():
                self.v4Routing[pfx] = PathEntry(0, pfx)
            routingEntry=self.v4Routing[pfx]
            for peer in self.v4Table.keys():
                if pfx  in self.v4Table[peer]:
                    activePath = next((x for x in self.v4Table[peer][pfx].paths if x.active), None)
                    if activePath is not None:
                        if routingEntry is None or routingEntry.peerASn == 0 or (len(activePath.path) < len(routingEntry.path) and activePath.risk < routingEntry.risk):
                            self.v4Routing[pfx]=activePath
        else:
            if pfx not in self.v6Routing.keys():
                self.v6Routing[pfx] = PathEntry(0,pfx)
            routingEntry=self.v6Routing[pfx]
            for peer in self.v6Table.keys():
                if pfx in self.v6Table[peer]:
                    activePath = next((x for x in self.v6Table[peer][pfx].paths if x.active), None)
                    if activePath is not None:
                        if routingEntry is None or routingEntry.peerASn == 0 or (len(activePath.path) < len(routingEntry.path) and activePath.risk < routingEntry.risk):
                            self.v6Routing[pfx]=activePath

    def toJson(self):
        return 'BGPRoutes:'+json.dumps({'IPv4': self.v4Table, 'IPv6': self.v6Table}, cls=BGPEntryEncoder) + \
               'Routing Tables:'+json.dumps({'IPv4': self.v4Routing, 'IPv6': self.v6Routing}, cls=BGPEntryEncoder)

