"""Audit whether benchmark evidence is present in the current chunked corpus."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from online_rag.models import Chunk

from .models import EvaluationQuestion


PROJECT_ROOT = Path(__file__).resolve().parents[1]


_ANCHOR_SPLIT_RE = re.compile(r"[、，,；;：:/|（）()\s]+")
_GENERIC_ANCHOR_TERMS = {
    "模块公式与变量说明", "实验指导", "相关说明", "相关内容", "实验原理",
    "数据处理", "注意事项", "实验步骤", "实验要求",
}


def normalized(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return "".join(character for character in text if not character.isspace())


def anchor_terms(anchor: str) -> list[str]:
    terms = [item.strip() for item in _ANCHOR_SPLIT_RE.split(anchor) if len(item.strip()) >= 2]
    useful = [item for item in terms if item not in _GENERIC_ANCHOR_TERMS]
    return useful or terms


def audit_corpus(
    questions: Iterable[EvaluationQuestion],
    chunks: Iterable[Chunk],
) -> dict:
    question_list = list(questions)
    chunk_list = list(chunks)
    by_experiment: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in chunk_list:
        by_experiment[chunk.experiment_id].append(chunk)

    details: list[dict] = []
    missing_experiments: set[str] = set()
    section_hits = 0
    anchor_hits = 0
    source_checks = 0
    source_path_hits = 0
    for question in question_list:
        resolved_ids = {
            candidate
            for experiment_id in question.relevant_experiment_ids
            for candidate in (
                experiment_id,
                experiment_id.rsplit("_", 1)[0]
                if re.fullmatch(r"exp\d+_[a-z]", experiment_id, re.I) else experiment_id,
            )
        }
        expected_chunks = []
        seen_chunks: set[str] = set()
        for experiment_id in resolved_ids:
            for chunk in by_experiment.get(experiment_id, []):
                if chunk.chunk_id not in seen_chunks:
                    seen_chunks.add(chunk.chunk_id)
                    expected_chunks.append(chunk)
        for experiment_id in question.relevant_experiment_ids:
            parent = (
                experiment_id.rsplit("_", 1)[0]
                if re.fullmatch(r"exp\d+_[a-z]", experiment_id, re.I) else experiment_id
            )
            if experiment_id not in by_experiment and parent not in by_experiment:
                missing_experiments.add(experiment_id)
        combined_text = normalized("\n".join(chunk.text for chunk in expected_chunks))
        combined_sections = normalized("\n".join(chunk.section for chunk in expected_chunks))
        source_results: list[dict] = []
        for source in question.source:
            source_checks += 1
            source_path = PROJECT_ROOT / source.relative_path
            path_exists = source_path.is_file()
            source_path_hits += int(path_exists)
            section = normalized(source.section)
            section_hit = bool(expected_chunks) and (
                not section or section in combined_sections or section in combined_text
            )
            terms = anchor_terms(source.anchor)
            matched_terms = [term for term in terms if normalized(term) in combined_text]
            anchor_hit = bool(expected_chunks) and (not terms or bool(matched_terms))
            section_hits += int(section_hit)
            anchor_hits += int(anchor_hit)
            source_results.append({
                "relative_path": source.relative_path,
                "path_exists": path_exists,
                "section": source.section,
                "section_hit": section_hit,
                "anchor": source.anchor,
                "anchor_terms": terms,
                "matched_anchor_terms": matched_terms,
                "anchor_hit": anchor_hit,
            })
        details.append({
            "id": question.id,
            "split": question.split,
            "relevant_experiment_ids": list(question.relevant_experiment_ids),
            "available_chunk_count": len(expected_chunks),
            "missing_experiment_ids": [
                item for item in question.relevant_experiment_ids
                if item not in by_experiment and not (
                    re.fullmatch(r"exp\d+_[a-z]", item, re.I)
                    and item.rsplit("_", 1)[0] in by_experiment
                )
            ],
            "sources": source_results,
        })

    experiment_counts = Counter(chunk.experiment_id for chunk in chunk_list)
    return {
        "summary": {
            "question_count": len(question_list),
            "chunk_count": len(chunk_list),
            "experiment_count": len(experiment_counts),
            "missing_experiment_ids": sorted(missing_experiments),
            "source_check_count": source_checks,
            "source_path_presence_rate": round(
                source_path_hits / source_checks, 4
            ) if source_checks else 1.0,
            "section_presence_rate": round(section_hits / source_checks, 4) if source_checks else 1.0,
            "anchor_presence_rate": round(anchor_hits / source_checks, 4) if source_checks else 1.0,
        },
        "chunks_by_experiment": dict(sorted(experiment_counts.items())),
        "details": details,
    }
