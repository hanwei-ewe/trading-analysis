import logging
import math
import threading
import time
from datetime import datetime, timezone

from . import data as data_mod
from . import indicators as ind_mod
from . import journal
from . import params as params_mod
from .analysis import analyze
from .config import load_config
from .exchange import get_adapter
from .explanations import explain
from .report import to_markdown

log = logging.getLogger(__name__)

_DF_CACHE = {}
_DF_LOCKS = {}
_DF_LOCKS_GUARD = threading.Lock()
_DF_TTL_SECONDS = 20.0


def _adapter(cfg):
    return get_adapter(market_type=cfg["exchange"]["market_type"])


def _key_lock(key):
    with _DF_LOCKS_GUARD:
        lock = _DF_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _DF_LOCKS[key] = lock
    return lock


def supported_timeframes(config_path=None):
    cfg = load_config(config_path)
    return cfg["timeframes"]["available"]


def _resolve_timeframe(cfg, timeframe):
    tf = timeframe or cfg["timeframes"]["primary"]
    if tf not in cfg["timeframes"]["available"]:
        raise ValueError(f"unsupported timeframe: {tf}")
    return tf


def _with_params(cfg, params):
    if not params:
        return cfg
    ind = dict(cfg["indicators"])
    if params.get("ema"):
        ind["ema"] = [int(p) for p in params["ema"] if int(p) > 1]
    if params.get("rsi"):
        ind["rsi"] = int(params["rsi"])
    if params.get("macd"):
        ind["macd"] = [int(v) for v in params["macd"]]
    if params.get("bollinger"):
        ind["bollinger"] = [int(params["bollinger"][0]), float(params["bollinger"][1])]
    if params.get("vwap"):
        ind["vwap"] = int(params["vwap"])
    if params.get("stoch"):
        ind["stoch"] = [int(v) for v in params["stoch"]]
    if params.get("adx"):
        ind["adx"] = int(params["adx"])
    if params.get("obv"):
        ind["obv"] = int(params["obv"])
    out = dict(cfg)
    out["indicators"] = ind
    return out


def _load_df(cfg, timeframe, refresh=False):
    symbol = cfg["universe"]["pair"]
    key = (symbol, timeframe)

    entry = _DF_CACHE.get(key)
    if entry and not refresh and (time.time() - entry[1]) < _DF_TTL_SECONDS:
        return entry[0]

    with _key_lock(key):
        entry = _DF_CACHE.get(key)
        if entry and not refresh and (time.time() - entry[1]) < _DF_TTL_SECONDS:
            return entry[0]

        adapter = _adapter(cfg)
        df = data_mod.load_candles(
            adapter, symbol, timeframe, limit=cfg["candles"]["limit"]
        )
        _DF_CACHE[key] = (df, time.time())
        return df


def warm_all(config_path=None):
    cfg = load_config(config_path)
    try:
        _adapter(cfg).load_markets()
    except Exception as err:
        log.warning("market preload failed: %s", err)
    for tf in cfg["timeframes"]["available"]:
        try:
            _load_df(cfg, tf)
        except Exception as err:
            log.warning("warm %s failed: %s", tf, err)


def _points(series):
    out = []
    for ts, value in series.items():
        if value is None:
            continue
        fv = float(value)
        if math.isnan(fv):
            continue
        out.append({"time": int(ts.timestamp()), "value": fv})
    return out


def _candles(df):
    return [
        {
            "time": int(ts.timestamp()),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": float(row["volume"]),
        }
        for ts, row in df.iterrows()
    ]


def _parse_periods(value):
    periods = []
    if value:
        for part in str(value).split(","):
            part = part.strip()
            if part.isdigit() and int(part) > 1:
                periods.append(int(part))
    return periods


def _compute_overlays(
    df, cfg, limit, ema_periods, bb_period, bb_std, show_bb, show_vwap, vwap_period
):
    overlays = {"ema": {}, "bb": None, "vwap": None, "levels": {}}

    for period in _parse_periods(ema_periods):
        overlays["ema"][str(period)] = _points(
            ind_mod.ema(df["close"], period).tail(limit)
        )

    if show_bb and int(bb_period) > 1:
        bb = ind_mod.bollinger(df["close"], int(bb_period), float(bb_std)).tail(limit)
        overlays["bb"] = {
            "upper": _points(bb["bb_upper"]),
            "mid": _points(bb["bb_mid"]),
            "lower": _points(bb["bb_lower"]),
        }

    if show_vwap:
        overlays["vwap"] = _points(
            ind_mod.rolling_vwap(df, int(vwap_period)).tail(limit)
        )

    return overlays


def _attach_levels(overlays, df, cfg, timeframe):
    closed = data_mod.drop_incomplete(df, timeframe)
    min_history = int(cfg["indicators"]["ema"][-1]) + 5
    if len(closed) >= min_history:
        result = analyze(closed, cfg)
        overlays["levels"] = result["levels"]
        overlays["bias"] = result["bias"]
        overlays["regime"] = result["regime"]["state"]


