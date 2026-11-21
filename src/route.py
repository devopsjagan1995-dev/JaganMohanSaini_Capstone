"""Decide whether to answer, escalate, or block. Same input, same decision."""

from __future__ import annotations


def decide(
    classification: dict,
    sources: list[dict],
    guardrail: dict,
    threshold: float,
) -> dict:
    confidence = float(classification["confidence"])
    intent = classification["intent"]

    if guardrail["results"].get("prompt_injection") == "block":
        action = "block"
        reason = (
            "Blocked because the ticket tries to change the system's instructions. "
            "The draft was not sent. The ticket is queued for a person."
        )
    elif guardrail["blocked"]:
        action = "block"
        detail = guardrail["findings"][0]["detail"] if guardrail["findings"] else "A check failed."
        reason = f"Blocked by a guardrail. {detail} The draft was not sent."
    elif classification.get("policy_escalate"):
        action = "escalate"
        reason = (
            f"Escalated because '{intent.replace('_', ' ')}' is on the never-auto-respond list. "
            "Security incidents, compliance requests, feature requests and unclear requests "
            "always go to a person, with a summary and any related articles attached."
        )
    elif not sources:
        action = "escalate"
        reason = (
            "Escalated because no documentation passage was relevant enough to cite. "
            "The system does not invent an answer when retrieval returns nothing."
        )
    elif confidence < threshold:
        action = "escalate"
        reason = (
            f"Escalated because the intent confidence was {confidence:.2f}, "
            f"below the threshold of {threshold:.2f}. "
            "The closest articles are attached so the agent does not start from a blank ticket."
        )
    else:
        action = "auto_respond"
        top = sources[0]
        reason = (
            f"Answered automatically because the intent confidence was {confidence:.2f}, "
            f"which is at or above {threshold:.2f}, and {top['doc_id']} "
            f"('{top['title']}') matched with score {top['score']:.2f}. "
            "The reply cites only that retrieved material."
        )

    return {"action": action, "reason": reason, "threshold": threshold}
