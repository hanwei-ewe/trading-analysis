import json
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.config import ROOT, load_config
from src.dca_report import ALLOCATION_PRESETS, run_dca_report, serialize, to_markdown
from src.pipeline import (
    get_chart_data,
    get_explanations,
    get_overlays,
    get_param_review,
    run_analysis,
    supported_timeframes,
    warm_all,
)


@asynccontextmanager
async def lifespan(app):
    threading.Thread(target=warm_all, daemon=True).start()
    yield


app = FastAPI(title="Trading Analysis", lifespan=lifespan)

templates = Jinja2Templates(directory=str(ROOT / "web" / "templates"))
app.mount(
    "/static",
    StaticFiles(directory=str(ROOT / "web" / "static")),
    name="static",
)


def _guard(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err


def _selected(osc):
    return [x.strip() for x in str(osc or "").split(",") if x.strip()]


def _active_from_query(q):
    raw = q.get("checks")
    if raw is None:
        return None
    return {x.strip() for x in raw.split(",") if x.strip()}


def _params_from_query(q, cfg):
    ind = cfg["indicators"]
    ema = ind["ema"]
    macd = ind["macd"]
    boll = ind["bollinger"]

    def to_int(name, default):
        try:
            return int(q.get(name, default))
        except (TypeError, ValueError):
            return default

    def to_float(name, default):
        try:
            return float(q.get(name, default))
        except (TypeError, ValueError):
            return default

    return {
        "ema": [
            to_int("ema_short", ema[0]),
            to_int("ema_mid", ema[1]),
            to_int("ema_long", ema[2]),
        ],
        "rsi": to_int("rsi_period", ind["rsi"]),
        "macd": [
            to_int("macd_fast", macd[0]),
            to_int("macd_slow", macd[1]),
            to_int("macd_signal", macd[2]),
        ],
        "bollinger": [to_int("bb_period", boll[0]), to_float("bb_std", boll[1])],
        "vwap": to_int("vwap_period", ind.get("vwap", ind["volume_ma"])),
        "stoch": [
            to_int("stoch_k", 14),
            to_int("stoch_d", 3),
            to_int("stoch_smooth", 3),
        ],
        "adx": to_int("adx_period", 14),
        "obv": to_int("obv_lookback", ind.get("obv", 10)),
    }


def _to_int(q, name, default):
    try:
        return int(q.get(name, default))
    except (TypeError, ValueError):
        return default


def _to_float(q, name, default):
    try:
        return float(q.get(name, default))
    except (TypeError, ValueError):
        return default


def _dca_from_query(q):
    return {
        "symbol": q.get("symbol") or None,
        "timeframe": q.get("timeframe") or "4h",
        "days": _to_int(q, "days", 1900),
        "initial_capital": _to_float(q, "initial_capital", 1000.0),
        "level_mode": q.get("level_mode") or "fib",
        "levels": q.get("levels") or None,
        "level_base": _to_float(q, "level_base", 0.10),
        "allocation": q.get("allocation") or "deep",
        "allocations": q.get("allocations") or None,
        "reference_mode": q.get("reference_mode") or "anchor",
        "target_mode": q.get("target_mode") or "percent",
        "profit_target": _to_float(q, "profit_target", 15.0),
        "target_retrace": _to_float(q, "target_retrace", 0.5),
        "target_atr": _to_float(q, "target_atr", 3.0),
        "reinvest_pct": _to_float(q, "reinvest_pct", 50.0),
        "trend_filter": q.get("trend_filter") or "ema200",
        "ema_period": _to_int(q, "ema_period", 200),
        "atr_period": _to_int(q, "atr_period", 14),
        "reference_lookback": _to_int(q, "reference_lookback", 180),
        "swing_lookback": _to_int(q, "swing_lookback", 50),
    }


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    cfg = load_config()
    timeframe = cfg["timeframes"]["primary"]
    ema = cfg["indicators"]["ema"]
    bb_period, bb_std = cfg["indicators"]["bollinger"]
    vwap_period = cfg["indicators"]["vwap"]

    result = run_analysis(
        timeframe=timeframe,
        do_journal=False,
        selected=["rsi"],
        active={"regime", "ema_position", "bollinger", "vwap", "rsi"},
    )
    chart = get_chart_data(
        timeframe=timeframe,
        ema_periods=",".join(str(p) for p in ema),
        bb_period=bb_period,
        bb_std=bb_std,
        show_bb=True,
        show_vwap=True,
        vwap_period=vwap_period,
        osc="rsi",
    )
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "r": result,
            "timeframes": supported_timeframes(),
            "active_timeframe": timeframe,
            "ema_periods": ema,
            "bb_period": bb_period,
            "bb_std": bb_std,
            "vwap_period": vwap_period,
            "obv_lookback": cfg["indicators"].get("obv", 10),
            "review": get_param_review(timeframe=timeframe),
            "chart_json": json.dumps(chart),
        },
    )


