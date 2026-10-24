import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from trading_analysis.app import (
    get_chart_data,
    get_explanations,
    get_param_review,
    run_analysis,
    supported_timeframes,
)
from trading_analysis.config import load_config
from web.query import (
    active_from_query,
    guard,
    params_from_query,
    selected,
)
from web.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
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


@router.get("/api/timeframes")
def api_timeframes():
    return supported_timeframes()


@router.get("/api/analysis")
def api_analysis(timeframe: str | None = None):
    return guard(run_analysis, timeframe=timeframe, do_journal=False)


@router.get("/params/review", response_class=HTMLResponse)
def params_review(request: Request):
    cfg = load_config()
    params = params_from_query(request.query_params, cfg)
    review = guard(
        get_param_review,
        timeframe=request.query_params.get("timeframe"),
        params=params,
    )
    return templates.TemplateResponse(request, "_params.html", {"review": review})


@router.get("/api/explain")
def api_explain(request: Request, osc: str = "rsi"):
    cfg = load_config()
    params = params_from_query(request.query_params, cfg)
    return guard(
        get_explanations,
        timeframe=request.query_params.get("timeframe"),
        selected=selected(osc),
        params=params,
        active=active_from_query(request.query_params),
    )


@router.get("/analysis/view", response_class=HTMLResponse)
def analysis_view(request: Request, osc: str = "rsi"):
    cfg = load_config()
    params = params_from_query(request.query_params, cfg)
    result = guard(
        run_analysis,
        timeframe=request.query_params.get("timeframe"),
        do_journal=False,
        selected=selected(osc),
        params=params,
        active=active_from_query(request.query_params),
    )
    return templates.TemplateResponse(request, "_summary.html", {"r": result})


@router.post("/analysis/run", response_class=HTMLResponse)
def analysis_run(request: Request, osc: str = "rsi"):
    cfg = load_config()
    params = params_from_query(request.query_params, cfg)
    result = guard(
        run_analysis,
        timeframe=request.query_params.get("timeframe"),
        do_journal=True,
        selected=selected(osc),
        params=params,
        active=active_from_query(request.query_params),
    )
    return templates.TemplateResponse(request, "_summary.html", {"r": result})
