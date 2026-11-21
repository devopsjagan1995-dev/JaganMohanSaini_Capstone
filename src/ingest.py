"""Normalise tickets from the four CloudServe channels into one shape."""

from __future__ import annotations

CHANNELS = ("email", "chat", "docs_comment", "forum")


def normalise(raw) -> dict:
    """Accept a ticket dict. Missing or odd fields do not raise."""
    if not isinstance(raw, dict):
        raw = {"body": "" if raw is None else str(raw), "channel": "email"}

    channel_raw = raw.get("channel")
    channel = str(channel_raw or "email").strip().lower()
    channel_known = channel in CHANNELS
    if not channel_known:
        channel = "email"

    subject = raw.get("subject")
    body = raw.get("body")
    subject = "" if subject is None else str(subject)
    body = "" if body is None else str(body)

    ticket_id = raw.get("ticket_id")
    ticket_id = "UNKNOWN" if ticket_id is None else str(ticket_id)

    labels = raw.get("labels")
    if not isinstance(labels, dict):
        labels = None

    return {
        "ticket_id": ticket_id,
        "channel": channel,
        "channel_known": channel_known,
        "subject": subject,
        "body": body,
        "text": f"{subject}\n{body}".strip(),
        "received_at": "" if raw.get("received_at") is None else str(raw.get("received_at")),
        "customer_id": "" if raw.get("customer_id") is None else str(raw.get("customer_id")),
        "customer_name": "" if raw.get("customer_name") is None else str(raw.get("customer_name")),
        "customer_tier": "" if raw.get("customer_tier") is None else str(raw.get("customer_tier")),
        "customer_region": "" if raw.get("customer_region") is None else str(raw.get("customer_region")),
        "language_fluency": ""
        if raw.get("language_fluency") is None
        else str(raw.get("language_fluency")),
        "labels": labels,
        "malformed": (not channel_known) or (not subject.strip() and not body.strip()),
    }
