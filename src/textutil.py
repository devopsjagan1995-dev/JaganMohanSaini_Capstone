"""Small token helpers shared by classification and retrieval."""

from __future__ import annotations

import re

TOKEN = re.compile(r"[a-z0-9]+")

STOP = {
    "the", "and", "for", "with", "that", "this", "from", "have", "has", "had",
    "are", "was", "were", "been", "being", "but", "not", "you", "your", "our",
    "can", "could", "would", "should", "what", "when", "where", "which", "who",
    "how", "why", "into", "about", "than", "then", "them", "they", "their",
    "there", "here", "just", "also", "any", "all", "some", "more", "most",
    "very", "over", "under", "after", "before", "because", "while", "does",
    "did", "doing", "please", "thanks", "thank", "hello", "help", "need",
    "able", "cannot", "cant", "will", "want", "like", "get", "got", "one",
    "two", "out", "off", "too", "its", "it", "a", "an", "of", "to", "in",
    "on", "at", "by", "or", "if", "is", "be", "we", "i", "my", "me", "us",
    "am", "as", "so", "do", "no", "yes", "hi",
}


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    return [tok for tok in TOKEN.findall(text.lower()) if len(tok) > 2 and tok not in STOP]
