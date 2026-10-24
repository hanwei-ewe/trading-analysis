import numpy as np
import pandas as pd

from .base import INDICATORS, ChartSpec, Indicator, IndicatorKind


def obv(close, volume):
    direction = np.sign(close.diff()).fillna(0.0)
    return (direction * volume).cumsum()


@INDICATORS.register
class OBVIndicator(Indicator):
    id = "obv"
    label = "OBV"
    description = "On-Balance Volume"
    kind = IndicatorKind.OSCILLATOR

    def compute(self, frame, params):
        return pd.DataFrame({"obv": obv(frame["close"], frame["volume"])})

    def warmup(self, params):
        return int(params) + 1

    def chart(self, frame, params, limit):
        return ChartSpec(series={"series": obv(frame["close"], frame["volume"]).tail(limit)})
