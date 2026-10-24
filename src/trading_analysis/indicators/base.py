from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

import pandas as pd

from ..core import Registry


class IndicatorKind(str, Enum):
    OVERLAY = "overlay"
    OSCILLATOR = "oscillator"
    FEATURE = "feature"


@dataclass(frozen=True)
class ChartSpec:
    series: Mapping[str, pd.Series] = field(default_factory=dict)
    levels: tuple[float, ...] = ()
    fixed_range: tuple[float, float] | None = None


class Indicator(ABC):
    id: str = ""
    label: str = ""
    description: str = ""
    kind: IndicatorKind = IndicatorKind.FEATURE
    outputs: tuple[str, ...] = ()

    @abstractmethod
    def compute(self, frame: pd.DataFrame, params: Any) -> pd.DataFrame:
        raise NotImplementedError

    def warmup(self, params: Any) -> int:
        return 0

    def chart(self, frame: pd.DataFrame, params: Any, limit: int) -> ChartSpec | None:
        return None


INDICATORS = Registry[Indicator]("indicator")