def _compute_oscillators(
    df,
    limit,
    osc,
    rsi_period,
    macd_fast,
    macd_slow,
    macd_signal,
    stoch_k,
    stoch_d,
    stoch_smooth,
    adx_period,
):
    ids = [x.strip() for x in str(osc or "").split(",") if x.strip()]
    out = {}
    for oid in ids:
        if oid == "rsi":
            out["rsi"] = {
                "series": _points(ind_mod.rsi(df["close"], int(rsi_period)).tail(limit)),
                "levels": [70, 30],
                "fixed_range": [0, 100],
            }
        elif oid == "macd":
            m = ind_mod.macd(
                df["close"], int(macd_fast), int(macd_slow), int(macd_signal)
            ).tail(limit)
            out["macd"] = {
                "macd": _points(m["macd"]),
                "signal": _points(m["macd_signal"]),
                "hist": _points(m["macd_hist"]),
            }
        elif oid == "stoch":
            s = ind_mod.stochastic(
                df["high"], df["low"], df["close"], int(stoch_k), int(stoch_d),
                int(stoch_smooth),
            ).tail(limit)
            out["stoch"] = {
                "k": _points(s["stoch_k"]),
                "d": _points(s["stoch_d"]),
                "levels": [80, 20],
                "fixed_range": [0, 100],
            }
        elif oid == "adx":
            a = ind_mod.adx(df["high"], df["low"], df["close"], int(adx_period)).tail(
                limit
            )
            out["adx"] = {
                "adx": _points(a["adx"]),
                "plus_di": _points(a["plus_di"]),
                "minus_di": _points(a["minus_di"]),
                "levels": [25],
            }
        elif oid == "obv":
            out["obv"] = {
                "series": _points(ind_mod.obv(df["close"], df["volume"]).tail(limit))
            }
    return out


def get_chart_data(
    timeframe=None,
    limit=500,
    ema_periods="20,50,200",
    bb_period=20,
    bb_std=2.0,
    show_bb=True,
    show_vwap=True,
    vwap_period=20,
    osc="",
    rsi_period=14,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9,
    stoch_k=14,
    stoch_d=3,
    stoch_smooth=3,
    adx_period=14,
    config_path=None,
):
    cfg = load_config(config_path)
    tf = _resolve_timeframe(cfg, timeframe)
    df = _load_df(cfg, tf)
    view = df.tail(limit)

    overlays = _compute_overlays(
        df, cfg, limit, ema_periods, bb_period, bb_std, show_bb, show_vwap, vwap_period
    )
    _attach_levels(overlays, df, cfg, tf)
    oscillators = _compute_oscillators(
        df, limit, osc, rsi_period, macd_fast, macd_slow, macd_signal,
        stoch_k, stoch_d, stoch_smooth, adx_period,
    )

    return {
        "symbol": cfg["universe"]["pair"],
        "timeframe": tf,
        "candles": _candles(view),
        "overlays": overlays,
        "oscillators": oscillators,
    }


def get_overlays(
    timeframe=None,
    limit=500,
    ema_periods="20,50,200",
    bb_period=20,
    bb_std=2.0,
    show_bb=True,
    show_vwap=True,
    vwap_period=20,
    osc="",
    rsi_period=14,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9,
    stoch_k=14,
    stoch_d=3,
    stoch_smooth=3,
    adx_period=14,
    config_path=None,
):
    cfg = load_config(config_path)
    tf = _resolve_timeframe(cfg, timeframe)
    df = _load_df(cfg, tf)

    overlays = _compute_overlays(
        df, cfg, limit, ema_periods, bb_period, bb_std, show_bb, show_vwap, vwap_period
    )
    _attach_levels(overlays, df, cfg, tf)
    oscillators = _compute_oscillators(
        df, limit, osc, rsi_period, macd_fast, macd_slow, macd_signal,
        stoch_k, stoch_d, stoch_smooth, adx_period,
    )

    return {
        "symbol": cfg["universe"]["pair"],
        "timeframe": tf,
        "overlays": overlays,
        "oscillators": oscillators,
    }


def run_analysis(config_path=None, timeframe=None, do_journal=True, selected=None, params=None, active=None):
    cfg = _with_params(load_config(config_path), params)
    symbol = cfg["universe"]["pair"]
    tf = _resolve_timeframe(cfg, timeframe)
    df = _load_df(cfg, tf)
    df = data_mod.drop_incomplete(df, tf)

    ind_df = ind_mod.add_indicators(df, cfg)
    result = analyze(df, cfg, ind=ind_df, active=active)
    result["symbol"] = symbol
    result["timeframe"] = tf
    result["data_as_of"] = df.index[-1].isoformat()
    result["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result["explanations"] = explain(
        result, cfg, ind_df=ind_df, selected=selected, params=params
    )
    result["markdown"] = to_markdown(result)
    if do_journal:
        result["journal_path"] = journal.write(result, config_path)
    return result


def get_param_review(config_path=None, timeframe=None, params=None):
    cfg = _with_params(load_config(config_path), params)
    tf = _resolve_timeframe(cfg, timeframe)
    df = data_mod.drop_incomplete(_load_df(cfg, tf), tf)
    return params_mod.review(cfg, timeframe=tf, candles=len(df))


def get_explanations(config_path=None, timeframe=None, selected=None, params=None, active=None):
    cfg = _with_params(load_config(config_path), params)
    symbol = cfg["universe"]["pair"]
    tf = _resolve_timeframe(cfg, timeframe)
    df = data_mod.drop_incomplete(_load_df(cfg, tf), tf)
    ind_df = ind_mod.add_indicators(df, cfg)
    result = analyze(df, cfg, ind=ind_df, active=active)
    return {
        "symbol": symbol,
        "timeframe": tf,
        "bias": result["bias"],
        "confidence": result["confidence"],
        "score": result["score"],
        **explain(result, cfg, ind_df=ind_df, selected=selected, params=params),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_analysis(), indent=2, default=str))
