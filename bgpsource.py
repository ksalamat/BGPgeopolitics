from abc import ABCMeta, abstractmethod

class BGPSource(metaclass=ABCMeta):
    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass
