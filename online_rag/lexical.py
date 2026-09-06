"""Small dependency-free BM25 index with mixed Chinese/Latin tokenization."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Sequence

from .models import Chunk


_TOKEN_RE = re.compile(r"[a-z]+(?:[-_][a-z0-9]+)*|\d+(?:\.\d+)?|[α-ωΑ-ΩμΩ]+", re.I)
_CJK_RE = re.compile(r"[\u3400-\u9fff]+")


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text or "").casefold()
    tokens = _TOKEN_RE.findall(normalized)
    for run in _CJK_RE.findall(normalized):
        tokens.extend(run)
        tokens.extend(run[i:i + 2] for i in range(len(run) - 1))
    return tokens


class BM25Index:
    def __init__(self, chunks: Sequence[Chunk], *, k1: float = 1.5, b: float = 0.75):
        self.chunks = list(chunks)
        self.k1 = k1
        self.b = b
        self.term_frequencies: list[Counter[str]] = []
        document_frequency: dict[str, int] = defaultdict(int)
        self.lengths: list[int] = []
        for chunk in self.chunks:
            field_text = (
                (chunk.experiment_name + " ") * 3
                + (chunk.section + " ") * 2
                + chunk.text
            )
            frequencies = Counter(tokenize(field_text))
            self.term_frequencies.append(frequencies)
            length = sum(frequencies.values())
            self.lengths.append(length)
            for term in frequencies:
                document_frequency[term] += 1
        count = len(self.chunks)
        self.average_length = sum(self.lengths) / count if count else 0.0
        self.idf = {
            term: math.log(1.0 + (count - freq + 0.5) / (freq + 0.5))
            for term, freq in document_frequency.items()
        }

    def search(self, query: str, top_k: int = 20) -> list[tuple[int, float]]:
        terms = Counter(tokenize(query))
        if not terms or not self.chunks:
            return []
        scores: list[tuple[int, float]] = []
        average = self.average_length or 1.0
        for index, frequencies in enumerate(self.term_frequencies):
            score = 0.0
            length_norm = 1.0 - self.b + self.b * self.lengths[index] / average
            for term, query_frequency in terms.items():
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * length_norm
                contribution = self.idf.get(term, 0.0) * frequency * (self.k1 + 1.0) / denominator
                if query_frequency > 1:
                    contribution *= 1.0 + min(query_frequency - 1, 2) * 0.1
                score += contribution
            if score > 0:
                scores.append((index, score))
        scores.sort(key=lambda item: (-item[1], self.chunks[item[0]].chunk_id))
        return scores[:top_k]
