import math

import numpy as np
import pandas as pd


def curve_series(curve, value_key="equity"):
    if isinstance(curve, pd.Series):
        series = curve.copy()
        series.index = pd.to_datetime(series.index, utc=True)
        series = series.sort_index()
        return series[~series.index.duplicated(keep="last")].astype(float)
    if not curve:
        return pd.Series(dtype=float)
    data = {}
    for row in curve:
        value = row.get(value_key)
        if value is None:
            value = row.get("total_wealth", row.get("equity"))
        data[pd.Timestamp(row["time"])] = float(value)
    series = pd.Series(data).sort_index()
    series = series[~series.index.duplicated(keep="last")]
    return series


def blend_curves(curves, weights):
    if len(curves) != len(weights):
        raise ValueError("curves and weights must have the same length")
    total = float(sum(weights))
    if total <= 0:
        raise ValueError("weights must sum to > 0")
    weights = [float(w) / total for w in weights]
    series = [curve_series(curve) for curve in curves]
    frame = pd.concat(series, axis=1, join="inner").dropna()
    if frame.empty:
        raise ValueError("curves do not overlap")
    combined = (frame * weights).sum(axis=1)
    return combined.sort_index()


def curve_metrics(series, periods_per_year=None):
    if series is None or len(series) < 2:
        raise ValueError("need at least two points")
    series = series.sort_index()
    first = float(series.iloc[0])
    final = float(series.iloc[-1])
    total_return = final / first - 1.0
    if periods_per_year is None:
        step = (
            (series.index[-1] - series.index[0]).total_seconds()
            / (len(series) - 1)
        )
        periods_per_year = 365.25 * 24 * 3600 / step if step > 0 else 0.0
    years = len(series) / periods_per_year if periods_per_year else 0.0
    cagr = (final / first) ** (1.0 / years) - 1.0 if years > 0 and final > 0 else 0.0
    returns = series.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    vol = float(returns.std()) if len(returns) > 1 else 0.0
    sharpe = (
        float(returns.mean() / vol * math.sqrt(periods_per_year))
        if vol > 0 and periods_per_year
        else 0.0
    )
    drawdown = float((series / series.cummax() - 1.0).min())
    calmar = cagr / abs(drawdown) if drawdown < 0 else 0.0
    return {
        "initial": first,
        "final": final,
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_drawdown": drawdown,
        "calmar": calmar,
        "bars": len(series),
        "start": series.index[0].isoformat(),
        "end": series.index[-1].isoformat(),
    }
