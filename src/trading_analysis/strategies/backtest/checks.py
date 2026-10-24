import copy

from ...analysis.checks import CHECK_IDS
from ...indicators import warmup_bars


DEFAULT_CHECKS = ("regime", "ema_position", "bollinger", "vwap", "rsi")
ALL_CHECKS = CHECK_IDS


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
    need = max(
        warmup_bars(cfg),
        int(cfg["indicators"].get("breakout", 20)),
    )
    return int(need) + int(cfg["swings"]["lookback"]) + 5
