import pandas as pd

from ...analytics.metrics import series_metrics, trade_metrics
from ...data import parse_timeframe


def _metrics(engine, ind, timeframe, buy_hold):
    curve = engine["equity_curve"]
    trades = engine["trades"]
    initial = engine["initial_equity"]
    step = parse_timeframe(timeframe)
    periods = 365.25 * 24 * 3600 / step

    equity = pd.Series([row["equity"] for row in curve])
    equity.index = pd.DatetimeIndex([row["time"] for row in curve])
    metrics = series_metrics(
        equity,
        periods_per_year=periods,
        initial=initial,
        buy_hold=buy_hold,
    )
    trades_metrics = trade_metrics(trades)
    exposure = engine["bars_in_position"] / len(curve) if curve else 0.0
    return {
        "initial_equity": initial,
        "final_equity": metrics["final"],
        "total_return": metrics["total_return"],
        "cagr": metrics["cagr"],
        "sharpe": metrics["sharpe"],
        "sortino": metrics["sortino"],
        "max_drawdown": metrics["max_drawdown"],
        "calmar": metrics["calmar"],
        "buy_hold_return": metrics["buy_hold_return"],
        "excess_return": metrics["excess_return"],
        **trades_metrics,
        "exposure": exposure,
        "bars": len(curve),
        "start": curve[0]["time"].isoformat() if curve else None,
        "end": curve[-1]["time"].isoformat() if curve else None,
        "timeframe": timeframe,
    }


def _buy_hold(ind, start_idx, end_idx=None):
    end = len(ind) if end_idx is None else end_idx
    first = float(ind["close"].iloc[start_idx])
    last = float(ind["close"].iloc[end - 1])
    return last / first - 1.0 if first else 0.0

