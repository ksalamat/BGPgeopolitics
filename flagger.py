from abc import ABCMeta, abstractmethod

class Flagger(metaclass=ABCMeta):
    @abstractmethod
    def flag(self, route):
        return route
