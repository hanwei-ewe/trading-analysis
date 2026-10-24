import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from trading_analysis.analytics.portfolio import blend_curves, curve_metrics


def _curve(values, start="2024-01-01", freq="4h"):
    index = pd.date_range(start, periods=len(values), freq=freq, tz="UTC")
    return [{"time": ts, "equity": float(value)} for ts, value in zip(index, values)]


def test_blend_equal_weights():
    a = _curve([100, 110, 120])
    b = _curve([100, 90, 100])
    combined = blend_curves([a, b], [0.5, 0.5])
    assert list(combined) == [100.0, 100.0, 110.0]


def test_blend_accepts_series():
    index = pd.date_range("2024-01-01", periods=3, freq="4h", tz="UTC")
    a = pd.Series([100.0, 110.0, 120.0], index=index)
    b = pd.Series([100.0, 90.0, 100.0], index=index)
    combined = blend_curves([a, b], [0.5, 0.5])
    assert list(combined) == [100.0, 100.0, 110.0]


def test_blend_requires_overlap():
    a = _curve([100, 110])
    b = _curve([100, 120], start="2025-01-01")
    try:
        blend_curves([a, b], [0.5, 0.5])
    except ValueError:
        pass
    else:
        raise AssertionError("non-overlapping curves should raise")


def test_curve_metrics_drawdown():
    index = pd.date_range("2024-01-01", periods=4, freq="4h", tz="UTC")
    metrics = curve_metrics(pd.Series([100.0, 120.0, 90.0, 110.0], index=index))
    assert abs(metrics["max_drawdown"] + 0.25) < 1e-9
    assert abs(metrics["total_return"] - 0.10) < 1e-9