@app.get("/dca", response_class=HTMLResponse)
def dca_page(request: Request):
    cfg = load_config()
    result = _guard(run_dca_report)
    symbols = list(dict.fromkeys([cfg["universe"]["pair"], "BTC/USDT", "ETH/USDT"]))
    return templates.TemplateResponse(
        request,
        "dca.html",
        {
            "result": result,
            "symbols": symbols,
            "presets": list(ALLOCATION_PRESETS),
            "timeframes": supported_timeframes(),
        },
    )


@app.get("/dca/run", response_class=HTMLResponse)
def dca_run(request: Request):
    result = _guard(run_dca_report, **_dca_from_query(request.query_params))
    return templates.TemplateResponse(request, "_dca.html", {"result": result})


@app.get("/api/dca")
def api_dca(request: Request):
    result = _guard(run_dca_report, **_dca_from_query(request.query_params))
    return serialize(result)


@app.get("/dca/report")
def dca_report(request: Request):
    result = _guard(run_dca_report, **_dca_from_query(request.query_params))
    if not isinstance(result, dict):
        return result
    return Response(
        to_markdown(result),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="dca-report.md"'},
    )


@app.get("/api/timeframes")
def api_timeframes():
    return supported_timeframes()


@app.get("/api/analysis")
def api_analysis(timeframe: str | None = None):
    return _guard(run_analysis, timeframe=timeframe, do_journal=False)


@app.get("/params/review", response_class=HTMLResponse)
def params_review(request: Request):
    cfg = load_config()
    params = _params_from_query(request.query_params, cfg)
    review = _guard(
        get_param_review,
        timeframe=request.query_params.get("timeframe"),
        params=params,
    )
    return templates.TemplateResponse(request, "_params.html", {"review": review})


@app.get("/api/explain")
def api_explain(request: Request, osc: str = "rsi"):
    cfg = load_config()
    params = _params_from_query(request.query_params, cfg)
    return _guard(
        get_explanations,
        timeframe=request.query_params.get("timeframe"),
        selected=_selected(osc),
        params=params,
        active=_active_from_query(request.query_params),
    )


@app.get("/api/chart")
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
    return _guard(
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


@app.get("/api/overlays")
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
    return _guard(
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


@app.get("/analysis/view", response_class=HTMLResponse)
def analysis_view(request: Request, osc: str = "rsi"):
    cfg = load_config()
    params = _params_from_query(request.query_params, cfg)
    result = _guard(
        run_analysis,
        timeframe=request.query_params.get("timeframe"),
        do_journal=False,
        selected=_selected(osc),
        params=params,
        active=_active_from_query(request.query_params),
    )
    return templates.TemplateResponse(request, "_summary.html", {"r": result})


@app.post("/analysis/run", response_class=HTMLResponse)
def analysis_run(request: Request, osc: str = "rsi"):
    cfg = load_config()
    params = _params_from_query(request.query_params, cfg)
    result = _guard(
        run_analysis,
        timeframe=request.query_params.get("timeframe"),
        do_journal=True,
        selected=_selected(osc),
        params=params,
        active=_active_from_query(request.query_params),
    )
    return templates.TemplateResponse(request, "_summary.html", {"r": result})
