"""Runtime configuration. Missing values fall back to paths inside this project."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def sqlite_path(url: str) -> Path:
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise ValueError(f"Only sqlite URLs are supported, got {url}")
    raw = url[len(prefix) :]
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_settings() -> dict:
    load_dotenv(ROOT / ".env")
    data_dir = Path(os.getenv("DATA_DIR", ROOT / "05_Datasets"))
    database_url = os.getenv("DATABASE_URL", "sqlite:///./storage/decisions.db")
    return {
        "root": ROOT,
        "data_dir": data_dir,
        "documentation_path": Path(
            os.getenv("DOCUMENTATION_PATH", data_dir / "documentation.json")
        ),
        "development_path": Path(
            os.getenv("DEVELOPMENT_PATH", data_dir / "development_tickets.json")
        ),
        "database_path": sqlite_path(database_url),
        "confidence_threshold": float(os.getenv("CONFIDENCE_THRESHOLD", "0.45")),
        "retrieval_top_k": int(os.getenv("RETRIEVAL_TOP_K", "3")),
        "retrieval_min_score": float(os.getenv("RETRIEVAL_MIN_SCORE", "0.08")),
        "model_name": os.getenv("MODEL_NAME", "offline-extractive-v1"),
        "use_llm": _as_bool(os.getenv("USE_LLM"), False),
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "prompt_version": "PR-ANSWER v1.0",
        "requirement_ids": ["FR-01", "FR-02", "FR-03", "FR-04", "FR-05", "FR-06", "FR-07"],
    }
