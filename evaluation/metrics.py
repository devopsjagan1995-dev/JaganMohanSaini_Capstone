"""Metrics the harness writes without any manual calculation."""

from __future__ import annotations

import statistics


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def classification_scores(rows: list[dict]) -> dict:
    labelled = [row for row in rows if row.get("true_intent")]
    labels = sorted({row["true_intent"] for row in labelled} | {row["intent"] for row in labelled})
    per_class = {}
    precisions = []
    recalls = []
    for label in labels:
        tp = sum(1 for row in labelled if row["true_intent"] == label and row["intent"] == label)
        fp = sum(1 for row in labelled if row["true_intent"] != label and row["intent"] == label)
        fn = sum(1 for row in labelled if row["true_intent"] == label and row["intent"] != label)
        precision = _safe_rate(tp, tp + fp)
        recall = _safe_rate(tp, tp + fn)
        per_class[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "support": tp + fn,
        }
        if tp + fp:
            precisions.append(precision)
        if tp + fn:
            recalls.append(recall)
    correct = sum(1 for row in labelled if row["true_intent"] == row["intent"])
    return {
        "accuracy": round(_safe_rate(correct, len(labelled)), 4),
        "macro_precision": round(sum(precisions) / len(precisions), 4) if precisions else 0.0,
        "macro_recall": round(sum(recalls) / len(recalls), 4) if recalls else 0.0,
        "per_class": per_class,
        "labelled_tickets": len(labelled),
    }


def fairness(rows: list[dict]) -> dict:
    def segment(field: str) -> dict:
        groups: dict[str, list[dict]] = {}
        for row in rows:
            key = row.get(field) or "unknown"
            groups.setdefault(key, []).append(row)
        summary = {}
        rates = []
        for key, group in sorted(groups.items()):
            answered = sum(1 for row in group if row["action"] == "auto_respond")
            labelled = [row for row in group if row.get("true_intent")]
            correct = sum(1 for row in labelled if row["true_intent"] == row["intent"])
            rate = _safe_rate(answered, len(group))
            rates.append(rate)
            summary[key] = {
                "tickets": len(group),
                "auto_respond_rate": round(rate, 4),
                "classification_accuracy": round(_safe_rate(correct, len(labelled)), 4),
            }
        gap = (max(rates) - min(rates)) if len(rates) >= 2 else 0.0
        summary["max_gap"] = round(gap, 4)
        return summary

    return {
        "by_tier": segment("customer_tier"),
        "by_region": segment("customer_region"),
        "by_fluency": segment("language_fluency"),
    }


