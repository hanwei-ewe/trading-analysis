from fastapi import APIRouter

from trading_analysis.app import get_chart_data, get_overlays
from web.query import guard

router = APIRouter()


@router.get("/api/chart")
def api_chart(
    timeframe: str | None = None,
    limit: int = 500,
    ema: str = "20,50,200",
    bb_period: int = 20,
    bb_std: float = 2.0,
    show_bb: bool = True,
    show_vwap: bool = True,
    vwap_period: int = 20,
    osc: str = "rsi",
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    stoch_k: int = 14,
    stoch_d: int = 3,
    stoch_smooth: int = 3,
    adx_period: int = 14,
):
    return guard(
        get_chart_data,
        timeframe=timeframe,
        limit=limit,
        ema_periods=ema,
        bb_period=bb_period,
        bb_std=bb_std,
        show_bb=show_bb,
        show_vwap=show_vwap,
        vwap_period=vwap_period,
        osc=osc,
        rsi_period=rsi_period,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
        stoch_k=stoch_k,
        stoch_d=stoch_d,
        stoch_smooth=stoch_smooth,
        adx_period=adx_period,
    )


@router.get("/api/overlays")
def api_overlays(
    timeframe: str | None = None,
    limit: int = 500,
    ema: str = "20,50,200",
    bb_period: int = 20,
    bb_std: float = 2.0,
    show_bb: bool = True,
    show_vwap: bool = True,
    vwap_period: int = 20,
    osc: str = "rsi",
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    stoch_k: int = 14,
    stoch_d: int = 3,
    stoch_smooth: int = 3,
    adx_period: int = 14,
):
    return guard(
        get_overlays,
        timeframe=timeframe,
        limit=limit,
        ema_periods=ema,
        bb_period=bb_period,
        bb_std=bb_std,
        show_bb=show_bb,
        show_vwap=show_vwap,
        vwap_period=vwap_period,
        osc=osc,
        rsi_period=rsi_period,
        macd_fast=macd_fast,
        macd_slow=macd_slow,
        macd_signal=macd_signal,
        stoch_k=stoch_k,
        stoch_d=stoch_d,
        stoch_smooth=stoch_smooth,
        adx_period=adx_period,
    )
