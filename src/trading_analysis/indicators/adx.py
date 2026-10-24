import numpy as np
import pandas as pd

from .base import INDICATORS, ChartSpec, Indicator, IndicatorKind


def adx(high, low, close, period=14):
    up = high.diff()
    down = -low.diff()
    plus_dm = pd.Series(
        np.where((up > down) & (up > 0), up, 0.0), index=high.index
    )
    minus_dm = pd.Series(
        np.where((down > up) & (down > 0), down, 0.0), index=high.index
    )
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr_ = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    plus_di = 100.0 * plus_dm.ewm(
        alpha=1.0 / period, adjust=False, min_periods=period
    ).mean() / atr_
    minus_di = 100.0 * minus_dm.ewm(
        alpha=1.0 / period, adjust=False, min_periods=period
    ).mean() / atr_
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_line = dx.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    return pd.DataFrame({"adx": adx_line, "plus_di": plus_di, "minus_di": minus_di})


@INDICATORS.register
class ADXIndicator(Indicator):
    id = "adx"
    label = "ADX"
    description = "Average Directional Index and directional indicators"
    kind = IndicatorKind.OSCILLATOR

    def compute(self, frame, params):
        return adx(frame["high"], frame["low"], frame["close"], int(params))

    def warmup(self, params):
        return int(params) * 2

    def chart(self, frame, params, limit):
        values = adx(
            frame["high"], frame["low"], frame["close"], int(params)
        ).tail(limit)
        return ChartSpec(
            series={
                "adx": values["adx"],
                "plus_di": values["plus_di"],
                "minus_di": values["minus_di"],
            },
            levels=(25.0,),
        )
