from asnrecord import ASRecord
from cymru.ip2asn.dns import DNSClient as ip2asn
import api
import bgpranking_web
import numpy as np
from contextlib import closing

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
        with closing(ASRecord()) as db:
            rows = db.dbGetObserved()
            for row in rows:
                (asn, country, secuRisk, geoRisk, perfRisk, otherRisk) = row
                db.dbUpdateRiskIndex(asn, secuRisk/stdRisk*0.5+geoRisk*0.5 )

if __name__ == '__main__':
    asnUpdater=ASnupdater()
    asnUpdater.updateASNinfo()
#    asnUpdater.getSecuRisk()
    asnUpdater.calcRiskIndex()

