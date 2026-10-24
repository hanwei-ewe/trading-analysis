import pandas as pd

from .base import INDICATORS, ChartSpec, Indicator, IndicatorKind
from .ema import ema


def macd(series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame(
        {"macd": macd_line, "macd_signal": signal_line, "macd_hist": hist}
    )


def _params(params):
    values = tuple(int(value) for value in params)
    return values[0], values[1], values[2]


@INDICATORS.register
class MACDIndicator(Indicator):
    id = "macd"
    label = "MACD"
    description = "Moving Average Convergence Divergence"
    kind = IndicatorKind.OSCILLATOR

    def compute(self, frame, params):
        return macd(frame["close"], *_params(params))

    def warmup(self, params):
        fast, slow, signal = _params(params)
        return slow + signal

    def chart(self, frame, params, limit):
        values = macd(frame["close"], *_params(params)).tail(limit)
        return ChartSpec(
            series={
                "macd": values["macd"],
                "signal": values["macd_signal"],
                "hist": values["macd_hist"],
            }
        )
