import argparse
import json
from itertools import product

import pandas as pd

from .backtest import run_backtest

STOP_MULTS = (1.0, 1.5, 2.0)
TARGET_RS = (1.5, 2.0, 3.0)


def _r_multiple(trade):
    return float(trade.get("r_multiple") or 0.0)


def summarize_trades(trades, start, end):
    selected = [
        t
        for t in trades
        if pd.Timestamp(start) <= pd.Timestamp(t["entry_time"]) < pd.Timestamp(end)
    ]
    values = [_r_multiple(t) for t in selected]
    total = float(sum(values))
    wins = [r for r in values if r > 0]
    losses = [r for r in values if r < 0]
    gross_win = float(sum(wins))
    gross_loss = -float(sum(losses))
    return {
        "trades": len(values),
        "total_r": total,
        "mean_r": total / len(values) if values else 0.0,
        "win_rate": len(wins) / len(values) if values else 0.0,
        "gross_win": gross_win,
        "gross_loss": gross_loss,
        "profit_factor": (
            gross_win / gross_loss
            if gross_loss > 0
            else (float("inf") if gross_win > 0 else 0.0)
        ),
    }


def fold_windows(start, end, train_days, test_days, step_days=None):
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    train = pd.Timedelta(days=train_days)
    test = pd.Timedelta(days=test_days)
    step = pd.Timedelta(days=step_days or test_days)
    windows = []
    test_start = start + train
    while test_start + test <= end:
        windows.append((test_start - train, test_start, test_start + test))
        test_start += step
    return windows


def _pool(summaries):
    trades = [s["trades"] for s in summaries]
    total = sum(s["total_r"] for s in summaries)
    count = sum(trades)
    wins = sum(s["win_rate"] * s["trades"] for s in summaries)
    gross_win = sum(s["gross_win"] for s in summaries)
    gross_loss = sum(s["gross_loss"] for s in summaries)
    return {
        "trades": count,
        "total_r": total,
        "mean_r": total / count if count else 0.0,
        "win_rate": wins / count if count else 0.0,
        "profit_factor": (
            gross_win / gross_loss
            if gross_loss > 0
            else (float("inf") if gross_win > 0 else 0.0)
        ),
    }


def run_walk_forward(
    timeframe=None,
    days=730,
    train_days=180,
    test_days=90,
    step_days=None,
    min_train_trades=5,
    entry_mode="market",
    regime_filter="none",
    use_mtf=True,
    fee=0.001,
    slippage=0.0005,
    initial_equity=10000.0,
    stop_mults=STOP_MULTS,
    target_rs=TARGET_RS,
    df=None,
    htf_dfs=None,
):
    start = None
    runs = {}
    for stop_mult, target_r in product(stop_mults, target_rs):
        result = run_backtest(
            timeframe=timeframe,
            days=days,
            entry_mode=entry_mode,
            regime_filter=regime_filter,
            use_mtf=use_mtf,
            fee=fee,
            slippage=slippage,
            initial_equity=initial_equity,
            stop_mult=stop_mult,
            target_r=target_r,
            df=df,
            htf_dfs=htf_dfs,
        )
        if result["metrics"]["start"] is None:
            raise ValueError("backtest produced no equity curve")
        if start is None:
            start = pd.Timestamp(result["metrics"]["start"])
        runs[(float(stop_mult), float(target_r))] = result
    if start is None:
        raise ValueError("empty parameter grid")
    end = min(
        pd.Timestamp(r["metrics"]["end"]) for r in runs.values()
    )
    if step_days is not None and step_days < test_days:
        raise ValueError("step_days must be >= test_days to keep tests disjoint")
    windows = fold_windows(start, end, train_days, test_days, step_days)
    if not windows:
        raise ValueError(
            f"no folds: {days}d of history, train {train_days}d + test {test_days}d"
        )

    fold_rows = []
    selected_values = []
    baseline_values = []
    candidate_values = []
    counts = {}
    for train_start, test_start, test_end in windows:
        train_rows = []
        for combo, result in runs.items():
            summary = summarize_trades(
                result["trades"], train_start, test_start
            )
            if summary["trades"] >= min_train_trades:
                train_rows.append((combo, summary))
        if not train_rows:
            fold_rows.append(
                {
                    "train_start": train_start,
                    "test_start": test_start,
                    "test_end": test_end,
                    "selected": None,
                    "train": None,
                    "test": None,
                }
            )
            continue
        combo, train_summary = max(
            train_rows,
            key=lambda row: (
                row[1]["total_r"],
                row[1]["profit_factor"],
            ),
        )
        test_summary = summarize_trades(runs[combo]["trades"], test_start, test_end)
        baseline = (
            summarize_trades(
                runs[(1.0, 2.0)]["trades"], test_start, test_end
            )
            if (1.0, 2.0) in runs
            else None
        )
        candidate = (
            summarize_trades(
                runs[(2.0, 3.0)]["trades"], test_start, test_end
            )
            if (2.0, 3.0) in runs
            else None
        )
        selected_values.append(test_summary)
        if baseline is not None:
            baseline_values.append(baseline)
        if candidate is not None:
            candidate_values.append(candidate)
        key = f"{combo[0]:.1f}x/{combo[1]:.1f}R"
        counts[key] = counts.get(key, 0) + 1
        fold_rows.append(
            {
                "train_start": train_start,
                "test_start": test_start,
                "test_end": test_end,
                "selected": {
                    "stop_mult": combo[0],
                    "target_r": combo[1],
                },
                "train": train_summary,
                "test": test_summary,
                "baseline": baseline,
                "candidate": candidate,
            }
        )

    return {
        "timeframe": timeframe,
        "days": days,
        "train_days": train_days,
        "test_days": test_days,
        "step_days": step_days or test_days,
        "grid": {
            "stop_mult": [float(v) for v in stop_mults],
            "target_r": [float(v) for v in target_rs],
        },
        "folds": fold_rows,
        "oos": _pool(selected_values),
        "fixed_1x_2r": _pool(baseline_values),
        "fixed_2x_3r": _pool(candidate_values),
        "selection_counts": counts,
    }


