from threading import Thread
import _pybgpstream
from bgpsource import BGPSource
from bgpmessage import BGPMessage
import urllib.request
import json
from pyparsing import *
from datetime import datetime as dt, timedelta


class CinecaStream(Thread, BGPSource):
    def __init__(self, fifo,  t_start, t_end, baseurl='http://194.242.226.17/exabgp/',hour0=9, day0=30, month0=9, year0=2016):
        Thread.__init__(self)
        BGPSource.__init__(self)
        self.fifo = fifo
        self.url = baseurl
        self.t_start = t_start
        self.t_end = t_end
        LBRACE, RBRACE = map(Suppress, "{}")
        wd = Word( nums )
        wd_list = delimitedList(wd, delim=',')
        brace_expr = Group(LBRACE + wd_list + RBRACE)
        self.parser = ZeroOrMore(wd) + Optional(brace_expr) + ZeroOrMore(wd)
        self.baseurl=baseurl
        first_time = dt(year0, month0, day0, hour0)
        self.now0 = dt.fromtimestamp(t_start)
        if self.now0<first_time:
            self.now0 = first_time
        self.end_time=dt.fromtimestamp(t_end)
        self.now = self.now0
        self.first = True

    def urlGenenerator(self):

        return self.baseurl+self.now.isoformat()+'.log'

    def newMessage(self, record):
        msg = BGPMessage()
        msg.time = record['time']
        msg.peer = {'address': record['neighbor']['address']['peer']
                     , 'asn': int(record['neighbor']['asn']['peer'])
        }
        return msg


    def convertAnnounce(self, record, prefix):
        msg = self.newMessage(record)
        msg.message = 'announce'
        msg.fields['asPath'] = record['neighbor']['message']['update']['attribute']['as-path']
        msg.fields['prefix'] = prefix
        msg.fields['nextHop'] = record['neighbor']['address']['peer']
        return msg

    def convertWithdrawal(self, record, prefix):
        msg = self.newMessage(record)
        msg.message = 'withdrawal'
        msg.fields['prefix'] = prefix
        return msg

    def run(self):
        self.cont = True
        while self.now < self.end_time:
            if self.now.hour<10:
                hourstr='0'+str(self.now.hour)
            else:
                hourstr=str(self.now.hour)
            while dt.now()< self.now: #the file in the server is not ready
                print('Sleep 10 mins\n')
                time.sleep(10*3600) #go to sleep and wait for the file to be ready
            target_url=self.baseurl+dt.date(self.now).isoformat()+'-'+hourstr+'.log'
            self.first=False
            print(target_url)
            data = urllib.request.urlopen(target_url)  # it's a file like object and works just like a file
            for rec in data:  # files are iterable
                if len(rec) > 2:
                    s = rec[60:len(rec)].decode('utf-8').rstrip()
                    if '"exabgp"' in s:
                        record = json.loads(s)
                        if (record['time'] >= self.t_start) and (record['time'] < self.t_end):
                            # keep announces and withdrawal
                            msg_type = ['A', 'W']
                            if 'announce' in record['neighbor']['message']['update'].keys():
                                for prefix in record['neighbor']['message']['update']['announce']['ipv4 unicast']['194.242.224.66'].keys():
                                    msg=self.convertAnnounce(record, prefix)
                                    self.fifo.put(msg)
                            elif 'withdraw' in record['neighbor']['message']['update'].keys():
                                for prefix in record['neighbor']['message']['update']['withdraw']['ipv4 unicast'].keys():
                                    msg=self.convertWithdrawal(record,prefix)
                                    self.fifo.put(msg)
            if not self.first:
                self.now = self.now + timedelta(hours=1)
                self.first = False

        self.stop()

    def stop(self):
        self.cont = False



