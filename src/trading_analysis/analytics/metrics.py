import math

import numpy as np
import pandas as pd


def _safe_returns(series):
    return series.pct_change().replace([np.inf, -np.inf], np.nan).dropna()


def series_metrics(series, periods_per_year=None, initial=None, buy_hold=0.0):
    if series is None or len(series) < 2:
        raise ValueError("need at least two points")
    series = series.sort_index()
    if periods_per_year is None:
        step = (
            (series.index[-1] - series.index[0]).total_seconds()
            / (len(series) - 1)
        )
        periods_per_year = 365.25 * 24 * 3600 / step if step > 0 else 0.0
    initial = float(series.iloc[0] if initial is None else initial)
    final = float(series.iloc[-1])
    total_return = final / initial - 1.0
    years = len(series) / periods_per_year if periods_per_year else 0.0
    cagr = (
        (final / initial) ** (1.0 / years) - 1.0
        if years > 0 and final > 0
        else 0.0
    )
    returns = _safe_returns(series)
    vol = float(returns.std()) if len(returns) > 1 else 0.0
    sharpe = (
        float(returns.mean() / vol * math.sqrt(periods_per_year))
        if vol > 0 and periods_per_year
        else 0.0
    )
    downside = returns.clip(upper=0.0)
    downside_std = float(np.sqrt((downside**2).mean())) if len(returns) else 0.0
    sortino = (
        float(returns.mean() / downside_std * math.sqrt(periods_per_year))
        if downside_std > 0 and periods_per_year
        else 0.0
    )
    drawdown = float((series / series.cummax() - 1.0).min()) if len(series) else 0.0
    calmar = cagr / abs(drawdown) if drawdown < 0 else 0.0
    return {
        "initial": initial,
        "final": final,
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": drawdown,
        "calmar": calmar,
        "buy_hold_return": float(buy_hold),
        "excess_return": total_return - float(buy_hold),
        "bars": len(series),
        "start": series.index[0].isoformat(),
        "end": series.index[-1].isoformat(),
    }


def trade_metrics(trades):
    wins = [trade for trade in trades if trade["pnl"] > 0]
    losses = [trade for trade in trades if trade["pnl"] < 0]
    gross_profit = sum(trade["pnl"] for trade in wins)
    gross_loss = abs(sum(trade["pnl"] for trade in losses))
    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else (float("inf") if gross_profit > 0 else 0.0)
    )
    r_values = [trade["r_multiple"] for trade in trades]
    return {
        "trades": len(trades),
        "long_trades": sum(1 for trade in trades if trade["side"] == "LONG"),
        "short_trades": sum(1 for trade in trades if trade["side"] == "SHORT"),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "profit_factor": profit_factor,
        "avg_r": float(np.mean(r_values)) if r_values else 0.0,
        "best_r": max(r_values) if r_values else 0.0,
        "worst_r": min(r_values) if r_values else 0.0,
        "avg_trade_pct": (
            float(np.mean([trade["return_pct"] for trade in trades]))
            if trades
            else 0.0
        ),
    }
