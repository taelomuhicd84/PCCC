"""Nạp cấu hình: config/settings.yaml + biến môi trường (.env)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
RULES_DIR = PROJECT_ROOT / "rules"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

DEFAULTS: dict[str, Any] = {
    "gemini": {"model": "gemini-2.5-flash", "dpi": 150, "max_tile_px": 3000, "temperature": 0.1},
    "rules": {"packs": ["qcvn06_2022_sd01_2023.yaml"]},
    "annotate": {"min_severity": "info", "font_size": 7},
}


def _load_dotenv() -> None:
    env = PROJECT_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_settings(path: Path | None = None) -> dict[str, Any]:
    _load_dotenv()
    path = path or CONFIG_DIR / "settings.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    return _merge(DEFAULTS, data or {})


def gemini_api_key() -> str | None:
    _load_dotenv()
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
