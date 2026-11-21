"""FastAPI service. Start with: python -m uvicorn src.api:app --port 8000"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest

from src.config import load_settings
from src.logging_store import DecisionLog
from src.pipeline import process_ticket

app = FastAPI(title="CloudServe Support Router", version="1.0.0")


def _store() -> DecisionLog:
    return DecisionLog(load_settings()["database_path"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": "offline-extractive"}


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type="text/plain")


@app.post("/tickets")
def submit_ticket(payload: dict) -> dict:
    store = _store()
    try:
        return process_ticket(payload, store=store)
    finally:
        store.close()