def build_report(rows: list[dict]) -> dict:
    total = len(rows)
    answered = sum(1 for row in rows if row["action"] == "auto_respond")
    blocked = sum(1 for row in rows if row["action"] == "block")
    escalated = sum(1 for row in rows if row["action"] in {"escalate", "block"})
    latencies = [row["latency_ms"] / 1000 for row in rows]
    reply_minutes = [row["latency_ms"] / 60000 for row in rows]

    activations: dict[str, int] = {}
    pii = 0
    for row in rows:
        for finding in row.get("guardrail_findings") or []:
            activations[finding["type"]] = activations.get(finding["type"], 0) + 1
            if finding["type"] == "pii":
                pii += 1

    retrieval_eligible = [
        row for row in rows if row.get("answerable_from_docs") and row.get("expected_doc_ids")
    ]
    hits = 0
    for row in retrieval_eligible:
        retrieved = {source["doc_id"] for source in row["sources"]}
        if retrieved.intersection(row["expected_doc_ids"]):
            hits += 1

    citation_checks = 0
    citation_ok = 0
    for row in rows:
        if row["action"] != "auto_respond":
            continue
        retrieved = {source["doc_id"] for source in row["sources"]}
        for doc_id in row["citations"]:
            citation_checks += 1
            if doc_id in retrieved:
                citation_ok += 1

    classes = classification_scores(rows)
    return {
        "volume": {
            "tickets_processed": total,
            "answered_automatically": answered,
            "escalated": escalated,
            "blocked_by_guardrails": blocked,
        },
        "business": {
            "first_contact_resolution": round(_safe_rate(answered, total), 4),
            "mean_response_time_minutes": round(statistics.mean(reply_minutes), 6) if reply_minutes else 0,
            "median_response_time_minutes": round(statistics.median(reply_minutes), 6) if reply_minutes else 0,
            "escalation_rate": round(_safe_rate(escalated, total), 4),
            "baseline_first_contact_resolution": 0.42,
            "baseline_escalation_rate": 0.58,
            "target_first_contact_resolution": 0.60,
            "target_escalation_rate": 0.30,
        },
        "technical": {
            "classification_precision_macro": classes["macro_precision"],
            "classification_recall_macro": classes["macro_recall"],
            "classification_accuracy": classes["accuracy"],
            "per_class": classes["per_class"],
            "retrieval_hit_rate": round(_safe_rate(hits, len(retrieval_eligible)), 4),
            "citation_accuracy": round(_safe_rate(citation_ok, citation_checks), 4) if citation_checks else 1.0,
            "latency_median_seconds": round(_percentile(latencies, 0.50), 4),
            "latency_p95_seconds": round(_percentile(latencies, 0.95), 4),
        },
        "governance": {
            "decisions_logged": sum(1 for row in rows if row.get("logged")),
            "guardrail_activations_by_type": activations,
            "private_data_detections": pii,
            "tickets_processed": total,
            "log_reconciles": sum(1 for row in rows if row.get("logged")) == total,
        },
        "fairness": fairness(rows),
    }


def render_markdown(report: dict) -> str:
    volume = report["volume"]
    business = report["business"]
    technical = report["technical"]
    governance = report["governance"]
    lines = [
        "# Evaluation report",
        "",
        "## Volume",
        f"- Tickets processed: {volume['tickets_processed']}",
        f"- Answered automatically: {volume['answered_automatically']}",
        f"- Escalated (including blocked): {volume['escalated']}",
        f"- Blocked by guardrails: {volume['blocked_by_guardrails']}",
        "",
        "## Business",
        f"- First contact resolution: {business['first_contact_resolution']:.1%} "
        f"(baseline {business['baseline_first_contact_resolution']:.0%}, "
        f"target {business['target_first_contact_resolution']:.0%})",
        f"- Mean response time: {business['mean_response_time_minutes'] * 60:.3f} seconds "
        f"({business['mean_response_time_minutes']:.6f} minutes)",
        f"- Median response time: {business['median_response_time_minutes'] * 60:.3f} seconds "
        f"({business['median_response_time_minutes']:.6f} minutes)",
        f"- Escalation rate: {business['escalation_rate']:.1%} "
        f"(baseline {business['baseline_escalation_rate']:.0%}, "
        f"target {business['target_escalation_rate']:.0%})",
        "",
        "## Technical",
        f"- Classification accuracy: {technical['classification_accuracy']:.1%}",
        f"- Macro precision: {technical['classification_precision_macro']:.1%}",
        f"- Macro recall: {technical['classification_recall_macro']:.1%}",
        f"- Retrieval hit rate: {technical['retrieval_hit_rate']:.1%}",
        f"- Citation accuracy: {technical['citation_accuracy']:.1%}",
        f"- Latency median: {technical['latency_median_seconds']:.4f}s",
        f"- Latency 95th percentile: {technical['latency_p95_seconds']:.4f}s",
        "",
        "## Governance",
        f"- Decisions logged: {governance['decisions_logged']}",
        f"- Log reconciles with tickets: {governance['log_reconciles']}",
        f"- Private data detections: {governance['private_data_detections']}",
        f"- Guardrail activations: {governance['guardrail_activations_by_type']}",
        "",
        "## Fairness (automatic-answer rate)",
        f"- By tier: {report['fairness']['by_tier']}",
        f"- By region: {report['fairness']['by_region']}",
        f"- By language fluency: {report['fairness']['by_fluency']}",
        "",
    ]
    return "\n".join(lines)
