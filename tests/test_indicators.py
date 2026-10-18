import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from src import indicators as ind


def test_ema_constant_series():
    s = pd.Series([5.0] * 30)
    assert abs(float(ind.ema(s, 10).iloc[-1]) - 5.0) < 1e-9


def test_rsi_bounds_and_trend():
    s = pd.Series(np.linspace(1.0, 50.0, 100))
    r = ind.rsi(s, 14).dropna()
    assert r.between(0.0, 100.0).all()
    assert float(r.iloc[-1]) > 90.0


def test_atr_positive():
    high = pd.Series(np.linspace(10.0, 20.0, 50))
    low = high - 1.0
    close = high - 0.5
    a = ind.atr(high, low, close, 14).dropna()
    assert (a > 0).all()


def test_bollinger_width_positive():
    s = pd.Series(np.random.default_rng(0).normal(100, 2, 60))
    bb = ind.bollinger(s, 20, 2.0).dropna()
    assert (bb["bb_width"] > 0).all()


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
