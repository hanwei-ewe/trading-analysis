import pandas as pd

from .base import INDICATORS, ChartSpec, Indicator, IndicatorKind


def sma(series, period):
    return series.rolling(period).mean()


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def _periods(params):
    if isinstance(params, (list, tuple)):
        return tuple(int(value) for value in params)
    return (int(params),)


@INDICATORS.register
class EMAIndicator(Indicator):
    id = "ema"
    label = "EMA"
    description = "Exponential moving averages"
    kind = IndicatorKind.OVERLAY

    def compute(self, frame, params):
        periods = _periods(params)
        return pd.DataFrame(
            {f"ema_{period}": ema(frame["close"], period) for period in periods}
        )

    def warmup(self, params):
        return max(_periods(params))

    def chart(self, frame, params, limit):
        periods = _periods(params)
        return ChartSpec(
            series={
                f"ema_{period}": ema(frame["close"], period).tail(limit)
                for period in periods
            }
        )
