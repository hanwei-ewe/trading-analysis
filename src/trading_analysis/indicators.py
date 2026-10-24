import numpy as np
import pandas as pd


def sma(series, period):
    return series.rolling(period).mean()


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return pd.DataFrame(
        {"macd": macd_line, "macd_signal": signal_line, "macd_hist": hist}
    )


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


def bollinger(series, period=20, num_std=2.0):
    mid = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    width = (upper - lower) / mid
    return pd.DataFrame(
        {"bb_mid": mid, "bb_upper": upper, "bb_lower": lower, "bb_width": width}
    )


def rolling_vwap(df, period=20):
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = (typical * df["volume"]).rolling(period).sum()
    vol = df["volume"].rolling(period).sum()
    return pv / vol


def stochastic(high, low, close, k=14, d=3, smooth=3):
    lowest = low.rolling(k).min()
    highest = high.rolling(k).max()
    raw = 100.0 * (close - lowest) / (highest - lowest)
    k_line = raw.rolling(smooth).mean()
    d_line = k_line.rolling(d).mean()
    return pd.DataFrame({"stoch_k": k_line, "stoch_d": d_line})


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


def obv(close, volume):
    direction = np.sign(close.diff()).fillna(0.0)
    return (direction * volume).cumsum()


def add_indicators(df, cfg):
    ind = cfg["indicators"]
    out = df.copy()
    for period in ind["ema"]:
        out[f"ema_{period}"] = ema(out["close"], period)
    out["rsi"] = rsi(out["close"], ind["rsi"])
    out = out.join(macd(out["close"], *ind["macd"]))
    out["atr"] = atr(out["high"], out["low"], out["close"], ind["atr"])
    out = out.join(bollinger(out["close"], *ind["bollinger"]))
    out["vol_ma"] = out["volume"].rolling(ind["volume_ma"]).mean()
    out["vwap"] = rolling_vwap(out, ind.get("vwap", ind["volume_ma"]))
    return out
