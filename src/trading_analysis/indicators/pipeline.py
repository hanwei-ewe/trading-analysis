from .base import INDICATORS


def add_indicators(df, cfg):
    values = cfg["indicators"]
    out = df.copy()
    for indicator in INDICATORS:
        if indicator.id not in values:
            continue
        result = indicator.compute(out, values[indicator.id])
        for column in result.columns:
            out[column] = result[column]
    return out


def warmup_bars(cfg):
    values = cfg.get("indicators", {})
    return max(
        (
            indicator.warmup(values[indicator.id])
            for indicator in INDICATORS
            if indicator.id in values
        ),
        default=0,
    )
