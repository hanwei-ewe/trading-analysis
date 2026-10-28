import math
from abc import abstractmethod

from ....core import Registry
from .base import Mode


TREND_FILTERS = Registry("DCA trend filter")


class TrendFilter(Mode):
    requires_ema = False

    @abstractmethod
    def allows(self, prev_close, prev_ema):
        raise NotImplementedError


@TREND_FILTERS.register
class NoTrendFilter(TrendFilter):
    id = "none"
    label = "No trend filter"
    description = "Allow buys regardless of trend"

    def allows(self, prev_close, prev_ema):
        return True


@TREND_FILTERS.register
class EMA200TrendFilter(TrendFilter):
    id = "ema200"
    label = "EMA trend filter"
    description = "Only buy when the previous close is above the EMA"
    requires_ema = True

    def allows(self, prev_close, prev_ema):
        return math.isfinite(prev_ema) and prev_close > prev_ema


def get_trend_filter(mode_id):
    try:
        return TREND_FILTERS.get(mode_id)
    except KeyError as err:
        choices = ", ".join(TREND_FILTERS.ids())
        raise ValueError(f"trend_filter must be one of: {choices}") from err
