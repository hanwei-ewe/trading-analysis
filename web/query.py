from fastapi import HTTPException


def guard(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


def selected(osc):
    return [x.strip() for x in str(osc or "").split(",") if x.strip()]


def active_from_query(query):
    raw = query.get("checks")
    if raw is None:
        return None
    return {x.strip() for x in raw.split(",") if x.strip()}


def to_int(query, name, default):
    try:
        return int(query.get(name, default))
    except (TypeError, ValueError):
        return default


def to_float(query, name, default):
    try:
        return float(query.get(name, default))
    except (TypeError, ValueError):
        return default


def params_from_query(query, cfg):
    ind = cfg["indicators"]
    ema = ind["ema"]
    macd = ind["macd"]
    boll = ind["bollinger"]
    return {
        "ema": [
            to_int(query, "ema_short", ema[0]),
            to_int(query, "ema_mid", ema[1]),
            to_int(query, "ema_long", ema[2]),
        ],
        "rsi": to_int(query, "rsi_period", ind["rsi"]),
        "macd": [
            to_int(query, "macd_fast", macd[0]),
            to_int(query, "macd_slow", macd[1]),
            to_int(query, "macd_signal", macd[2]),
        ],
        "bollinger": [
            to_int(query, "bb_period", boll[0]),
            to_float(query, "bb_std", boll[1]),
        ],
        "vwap": to_int(query, "vwap_period", ind.get("vwap", ind["volume_ma"])),
        "stoch": [
            to_int(query, "stoch_k", 14),
            to_int(query, "stoch_d", 3),
            to_int(query, "stoch_smooth", 3),
        ],
        "adx": to_int(query, "adx_period", 14),
        "obv": to_int(query, "obv_lookback", ind.get("obv", 10)),
    }


def dca_from_query(query):
    return {
        "symbol": query.get("symbol") or None,
        "timeframe": query.get("timeframe") or "4h",
        "days": to_int(query, "days", 1900),
        "initial_capital": to_float(query, "initial_capital", 1000.0),
        "level_mode": query.get("level_mode") or "fib",
        "levels": query.get("levels") or None,
        "level_base": to_float(query, "level_base", 0.10),
        "allocation": query.get("allocation") or "deep",
        "allocations": query.get("allocations") or None,
        "reference_mode": query.get("reference_mode") or "anchor",
        "target_mode": query.get("target_mode") or "percent",
        "profit_target": to_float(query, "profit_target", 15.0),
        "target_retrace": to_float(query, "target_retrace", 0.5),
        "target_atr": to_float(query, "target_atr", 3.0),
        "reinvest_pct": to_float(query, "reinvest_pct", 50.0),
        "trend_filter": query.get("trend_filter") or "ema200",
        "ema_period": to_int(query, "ema_period", 200),
        "atr_period": to_int(query, "atr_period", 14),
        "reference_lookback": to_int(query, "reference_lookback", 180),
        "swing_lookback": to_int(query, "swing_lookback", 50),
    }
