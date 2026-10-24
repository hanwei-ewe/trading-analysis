import pandas as pd

from .base import INDICATORS, ChartSpec, Indicator, IndicatorKind


def rolling_vwap(df, period=20):
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = (typical * df["volume"]).rolling(period).sum()
    vol = df["volume"].rolling(period).sum()
    return pv / vol


@INDICATORS.register
class VWAPIndicator(Indicator):
    id = "vwap"
    label = "VWAP"
    description = "Rolling volume-weighted average price"
    kind = IndicatorKind.OVERLAY

    def compute(self, frame, params):
        return pd.DataFrame({"vwap": rolling_vwap(frame, int(params))})

    def warmup(self, params):
        return int(params)

    def chart(self, frame, params, limit):
        return ChartSpec(
            series={"vwap": rolling_vwap(frame, int(params)).tail(limit)}
        )
