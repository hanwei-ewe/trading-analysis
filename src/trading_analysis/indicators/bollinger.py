import pandas as pd

from .base import INDICATORS, ChartSpec, Indicator, IndicatorKind


def bollinger(series, period=20, num_std=2.0):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    width = (upper - lower) / mid
    return pd.DataFrame(
        {"bb_mid": mid, "bb_upper": upper, "bb_lower": lower, "bb_width": width}
    )


def _params(params):
    values = tuple(float(value) for value in params)
    return int(values[0]), values[1]


@INDICATORS.register
class BollingerIndicator(Indicator):
    id = "bollinger"
    label = "Bollinger Bands"
    description = "Bollinger Bands and width"
    kind = IndicatorKind.OVERLAY

    def compute(self, frame, params):
        period, num_std = _params(params)
        return bollinger(frame["close"], period, num_std)

    def warmup(self, params):
        return _params(params)[0]

    def chart(self, frame, params, limit):
        period, num_std = _params(params)
        values = bollinger(frame["close"], period, num_std).tail(limit)
        return ChartSpec(
            series={
                "bb_upper": values["bb_upper"],
                "bb_mid": values["bb_mid"],
                "bb_lower": values["bb_lower"],
            }
        )
