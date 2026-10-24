import logging

import pandas as pd

from ..config import resolve_path
from .timeframes import drop_incomplete, parse_timeframe


log = logging.getLogger(__name__)


COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def candles_to_df(ohlcv):
    df = pd.DataFrame(ohlcv, columns=COLUMNS)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df = df.set_index("timestamp").sort_index()
    df.index.name = "timestamp"
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    return df


def _cache_path(cache_dir, symbol, timeframe):
    name = f"{symbol.replace('/', '_')}_{timeframe}.csv"
    return cache_dir / name


def _history_path(cache_dir, symbol, timeframe):
    name = f"{symbol.replace('/', '_')}_{timeframe}_history.csv"
    return cache_dir / name


def _read_cache(path):
    df = pd.read_csv(path, index_col="timestamp", parse_dates=["timestamp"])
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    return df


def _fetch_range(adapter, symbol, timeframe, since, limit, step_ms, max_batches=20):
    rows = []
    cursor = since
    for _ in range(max_batches):
        batch = adapter.fetch_ohlcv(symbol, timeframe, limit=limit, since=cursor)
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < limit:
            break
        cursor = batch[-1][0] + step_ms
    return rows


def load_candles(adapter, symbol, timeframe, limit=1000, cache_dir=None, use_cache=True):
    cache_dir = resolve_path(cache_dir) if cache_dir else resolve_path("data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _cache_path(cache_dir, symbol, timeframe)

    cached = None
    if use_cache and path.exists():
        try:
            cached = _read_cache(path)
        except Exception as err:
            log.warning("cache read failed for %s: %s", path, err)
            cached = None

    if cached is not None and not cached.empty:
        step_ms = parse_timeframe(timeframe) * 1000
        since = int(cached.index[-1].timestamp() * 1000) + step_ms
        raw = _fetch_range(adapter, symbol, timeframe, since, limit, step_ms)
    else:
        raw = adapter.fetch_ohlcv(symbol, timeframe, limit=limit)

    fresh = candles_to_df(raw)

    if cached is not None and not cached.empty:
        combined = pd.concat([cached, fresh])
        combined = combined[~combined.index.duplicated(keep="last")].sort_index()
    else:
        combined = fresh

    combined.to_csv(path)
    return combined


def load_history(
    adapter,
    symbol,
    timeframe,
    days,
    cache_dir=None,
    use_cache=True,
    limit=1000,
):
    cache_dir = resolve_path(cache_dir) if cache_dir else resolve_path("data/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = _history_path(cache_dir, symbol, timeframe)

    step = parse_timeframe(timeframe)
    step_ms = step * 1000
    now = pd.Timestamp.now(tz="UTC")
    start = now - pd.Timedelta(days=days)

    cached = None
    if use_cache and path.exists():
        try:
            cached = _read_cache(path)
        except Exception as err:
            log.warning("history cache read failed for %s: %s", path, err)
            cached = None

    covered = (
        cached is not None
        and not cached.empty
        and cached.index[0] <= start
        and cached.index[-1] >= now - pd.Timedelta(seconds=2 * step)
    )

    if not covered:
        fetch_start = start
        if cached is not None and not cached.empty:
            fetch_start = min(fetch_start, cached.index[0])
        span = max((now - fetch_start).total_seconds(), 0.0)
        max_batches = int(span / step / limit) + 3
        raw = _fetch_range(
            adapter,
            symbol,
            timeframe,
            int(fetch_start.timestamp() * 1000),
            limit,
            step_ms,
            max_batches=max_batches,
        )
        fresh = candles_to_df(raw)
        if cached is not None and not cached.empty:
            combined = pd.concat([cached, fresh])
            combined = combined[~combined.index.duplicated(keep="last")].sort_index()
        else:
            combined = fresh
        combined.to_csv(path)
    else:
        combined = cached

    window = combined[combined.index >= start]
    window = window[window.index < now]
    return drop_incomplete(window, timeframe)
