from asnrecord import ASRecord
from flagger import Flagger
from asnupdater import ASnupdater
from contextlib import closing


class GeoFlagger(Flagger):

    def __init__(self):
        self.countrytable = {}
        asnUpdater=ASnupdater()
        with closing(ASRecord()) as db:
            rows = db.dbGetObserved()
            for row in rows:
                (asn, country, secuRisk, geoRisk, perfRisk, otherRisk) = row
                self.countrytable[asn] = [country, secuRisk, geoRisk, perfRisk, otherRisk]
            self.stdRisk = asnUpdater.calcSecuRiskStd()

    def prepare(self, route):
        route = super(GeoFlagger, self).flag(route)
        if 'geoPath' not in route.flags:
            route.flags['geoPath'] = []
        if 'risk' not in route.flags:
            route.flags['risk'] = []
        return route

    def fusionRisks(self, geoRisk, perfRisk, secuRisk, otherRisk):
        return secuRisk/self.stdRisk*0.5+geoRisk*0.5

    def flag(self, route):
        if not (route.message == 'announce'):
            return route
        self.prepare(route)
        maxRisk=0.0
        for asn in route.fields['asPath']:
            if isinstance(asn, list):
                sublist=[]
                for subasn in asn:
                    if int(subasn) not in self.countrytable.keys():
                        with closing(ASRecord()) as db:
                            res = db.dbQueryCountryRisk(subasn)
                        if res is None:
                            country = '??'
                            geoRisk = 0.0
                            perfRisk = 0.0
                            secuRisk = 0.0
                            otherRisk = 0.0
                        else:
                            [network, country, riskIndex, geoRisk, perfRisk, secuRisk, otherRisk] = res
                    else:
                        [country, secuRisk, geoRisk, perfRisk, otherRisk] = self.countrytable[int(subasn)]
                    if country is None:
                        country = '??'
                    risk = self.fusionRisks(geoRisk, perfRisk, secuRisk, otherRisk)
                    if risk > maxRisk:
                        maxRisk = risk
                    sublist.append(country)
                route.flags['geoPath'].append(sublist)
            else:
                if int(asn) not in self.countrytable.keys():
                    with closing(ASRecord()) as db:
                        res = db.dbQueryCountryRisk(asn)
                    if res is None:
                        country = '??'
                        geoRisk = 0.0
                        perfRisk = 0.0
                        secuRisk = 0.0
                        otherRisk = 0.0
                    else:
                        [network, country, riskIndex, geoRisk, perfRisk, secuRisk, otherRisk]= res
                else:
                    [country, secuRisk, geoRisk, perfRisk, otherRisk] = self.countrytable[int(asn)]
                if country is None:
                    country = '??'
                risk = self.fusionRisks(geoRisk, perfRisk, secuRisk, otherRisk)
                if risk > maxRisk:
                    maxRisk = risk
                route.flags['geoPath'].append(country)
        route.flags['risk'] = maxRisk
        return route
