"""Draft an answer only from retrieved passages. If nothing was retrieved, say so."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from src.retrieve import get_index


HOLDING = (
    "Thank you for contacting CloudServe Support. A specialist will reply to this ticket. "
    "This note was sent automatically so you are not left waiting in silence. "
    "It is not a technical answer, and nothing in your account has been changed."
)


def _resolution_passage(sources: list[dict]) -> dict | None:
    """Prefer the Resolution section of the best-matching article.

    Retrieval may rank the title or the symptoms higher than the steps.
    The customer needs the steps, and the citation still names that article.
    """
    if not sources:
        return None
    chosen = sources[0]
    for passage in get_index().passages:
        if passage["doc_id"] == chosen["doc_id"] and passage["section"].lower().startswith("resolution"):
            return {
                **chosen,
                "section": passage["section"],
                "passage": passage["text"],
            }
    return chosen


def draft_answer(ticket: dict, classification: dict, sources: list[dict]) -> dict:
    citations = []
    for source in sources:
        if source["doc_id"] not in citations:
            citations.append(source["doc_id"])

    if not sources:
        message = (
            "Thank you for contacting CloudServe Support. "
            "I could not find a knowledge-base article that matches this request, "
            "so I am not going to guess. A specialist will take it from here. "
            "This note was drafted automatically."
        )
        return {"message": message, "citations": [], "grounded": False}

    chosen = _resolution_passage(sources)
    others = [source for source in sources if source["doc_id"] != chosen["doc_id"]]
    extra = ""
    if others:
        extra = " Related articles: " + ", ".join(
            f"{source['doc_id']} ({source['title']})" for source in others[:2]
        ) + "."

    passage = chosen["passage"].strip()
    if len(passage) > 900:
        passage = passage[:900].rsplit(" ", 1)[0] + "..."

    name = ticket.get("customer_name") or "there"
    message = (
        f"Hello {name}. This reply was drafted automatically from CloudServe's "
        f"support documentation. Please check the cited article before you act on it.\n\n"
        f"I read this as {classification['intent'].replace('_', ' ')} "
        f"({classification['urgency']} urgency).\n\n"
        f"From {chosen['title']} ({chosen['doc_id']}):\n{passage}\n\n"
        f"Citation: {chosen['doc_id']}."
        f"{extra}\n"
        "If this does not match what you are seeing, reply with what happened at each step "
        "and a person will look at the account directly. Nothing has been changed on our side."
    )
    return {"message": message, "citations": citations, "grounded": True}


def try_llm(settings: dict, ticket: dict, sources: list[dict]) -> str | None:
    """Optional OpenRouter call. Any failure returns None so the offline draft is used."""
    key = (settings.get("openrouter_api_key") or "").strip()
    if not settings.get("use_llm") or not key or key == "your_key_here":
        return None
    context = "\n\n".join(
        f"{source['doc_id']}: {source['passage'][:500]}" for source in sources[:2]
    )
    payload = {
        "model": settings.get("model_name") or "meta-llama/llama-3.1-8b-instruct",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Answer only from the supplied documentation. Cite the doc id. "
                    "If the documentation does not cover it, say you do not know. "
                    "Never claim a refund was issued or that an issue has been fixed."
                ),
            },
            {
                "role": "user",
                "content": f"Ticket:\n{ticket.get('text', '')[:1500]}\n\nDocumentation:\n{context}",
            },
        ],
        "temperature": 0,
    }
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]
    except (urllib.error.URLError, TimeoutError, KeyError, json.JSONDecodeError, OSError):
        return None
