from threading import Thread
from pymongo import MongoClient
import gzip
import time
import json
import networkx as nx

class ScheduleSaver(Thread):
    def __init__(self, e, fd, G, dumpsize):
        Thread.__init__(self)
        self.e = e
        #preparing Mongodb connection
        self.client = MongoClient()
        #database containing BGP announcements
        self.db = self.client['BGPdb']
        #database containing BGP table dumps
        self.bgpDump = self.db['BGPdump']
        self.fd = fd
        self.cont=True
        self.G=G

    def urlGenenerator(self):

        return self.baseurl+self.now.isoformat()+'.log'

    def save(self):
        with gzip.open('dumps/tabledumps' + str(int(time.time())) + '.gz', 'wb') as f:
            f.write(self.fd.bgptable.toJson().encode())
        f.close()
        with gzip.open('dumps/routedumps' + str(int(time.time())) + '.gz', 'wb') as f:
            f.write(json.dumps(self.fd.routes).encode())
        f.close()

#        self.db.insert_many(json.dumps(self.fd.routes))
        self.fd.deque()
        nx.write_gexf(self.G, 'dumps/graphdumps' + str(int(time.time())) + '.gexf')

    def run(self):
        while self.cont:
            event_is_set = self.e.wait()
            self.save()
            self.e.clear()

    def stop(self):
        self.save()
        self.cont = False


