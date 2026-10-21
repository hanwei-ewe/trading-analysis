import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src.walkforward import (
    fold_windows,
    run_walk_forward,
    summarize_trades,
)


def _df(n=1500):
    rng = np.random.default_rng(3)
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
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


def test_fold_windows_are_disjoint():
    start = pd.Timestamp("2024-01-01", tz="UTC")
    windows = fold_windows(start, start + pd.Timedelta(days=100), 40, 20, 20)
    assert len(windows) == 3
    assert windows[0][1] == start + pd.Timedelta(days=40)
    assert windows[0][2] == windows[1][1]
    assert windows[1][2] == windows[2][1]
    assert windows[-1][2] == start + pd.Timedelta(days=100)


def test_fold_windows_empty_when_too_short():
    start = pd.Timestamp("2024-01-01", tz="UTC")
    assert fold_windows(start, start + pd.Timedelta(days=30), 40, 20, 20) == []


def test_summarize_trades_uses_entry_window():
    trades = [
        {"entry_time": "2024-01-02", "r_multiple": 2.0},
        {"entry_time": "2024-01-03", "r_multiple": -1.0},
        {"entry_time": "2024-01-04", "r_multiple": 3.0},
    ]
    summary = summarize_trades(trades, "2024-01-01", "2024-01-04")
    assert summary["trades"] == 2
    assert summary["total_r"] == 1.0
    assert summary["win_rate"] == 0.5
    assert summary["profit_factor"] == 2.0


def test_walk_forward_runs_offline():
    result = run_walk_forward(
        timeframe="1h",
        symbol="BTC/USDT",
        days=65,
        train_days=10,
        test_days=10,
        step_days=10,
        min_train_trades=1,
        use_mtf=False,
        stop_mults=(1.0,),
        target_rs=(2.0,),
        df=_df(),
    )
    assert result["symbol"] == "BTC/USDT"
    assert len(result["folds"]) == 4
    assert result["oos"]["trades"] >= 0
    assert result["fixed_1x_2r"]["trades"] >= 0
    assert result["fixed_2x_3r"]["trades"] == 0
    assert result["step_days"] == 10
