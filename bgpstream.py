from threading import Thread
import _pybgpstream
from bgpsource import BGPSource
from bgpmessage import BGPMessage
from bson.json_util import dumps
import json
from pyparsing import *


class BGPMsgEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, BGPMessage):
            return obj.__dict__
        return dumps(obj)


class BGPStream(Thread, BGPSource):
    def __init__(self, fifo,  t_start, t_end=0, collectors = ['rrc11'], custom_filters = [('record-type', 'updates')]):
        Thread.__init__(self)
        BGPSource.__init__(self)
        self.fifo = fifo
        self.collectors=collectors
        self.t_start = t_start
        self.t_end = t_end
        self.custom_filters = custom_filters
        LBRACE, RBRACE = map(Suppress, "{}")
        wd = Word( nums )
        wd_list = delimitedList(wd, delim=',')
        brace_expr = Group(LBRACE + wd_list + RBRACE)
        self.parser = ZeroOrMore(wd) + Optional(brace_expr) + ZeroOrMore(wd)


    def newMessage(self, elem):
        msg = BGPMessage()
        msg.time = elem.time
        msg.peer = { 'address': elem.peer_address
                     , 'asn': int(elem.peer_asn)
        }
        return msg

    def convertAnnounce(self, elem):

        msg = self.newMessage(elem)
        msg.message = 'announce'
        msg.time=elem.time
#        msg.fields['asPath'] = elem.fields['as-path'].split()
        msg.fields['asPath'] = self.parser.parseString(elem.fields['as-path']).asList()
        msg.fields['prefix'] = elem.fields['prefix']
        msg.fields['nextHop'] = elem.fields['next-hop']
        return msg

    def convertWithdrawal(self, elem):
        msg = self.newMessage(elem)
        msg.message = 'withdrawal'
        msg.time = elem.time
        msg.fields['prefix'] = elem.fields['prefix']
        return msg



    def run(self):
        self.cont = True
        stream = _pybgpstream.BGPStream()
        record = _pybgpstream.BGPRecord()
        for collector in self.collectors:
            stream.add_filter('collector', collector)
        for name, value in self.custom_filters:
            stream.add_filter(name, value)
        stream.add_interval_filter(self.t_start, self.t_end)
        stream.start()

        # keep announces and withdrawal
        msg_type = ['A', 'W']

        while self.cont and stream.get_next_record(record):
            if record.status == 'valid':
                if record.type == 'update':
                    elem = record.get_next_elem()
                    while self.cont and elem:
                        if elem.type not in msg_type:
                            elem = record.get_next_elem()
                            continue
                        elif elem.type == 'A':
                            msg=self.convertAnnounce(elem)
                            self.fifo.put(msg)
                        elif elem.type == 'W':
                            msg=self.convertWithdrawal(elem)
                            self.fifo.put(msg)
                        elem = record.get_next_elem()

    def stop(self):
        self.cont = False