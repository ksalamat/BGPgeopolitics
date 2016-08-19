import sqlite3
from contextlib import closing
from cymru.ip2asn.dns import DNSClient as ip2asn
import api
import bgpranking_web
import numpy as np
from scipy import percentile


class ASRecord( object ):
    def __init__( self, dbname='resources/as.sqlite' ):
        self.dbname = dbname
        self.db = sqlite3.connect(self.dbname)
    def close( self ):
        self.db.commit()
        self.db.close()

    def setObserved(self,asn):
        self.db.execute('update asn set observed= 1 where asNumber=? and observed=0', [asn])

    def queryCountryRisk( self, asn ):
        dbCursor = self.db.cursor()
        dbCursor.execute('select asNumber, country, riskIndex from asn where asNumber=?', [asn])
        res = dbCursor.fetchone()
        if res is not None:
            (network, country, risk) = res
            return [country, risk]
        else:
            self.db.execute(
                'insert into asn (asNumber, riskIndex, geoRisk, perfRisk, secuRisk, otherRisk)  values(?,0.0,0.0,0.0,0.0,0.0)', [asn])
            return None

    def queryUnknownCountry(self):
        dbCursor = self.db.cursor()
        dbCursor.execute('select asNumber,country from asn where country is null and name is null')
        rows = dbCursor.fetchall()
        return rows

    def updateRecord(self,asn,name, country,RIR):
        self.db.execute(
            'update asn set name=?, country=?, RIR=?, riskIndex=0.0, geoRisk=0.0, perfRisk=0.0, secuRisk=0.0, otherRisk=0.0 where asNumber=?', [name,country,RIR,asn])

    def getObserved(self):
        dbCursor = self.db.cursor()
        dbCursor.execute('select asNumber, country from asn where observed=1')
        rows = dbCursor.fetchall()
        return rows

    def updateSecuRisk(self,asn, risk):
        self.db.execute(
            'update asn set secuRisk=? where asNumber=?',[risk, asn])

    def getSecuRisk(self):
        dbCursor = self.db.cursor()
        dbCursor.execute(
            'select secuRisk from asn where secuRisk>0'
        )
        rows=dbCursor.fetchall()
        return rows

class ASnupdater:
    def __init__(self):
        self.dbname='resource/as.sqlite'

    def updateASNinfo(self):
        asList = list()
        with closing(ASRecord()) as db:
            rows = db.queryUnknownCountry()
            for row in rows:
                (asn, country) = row
                asList.append(asn)
            print(asList)
            client = ip2asn()
            for result in client.lookupmany(asList, qType='ASN'):
                if not result.asn == None:
                    print(result.asn[2:], result.owner, result.cc, result.lir)
                    db.updateRecord(result.asn[2:], result.owner, result.cc, result.lir)

    def getSecuRisk(self):
        asList = list()
        with closing(ASRecord()) as db:
            rows = db.getObserved()
            for row in rows:
                (asn, country) = row
                asList.append(asn)
            print(asList)
            for asn in asList:
                result=bgpranking_web.cached_daily_rank(asn)
                if not result==None :
                    if not result=={'error': 'Something went wrong.'}:
                        print(asn, result)
                        if result[4]==None:
                            securisk=0.0
                        else:
                         securisk=result[4]
                         db.updateSecuRisk(asn,securisk)

    def calcRiskIndex(self):
        riskList=list()
        with closing(ASRecord()) as db:
            rows=db.getSecuRisk()
        for row in rows:
            (risk)=row
            riskList.append(risk)
        riskArray = np.asarray(riskList)
        stdRisk=np.std(riskArray)
        riskArray= riskArray/stdRisk
        return riskArray



if __name__ == '__main__':
    asnUpdater=ASnupdater()
    asnUpdater.updateASNinfo()
    asnUpdater.getSecuRisk()

