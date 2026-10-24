import re

import pandas as pd

_UNIT_SECONDS = {"m": 60, "h": 3600, "d": 86400, "w": 604800}


def parse_timeframe(timeframe):
    match = re.match(r"^(\d+)([mhdw])$", timeframe)
    if not match:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    return int(match.group(1)) * _UNIT_SECONDS[match.group(2)]


def drop_incomplete(df, timeframe):
    if df.empty:
        return df
    seconds = parse_timeframe(timeframe)
    close_time = df.index[-1] + pd.Timedelta(seconds=seconds)
    now = pd.Timestamp.now(tz="UTC")
    return df.iloc[:-1] if now < close_time else df

