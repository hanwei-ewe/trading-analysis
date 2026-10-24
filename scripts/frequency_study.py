import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from src.backtest import run_backtest
from src.config import load_config
from src.data import load_history
from src.dca import run_dca
from src.exchange import get_adapter
from src.portfolio import curve_metrics

CHECKS = ["regime", "rsi", "vwap", "bollinger", "adx", "obv"]
OVERRIDES = {"indicators": {"rsi": 21}}
START = pd.Timestamp("2024-10-24", tz="UTC")
END = pd.Timestamp("2026-10-20", tz="UTC")


def main():
    cfg = load_config()
    adapter = get_adapter(cfg["exchange"]["market_type"])
    rows = []
    for symbol in ("ETH/USDT", "BTC/USDT"):
        df = load_history(
            adapter, symbol, "15m", 730, cache_dir=cfg["paths"]["cache"], use_cache=True
        )
        print(symbol, "15m", len(df), df.index[0], df.index[-1])
        for stop, target in ((2.0, 4.0), (1.5, 3.0)):
            started = time.time()
            result = run_backtest(
                symbol=symbol,
                timeframe="15m",
                checks=CHECKS,
                indicator_overrides=OVERRIDES,
                use_mtf=True,
                target_mode="rr",
                target_r=target,
                stop_mult=stop,
                long_only=True,
                risk_pct=1.0,
                df=df,
                window_start=START,
                window_end=END,
            )
            metrics = result["metrics"]
            print(
                "trend",
                stop,
                target,
                round(metrics["total_return"] * 100, 2),
                round(metrics["max_drawdown"] * 100, 2),
                metrics["trades"],
                "wall",
                round(time.time() - started, 1),
            )
            rows.append(
                {
                    "symbol": symbol,
                    "strategy": f"trend_{stop}x_{target}R",
                    "ret": metrics["total_return"] * 100,
                    "dd": metrics["max_drawdown"] * 100,
                    "n": metrics["trades"],
                    "calmar": metrics.get("calmar", 0),
                }
            )

        dca_df = df[(df.index >= START - pd.Timedelta(days=7)) & (df.index < END)]
        for mode in ("fixed", "fib", "trend_fib"):
            for target in (0.01, 0.02, 0.05):
                started = time.time()
                result = run_dca(
                    dca_df,
                    initial_capital=1000.0,
                    level_mode=mode,
                    swing_lookback=96,
                    reference_mode="rolling",
                    reference_lookback=96,
                    profit_target=target,
                    target_mode="percent",
                    reinvest_pct=0.5,
                    trend_filter="ema200",
                    include_curve=True,
                )
                curve = pd.Series(
                    [row["total_wealth"] for row in result["equity_curve"]],
                    index=pd.DatetimeIndex([row["time"] for row in result["equity_curve"]]),
                )
                metrics = curve_metrics(curve)
                print(
                    "dca",
                    mode,
                    target,
                    round(metrics["total_return"] * 100, 2),
                    round(metrics["max_drawdown"] * 100, 2),
                    result["buys"],
                    result["sells"],
                    result["open_lot_count"],
                    "wall",
                    round(time.time() - started, 1),
                )
                rows.append(
                    {
                        "symbol": symbol,
                        "strategy": f"dca_{mode}_{int(target * 100)}pct",
                        "ret": metrics["total_return"] * 100,
                        "dd": metrics["max_drawdown"] * 100,
                        "n": result["buys"],
                        "calmar": metrics["calmar"],
                        "buys": result["buys"],
                        "sells": result["sells"],
                        "open": result["open_lot_count"],
                    }
                )

    output = pd.DataFrame(rows)
    path = ROOT / "results" / "study_15m_sr.csv"
    output.to_csv(path, index=False)
    print(f"wrote {path}")
    print(output.to_string(index=False))


if __name__ == "__main__":
    main()
