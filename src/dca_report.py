import json
from datetime import datetime, timezone

from .config import load_config, resolve_path
from .data import load_history
from .dca import FIB_LEVELS, run_dca
from .exchange import get_adapter

ALLOCATION_PRESETS = {
    "equal": [0.20, 0.20, 0.20, 0.20, 0.20],
    "front": [0.30, 0.25, 0.20, 0.15, 0.10],
    "back": [0.10, 0.15, 0.20, 0.25, 0.30],
    "deep": [0.05, 0.10, 0.15, 0.25, 0.45],
    "very_deep": [0.05, 0.05, 0.10, 0.20, 0.60],
    "fib": [0.0936, 0.1515, 0.1983, 0.2450, 0.3116],
    "inverse": [0.35, 0.25, 0.18, 0.13, 0.09],
    "martingale": [0.0323, 0.0645, 0.1290, 0.2581, 0.5161],
    "anti_martingale": [0.5161, 0.2581, 0.1290, 0.0645, 0.0323],
}


def _parse_floats(raw):
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    return [float(part.strip()) for part in text.split(",") if part.strip()]


def _normalize(weights):
    total = float(sum(weights))
    if total <= 0:
        raise ValueError("allocation weights must sum to > 0")
    return [weight / total for weight in weights]


def _resolve_allocations(allocation, allocations, levels):
    if allocation == "custom":
        parsed = _parse_floats(allocations)
        if not parsed:
            raise ValueError("custom allocation requires weights")
        return _normalize(parsed)
    if allocation not in ALLOCATION_PRESETS:
        raise ValueError(f"unknown allocation preset: {allocation}")
    weights = list(ALLOCATION_PRESETS[allocation])
    if levels is not None and len(levels) != len(weights):
        if len(levels) < len(weights):
            weights = weights[: len(levels)]
        else:
            weights = _normalize(weights + [1.0] * (len(levels) - len(weights)))
    return _normalize(weights)


