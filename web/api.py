import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from trading_analysis.app import warm_all
from trading_analysis.config import ROOT
from web.routes import analysis_router, charts_router, dca_router


@asynccontextmanager
async def lifespan(app):
    threading.Thread(target=warm_all, daemon=True).start()
    yield


app = FastAPI(title="Trading Analysis", lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=str(ROOT / "web" / "static")),
    name="static",
)
app.include_router(analysis_router)
app.include_router(charts_router)
app.include_router(dca_router)
