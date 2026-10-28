from datetime import datetime, timezone

import pandas as pd

from ...config import load_config
from ...data import get_adapter, load_history, parse_timeframe
from .checks import DEFAULT_CHECKS, _merge_overrides, _warmup_bars
from .engine import _run_engine
from .execution import get_execution_model
from .features import _evaluate_frame, _htf_check_map, _prep, _regime_map
from .metrics import _buy_hold, _metrics
from .risk import get_risk_model


def run_backtest(
    config_path=None,
    timeframe=None,
    symbol=None,
    days=365,
    checks=None,
    initial_equity=1000.0,
    fee=0.001,
    slippage=0.0005,
    use_cache=True,
    use_mtf=True,
    target_mode="proposal",
    entry_mode="market",
    limit_bars=5,
    regime_filter="none",
    stop_mult=1.0,
    target_r=None,
    long_only=False,
    risk_pct=None,
    cash_buffer=0.02,
    min_notional=5.0,
    window_start=None,
    window_end=None,
    indicator_overrides=None,
    adapter=None,
    df=None,
    htf_dfs=None,
    risk_model="percent",
    execution_model="default",
):
    if float(stop_mult) <= 0:
        raise ValueError("stop_mult must be > 0")
    if target_r is not None and float(target_r) <= 0:
        raise ValueError("target_r must be > 0")
    if risk_pct is not None and not 0 < float(risk_pct) <= 100:
        raise ValueError("risk_pct must be in (0, 100]")
    if not 0 <= float(cash_buffer) < 1:
        raise ValueError("cash_buffer must be in [0, 1)")
    if float(min_notional) < 0:
        raise ValueError("min_notional must be >= 0")
    get_risk_model(risk_model)
    get_execution_model(execution_model)
    cfg = load_config(config_path)
    if indicator_overrides:
        if not isinstance(indicator_overrides, dict):
            raise ValueError("indicator_overrides must be a dict")
        cfg = _merge_overrides(cfg, indicator_overrides)
    pair = symbol or cfg["universe"]["pair"]
    tf = timeframe or cfg["timeframes"]["primary"]
    active = set(checks or DEFAULT_CHECKS)
    step = parse_timeframe(tf)
    warm = _warmup_bars(cfg)
    cache_dir = cfg["paths"]["cache"]

    if df is None:
        adapter = adapter or get_adapter(
            market_type=cfg["exchange"]["market_type"],
            exchange_id=cfg["exchange"].get("id", "binance"),
        )
        extra_days = warm * step / 86400.0 + 2.0
        df = load_history(
            adapter, pair, tf, days + extra_days, cache_dir=cache_dir, use_cache=use_cache
        )
    df = df.sort_index()
    if len(df) <= warm + 10:
        raise ValueError(
            f"need more than {warm + 10} candles, got {len(df)}"
        )

    primary_ind = _prep(df, cfg)

    htf_frames = []
    if use_mtf:
        specs = [cfg["timeframes"]["regime"], *cfg["timeframes"]["context"]]
        for htf in dict.fromkeys(specs):
            htf_step = parse_timeframe(htf)
            if htf == tf or htf_step <= step:
                continue
            if htf_dfs is not None:
                if htf in htf_dfs:
                    htf_frames.append((htf, htf_dfs[htf].sort_index()))
                continue
            extra_days = warm * htf_step / 86400.0 + 2.0
            hdf = load_history(
                adapter,
                pair,
                htf,
                days + extra_days,
                cache_dir=cache_dir,
                use_cache=use_cache,
            )
            htf_frames.append((htf, hdf.sort_index()))

    htf_by_pos = (
        _htf_check_map(primary_ind, cfg, active, htf_frames, tf)
        if htf_frames
        else {}
    )
    regime_bias = {}
    if regime_filter != "none":
        if not use_mtf:
            raise ValueError("regime filter requires MTF; remove --no-mtf")
        regime_bias = _regime_map(htf_by_pos, cfg["timeframes"]["regime"])
        if not regime_bias:
            raise ValueError(
                "regime filter needs a higher regime frame; "
                "use a lower primary timeframe"
            )
    results = _evaluate_frame(primary_ind, cfg, active, tf, htf_by_pos)

    if window_start is None:
        window_start = primary_ind.index[-1] - pd.Timedelta(days=days)
        warm_start = primary_ind.index[min(warm, len(primary_ind) - 1)]
        if window_start < warm_start:
            window_start = warm_start
    else:
        window_start = pd.Timestamp(window_start)
        if window_start.tzinfo is None:
            window_start = window_start.tz_localize("UTC")
    if window_end is not None:
        window_end = pd.Timestamp(window_end)
        if window_end.tzinfo is None:
            window_end = window_end.tz_localize("UTC")

    engine = _run_engine(
        primary_ind,
        results,
        cfg,
        window_start,
        initial_equity,
        float(fee),
        float(slippage),
        target_mode=target_mode,
        entry_mode=entry_mode,
        limit_bars=limit_bars,
        regime_bias=regime_bias,
        regime_filter=regime_filter,
        stop_mult=stop_mult,
        target_r=target_r,
        long_only=long_only,
        risk_pct=risk_pct,
        cash_buffer=cash_buffer,
        min_notional=min_notional,
        window_end=window_end,
        risk_model=risk_model,
        execution_model=execution_model,
    )
    start_idx = engine["start_index"]
    metrics = _metrics(
        engine,
        primary_ind,
        tf,
        _buy_hold(primary_ind, start_idx, engine["end_index"]),
    )
    return {
        "symbol": pair,
        "timeframe": tf,
        "days": days,
        "checks": sorted(active),
        "htf_frames": [htf for htf, _ in htf_frames],
        "fee": float(fee),
        "slippage": float(slippage),
        "target_mode": target_mode,
        "entry_mode": entry_mode,
        "limit_bars": int(limit_bars),
        "regime_filter": regime_filter,
        "stop_mult": float(stop_mult),
        "target_r": None if target_r is None else float(target_r),
        "long_only": bool(long_only),
        "risk_pct": float(
            risk_pct if risk_pct is not None else cfg["risk"]["max_risk_pct"]
        ),
        "cash_buffer": float(cash_buffer),
        "min_notional": float(min_notional),
        "risk_model": risk_model,
        "execution_model": execution_model,
        "indicator_overrides": indicator_overrides or {},
        "metrics": metrics,
        "trades": engine["trades"],
        "equity_curve": engine["equity_curve"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
