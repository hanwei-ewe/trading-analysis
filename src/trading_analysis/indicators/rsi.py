import pandas as pd

from .base import INDICATORS, ChartSpec, Indicator, IndicatorKind


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


@INDICATORS.register
class RSIIndicator(Indicator):
    id = "rsi"
    label = "RSI"
    description = "Relative Strength Index"
    kind = IndicatorKind.OSCILLATOR

    def compute(self, frame, params):
        return pd.DataFrame({"rsi": rsi(frame["close"], int(params))})

    def warmup(self, params):
        return int(params)

    def chart(self, frame, params, limit):
        return ChartSpec(
            series={"series": rsi(frame["close"], int(params)).tail(limit)},
            levels=(70.0, 30.0),
            fixed_range=(0.0, 100.0),
        )
