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
import luigi



class FlaggerProcess(threading.Thread):
    def __init__(self, flagger, fifo, bgptable,db):
        threading.Thread.__init__(self)
        self.flagger = flagger
        self.fifo = fifo
        self.bgptable = bgptable
        self.db=db
        self.routes=[]
        self.count=0

    def run(self):
        self.cont = True
        while self.cont:
            try:
                route = self.fifo.get(timeout=10)
            except Empty:
                continue
            flaggedRoute = self.flagger.flag(route)
            self.bgptable.update(flaggedRoute)
            self.save(flaggedRoute)
            print(flaggedRoute.__dict__)
            self.count += 1
        while not self.fifo.empty():
            route = self.fifo.get()
            flaggedRoute = self.flagger.flag(route)
            self.bgptable.update(flaggedRoute)
            self.save(flaggedRoute)
            print(flaggedRoute.__dict__)
            self.count += 1
        self.db.insert_many(self.routes)

    def stop(self):
        self.cont = False

    def save(self,route):
        self.routes.append(route.__dict__)
        if len(self.routes) == 10000:
            self.db.insert_many(self.routes)
            self.routes = []

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--collector",
                        help="collector name from where the log files are",
                        default=['rrc00'])
    parser.add_argument("-start_time", "--tstart",
                        help="Start time",
                        default=1471759300 )
    parser.add_argument( "-end_time", "--tend",
                        help="end time",
                        default=1471759310 )

    args = parser.parse_args()



    client = MongoClient()
    db = client['BGPdb']
    bgpDump = db['BGPdump']
    tableDump=db['TableDump']
    G=nx.Graph()

    table = BGPTable()
    geoFlagger = GeoFlagger()

#   graphFlagger=GraphFlagger(G,table)
#    routingDynamicFlagger=RoutingDynamicFlagger(table)
    flaggerPipe = FlaggerPipe()
    flaggerPipe.append(geoFlagger)
#    flaggerPipe.append(GraphFlagger)

    inFifo = Queue()
#    start = 1438416600
    start = args.tstart
    end = args.tend
    collector=args.collector

    bgpsource = BGPStream(inFifo, start, end, collector)
    fd = FlaggerProcess(flaggerPipe, inFifo, table,bgpDump)

    bgpsource.start()
    fd.start()
    bgpsource.join()
    fd.stop()
    fd.join()
    bgpsource.stop()

#    print(nx.number_of_nodes(graphFlagger.G))
#    print(nx.number_of_edges(graphFlagger.G))
    print(table.toJson())

    tableDump.insert({'time': datetime.datetime.now().time().isoformat(),'tableDump':table.toJson()})

