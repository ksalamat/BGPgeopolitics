from flagger import Flagger
from datetime import timedelta, datetime
import json


class RoutingDynamicFlagger(Flagger):
    def __init__(self,table):
        self.table=table

    def prepare(self, route):
        route = super(RoutingDynamicFlagger, self).flag(route)
        if 'category' not in route.flags:
            route.flags['category'] = None
        return route

    def checkroute(self,route,bgpEntry):
        if route.message=='announce':
            annoucedPath = [path for path in bgpEntry.paths if path.peerASn == route.peer['asn']]
            if len(annoucedPath) == 1:
                [path] =annoucedPath
                if path.active :
                    if (path.path == route.fields['asPath']):
                        return 1 ##AADup
                    else :
                        return 2  ##AADiff
                else:
                    if (route.time-path.lastChange<300):
                        if (path.path==route.fields['asPath']):
                            return 3 ##WADup
                        else:
                            return 4  ##WADiff
        elif route.message=='withdrawal':
            annoucedPath = [path for path in bgpEntry.paths if path.peerASn == route.peer['asn']]
            if len(annoucedPath) == 1:
                [path] =annoucedPath
                if not path.active:
                    return 5 ##WWDup
        return 0


    def flag(self, route):
        prefix = route.fields['prefix']
        if self.table.hasV4Prefix(prefix):
            bgpEntry=self.table.v4Table[prefix]
        elif self.table.hasV6Prefix(prefix):
            bgpEntry=self.table.v6Table[prefix]
        else :
            return route
        status =self.checkroute(route,bgpEntry)
        if status==1 :
            route.flags['category'] = 'AADup'
        elif status==2 :
            route.flags['category'] = 'AADiff'
        elif status==3 :
            route.flags['category'] = 'WADup'
        elif status==4:
            route.flags['category'] = 'WAADiff'
        elif status==5:
            route.flags['category'] = 'WWDup'
        else:
            route.flags['category'] = 'None'
        print(route.__dict__)
        return route
