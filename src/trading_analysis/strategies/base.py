from abc import ABC, abstractmethod

from ..core import Registry


class Strategy(ABC):
    id: str = ""
    label: str = ""
    description: str = ""

    @abstractmethod
    def run(self, frame=None, **params):
        raise NotImplementedError


STRATEGIES = Registry[Strategy]("strategy")