def format_report(result):
    tf = result["timeframe"] or "default"
    lines = [
        f"# Walk-forward — {tf} ({result['days']}d)",
        "",
        f"- Train {result['train_days']}d / test {result['test_days']}d / "
        f"step {result['step_days']}d",
        f"- Grid: stop {result['grid']['stop_mult']}, "
        f"target {result['grid']['target_r']}R",
        "",
        "| Train | Test | Selected | Train R | Test R | 1x/2R | 2x/3R "
        "| Trades | Win | PF |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for fold in result["folds"]:
        if fold["selected"] is None:
            continue
        label = (
            f"{fold['selected']['stop_mult']:.1f}x/"
            f"{fold['selected']['target_r']:.1f}R"
        )
        test = fold["test"]
        base = fold["baseline"]
        cand = fold["candidate"]
        base_r = f"{base['total_r']:+.1f}" if base else "—"
        cand_r = f"{cand['total_r']:+.1f}" if cand else "—"
        lines.append(
            f"| {fold['train_start'].date()} → {fold['test_start'].date()} "
            f"| {fold['test_start'].date()} → {fold['test_end'].date()} "
            f"| {label} | {fold['train']['total_r']:+.1f} "
            f"| {test['total_r']:+.1f} | {base_r} | {cand_r} "
            f"| {test['trades']} | {test['win_rate'] * 100:.1f}% "
            f"| {test['profit_factor']:.2f} |"
        )
    lines.extend(["", "## Out-of-sample", ""])
    for label, key in (
        ("Selected", "oos"),
        ("Fixed 1.0x/2R", "fixed_1x_2r"),
        ("Fixed 2.0x/3R", "fixed_2x_3r"),
    ):
        stats = result[key]
        lines.append(
            f"- {label}: {stats['trades']} trades, "
            f"{stats['total_r']:+.1f}R, {stats['mean_r']:+.3f}R/trade, "
            f"win {stats['win_rate'] * 100:.1f}%, "
            f"PF {stats['profit_factor']:.2f}"
        )
    counts = ", ".join(
        f"{key} ×{value}" for key, value in sorted(result["selection_counts"].items())
    )
    lines.append(f"- Selection counts: {counts or 'none'}")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Walk-forward backtest validation")
    parser.add_argument("--timeframe", default=None)
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--train-days", type=int, default=180)
    parser.add_argument("--test-days", type=int, default=90)
    parser.add_argument("--step-days", type=int, default=None)
    parser.add_argument("--min-train-trades", type=int, default=5)
    parser.add_argument("--entry", choices=("market", "limit"), default="market")
    parser.add_argument(
        "--regime-filter", choices=("none", "aligned", "loose"), default="none"
    )
    parser.add_argument("--no-mtf", action="store_true")
    parser.add_argument("--fee", type=float, default=0.001)
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--equity", type=float, default=10000.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_walk_forward(
        timeframe=args.timeframe,
        days=args.days,
        train_days=args.train_days,
        test_days=args.test_days,
        step_days=args.step_days,
        min_train_trades=args.min_train_trades,
        entry_mode=args.entry,
        regime_filter=args.regime_filter,
        use_mtf=not args.no_mtf,
        fee=args.fee,
        slippage=args.slippage,
        initial_equity=args.equity,
    )
    print(json.dumps(result, indent=2, default=str) if args.json else format_report(result))


if __name__ == "__main__":
    main()
