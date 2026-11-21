"""Run one ticket through ingest, classify, retrieve, generate, validate and route."""

from __future__ import annotations

import time
import uuid

from prometheus_client import Counter, Histogram

from src.classify import classify
from src.config import load_settings
from src.generate import HOLDING, draft_answer, try_llm
from src.guardrails import review
from src.ingest import normalise
from src.logging_store import DecisionLog, make_record
from src.retrieve import retrieve
from src.route import decide

TICKETS = Counter(
    "tickets_processed_total",
    "Tickets processed",
    ["channel", "outcome"],
)
GUARDRAIL = Counter(
    "guardrail_blocks_total",
    "Responses blocked",
    ["guardrail"],
)
LATENCY = Histogram(
    "response_seconds",
    "End to end response time",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)


def _agent_brief(ticket: dict, classification: dict, sources: list[dict], reason: str, draft: str) -> str:
    source_lines = "\n".join(
        f"- {source['doc_id']} ({source['title']}), score {source['score']}" for source in sources
    ) or "- none"
    return (
        f"Ticket {ticket['ticket_id']} via {ticket['channel']}.\n"
        f"Customer: {ticket['customer_name'] or 'unknown'} "
        f"({ticket['customer_tier'] or 'unknown tier'}, "
        f"{ticket['language_fluency'] or 'fluency not set'}).\n"
        f"Intent: {classification['intent']} (confidence {classification['confidence']}). "
        f"Urgency: {classification['urgency']}.\n"
        f"Why this was not sent automatically: {reason}\n"
        f"Closest documentation:\n{source_lines}\n"
        f"Draft that was NOT sent to the customer:\n{draft[:700]}"
    )


def process_ticket(raw, settings: dict | None = None, store: DecisionLog | None = None) -> dict:
    settings = settings or load_settings()
    started = time.perf_counter()
    ticket = normalise(raw)

    with LATENCY.time():
        classification = classify(ticket["text"])
        sources = retrieve(
            ticket["text"],
            top_k=settings["retrieval_top_k"],
            min_score=settings["retrieval_min_score"],
        )
        drafted = draft_answer(ticket, classification, sources)
        llm_text = try_llm(settings, ticket, sources)
        if llm_text and sources:
            drafted["message"] = llm_text
        guardrail = review(ticket["text"], drafted["message"], sources)
        # Injection is judged on the ticket even when the draft itself is clean.
        if any(item["type"] == "prompt_injection" for item in guardrail["findings"]):
            guardrail["blocked"] = True
        decision = decide(
            classification,
            sources,
            guardrail,
            settings["confidence_threshold"],
        )

    latency_ms = round((time.perf_counter() - started) * 1000, 3)
    action = decision["action"]
    if action == "auto_respond":
        customer_message = drafted["message"]
        agent_brief = ""
    else:
        customer_message = HOLDING
        agent_brief = _agent_brief(
            ticket, classification, sources, decision["reason"], drafted["message"]
        )

    for finding in guardrail["findings"]:
        GUARDRAIL.labels(guardrail=finding["type"]).inc()
    TICKETS.labels(channel=ticket["channel"], outcome=action).inc()

    result = {
        "decision_id": f"{ticket['ticket_id']}-{uuid.uuid4().hex[:8]}",
        "ticket_id": ticket["ticket_id"],
        "channel": ticket["channel"],
        "customer_tier": ticket["customer_tier"],
        "customer_region": ticket["customer_region"],
        "language_fluency": ticket["language_fluency"],
        "intent": classification["intent"],
        "urgency": classification["urgency"],
        "confidence": classification["confidence"],
        "alternatives": classification["alternatives"],
        "sources": sources,
        "citations": drafted["citations"] if action == "auto_respond" else [],
        "action": action,
        "reason": decision["reason"],
        "threshold": decision["threshold"],
        "customer_message": customer_message,
        "agent_brief": agent_brief,
        "guardrails": guardrail["results"],
        "guardrail_findings": guardrail["findings"],
        "latency_ms": latency_ms,
        "input_summary": ticket["text"][:400],
        "model": settings["model_name"] if settings.get("use_llm") else "offline-extractive-v1",
    }

    if store is not None:
        store.write(make_record(result, settings))
    return result
