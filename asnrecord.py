import sqlite3
from contextlib import closing

class ASRecord( object ):
    def __init__( self, dbname='resources/as.sqlite' ):
        self.dbname = dbname
        self.db = sqlite3.connect(self.dbname)

    def close( self ):
        self.db.commit()
        self.db.close()

    def dbSetObserved(self,asn):
        self.db.execute('update asn set observed= 1 where asNumber=? and observed=0', [asn])

    def dbQueryCountryRisk( self, asn ):
        dbCursor = self.db.cursor()
        dbCursor.execute('select asNumber, country, riskIndex, geoRisk, perfRisk, secuRisk, otherRisk,observed from asn where asNumber=?',
                         [asn])
        res = dbCursor.fetchone()
        if res is not None:
            (network, country, riskIndex, geoRisk, perfRisk, secuRisk, otherRisk, observed) = res
            if observed == 0:
                self.dbSetObserved(asn)
            return [network, country, riskIndex, geoRisk, perfRisk, secuRisk, otherRisk]
        else:
            self.db.execute(
                'insert into asn (asNumber, riskIndex, geoRisk, perfRisk, secuRisk, otherRisk,observed)  values(?,0.0,0.0,0.0,0.0,0.0,1)', [asn])
            return None

    def dbQueryUnknownCountries(self):
        dbCursor = self.db.cursor()
        dbCursor.execute('select asNumber,country from asn where country is null and name is null')
        rows = dbCursor.fetchall()
        return rows

    def dbUpdateRecord(self,asn,name, country,RIR):
        self.db.execute(
            'update asn set name=?, country=?, RIR=?, riskIndex=0.0, geoRisk=0.0, perfRisk=0.0, secuRisk=0.0, otherRisk=0.0 where asNumber=?', [name,country,RIR,asn])


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

    def dbGetObserved(self):
        dbCursor = self.db.cursor()
        dbCursor.execute('select asNumber, country, secuRisk, geoRisk, perfRisk, otherRisk from asn where observed=1')
        rows=dbCursor.fetchall()
        return rows
