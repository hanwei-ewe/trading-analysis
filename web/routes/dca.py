from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from trading_analysis.app import supported_timeframes
from trading_analysis.config import load_config
from trading_analysis.reporting import (
    ALLOCATION_PRESETS,
    run_dca_report,
    serialize,
    dca_to_markdown,
)
from web.query import dca_from_query, guard
from web.templating import templates

router = APIRouter()


@router.get("/dca", response_class=HTMLResponse)
def dca_page(request: Request):
    cfg = load_config()
    result = guard(run_dca_report)
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


@router.get("/dca/run", response_class=HTMLResponse)
def dca_run(request: Request):
    result = guard(run_dca_report, **dca_from_query(request.query_params))
    return templates.TemplateResponse(request, "_dca.html", {"result": result})


@router.get("/api/dca")
def api_dca(request: Request):
    result = guard(run_dca_report, **dca_from_query(request.query_params))
    return serialize(result)


@router.get("/dca/report")
def dca_report(request: Request):
    result = guard(run_dca_report, **dca_from_query(request.query_params))
    return Response(
        dca_to_markdown(result),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="dca-report.md"'},
    )
