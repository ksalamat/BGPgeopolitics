import threading
from queue import Queue, Empty
import networkx as nx

from graphflagger import GraphFlagger
from geoflagger import GeoFlagger
from routingDynamicFlagger import RoutingDynamicFlagger
from flaggerpipe import FlaggerPipe
from bgpstream import BGPStream
from bgptable import BGPTable
from pymongo import MongoClient
import datetime



class FlaggerProcess(threading.Thread):
    def __init__(self, flagger, fifo, bgptable):
        threading.Thread.__init__(self)
        self.flagger = flagger
        self.fifo = fifo
        self.bgptable = bgptable

    def run(self):
        self.cont = True
        while self.cont:
            try:
                route = self.fifo.get(timeout=10)
            except Empty:
                continue
            flaggedRoute = self.flagger.flag(route)
            self.bgptable.update(flaggedRoute)
        while not self.fifo.empty():
            route = self.fifo.get()
            flaggedRoute = self.flagger.flag(route)
            self.bgptable.update(flaggedRoute)
        
    def stop(self):
        self.cont = False
        
if __name__ == '__main__':
    client = MongoClient()
    db = client['BGPdb']
    bgpDump = db['BGPdump']
    tableDump=db['TableDump']
    G=nx.Graph()

    table = BGPTable()
    geoFlagger = GeoFlagger()
    graphFlagger=GraphFlagger(G,table)
    routingDynamicFlagger=RoutingDynamicFlagger(table)
    flaggerPipe = FlaggerPipe()
    flaggerPipe.append(geoFlagger)
    flaggerPipe.append(graphFlagger)


    inFifo = Queue()
#    start = 1438416600
    start = 1438500000
    bgpsource = BGPStream(inFifo, bgpDump, start, start + 60)
    fd = FlaggerProcess(flaggerPipe, inFifo, table)

    bgpsource.start()
    fd.start()
    bgpsource.join()
    fd.stop()
    fd.join()
    bgpsource.stop()

    print(nx.number_of_nodes(graphFlagger.G))
    print(nx.number_of_edges(graphFlagger.G))
    print(table.toJson())
#    thebytes = pickle.dump(table)
    tableDump.insert({'time': datetime.datetime.now().time().isoformat(),'tableDump':table.toJson()})

