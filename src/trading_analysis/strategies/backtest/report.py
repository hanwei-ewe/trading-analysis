import json
from datetime import datetime, timezone

import pandas as pd

from ...config import load_config, resolve_path
from ...reporting.serialization import json_ready


def to_markdown(result):
    m = result["metrics"]
    lines = [
        f"# Backtest — {result['symbol']} {result['timeframe']}",
        "",
        f"- Window: {m['start']} → {m['end']} ({m['bars']} bars)",
        f"- Checks: {', '.join(result['checks'])}",
        f"- Higher frames: {', '.join(result['htf_frames']) or 'none'}",
        f"- Costs: {result['fee'] * 100:.3f}% fee, "
        f"{result['slippage'] * 100:.3f}% slippage",
        f"- Target: {result['target_r']}R"
        if result.get("target_r") is not None
        else (
            "2R from fill"
            if result.get("target_mode") == "rr"
            else "proposal T1"
        ),
        f"- Stop width: {result.get('stop_mult', 1.0)}x structural",
        f"- Initial capital: ${result['metrics']['initial_equity']:,.0f}",
        "- Direction: long-only (spot, no leverage)"
        if result.get("long_only")
        else "- Direction: long and short",
        f"- Risk: {result.get('risk_pct', 0):.1f}% per trade, "
        f"{result.get('cash_buffer', 0) * 100:.1f}% cash buffer",
        f"- Entry: {'limit at zone mid' if result.get('entry_mode') == 'limit' else 'market at next open'}"
        + (
            f" (valid {result['limit_bars']} bars)"
            if result.get("entry_mode") == "limit"
            else ""
        ),
        f"- Regime filter: {result.get('regime_filter', 'none')}",
        "",
        "## Performance",
        "",
        "| Metric | Strategy | Buy & hold |",
        "| --- | ---: | ---: |",
        f"| Total return | {m['total_return'] * 100:.2f}% | "
        f"{m['buy_hold_return'] * 100:.2f}% |",
        f"| CAGR | {m['cagr'] * 100:.2f}% | — |",
        f"| Sharpe | {m['sharpe']:.2f} | — |",
        f"| Sortino | {m['sortino']:.2f} | — |",
        f"| Max drawdown | {m['max_drawdown'] * 100:.2f}% | — |",
        f"| Calmar | {m['calmar']:.2f} | — |",
        "",
        "## Trading",
        "",
        f"- Trades: {m['trades']} "
        f"({m['long_trades']} long / {m['short_trades']} short)",
        f"- Win rate: {m['win_rate'] * 100:.1f}%",
        f"- Profit factor: {m['profit_factor']:.2f}",
        f"- Avg R: {m['avg_r']:.2f} (best {m['best_r']:.2f}, "
        f"worst {m['worst_r']:.2f})",
        f"- Exposure: {m['exposure'] * 100:.1f}%",
        f"- Final equity: {m['final_equity']:,.2f} "
        f"from {m['initial_equity']:,.2f}",
    ]
    return "\n".join(lines) + "\n"


def save_results(result, config_path=None):
    cfg = load_config(config_path)
    out_dir = resolve_path(cfg["paths"]["results"])
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    symbol = result["symbol"].replace("/", "_")
    base = out_dir / f"backtest_{symbol}_{result['timeframe']}_{result['days']}d_{stamp}"

    payload = dict(result)
    payload["equity_curve"] = result["equity_curve"]
    base.with_suffix(".json").write_text(
        json.dumps(json_ready(payload), indent=2), encoding="utf-8"
    )
    base.with_suffix(".md").write_text(to_markdown(result), encoding="utf-8")

    trades = pd.DataFrame(result["trades"])
    if not trades.empty:
        trades.to_csv(base.parent / f"{base.name}_trades.csv", index=False)
    curve = pd.DataFrame(result["equity_curve"])
    curve.to_csv(base.parent / f"{base.name}_equity.csv", index=False)
    return {
        "json": str(base.with_suffix(".json")),
        "markdown": str(base.with_suffix(".md")),
    }

