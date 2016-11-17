import threading
from queue import Queue, Empty
import networkx as nx

from graphflagger import GraphFlagger
from geoflagger import GeoFlagger
from flaggerpipe import FlaggerPipe
from schedulesaver import ScheduleSaver
from bgpstream import BGPStream
from cinecaStream import CinecaStream
from bgptable import BGPTable

class FlaggerProcess(threading.Thread):
    def __init__(self, e, flagger, fifo, bgptable, dumpsize):
        threading.Thread.__init__(self)
        self.flagger = flagger
        self.fifo = fifo
        self.bgptable = bgptable
        self.routes = []
        self.count = 0
        self.e = e
        self.dumpsize = dumpsize

    def run(self):
        self.cont = True
        while self.cont:
            try:
                route = self.fifo.get(timeout=10)
            except Empty:
                break
            flaggedRoute = self.flagger.flag(route)
            self.bgptable.update(flaggedRoute)
            self.save(flaggedRoute)
            print(flaggedRoute.__dict__)
            self.count += 1
        e.set()
        self.stop()

    def stop(self):
        self.cont = False

    def save(self,route):
        self.routes.append(route.__dict__)
        if len(self.routes) == self.dumpsize:
            e.set()

    def deque(self):
        L = min(len(self.routes), dumpsize)
        if L > 0:
            self.routes[0:L] = []



if __name__ == '__main__':
    #parsing given parameter
    import argparse

    dumpsize= 1000
    parser = argparse.ArgumentParser()
    #Collector name can be rrc00..11 (ripe collectors) or routeviews one.
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

    e = threading.Event()


    #create the graph to be used
    G=nx.Graph()

    #create the BGP table
    table = BGPTable()
    #initiate a GeoFlagger
    #GeoFlagger adds countries crossed by the given AS path
    geoFlagger = GeoFlagger()
    #initiate a GraphFlagger
    #update the AS connectivity graph using received BG updates
    graphFlagger=GraphFlagger(G, table)

    #initiate a pipeline of flagger and  add the flaggers in it
    flaggerPipe = FlaggerPipe()
    flaggerPipe.append(geoFlagger)
    flaggerPipe.append(graphFlagger)

    inFifo = Queue()
#    start = 1438416600
    start = int(args.tstart)
    end = int(args.tend)
    collector=list()
    collector.append(args.collector)

#    bgpsource = BGPStream(inFifo, start, end, collector)
    bgpsource = CinecaStream(inFifo, start, end)
    fd = FlaggerProcess(e, flaggerPipe, inFifo, table, dumpsize)
    saver = ScheduleSaver(e, fd, G, dumpsize)

    bgpsource.start()
    fd.start()
    saver.start()
    bgpsource.join()
    fd.join()
    fd.stop()
    bgpsource.stop()
    saver.stop()

    print(nx.number_of_nodes(graphFlagger.G))
    print(nx.number_of_edges(graphFlagger.G))



