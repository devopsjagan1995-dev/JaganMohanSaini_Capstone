"""Checks that can stop a response. A warning that still sends is not a guardrail."""

from __future__ import annotations

import re

INJECTION_PHRASES = (
    "ignore previous",
    "ignore all previous",
    "ignore your instructions",
    "disregard your",
    "disregard the above",
    "you are now",
    "system prompt",
    "jailbreak",
    "do not follow",
    "new instructions",
)

FORBIDDEN_CLAIMS = (
    "a refund has been issued",
    "refund has been issued",
    "the issue has been fixed",
    "issue has been fixed on our side",
    "we have fixed this",
    "this will be delivered on",
    "guaranteed delivery date",
    "your money has been refunded",
)

CARD = re.compile(r"\b(?:\d[ -]?){13,16}\b")
SECRET = re.compile(
    r"\b(?:sk|rk|pk|api)[_-][A-Za-z0-9]{12,}\b|\bAKIA[0-9A-Z]{16}\b",
    re.IGNORECASE,
)
EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


def _status(findings: list[dict], name: str) -> str:
    return "block" if any(item["type"] == name for item in findings) else "pass"


def review(ticket_text: str, draft: str, sources: list[dict]) -> dict:
    findings = []
    lowered = (ticket_text or "").lower()
    draft_lower = (draft or "").lower()

    if any(phrase in lowered for phrase in INJECTION_PHRASES):
        findings.append(
            {
                "type": "prompt_injection",
                "detail": "The ticket tries to override the system instructions.",
            }
        )

    for claim in FORBIDDEN_CLAIMS:
        if claim in draft_lower:
            findings.append(
                {
                    "type": "forbidden_claim",
                    "detail": f"The draft makes a claim the system must not make: {claim}.",
                }
            )
            break

    if CARD.search(draft or "") or SECRET.search(draft or ""):
        findings.append(
            {
                "type": "pii",
                "detail": "The draft contains a payment number or a credential-like string.",
            }
        )

    # An email address that the customer did not themselves supply is treated as a leak.
    customer_emails = {match.lower() for match in EMAIL.findall(ticket_text or "")}
    for match in EMAIL.findall(draft or ""):
        if match.lower() not in customer_emails:
            findings.append(
                {
                    "type": "pii",
                    "detail": "The draft contains an email address that was not in the ticket.",
                }
            )
            break

    retrieved_ids = {source["doc_id"] for source in sources}
    cited = set(re.findall(r"DOC-[A-Z]+-\d+", draft or ""))
    if cited and not cited.issubset(retrieved_ids):
        findings.append(
            {
                "type": "grounding",
                "detail": "The draft cites a document that was not retrieved.",
            }
        )

    blocked = bool(findings)
    return {
        "blocked": blocked,
        "findings": findings,
        "results": {
            "prompt_injection": _status(findings, "prompt_injection"),
            "pii": _status(findings, "pii"),
            "forbidden_claim": _status(findings, "forbidden_claim"),
            "grounding": _status(findings, "grounding"),
        },
    }
