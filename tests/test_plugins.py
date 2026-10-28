import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import numpy as np
import pandas as pd

from trading_analysis.analysis import CHECKS, Check, CheckResult, analyze
from trading_analysis.app.pipeline import _compute_oscillators
from trading_analysis.config import load_config
from trading_analysis.strategies import STRATEGIES
from trading_analysis.strategies.dca import (
    ALLOCATION_MODES,
    LEVEL_MODES,
    REFERENCE_MODES,
    TARGET_MODES,
    TREND_FILTERS,
    run_dca,
)
from trading_analysis.strategies.dca.levels import _target_price
from trading_analysis.strategies.dca.modes import LevelMode, TargetMode
from trading_analysis.indicators import (
    ChartSpec,
    INDICATORS,
    Indicator,
    IndicatorKind,
    add_indicators,
)


CFG = load_config()


def _df(n=260):
    rng = np.random.default_rng(11)
    idx = pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")
    close = 100.0 + np.arange(n) * 0.2 + rng.normal(0.0, 0.3, n)
    return pd.DataFrame(
        {
            "open": close - 0.1,
            "high": close + 0.8,
            "low": close - 0.8,
            "close": close,
            "volume": np.full(n, 1000.0),
        },
        index=idx,
    )


class MidpointIndicator(Indicator):
    id = "test_midpoint"
    label = "Test midpoint"

    def compute(self, frame, params):
        return pd.DataFrame({"test_midpoint": frame["close"].rolling(int(params)).mean()})

    def warmup(self, params):
        return int(params)


class TestOscillator(Indicator):
    id = "test_oscillator"
    label = "Test oscillator"
    kind = IndicatorKind.OSCILLATOR

    def compute(self, frame, params):
        return pd.DataFrame({"test_oscillator": frame["close"].diff()})

    def chart(self, frame, params, limit):
        return ChartSpec(
            series={"series": frame["close"].diff().tail(limit)},
            levels=(0.0,),
            fixed_range=(-1.0, 1.0),
        )


class HalfLevels(LevelMode):
    id = "test_half_levels"
    label = "Half level"

    def default_levels(self, n_levels, level_base):
        return (0.5,)


class OnePercentTarget(TargetMode):
    id = "test_one_percent"
    label = "One percent target"

    def price(self, fill, reference, atr, profit_target, target_retrace, target_atr):
        return fill * 1.01


class AlwaysLongCheck(Check):
    id = "test_always_long"

    def evaluate(self, ctx):
        return CheckResult(
            id=self.id,
            label="Always long",
            vote=1,
            reading="test plugin",
        )


INDICATORS.register(MidpointIndicator)
INDICATORS.register(TestOscillator)
LEVEL_MODES.register(HalfLevels)
TARGET_MODES.register(OnePercentTarget)
CHECKS.register(AlwaysLongCheck)


def test_indicator_plugin_is_discovered():
    cfg = load_config()
    cfg["indicators"]["test_midpoint"] = 5
    out = add_indicators(_df(), cfg)
    assert "test_midpoint" in out.columns
    assert out["test_midpoint"].iloc[-1] == out["test_midpoint"].iloc[-1]


def test_oscillator_plugin_builds_chart_payload():
    cfg = load_config()
    out = _compute_oscillators(
        _df(),
        cfg,
        20,
        "test_oscillator",
        14,
        12,
        26,
        9,
        14,
        3,
        3,
        14,
    )
    assert "test_oscillator" in out
    assert out["test_oscillator"]["levels"] == [0.0]
    assert out["test_oscillator"]["fixed_range"] == [-1.0, 1.0]


def _dca_df(n=420):
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


def test_dca_mode_registries_are_populated():
    assert set(LEVEL_MODES.ids()) >= {"fixed", "fib", "trend_fib", "atr", "geometric"}
    assert set(TARGET_MODES.ids()) >= {"percent", "retrace", "atr"}
    assert set(REFERENCE_MODES.ids()) >= {"anchor", "rolling", "ath"}
    assert set(ALLOCATION_MODES.ids()) >= {"equity", "fixed"}
    assert set(TREND_FILTERS.ids()) >= {"none", "ema200"}


def test_dca_level_mode_plugin_is_used():
    result = run_dca(
        _dca_df(),
        level_mode="test_half_levels",
        allocations=(1.0,),
        reference_lookback=180,
        profit_target=0.1,
    )
    assert result["levels"] == [0.5]
    assert result["buys"] > 0


def test_dca_target_mode_plugin_is_used():
    assert _target_price(
        100.0, 110.0, 0.0, "test_one_percent", 0.1, 0.382, 3.0
    ) == 101.0


def test_strategy_plugins_are_registered():
    assert set(STRATEGIES.ids()) == {"trend", "dca"}


def test_check_plugin_is_discovered():
    res = analyze(_df(), CFG, active={"test_always_long"})
    assert res["max_score"] == 1
    assert res["checks"][0]["id"] == "test_always_long"
    assert res["score"] == 1


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
