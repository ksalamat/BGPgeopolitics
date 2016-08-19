from flagger import Flagger
from ipaddress import ip_network, IPv4Network, IPv6Network


class GraphFlagger(Flagger):
    def __init__(self,G,table):
        self.G = G
        self.table = table

    def flag(self, route):
        if route.message == 'announce':
            for (asn,country) in list(zip(route.fields['asPath'], route.flags['geoPath'])):
                if asn not in self.G:
                    nodeDict={}
                    nodeDict["Country"]=country
                    self.G.add_node(asn, nodeDict)
            dest=route.fields['asPath'].copy()
            dest.pop(0)
            source=route.fields['asPath'].copy()
            source.pop()
            edgeList= list(zip(source, dest))
            for (src,dst) in edgeList:
                if not (src == dst):
                    if self.G.has_edge(src,dst):
                        att=self.G.get_edge_data(src,dst)
                        prefix=[prefix for prefix in att['prefixes'] if prefix['prefix']== route.fields['prefix'] and prefix['peer']==route.peer['asn']]
                        if not prefix:
                            att['prefixes'].append({'peer': route.peer['asn'], 'prefix': route.fields['prefix']})
                    else :
                        self.G.add_edge(src,dst, prefixes=[{'peer':route.peer['asn'],'prefix': route.fields['prefix']}])
        elif route.message == 'withdrawal' :
            network = ip_network(route.fields['prefix'])
            prefix = route.fields['prefix']
            peer = route.peer['asn']
            if network.version == 4:
                paths=self.table.getV4Prefix(peer,prefix).paths
            else :
                paths=self.table.getV4Prefix(peer,prefix).paths
            withdrawnpaths = [path for path in self.table.v4Table[peer][prefix].paths if path.peerASn ==route.peer['asn'] and path.active ]
            if len(withdrawnpaths) == 1:
                [wpath] = withdrawnpaths
                dest = wpath.path.copy()
                dest.pop(0)
                source = wpath.path.copy()
                source.pop()
                edgeList = list(zip(source, dest))
                for (src, dst) in edgeList:
                    if self.G.has_edge(src, dst):
                        att = self.G.get_edge_data(src, dst)
                        prefix = [prefix for prefix in att['prefixes'] if prefix['prefix'] == route.fields['prefix'] and
                                  prefix['peer'] == route.peer['asn']]
                        if prefix:
                            att['prefixes'].remove({'peer': route.peer['asn'], 'prefix': route.fields['prefix']})
                            if not att['prefixes']:
                                self.G.remove_edge(src,dst)
        return route
