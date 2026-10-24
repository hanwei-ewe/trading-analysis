import pandas as pd

from .base import INDICATORS, ChartSpec, Indicator, IndicatorKind


def stochastic(high, low, close, k=14, d=3, smooth=3):
    lowest = low.rolling(k).min()
    highest = high.rolling(k).max()
    raw = 100.0 * (close - lowest) / (highest - lowest)
    k_line = raw.rolling(smooth).mean()
    d_line = k_line.rolling(d).mean()
    return pd.DataFrame({"stoch_k": k_line, "stoch_d": d_line})


def _params(params):
    values = tuple(int(value) for value in params)
    return values[0], values[1], values[2]


@INDICATORS.register
class StochasticIndicator(Indicator):
    id = "stoch"
    label = "Stochastic"
    description = "Stochastic oscillator"
    kind = IndicatorKind.OSCILLATOR

    def compute(self, frame, params):
        return stochastic(
            frame["high"], frame["low"], frame["close"], *_params(params)
        )

    def warmup(self, params):
        return sum(_params(params))

    def chart(self, frame, params, limit):
        values = stochastic(
            frame["high"], frame["low"], frame["close"], *_params(params)
        ).tail(limit)
        return ChartSpec(
            series={"k": values["stoch_k"], "d": values["stoch_d"]},
            levels=(80.0, 20.0),
            fixed_range=(0.0, 100.0),
        )
