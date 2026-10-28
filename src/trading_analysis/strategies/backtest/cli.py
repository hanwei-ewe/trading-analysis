import argparse
import json

from ..runner import run_strategy
from .checks import _parse_checks
from .report import save_results, to_markdown


def main(argv=None):
    parser = argparse.ArgumentParser(description="Backtest the confluence strategy")
    parser.add_argument("--config", default=None)
    parser.add_argument("--timeframe", default=None)
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--checks", default="default",
                        help="default, all, or comma-separated check ids")
    parser.add_argument("--equity", type=float, default=1000.0)
    parser.add_argument("--fee", type=float, default=0.001)
    parser.add_argument("--slippage", type=float, default=0.0005)
    parser.add_argument("--no-mtf", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--target", choices=("proposal", "rr"), default="proposal")
    parser.add_argument("--entry", choices=("market", "limit"), default="market")
    parser.add_argument("--limit-bars", type=int, default=5)
    parser.add_argument(
        "--regime-filter", choices=("none", "aligned", "loose"), default="none"
    )
    parser.add_argument("--stop-mult", type=float, default=1.0,
                        help="scale structural stop distance (1 = as proposed)")
    parser.add_argument("--target-r", type=float, default=None,
                        help="fixed R-multiple target from fill; overrides --target")
    parser.add_argument("--long-only", action="store_true",
                        help="spot mode: no shorts, cash-only notional")
    parser.add_argument("--risk-pct", type=float, default=None,
                        help="risk per trade in percent of equity")
    parser.add_argument("--risk-model", default="percent",
                        help="registered risk model id")
    parser.add_argument("--execution-model", default="default",
                        help="registered execution model id")
    parser.add_argument("--cash-buffer", type=float, default=0.02)
    parser.add_argument("--min-notional", type=float, default=5.0)
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--overrides", default=None,
                        help="JSON config overrides, e.g. '{\"indicators\":{\"rsi\":7}}'")
    args = parser.parse_args(argv)

    result = run_strategy(
        "trend",
        config_path=args.config,
        timeframe=args.timeframe,
        symbol=args.symbol,
        days=args.days,
        checks=_parse_checks(args.checks),
        initial_equity=args.equity,
        fee=args.fee,
        slippage=args.slippage,
        use_cache=not args.no_cache,
        use_mtf=not args.no_mtf,
        target_mode=args.target,
        entry_mode=args.entry,
        limit_bars=args.limit_bars,
        regime_filter=args.regime_filter,
        stop_mult=args.stop_mult,
        target_r=args.target_r,
        long_only=args.long_only,
        risk_pct=args.risk_pct,
        risk_model=args.risk_model,
        execution_model=args.execution_model,
        cash_buffer=args.cash_buffer,
        min_notional=args.min_notional,
        window_start=args.start,
        window_end=args.end,
        indicator_overrides=(
            json.loads(args.overrides) if args.overrides else None
        ),
    )
    paths = save_results(result, args.config)
    print(to_markdown(result))
    print(f"Saved: {paths['json']}")
    print(f"Saved: {paths['markdown']}")
    return result


if __name__ == "__main__":
    main()
