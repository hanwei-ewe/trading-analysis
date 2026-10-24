import pandas as pd

from .base import INDICATORS, Indicator


@INDICATORS.register
class VolumeMAIndicator(Indicator):
    id = "volume_ma"
    label = "Volume MA"
    description = "Simple moving average of volume"

    def compute(self, frame, params):
        return pd.DataFrame(
            {"vol_ma": frame["volume"].rolling(int(params)).mean()}
        )

    def warmup(self, params):
        return int(params)
