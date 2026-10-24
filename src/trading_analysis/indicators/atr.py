import pandas as pd

from .base import INDICATORS, Indicator


def atr(high, low, close, period=14):
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


@INDICATORS.register
class ATRIndicator(Indicator):
    id = "atr"
    label = "ATR"
    description = "Average True Range"

    def compute(self, frame, params):
        value = atr(frame["high"], frame["low"], frame["close"], int(params))
        return pd.DataFrame({"atr": value})

    def warmup(self, params):
        return int(params)
