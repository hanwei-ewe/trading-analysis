from fastapi.templating import Jinja2Templates

from trading_analysis.config import ROOT

templates = Jinja2Templates(directory=str(ROOT / "web" / "templates"))
