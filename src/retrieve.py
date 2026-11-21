"""Search the documentation corpus and return real, scored passages.

Articles are split on their own headings (Symptoms, Common causes, Resolution,
Notes) rather than on a fixed character count. A resolution sequence stays in
one passage, which is the unit a citation has to support.

Scoring is cosine similarity over a local TF-IDF index. No model is downloaded.
A query that matches nothing useful returns an empty list.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter

from src.config import load_settings
from src.textutil import tokenize

HEADING = re.compile(r"\n## ")
_INDEX: "CorpusIndex | None" = None


class CorpusIndex:
    def __init__(self, passages: list[dict], idf: dict[str, float]) -> None:
        self.passages = passages
        self.idf = idf
        self.doc_ids = sorted({item["doc_id"] for item in passages})

    def search(self, query: str, top_k: int, min_score: float) -> list[dict]:
        query_weights = self._weights(tokenize(query))
        if not query_weights:
            return []
        query_norm = math.sqrt(sum(value * value for value in query_weights.values()))
        ranked = []
        for passage in self.passages:
            dot = sum(
                weight * passage["weights"].get(term, 0.0)
                for term, weight in query_weights.items()
            )
            if dot <= 0 or passage["norm"] == 0 or query_norm == 0:
                continue
            score = dot / (passage["norm"] * query_norm)
            if score < min_score:
                continue
            ranked.append((score, passage))
        ranked.sort(key=lambda item: item[0], reverse=True)
        results = []
        for score, passage in ranked[:top_k]:
            results.append(
                {
                    "doc_id": passage["doc_id"],
                    "title": passage["title"],
                    "section": passage["section"],
                    "score": round(score, 4),
                    "passage": passage["text"],
                }
            )
        return results

    def _weights(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        if not counts:
            return {}
        length = sum(counts.values())
        return {
            term: (count / length) * self.idf.get(term, 0.0)
            for term, count in counts.items()
            if term in self.idf
        }


def _chunks(document: dict) -> list[tuple[str, str]]:
    content = document.get("content") or ""
    pieces = HEADING.split(content)
    chunks = []
    for piece in pieces:
        text = piece.strip()
        if len(text) < 40:
            continue
        section = text.split("\n", 1)[0][:80]
        titled = f"{document.get('title', '')}\n{text}"
        chunks.append((section, titled))
    if not chunks and content.strip():
        chunks.append(("full", f"{document.get('title', '')}\n{content.strip()}"))
    return chunks


def build_index(path) -> CorpusIndex:
    documents = json.loads(path.read_text(encoding="utf-8"))
    raw_chunks = []
    for document in documents:
        for section, text in _chunks(document):
            tokens = tokenize(text)
            raw_chunks.append(
                {
                    "doc_id": document["doc_id"],
                    "title": document.get("title", ""),
                    "section": section,
                    "text": text,
                    "tokens": tokens,
                }
            )
    doc_freq: Counter = Counter()
    for chunk in raw_chunks:
        doc_freq.update(set(chunk["tokens"]))
    total = len(raw_chunks) or 1
    idf = {
        term: math.log((1 + total) / (1 + freq)) + 1.0 for term, freq in doc_freq.items()
    }
    passages = []
    for chunk in raw_chunks:
        counts = Counter(chunk["tokens"])
        length = sum(counts.values()) or 1
        weights = {
            term: (count / length) * idf[term] for term, count in counts.items() if term in idf
        }
        norm = math.sqrt(sum(value * value for value in weights.values()))
        passages.append(
            {
                "doc_id": chunk["doc_id"],
                "title": chunk["title"],
                "section": chunk["section"],
                "text": chunk["text"],
                "weights": weights,
                "norm": norm,
            }
        )
    return CorpusIndex(passages, idf)


def get_index() -> CorpusIndex:
    global _INDEX
    if _INDEX is None:
        settings = load_settings()
        _INDEX = build_index(settings["documentation_path"])
    return _INDEX


def retrieve(query: str, top_k: int | None = None, min_score: float | None = None) -> list[dict]:
    settings = load_settings()
    index = get_index()
    return index.search(
        query,
        top_k if top_k is not None else settings["retrieval_top_k"],
        min_score if min_score is not None else settings["retrieval_min_score"],
    )
