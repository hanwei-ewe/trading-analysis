import pandas as pd

from .metrics import series_metrics


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
    metrics = series_metrics(series, periods_per_year=periods_per_year)
    return {
        "initial": metrics["initial"],
        "final": metrics["final"],
        "total_return": metrics["total_return"],
        "cagr": metrics["cagr"],
        "sharpe": metrics["sharpe"],
        "max_drawdown": metrics["max_drawdown"],
        "calmar": metrics["calmar"],
        "bars": metrics["bars"],
        "start": metrics["start"],
        "end": metrics["end"],
    }
