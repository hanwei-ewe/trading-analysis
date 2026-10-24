import copy


DEFAULT_CHECKS = ("regime", "ema_position", "bollinger", "vwap", "rsi")


ALL_CHECKS = (
    "regime",
    "ema_position",
    "rsi",
    "macd",
    "vwap",
    "bollinger",
    "stoch",
    "adx",
    "obv",
    "pa",
    "breakout",
    "extension",
)


def _parse_checks(raw):
    if not raw or raw == "default":
        return list(DEFAULT_CHECKS)
    if raw == "all":
        return list(ALL_CHECKS)
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    bad = set(parts) - set(ALL_CHECKS)
    if bad:
        raise ValueError(f"unknown checks: {', '.join(sorted(bad))}")
    return parts


def _merge_overrides(base, overrides):
    out = copy.deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge_overrides(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _warmup_bars(cfg):
    ind = cfg["indicators"]
    macd_cfg = ind["macd"]
    stoch_cfg = ind.get("stoch", [14, 3, 3])
    adx_period = ind.get("adx", 14)
    obv_period = ind.get("obv", 10)
    vwap_period = ind.get("vwap", ind.get("volume_ma", 20))
    need = max(
        max(ind["ema"]),
        ind["rsi"],
        macd_cfg[1] + macd_cfg[2],
        ind["atr"],
        ind["bollinger"][0],
        vwap_period,
        ind.get("volume_ma", 20),
        stoch_cfg[0] + stoch_cfg[1] + stoch_cfg[2],
        adx_period * 2,
        obv_period + 1,
        ind.get("breakout", 20),
    )
    return int(need) + int(cfg["swings"]["lookback"]) + 5

