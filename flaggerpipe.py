from flagger import Flagger

class FlaggerPipe(Flagger):
    def __init__(self):
        self.flaggers = []

    def append(self, flagger):
        self.flaggers.append(flagger)

    def flag(self, route):
        for flagger in self.flaggers:
            route = flagger.flag(route)
        return route
