from flagger import Flagger
from ipaddress import ip_network


class GraphFlagger(Flagger):
    def __init__(self, G, table):
        self.G = G
        self.table = table

    def flag(self, route):
        if route.message == 'announce':
            for (asn,country) in list(zip(route.fields['asPath'], route.flags['geoPath'])):
                if isinstance(asn, list): # We have an aggregated route
                    for (subasn,subcountry) in list(zip(asn,country )):
                        if subasn not in self.G:
                            nodeDict = {}
                            nodeDict['Country'] = subcountry
                            self.G.add_node(subasn, nodeDict)
                else:
                    if asn not in self.G:
                        nodeDict = {}
                        nodeDict['Country'] = country
                        self.G.add_node(asn, nodeDict)
            dest = route.fields['asPath'].copy()
            dest.pop(0)
            source = route.fields['asPath'].copy()
            source.pop()
            edgeList = list(zip(source, dest))
            for (src, dst) in edgeList:
                if isinstance(dst, list) and isinstance(src, int):
                    for subdst in dst:
                        if not (src == subdst):
                            if self.G.has_edge(src, subdst):
                                att = self.G.get_edge_data(src, subdst)
                                att['count'] += 1
                            else:
                                self.G.add_edge(src, subdst, {'count': 1})
                elif isinstance(src, list) and isinstance(dst, int):
                    for subsrc in src:
                        if not (subsrc == dst):
                            if self.G.has_edge(subsrc, dst):
                                att = self.G.get_edge_data(subsrc, dst)
                                att['count'] += 1
                            else:
                                self.G.add_edge(subsrc, dst, {'count': 1})
                elif isinstance(src, int) and isinstance(dst, int):
                    if not (src == dst):
                        if self.G.has_edge(src, dst):
                            att = self.G.get_edge_data(src, dst)
                            att['count'] += 1
                        else:
                            self.G.add_edge(src,dst, {'count': 1})
                    else:
                        print('Two consecutive as-set in a path!')
        elif route.message == 'withdrawal':
            peer = route.peer['asn']
            prefix =route.fields['prefix']
            bgpEntry=self.table.getPrefix(peer, prefix)
            if bgpEntry is not None:
                paths = self.table.getPrefix(peer, prefix).paths
                withdrawnpaths = [path for path in paths if path.peerASn ==route.peer['asn'] and path.active ]
                if len(withdrawnpaths) == 1:
                    [wpath] = withdrawnpaths
                    dest = wpath.path.copy()
                    dest.pop(0)
                    source = wpath.path.copy()
                    source.pop()
                    edgeList = list(zip(source, dest))
                    for (src, dst) in edgeList:
                        if isinstance(dst, list) and isinstance(src, str):
                            for subdst in dst:
                                if self.G.has_edge(src, subdst):
                                    att = self.G.get_edge_data(src, subdst)
                                    att['count'] -= 1
                                    if att['count'] == 0:
                                        self.G.remove_edge(src, subdst)
                        elif isinstance(src, list) and isinstance(dst, str):
                            for subsrc in src:
                                if self.G.has_edge(subsrc, dst):
                                    att = self.G.get_edge_data(subsrc, dst)
                                    att['count'] -= 1
                                    if att['count'] == 0:
                                        self.G.remove_edge(subsrc, dst)
                        elif isinstance(src, str) and isinstance(dst, str):
                            if self.G.has_edge(src, dst):
                                att = self.G.get_edge_data(src, dst)
                                att['count'] -=1
                                if att['count'] == 0:
                                        self.G.remove_edge(src,dst)
        return route
