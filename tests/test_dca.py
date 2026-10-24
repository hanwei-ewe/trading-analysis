import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src.dca import run_dca


def _v_shape(n=420):
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    close = np.full(n, 100.0)
    close[180:260] = np.linspace(100.0, 50.0, 80)
    close[260:] = np.linspace(50.0, 120.0, n - 260)
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(n, 1000.0),
        },
        index=idx,
    )


def _trend_pullback(n=420):
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    close = np.concatenate(
        [
            np.linspace(50.0, 120.0, 200),
            np.linspace(120.0, 88.0, 100),
            np.full(n - 300, 88.0),
        ]
    )
    return pd.DataFrame(
        {
            "open": close,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": np.full(n, 1000.0),
        },
        index=idx,
    )


def test_dca_buys_gaps_and_sells_targets():
    result = run_dca(
        _v_shape(),
        initial_capital=1000.0,
        levels=(0.1, 0.2, 0.3, 0.4, 0.5),
        allocations=(0.2, 0.2, 0.2, 0.2, 0.2),
        profit_target=0.1,
        reference_lookback=180,
        reinvest_pct=0.5,
        include_curve=True,
    )
    assert result["buys"] >= 5
    assert result["sells"] >= 5
    assert result["min_cash"] >= -1e-9
    assert result["final_reserve"] > 0
    assert result["total_return"] > 0
    assert result["open_lot_count"] == 0
    assert len(result["equity_curve"]) > 0


def test_dca_never_uses_leverage():
    result = run_dca(
        _v_shape(),
        initial_capital=1000.0,
        levels=(0.1, 0.2, 0.3, 0.4, 0.5),
        allocations=(0.2, 0.2, 0.2, 0.2, 0.2),
        profit_target=0.1,
        reference_lookback=180,
        reinvest_pct=1.0,
    )
    assert result["min_cash"] >= -1e-9
    assert result["max_deployed"] <= result["initial_capital"] + 1e-6


def test_dca_rejects_overallocation():
    try:
        run_dca(_v_shape(), allocations=(0.5, 0.5, 0.5))
    except ValueError:
        pass
    else:
        raise AssertionError("overallocation should raise")


def test_dca_fibonacci_levels():
    result = run_dca(
        _v_shape(),
        level_mode="fib",
        allocations=(0.2, 0.2, 0.2, 0.2, 0.2),
        reference_lookback=180,
        profit_target=0.1,
    )
    assert result["levels"] == [0.236, 0.382, 0.5, 0.618, 0.786]
    assert result["buys"] > 0
    assert result["min_cash"] >= -1e-9


def test_dca_trend_fib_uses_swing_leg():
    result = run_dca(
        _trend_pullback(),
        level_mode="trend_fib",
        swing_lookback=60,
        allocations=(0.2, 0.2, 0.2, 0.2, 0.2),
        reference_lookback=180,
        profit_target=0.1,
    )
    assert result["levels"] == [0.236, 0.382, 0.5, 0.618, 0.786]
    assert result["buys"] > 0
    assert result["min_cash"] >= -1e-9


def test_dca_geometric_levels():
    result = run_dca(
        _v_shape(),
        level_mode="geometric",
        level_base=0.10,
        allocations=(0.2, 0.2, 0.2, 0.2, 0.2),
        reference_lookback=180,
        profit_target=0.1,
    )
    expected = [1 - 0.9**n for n in range(1, 6)]
    assert all(abs(a - b) < 1e-12 for a, b in zip(result["levels"], expected))
    assert result["buys"] > 0


def test_dca_atr_levels():
    result = run_dca(
        _v_shape(),
        level_mode="atr",
        levels=(3.0, 6.0, 9.0, 12.0, 15.0),
        allocations=(0.2, 0.2, 0.2, 0.2, 0.2),
        reference_lookback=180,
        profit_target=0.1,
    )
    assert result["levels"] == [3.0, 6.0, 9.0, 12.0, 15.0]
    assert result["buys"] > 0
    assert result["min_cash"] >= -1e-9


def test_dca_retrace_target():
    result = run_dca(
        _v_shape(),
        level_mode="fixed",
        allocations=(0.2, 0.2, 0.2, 0.2, 0.2),
        reference_lookback=180,
        target_mode="retrace",
        target_retrace=0.382,
        include_curve=True,
    )
    assert result["sells"] > 0
    assert all(t["exit_price"] > t["entry_price"] for t in result["sell_trades"])


def test_dca_trend_filter_blocks_falling_knife():
    unfiltered = run_dca(
        _v_shape(),
        level_mode="fixed",
        allocations=(0.2, 0.2, 0.2, 0.2, 0.2),
        reference_lookback=180,
        trend_filter="none",
    )
    filtered = run_dca(
        _v_shape(),
        level_mode="fixed",
        allocations=(0.2, 0.2, 0.2, 0.2, 0.2),
        reference_lookback=180,
        trend_filter="ema200",
    )
    assert filtered["buys"] <= unfiltered["buys"]
