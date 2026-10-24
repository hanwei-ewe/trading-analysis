import copy
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from trading_analysis.config import load_config
from trading_analysis.reporting.params import review

CFG = load_config()


def _cfg(**indicator_overrides):
    cfg = copy.deepcopy(CFG)
    cfg["indicators"].update(indicator_overrides)
    return cfg


def _levels(findings):
    return {f["level"] for f in findings}


def test_defaults_are_clean():
    result = review(CFG)
    assert result["errors"] == 0
    assert result["findings"] == []


def test_ema_order_is_an_error():
    result = review(_cfg(ema=[200, 50, 20]))
    assert result["errors"] >= 1
    assert "error" in _levels(result["findings"])


def test_macd_fast_slower_than_slow_is_an_error():
    result = review(_cfg(macd=[26, 12, 9]))
    assert any(f["scope"] == "MACD" and f["level"] == "error" for f in result["findings"])


def test_macd_duplicating_emas_warns():
    result = review(_cfg(ema=[12, 26, 200], macd=[12, 26, 9]))
    assert any(f["level"] == "warning" for f in result["findings"])


def test_bollinger_std_error():
    result = review(_cfg(bollinger=[20, 0.0]))
    assert any(f["scope"] == "Bollinger" and f["level"] == "error" for f in result["findings"])


def test_stoch_d_ge_k_warns():
    result = review(_cfg(stoch=[3, 14, 3]))
    assert any(f["scope"] == "Stochastic" and f["level"] == "warning" for f in result["findings"])


def test_insufficient_history_is_an_error():
    result = review(CFG, timeframe="1w", candles=10)
    assert any(f["scope"] == "History" and f["level"] == "error" for f in result["findings"])


def main():
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as err:
                failures += 1
                print(f"FAIL {name}: {err}")
    if failures:
        raise SystemExit(1)
    print("all tests passed")


if __name__ == "__main__":
    main()
