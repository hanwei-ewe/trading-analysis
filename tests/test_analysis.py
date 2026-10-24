import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from trading_analysis.analysis import _build_signal, analyze
from trading_analysis.config import load_config

CFG = load_config()


def _df(n=260, drift=0.4):
    rng = np.random.default_rng(7)
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    base = 100.0 + np.arange(n) * drift
    close = base + rng.normal(0.0, 0.3, n)
    return pd.DataFrame(
        {
            "open": close - 0.2,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": np.full(n, 1000.0),
        },
        index=idx,
    )


def test_default_active_is_core_five():
    res = analyze(_df(), CFG)
    assert res["max_score"] == 5
    assert set(res["active"]) == {"regime", "ema_position", "rsi", "macd", "vwap"}


def test_selection_limits_checks():
    res = analyze(_df(), CFG, active={"rsi", "macd"})
    assert res["max_score"] == 2
    assert set(res["active"]) == {"rsi", "macd"}


def test_no_checks_is_neutral():
    res = analyze(_df(), CFG, active=set())
    assert res["max_score"] == 0
    assert res["bias"] == "NEUTRAL-FLAT"
    assert res["confidence"] == "Low"


def test_invalidation_uses_timeframe():
    long_sig = _build_signal("LONG", 100.0, 2.0, 95.0, 110.0, CFG, "4h")
    assert long_sig is not None
    assert long_sig["invalidation"].startswith("4h close below")

    short_sig = _build_signal("SHORT", 100.0, 2.0, 95.0, 110.0, CFG, "15m")
    assert short_sig is not None
    assert short_sig["invalidation"].startswith("15m close above")


def test_score_within_active_bounds():
    for active in ({"regime", "rsi", "vwap"}, {"regime", "ema_position", "rsi", "macd", "vwap"}):
        res = analyze(_df(), CFG, active=active)
        assert abs(res["score"]) <= res["max_score"] == len(active)


def test_price_action_check_is_available():
    res = analyze(_df(), CFG, active={"pa"})
    assert res["max_score"] == 1
    assert res["checks"][0]["id"] == "pa"


def test_breakout_and_extension_checks_are_available():
    breakout = analyze(_df(), CFG, active={"breakout"})
    assert breakout["max_score"] == 1
    assert breakout["checks"][0]["id"] == "breakout"
    extension = analyze(_df(), CFG, active={"extension"})
    assert extension["max_score"] == 1
    assert extension["checks"][0]["id"] == "extension"


def test_htf_check_counts_toward_score():
    base = analyze(_df(), CFG)
    htf = [{"id": "htf_4h", "label": "x", "vote": 0, "weight": 0, "reading": "y"}]
    res = analyze(_df(), CFG, htf_checks=htf)
    assert res["max_score"] == base["max_score"] + 1
    assert any(c["id"] == "htf_4h" for c in res["checks"])


def test_opposing_htf_caps_confidence():
    strong = _df(n=260, drift=1.0)
    base = analyze(strong, CFG)
    assert base["confidence"] == "High"
    weight = -1 if base["bias"] == "LONG" else 1
    htf = [{"id": "htf_1d", "label": "HTF", "vote": weight, "weight": weight, "reading": "opposing"}]
    capped = analyze(strong, CFG, htf_checks=htf)
    assert capped["confidence"] != "High"


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
