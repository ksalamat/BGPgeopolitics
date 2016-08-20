import sqlite3
from contextlib import closing
from cymru.ip2asn.dns import DNSClient as ip2asn
import api
import bgpranking_web
import numpy as np


class ASRecord( object ):
    def __init__( self, dbname='resources/as.sqlite' ):
        self.dbname = dbname
        self.db = sqlite3.connect(self.dbname)

    def close( self ):
        self.db.commit()
        self.db.close()

    def dbSsetObserved(self,asn):
        self.db.execute('update asn set observed= 1 where asNumber=? and observed=0', [asn])

    def dbQueryCountryRisk( self, asn ):
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

    def dbQueryUnknownCountries(self):
        dbCursor = self.db.cursor()
        dbCursor.execute('select asNumber,country from asn where country is null and name is null')
        rows = dbCursor.fetchall()
        return rows

    def dbUpdateRecord(self,asn,name, country,RIR):
        self.db.execute(
            'update asn set name=?, country=?, RIR=?, riskIndex=0.0, geoRisk=0.0, perfRisk=0.0, secuRisk=0.0, otherRisk=0.0 where asNumber=?', [name,country,RIR,asn])

    def dbGetObserved(self):
        dbCursor = self.db.cursor()
        dbCursor.execute('select asNumber, country from asn where observed=1')
        rows = dbCursor.fetchall()
        return rows

    def dbUpdateSecuRisk(self,asn, risk):
        self.db.execute(
            'update asn set secuRisk=? where asNumber=?',[risk, asn])

    def dbUpdateRiskIndex(self,asn, risk):
        self.db.execute(
            'update asn set riskIndex=? where asNumber=?',[risk, asn])


    def dbGetSecuRisks(self):
        dbCursor = self.db.cursor()
        dbCursor.execute('select secuRisk from asn where secuRisk>0')
        rows=dbCursor.fetchall()
        return rows

    def dbGetObservedRisk(self):
        dbCursor = self.db.cursor()
        dbCursor.execute('select asNumber, secuRisk, geoRisk, perfRisk, otherRisk from asn where observed=1')
        rows=dbCursor.fetchall()
        return rows


class ASnupdater:
    def __init__(self):
        self.dbname='resource/as.sqlite'

    def updateASNinfo(self):
        asList = list()
        with closing(ASRecord()) as db:
            rows = db.dbQueryUnknownCountries()
            for row in rows:
                (asn, country) = row
                asList.append(asn)
            print(asList)
            client = ip2asn()
            for result in client.lookupmany(asList, qType='ASN'):
                if not result.asn == None:
                    print(result.asn[2:], result.owner, result.cc, result.lir)
                    db.dbUpdateRecord(result.asn[2:], result.owner, result.cc, result.lir)

    def calcSecuRiskStd(self):
        riskList=list()
        with closing(ASRecord()) as db:
            rows=db.dbGetSecuRisks()
        for row in rows:
            (risk)=row
            riskList.append(risk)
        riskArray = np.asarray(riskList)
        stdRisk=np.std(riskArray)
        return stdRisk


    def calcRiskIndex(self):
        stdRisk = self.calcSecuRiskStd()
        riskList = list()
        with closing(ASRecord()) as db:
            rows = db.dbGetObservedRisk()
            for row in rows:
                (asn, secuRisk, geoRisk, perfRisk, otherRisk) = row
                db.dbUpdateRiskIndex(asn, secuRisk/stdRisk*0.5+geoRisk*0.5 )

if __name__ == '__main__':
    asnUpdater=ASnupdater()
    asnUpdater.updateASNinfo()
#    asnUpdater.getSecuRisk()
    asnUpdater.calcRiskIndex()

