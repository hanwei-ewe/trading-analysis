from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path=None):
    config_path = Path(path) if path else ROOT / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def resolve_path(relative):
    p = Path(relative)
    return p if p.is_absolute() else ROOT / p
