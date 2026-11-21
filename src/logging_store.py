"""One persistent row for every ticket the system decides on."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    decision_id     TEXT PRIMARY KEY,
    created_at      TEXT NOT NULL,
    ticket_id       TEXT NOT NULL,
    stage           TEXT NOT NULL,
    prediction      TEXT,
    confidence      REAL,
    threshold_applied REAL,
    action_taken    TEXT NOT NULL,
    reason          TEXT NOT NULL,
    sources_used    TEXT,
    guardrails      TEXT,
    prompt_version  TEXT,
    requirement_ids TEXT,
    input_summary   TEXT,
    alternatives    TEXT,
    channel         TEXT,
    customer_tier   TEXT,
    customer_region TEXT,
    language_fluency TEXT,
    latency_ms      REAL
)
"""


class DecisionLog:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(SCHEMA)
        self._connection.commit()

    def write(self, record: dict) -> None:
        self._connection.execute(
            """
            INSERT OR REPLACE INTO decisions (
                decision_id, created_at, ticket_id, stage, prediction, confidence,
                threshold_applied, action_taken, reason, sources_used, guardrails,
                prompt_version, requirement_ids, input_summary, alternatives,
                channel, customer_tier, customer_region, language_fluency, latency_ms
            ) VALUES (
                :decision_id, :created_at, :ticket_id, :stage, :prediction, :confidence,
                :threshold_applied, :action_taken, :reason, :sources_used, :guardrails,
                :prompt_version, :requirement_ids, :input_summary, :alternatives,
                :channel, :customer_tier, :customer_region, :language_fluency, :latency_ms
            )
            """,
            record,
        )
        self._connection.commit()

    def count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) AS n FROM decisions").fetchone()
        return int(row["n"])

    def ticket_ids(self) -> list[str]:
        rows = self._connection.execute(
            "SELECT ticket_id FROM decisions ORDER BY created_at"
        ).fetchall()
        return [row["ticket_id"] for row in rows]

    def close(self) -> None:
        self._connection.close()


def make_record(result: dict, settings: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "decision_id": result["decision_id"],
        "created_at": now,
        "ticket_id": result["ticket_id"],
        "stage": "routing",
        "prediction": json.dumps(
            {"intent": result["intent"], "urgency": result["urgency"]}
        ),
        "confidence": result["confidence"],
        "threshold_applied": result["threshold"],
        "action_taken": result["action"],
        "reason": result["reason"],
        "sources_used": json.dumps(
            [
                {"doc_id": source["doc_id"], "score": source["score"], "title": source["title"]}
                for source in result["sources"]
            ]
        ),
        "guardrails": json.dumps(result["guardrails"]),
        "prompt_version": settings["prompt_version"],
        "requirement_ids": json.dumps(settings["requirement_ids"]),
        "input_summary": result["input_summary"],
        "alternatives": json.dumps(result["alternatives"]),
        "channel": result["channel"],
        "customer_tier": result["customer_tier"],
        "customer_region": result["customer_region"],
        "language_fluency": result["language_fluency"],
        "latency_ms": result["latency_ms"],
    }
