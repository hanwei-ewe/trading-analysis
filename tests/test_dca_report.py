import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src.dca_report import run_dca_report, serialize, to_markdown


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


def test_report_runs_offline_and_has_chart():
    result = run_dca_report(
        symbol="ETH/USDT",
        timeframe="4h",
        days=60,
        df=_v_shape(),
        allocation="deep",
        level_mode="fib",
        trend_filter="none",
    )
    assert result["symbol"] == "ETH/USDT"
    assert result["chart"]
    assert result["buys"] > 0
    text = to_markdown(result)
    assert "DCA ladder" in text
    assert "Total return" in text


def test_serialize_handles_timestamps():
    result = run_dca_report(
        symbol="ETH/USDT",
        timeframe="4h",
        days=60,
        df=_v_shape(),
        trend_filter="none",
    )
    payload = serialize(result)
    assert isinstance(payload["chart"][0]["time"], str)
