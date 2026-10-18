import json
from datetime import datetime, timezone

from .config import load_config, resolve_path


def write(result, config_path=None):
    cfg = load_config(config_path)
    journal_dir = resolve_path(cfg["paths"]["journal"])
    journal_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    symbol = str(result.get("symbol", "ETH_USDT")).replace("/", "_")
    timeframe = result.get("timeframe", "1h")
    base = journal_dir / f"{stamp}_{symbol}_{timeframe}"

    with open(f"{base}.json", "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, default=str)
    with open(f"{base}.md", "w", encoding="utf-8") as fh:
        fh.write(result.get("markdown", ""))

    return str(base)
