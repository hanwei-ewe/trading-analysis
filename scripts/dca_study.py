import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd

from trading_analysis.strategies.backtest import run_backtest
from trading_analysis.config import load_config
from trading_analysis.data import load_history
from trading_analysis.strategies.dca import run_dca
from trading_analysis.data import get_adapter
from trading_analysis.analytics.portfolio import blend_curves, curve_metrics

FIB = [0.236, 0.382, 0.5, 0.618, 0.786]
FIXED = [0.1, 0.2, 0.3, 0.4, 0.5]
CHECKS = ["regime", "rsi", "vwap", "bollinger", "adx", "obv"]
OVERRIDES = {"indicators": {"rsi": 21}}
WINDOWS = {
    "5y": ("2021-10-21", "2026-10-20"),
    "test": ("2024-10-20", "2026-10-20"),
}


def normalize(weights):
    total = sum(weights)
    return [weight / total for weight in weights]


DCA_CONFIGS = {
    "fib_deep_retrace50": {
        "level_mode": "fib",
        "levels": FIB,
        "allocations": [0.05, 0.1, 0.15, 0.25, 0.45],
        "target_mode": "retrace",
        "target_retrace": 0.5,
        "reference_mode": "anchor",
        "trend_filter": "ema200",
        "reinvest_pct": 0.5,
    },
    "fib_fib_retrace50": {
        "level_mode": "fib",
        "levels": FIB,
        "allocations": normalize(FIB),
        "target_mode": "retrace",
        "target_retrace": 0.5,
        "reference_mode": "anchor",
        "trend_filter": "ema200",
        "reinvest_pct": 0.5,
    },
    "fib_equal_retrace50": {
        "level_mode": "fib",
        "levels": FIB,
        "allocations": [0.2] * 5,
        "target_mode": "retrace",
        "target_retrace": 0.5,
        "reference_mode": "anchor",
        "trend_filter": "ema200",
        "reinvest_pct": 0.5,
    },
    "fib_deep_percent15": {
        "level_mode": "fib",
        "levels": FIB,
        "allocations": [0.05, 0.1, 0.15, 0.25, 0.45],
        "target_mode": "percent",
        "profit_target": 0.15,
        "reference_mode": "anchor",
        "trend_filter": "ema200",
        "reinvest_pct": 0.5,
    },
    "fixed_deep_percent15": {
        "level_mode": "fixed",
        "levels": FIXED,
        "allocations": [0.05, 0.1, 0.15, 0.25, 0.45],
        "target_mode": "percent",
        "profit_target": 0.15,
        "reference_mode": "anchor",
        "trend_filter": "ema200",
        "reinvest_pct": 0.5,
    },
}


def main():
    cfg = load_config()
    adapter = get_adapter(cfg["exchange"]["market_type"])
    cache = cfg["paths"]["cache"]

    def load(symbol):
        return load_history(adapter, symbol, "4h", 1900, cache_dir=cache, use_cache=True)

    def trend_curve(df, symbol, start, end, risk_pct):
        result = run_backtest(
            symbol=symbol,
            df=df,
            adapter=adapter,
            timeframe="4h",
            days=1900,
            checks=CHECKS,
            indicator_overrides=OVERRIDES,
            long_only=True,
            risk_pct=risk_pct,
            target_r=4.0,
            stop_mult=2.0,
            use_mtf=True,
            window_start=start,
            window_end=end,
        )
        return result["equity_curve"], result["metrics"]

    rows = []
    started = time.time()
    for symbol in ("ETH/USDT", "BTC/USDT"):
        df = load(symbol)
        for window, (start, end) in WINDOWS.items():
            start_ts = pd.Timestamp(start, tz="UTC")
            end_ts = pd.Timestamp(end, tz="UTC")
            for name, dca_config in DCA_CONFIGS.items():
                dca_df = df[(df.index >= start_ts - pd.Timedelta(days=30)) & (df.index < end_ts)]
                dca_curve = run_dca(
                    dca_df,
                    initial_capital=1000.0,
                    include_curve=True,
                    allow_reentry=True,
                    **dca_config,
                )["equity_curve"]
                for weight in (0.0, 0.25, 0.5, 0.75, 1.0):
                    if weight == 1.0:
                        combined = blend_curves([dca_curve], [1.0])
                    else:
                        trend, _ = trend_curve(df, symbol, start, end, 1.0 / (1.0 - weight))
                        combined = blend_curves([trend, dca_curve], [1.0 - weight, weight])
                    metrics = curve_metrics(combined, periods_per_year=365.25 * 24 * 3600 / 14400)
                    rows.append(
                        {
                            "symbol": symbol,
                            "window": window,
                            "dca": name,
                            "dca_weight": weight,
                            "ret": round(metrics["total_return"] * 100, 2),
                            "cagr": round(metrics["cagr"] * 100, 2),
                            "dd": round(metrics["max_drawdown"] * 100, 2),
                            "calmar": round(metrics["calmar"], 2),
                            "sharpe": round(metrics["sharpe"], 2),
                            "bars": metrics["bars"],
                        }
                    )

    output = pd.DataFrame(rows)
    path = ROOT / "results" / "study_blend_dca_trend.csv"
    output.to_csv(path, index=False)
    print(f"wrote {path} in {time.time() - started:.1f}s")
    for symbol in ("ETH/USDT", "BTC/USDT"):
        for window in ("5y", "test"):
            subset = output[(output.symbol == symbol) & (output.window == window)]
            print(f"\n{symbol} {window}")
            print(subset.pivot_table(index="dca", columns="dca_weight", values="ret").to_string())
            print("DD")
            print(subset.pivot_table(index="dca", columns="dca_weight", values="dd").to_string())
            print("Calmar")
            print(subset.pivot_table(index="dca", columns="dca_weight", values="calmar").to_string())


if __name__ == "__main__":
    main()
