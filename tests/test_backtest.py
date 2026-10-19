import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src.analysis import analyze
from src.backtest import (
    ALL_CHECKS,
    _align_bias,
    _exit_check,
    _fill,
    _parse_checks,
    _pivot_schedule,
    _prep,
    run_backtest,
)
from src.config import load_config

CFG = load_config()


def _df(n=1500, freq="h", seed=3):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC")
    trend = np.sin(np.arange(n) / 90.0) * 8.0 + np.arange(n) * 0.01
    close = 100.0 + trend + rng.normal(0.0, 1.0, n)
    return pd.DataFrame(
        {
            "open": close + rng.normal(0.0, 0.3, n),
            "high": close + 1.5,
            "low": close - 1.5,
            "close": close,
            "volume": rng.uniform(500.0, 1500.0, n),
        },
        index=idx,
    )


def test_parse_checks():
    assert _parse_checks("default") == [
        "regime",
        "ema_position",
        "bollinger",
        "vwap",
        "rsi",
    ]
    assert set(_parse_checks("all")) == set(ALL_CHECKS)
    assert _parse_checks("rsi, macd") == ["rsi", "macd"]
    try:
        _parse_checks("rsi,nope")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown check should raise")


def test_pivot_is_confirmed_after_lookback():
    idx = pd.date_range("2024-01-01", periods=40, freq="h", tz="UTC")
    high = np.full(40, 10.0)
    low = np.full(40, 9.0)
    high[10] = 20.0
    low[10] = 8.0
    df = pd.DataFrame(
        {"open": 9.5, "high": high, "low": low, "close": 9.5, "volume": 1.0},
        index=idx,
    )
    highs, lows = _pivot_schedule(df, 3)
    assert 13 in highs and max(highs[13]) == 20.0
    assert 13 in lows and min(lows[13]) == 8.0
    assert all(20.0 not in prices for key, prices in highs.items() if key < 13)


def test_align_bias_uses_only_completed_htf_bars():
    bias = pd.DataFrame(
        {
            "close_time": pd.to_datetime(
                ["2024-01-01T04:00Z", "2024-01-01T08:00Z"]
            ),
            "bias": ["LONG", "SHORT"],
            "score": [3, -3],
            "max_score": [5, 5],
        }
    )
    base = pd.to_datetime(
        [
            "2024-01-01T03:00Z",
            "2024-01-01T04:00Z",
            "2024-01-01T05:00Z",
            "2024-01-01T08:00Z",
        ]
    )
    aligned = _align_bias(base, bias)
    assert pd.isna(aligned["bias"].iloc[0])
    assert aligned["bias"].iloc[1] == "LONG"
    assert aligned["bias"].iloc[2] == "LONG"
    assert aligned["bias"].iloc[3] == "SHORT"


def test_fill_direction_and_slippage():
    assert _fill(100.0, "LONG", 0.01, True) == 101.0
    assert _fill(100.0, "LONG", 0.01, False) == 99.0
    assert _fill(100.0, "SHORT", 0.01, True) == 99.0
    assert _fill(100.0, "SHORT", 0.01, False) == 101.0


def test_stop_wins_when_both_levels_hit():
    long_pos = {"side": "LONG", "stop": 95.0, "target": 105.0}
    raw, reason = _exit_check(long_pos, 100.0, 110.0, 90.0)
    assert raw == 95.0 and reason == "stop"

    short_pos = {"side": "SHORT", "stop": 105.0, "target": 95.0}
    raw, reason = _exit_check(short_pos, 100.0, 110.0, 90.0)
    assert raw == 105.0 and reason == "stop"


def test_at_index_matches_sliced_frame():
    df = _df(n=400)
    ind = _prep(df, CFG)
    i = 320
    sliced = ind.iloc[: i + 1]
    left = analyze(
        sliced,
        CFG,
        ind=sliced,
        active=set(ALL_CHECKS),
        timeframe="1h",
        support=90.0,
        resistance=110.0,
    )
    row = analyze(
        ind,
        CFG,
        ind=ind,
        active=set(ALL_CHECKS),
        timeframe="1h",
        at=i,
        support=90.0,
        resistance=110.0,
    )
    assert left["bias"] == row["bias"]
    assert left["score"] == row["score"]
    assert left["max_score"] == row["max_score"]


def test_backtest_runs_offline():
    result = run_backtest(df=_df(), days=30, use_mtf=False)
    m = result["metrics"]
    assert m["trades"] == len(result["trades"])
    assert len(result["equity_curve"]) > 0
    assert np.isfinite(m["final_equity"])
    assert np.isfinite(m["total_return"])
    assert 0.0 <= m["win_rate"] <= 1.0


def test_backtest_includes_higher_frames_offline():
    df = _df()
    htf = {
        "4h": _df(n=400, freq="4h", seed=4),
        "1d": _df(n=300, freq="D", seed=5),
    }
    result = run_backtest(df=df, days=30, use_mtf=True, htf_dfs=htf)
    assert set(result["htf_frames"]) == {"4h", "1d"}
    assert result["metrics"]["trades"] == len(result["trades"])
