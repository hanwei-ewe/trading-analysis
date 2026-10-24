from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping

import pandas as pd

from ...core import Registry


@dataclass(frozen=True)
class CheckContext:
    ind: pd.DataFrame
    cfg: Mapping[str, Any]
    pos: int
    timeframe: str
    support: float
    resistance: float
    regime: str
    ema_short: float
    ema_mid: float
    ema_long: float
    periods: tuple[int, ...]

    @property
    def row(self):
        return self.ind.iloc[self.pos]

    @property
    def price(self):
        return float(self.row["close"])

    def value(self, column, default=float("nan")):
        if column not in self.ind.columns:
            return default
        return float(self.ind[column].iloc[self.pos])


@dataclass(frozen=True)
class CheckResult:
    id: str
    label: str
    vote: int
    reading: str

    def as_dict(self):
        return {
            "id": self.id,
            "label": self.label,
            "vote": self.vote,
            "weight": self.vote,
            "reading": self.reading,
        }


class Check(ABC):
    id: str = ""

    @abstractmethod
    def evaluate(self, ctx: CheckContext) -> CheckResult | None:
        raise NotImplementedError


CHECKS = Registry[Check]("check")
