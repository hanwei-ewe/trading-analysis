from bisect import bisect_left, bisect_right, insort
from collections import defaultdict

import pandas as pd

from ...indicators import add_indicators
from ...analysis import analyze
from ...data import parse_timeframe
from .checks import _warmup_bars


def _prep(df, cfg):
    return add_indicators(df, cfg)


def _pivot_schedule(df, lookback):
    window = 2 * lookback + 1
    high = df["high"]
    low = df["low"]
    roll_high = high.rolling(window, center=True).max()
    roll_low = low.rolling(window, center=True).min()
    highs = defaultdict(list)
    lows = defaultdict(list)
    n = len(df)
    for j in range(n):
        confirm = j + lookback
        if confirm >= n:
            break
        rh = roll_high.iloc[j]
        rl = roll_low.iloc[j]
        if rh == rh and high.iloc[j] >= rh:
            highs[confirm].append(float(high.iloc[j]))
        if rl == rl and low.iloc[j] <= rl:
            lows[confirm].append(float(low.iloc[j]))
    return highs, lows


def _evaluate_frame(ind, cfg, active, timeframe, htf_checks_by_pos=None):
    n = len(ind)
    warm = _warmup_bars(cfg)
    if n <= warm:
        return []
    highs_by, lows_by = _pivot_schedule(ind, cfg["swings"]["lookback"])
    highs = []
    lows = []
    rows = []
    for i in range(warm, n):
        for level in highs_by.get(i, ()):
            insort(highs, level)
        for level in lows_by.get(i, ()):
            insort(lows, level)

        price = float(ind["close"].iloc[i])
        atr_v = float(ind["atr"].iloc[i])
        idx = bisect_right(highs, price)
        resistance = highs[idx] if idx < len(highs) else price + 2.0 * atr_v
        idx = bisect_left(lows, price) - 1
        support = lows[idx] if idx >= 0 else price - 2.0 * atr_v

        htf = (htf_checks_by_pos or {}).get(i)
        res = analyze(
            ind,
            cfg,
            ind=ind,
            active=active,
            timeframe=timeframe,
            htf_checks=htf,
            at=i,
            support=support,
            resistance=resistance,
        )
        rows.append(
            (
                i,
                {
                    "bias": res["bias"],
                    "signal": res["signal"],
                    "score": res["score"],
                    "max_score": res["max_score"],
                    "confidence": res["confidence"],
                },
            )
        )
    return rows


def _bias_frame(df, cfg, active, timeframe):
    ind = _prep(df, cfg)
    step = parse_timeframe(timeframe)
    rows = []
    for i, res in _evaluate_frame(ind, cfg, active, timeframe):
        rows.append(
            {
                "close_time": ind.index[i] + pd.Timedelta(seconds=step),
                "bias": res["bias"],
                "score": res["score"],
                "max_score": res["max_score"],
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values("close_time").drop_duplicates("close_time", keep="last")
    return out


def _align_bias(close_times, bias):
    base = pd.DataFrame({"close_time": close_times})
    return pd.merge_asof(base, bias, on="close_time", direction="backward")


def _htf_check_map(primary_ind, cfg, active, frames, primary_tf):
    step = parse_timeframe(primary_tf)
    close_times = primary_ind.index + pd.Timedelta(seconds=step)
    out = {i: [] for i in range(len(primary_ind))}
    for htf, hdf in frames:
        bias = _bias_frame(hdf, cfg, active, htf)
        if bias.empty:
            continue
        aligned = _align_bias(close_times, bias)
        biases = aligned["bias"].tolist()
        scores = aligned["score"].tolist()
        max_scores = aligned["max_score"].tolist()
        for i, state in enumerate(biases):
            if pd.isna(state):
                continue
            vote = 1 if state == "LONG" else (-1 if state == "SHORT" else 0)
            out[i].append(
                {
                    "id": f"htf_{htf}",
                    "label": f"Higher timeframe ({htf}) bias",
                    "vote": vote,
                    "weight": vote,
                    "reading": (
                        f"{htf} reads {state} "
                        f"(score {int(scores[i]):+d}/{int(max_scores[i])})"
                    ),
                }
            )
    return {i: checks for i, checks in out.items() if checks}


def _regime_map(htf_by_pos, regime_tf):
    key = f"htf_{regime_tf}"
    out = {}
    for i, checks in htf_by_pos.items():
        for check in checks:
            if check["id"] == key:
                if check["vote"] > 0:
                    out[i] = "LONG"
                elif check["vote"] < 0:
                    out[i] = "SHORT"
                else:
                    out[i] = "NEUTRAL-FLAT"
                break
    return out


def _regime_allows(regime_bias, side, mode):
    if mode == "none":
        return True
    if regime_bias is None:
        return False
    if mode == "loose":
        return regime_bias == "NEUTRAL-FLAT" or regime_bias == side
    return regime_bias == side