def _downsample(curve, limit=600):
    if len(curve) <= limit:
        return curve
    step = max(1, len(curve) // limit)
    out = curve[::step]
    if out[-1] is not curve[-1]:
        out.append(curve[-1])
    return out


def run_dca_report(
    symbol=None,
    timeframe="4h",
    days=1900,
    initial_capital=1000.0,
    level_mode="fib",
    levels=None,
    level_base=0.10,
    allocation="deep",
    allocations=None,
    reference_mode="anchor",
    target_mode="percent",
    profit_target=15.0,
    target_retrace=0.5,
    target_atr=3.0,
    reinvest_pct=50.0,
    trend_filter="ema200",
    ema_period=200,
    atr_period=14,
    reference_lookback=180,
    swing_lookback=50,
    config_path=None,
    adapter=None,
    df=None,
):
    cfg = load_config(config_path)
    pair = symbol or cfg["universe"]["pair"]
    tf = timeframe or cfg["timeframes"]["primary"]
    if tf not in cfg["timeframes"]["available"]:
        raise ValueError(f"unsupported timeframe: {tf}")
    parsed_levels = _parse_floats(levels)
    resolved_allocations = _resolve_allocations(allocation, allocations, parsed_levels)
    if parsed_levels is None and level_mode == "fib":
        parsed_levels = list(FIB_LEVELS)
    if parsed_levels is not None and len(parsed_levels) != len(resolved_allocations):
        raise ValueError("levels and allocations must have the same length")

    if df is None:
        adapter = adapter or get_adapter(cfg["exchange"]["market_type"])
        df = load_history(
            adapter,
            pair,
            tf,
            int(days),
            cache_dir=cfg["paths"]["cache"],
            use_cache=True,
        )

    result = run_dca(
        df,
        initial_capital=float(initial_capital),
        levels=parsed_levels,
        allocations=resolved_allocations,
        level_mode=level_mode,
        level_base=float(level_base),
        atr_period=int(atr_period),
        profit_target=float(profit_target) / 100.0,
        target_mode=target_mode,
        target_retrace=float(target_retrace),
        target_atr=float(target_atr),
        reference_mode=reference_mode,
        reference_lookback=int(reference_lookback),
        swing_lookback=int(swing_lookback),
        reinvest_pct=float(reinvest_pct) / 100.0,
        trend_filter=trend_filter,
        ema_period=int(ema_period),
        include_curve=True,
    )
    result.update(
        {
            "symbol": pair,
            "timeframe": tf,
            "days": int(days),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "allocation": allocation,
            "initial_capital": float(initial_capital),
            "chart": [
                {
                    "time": row["time"].isoformat(),
                    "wealth": row["total_wealth"],
                    "reserve": row["reserve"],
                }
                for row in _downsample(result["equity_curve"])
            ],
        }
    )
    result["assumptions"] = [
        "Spot only: no leverage, no shorts, no deposits.",
        f"Capital is split across {len(result['levels'])} levels; unspent cash stays idle.",
        f"Reference: {reference_mode}; target: {target_mode}; trend filter: {trend_filter}.",
        f"{result['reinvest_pct'] * 100:.0f}% of each profitable sale is reinvested; "
        f"the rest is reserved.",
        "Fees 0.10% and slippage 0.05% are applied on entries and exits.",
        "Open lots are marked to market at the last close; they are not forced closed.",
    ]
    return result


def _money(value):
    return f"{value:,.2f}"


def to_markdown(result):
    levels = ", ".join(f"{level:.3f}" for level in result["levels"])
    allocations = ", ".join(f"{weight:.3f}" for weight in result["allocations"])
    lines = [
        f"# DCA ladder — {result['symbol']} {result['timeframe']}",
        "",
        f"- Window: {result['chart'][0]['time']} → {result['chart'][-1]['time']}",
        f"- Initial capital: ${_money(result['initial_capital'])}",
        f"- Levels: {levels}",
        f"- Allocations: {allocations}",
        f"- Reference: {result['reference_mode']}",
        f"- Target: {result['target_mode']}",
        f"- Trend filter: {result['trend_filter']}",
        f"- Reinvest: {result['reinvest_pct'] * 100:.0f}%",
        "",
        "## Performance",
        "",
        "| Metric | DCA | Buy & hold |",
        "| --- | ---: | ---: |",
        f"| Total return | {result['total_return'] * 100:.2f}% | "
        f"{result['buy_hold_return'] * 100:.2f}% |",
        f"| CAGR | {result['cagr'] * 100:.2f}% | — |",
        f"| Max drawdown | {result['max_drawdown'] * 100:.2f}% | — |",
        f"| Final wealth | ${_money(result['final_total_wealth'])} | — |",
        f"| Reserved profit | ${_money(result['final_reserve'])} | — |",
        "",
        "## Activity",
        "",
        f"- Buys: {result['buys']}",
        f"- Sells: {result['sells']}",
        f"- Open lots: {result['open_lot_count']}",
        f"- Exposure: {result['exposure'] * 100:.1f}%",
        f"- Max deployed: ${_money(result['max_deployed'])}",
        f"- Win rate: {result['win_rate'] * 100:.1f}%",
        "",
        "## Assumptions",
        "",
    ]
    for item in result["assumptions"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def serialize(result):
    def clean(value):
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, (datetime,)):
            return value.isoformat()
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
            return None
        return value

    return clean(result)


def save_report(result, config_path=None):
    cfg = load_config(config_path)
    out_dir = resolve_path(cfg["paths"]["results"])
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = out_dir / f"dca_{result['symbol'].replace('/', '_')}_{result['timeframe']}_{stamp}"
    base.with_suffix(".md").write_text(to_markdown(result), encoding="utf-8")
    base.with_suffix(".json").write_text(
        json.dumps(serialize(result), indent=2), encoding="utf-8"
    )
    return {"markdown": str(base.with_suffix(".md")), "json": str(base.with_suffix(".json"))}
