from flagger import Flagger
import sqlite3


class RiskFlagger(Flagger):
    def __init__(self,dbcursor):

        self.dbCursor = dbcursor

    def prepare(self, route):
        route = super(RiskFlagger, self).flag(route)
        if 'risk' not in route.flags:
            route.flags['risk'] = []
        return route

    def flag(self, route):
        if not (route.message == 'announce'):
            return route
        self.prepare(route)
        #We assume risk is the maximulm risk of the path
        maxRisk=0.0;
        for asn in route.fields['asPath']:
            self.dbCursor.execute('select riskIndex from asn where asNumber=?', [asn])
            res = self.dbCursor.fetchone()
            if res is not None:
                [risk] = res
                if risk > maxRisk:
                    maxRisk=risk
        route.flags['risk']=maxRisk
        return route
