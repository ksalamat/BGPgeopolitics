from flagger import Flagger
import sqlite3
from contextlib import closing

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
        dbCursor.execute('select asNumber from asn where country is null')
        rows = dbCursor.fetchall()
        return rows


class GeoFlagger(Flagger):
    def prepare(self, route):
        route = super(GeoFlagger, self).flag(route)
        if 'geoPath' not in route.flags:
            route.flags['geoPath'] = []
        if 'risk' not in route.flags:
            route.flags['risk'] = []
        return route
        
    def flag(self, route):
        if not (route.message == 'announce'):
            return route
        self.prepare(route)
        maxRisk=0.0
        for asn in route.fields['asPath']:
            asn = asn.replace("{", "")
            asn = asn.replace("}","")
            with closing(ASRecord()) as db:
                res=db.queryCountryRisk(asn)
                db.setObserved(asn)
            if res==None:
                country='??'
                risk=0.0
            else:
                [country, risk] = res
                if risk > maxRisk:
                    maxRisk = risk
            route.flags['geoPath'].append(country)
        route.flags['risk'] = maxRisk
        return route
