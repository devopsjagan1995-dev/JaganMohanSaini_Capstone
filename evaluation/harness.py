"""Process every ticket in an input file and write a metrics report.

Example:
    python -m evaluation.harness --input 05_Datasets/validation_tickets.json --output evaluation/results/validation
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.config import ROOT, load_settings
from src.logging_store import DecisionLog
from src.pipeline import process_ticket

from evaluation.metrics import build_report, render_markdown


def run(input_path: Path, output_path: Path) -> dict:
    tickets = json.loads(input_path.read_text(encoding="utf-8"))
    if isinstance(tickets, dict):
        tickets = tickets.get("tickets") or tickets.get("data") or []
    if not isinstance(tickets, list):
        raise SystemExit("Input JSON must be a list of tickets.")

    output_path.mkdir(parents=True, exist_ok=True)
    settings = load_settings()
    settings = dict(settings)
    settings["database_path"] = output_path / "decisions.db"
    if settings["database_path"].exists():
        settings["database_path"].unlink()
    store = DecisionLog(settings["database_path"])
    rows = []
    try:
        for index, raw in enumerate(tickets):
            if not isinstance(raw, dict):
                raw = {"ticket_id": f"MALFORMED-{index}", "body": str(raw), "channel": "email"}
            result = process_ticket(raw, settings=settings, store=store)
            labels = raw.get("labels") if isinstance(raw, dict) else None
            labels = labels or {}
            rows.append(
                {
                    **result,
                    "logged": True,
                    "true_intent": labels.get("intent"),
                    "true_urgency": labels.get("urgency"),
                    "expected_route": labels.get("expected_route"),
                    "answerable_from_docs": labels.get("answerable_from_docs"),
                    "expected_doc_ids": labels.get("expected_doc_ids") or [],
                    "must_not_auto_respond": labels.get("must_not_auto_respond"),
                }
            )
    finally:
        logged = store.count()
        store.close()

    report = build_report(rows)
    report["governance"]["decisions_logged"] = logged
    report["governance"]["log_reconciles"] = logged == len(rows)
    report["run"] = {
        "input": str(input_path),
        "tickets": len(rows),
        "system": "offline-extractive-v1",
    }

    (output_path / "results.json").write_text(
        json.dumps(rows, indent=2, default=str), encoding="utf-8"
    )
    (output_path / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output_path / "metrics.md").write_text(render_markdown(report), encoding="utf-8")

    if logged != len(rows):
        raise SystemExit(
            f"Decision log does not reconcile: logged {logged}, processed {len(rows)}."
        )
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the support router over a ticket file.")
    parser.add_argument("--input", required=True, help="Path to a JSON ticket file.")
    parser.add_argument("--output", required=True, help="Directory for the metrics report.")
    args = parser.parse_args(argv)
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = ROOT / input_path
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    report = run(input_path, output_path)
    volume = report["volume"]
    print(
        f"Processed {volume['tickets_processed']} tickets. "
        f"Answered {volume['answered_automatically']}, "
        f"escalated {volume['escalated']}, "
        f"blocked {volume['blocked_by_guardrails']}."
    )
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
