"""Intent and urgency classification with a confidence score.

The model is a multinomial Naive Bayes fit only on development_tickets.json.
Validation tickets and any hidden set are never read here. Labels on the
ticket being classified are ignored.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict

from src.config import load_settings
from src.textutil import tokenize  # used for the short-ticket rule

# Policy from discovery, confirmed on the development set:
# these four intents are never safe to answer automatically.
POLICY_ESCALATE = {
    "compliance_request",
    "security_incident",
    "feature_request",
    "unclear_request",
}


class NaiveBayes:
    def __init__(self) -> None:
        self.labels: list[str] = []
        self.prior: dict[str, float] = {}
        self.counts: dict[str, Counter] = {}
        self.totals: dict[str, int] = {}
        self.vocab: set[str] = set()

    def train(self, pairs: list[tuple[str, str]]) -> None:
        grouped: dict[str, list[str]] = defaultdict(list)
        for text, label in pairs:
            grouped[label].append(text)
        self.labels = sorted(grouped)
        total_docs = sum(len(v) for v in grouped.values()) or 1
        self.prior = {label: len(rows) / total_docs for label, rows in grouped.items()}
        self.counts = {}
        self.totals = {}
        self.vocab = set()
        for label, rows in grouped.items():
            counts: Counter = Counter()
            for text in rows:
                counts.update(tokenize(text))
            self.counts[label] = counts
            self.totals[label] = sum(counts.values())
            self.vocab.update(counts)
        if not self.labels:
            self.labels = ["unclear_request"]
            self.prior = {"unclear_request": 1.0}
            self.counts = {"unclear_request": Counter()}
            self.totals = {"unclear_request": 0}

    def predict(self, text: str) -> tuple[str, float, list[dict]]:
        tokens = tokenize(text)
        if not tokens or not self.labels:
            fallback = "unclear_request" if "unclear_request" in self.prior else self.labels[0]
            return fallback, 0.2, [{"value": fallback, "confidence": 0.2}]

        vocab_size = max(len(self.vocab), 1)
        log_scores: dict[str, float] = {}
        for label in self.labels:
            score = math.log(self.prior.get(label, 1e-6))
            total = self.totals.get(label, 0)
            counts = self.counts.get(label, Counter())
            denom = total + vocab_size
            for token in tokens:
                score += math.log((counts.get(token, 0) + 1) / denom)
            log_scores[label] = score

        peak = max(log_scores.values())
        weights = {label: math.exp(score - peak) for label, score in log_scores.items()}
        normaliser = sum(weights.values()) or 1.0
        ranked = sorted(
            ((label, weight / normaliser) for label, weight in weights.items()),
            key=lambda item: item[1],
            reverse=True,
        )
        top_label, top_prob = ranked[0]
        alternatives = [
            {"value": label, "confidence": round(prob, 4)} for label, prob in ranked[:4]
        ]
        return top_label, float(top_prob), alternatives


_INTENT: NaiveBayes | None = None
_URGENCY: NaiveBayes | None = None


def _training_pairs(path) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    tickets = json.loads(path.read_text(encoding="utf-8"))
    intent_pairs = []
    urgency_pairs = []
    for ticket in tickets:
        subject = ticket.get("subject") or ""
        body = ticket.get("body") or ""
        text = f"{subject}\n{body}"
        labels = ticket.get("labels") or {}
        if labels.get("intent"):
            intent_pairs.append((text, labels["intent"]))
        if labels.get("urgency"):
            urgency_pairs.append((text, labels["urgency"]))
    return intent_pairs, urgency_pairs


def models() -> tuple[NaiveBayes, NaiveBayes]:
    global _INTENT, _URGENCY
    if _INTENT is not None and _URGENCY is not None:
        return _INTENT, _URGENCY
    settings = load_settings()
    path = settings["development_path"]
    intent_model = NaiveBayes()
    urgency_model = NaiveBayes()
    if path.exists():
        intent_pairs, urgency_pairs = _training_pairs(path)
        intent_model.train(intent_pairs)
        urgency_model.train(urgency_pairs)
    else:
        intent_model.train([("unclear", "unclear_request")])
        urgency_model.train([("unclear", "medium")])
    _INTENT = intent_model
    _URGENCY = urgency_model
    return intent_model, urgency_model


def classify(text: str) -> dict:
    intent_model, urgency_model = models()
    intent, confidence, alternatives = intent_model.predict(text)
    urgency, urgency_confidence, urgency_alternatives = urgency_model.predict(text)
    # Development tickets with three or fewer content words were all unclear
    # requests. A ticket that short does not identify a product problem, so the
    # safe action is to escalate rather than attach a loosely related article.
    if not text.strip() or len(tokenize(text)) <= 3:
        intent = "unclear_request"
        confidence = 0.2
        urgency = "low"
        urgency_confidence = 0.5
        alternatives = [
            {"value": "unclear_request", "confidence": 0.2},
            {"value": "other", "confidence": 0.05},
        ]
    return {
        "intent": intent,
        "confidence": round(confidence, 4),
        "alternatives": alternatives,
        "urgency": urgency,
        "urgency_confidence": round(urgency_confidence, 4),
        "urgency_alternatives": urgency_alternatives,
        "policy_escalate": intent in POLICY_ESCALATE,
    }
