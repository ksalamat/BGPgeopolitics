import asnrecord
from flagger import Flagger
from contextlib import closing
from asnupdater import calcSecuRiskStd



class GeoFlagger(Flagger):

    def __init__(self):
        self.countrytable={}
        with closing(ASRecord()) as db:
            rows = db.dbGetObserved()
            for row in rows:
                (asn, country, secuRisk, geoRisk, perfRisk, otherRisk) = row
                self.countrytable[asn] = [country, secuRisk, geoRisk, perfRisk, otherRisk]
            self.stdRisk = calcSecuRiskStd()


    def prepare(self, route):
        route = super(GeoFlagger, self).flag(route)
        if 'geoPath' not in route.flags:
            route.flags['geoPath'] = []
        if 'risk' not in route.flags:
            route.flags['risk'] = []
        return route

    def fusion(self, geoRisk, perfRisk, secuRisk, otherRisk):
        return secuRisk/self.stdRisk*0.5+geoRisk*0.5

        
    def flag(self, route):
        if not (route.message == 'announce'):
            return route
        self.prepare(route)
        maxRisk=0.0
        for asn in route.fields['asPath']:
            asn = asn.replace("{", "")
            asn = asn.replace("}", "")
            if asn not in self.countrytable.keys():
                with closing(ASRecord()) as db:
                    res = db.dbQueryCountryRisk(asn)
                if res == None:
                    country = '??'
                    geoRisk = 0.0
                    perfRisk = 0.0
                    secuRisk = 0.0
                    otherRisk = 0.0
                else:
                    [network, country, riskIndex, geoRisk, perfRisk, secuRisk, otherRisk]= res
            else:
                [country, secuRisk, geoRisk, perfRisk, otherRisk] = self.countrytable[asn]
            risk = self.fusionRisks(geoRisk, perfRisk, secuRisk, otherRisk)
            if risk > maxRisk:
                maxRisk = risk
            route.flags['geoPath'].append(country)
        route.flags['risk'] = maxRisk
        return route
