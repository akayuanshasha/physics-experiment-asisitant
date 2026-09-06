"""Write reproducible run artifacts without legacy comparison output."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from online_rag.models import Chunk

from .models import EvaluationQuestion, Prediction


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def corpus_fingerprint(chunks: Iterable[Chunk]) -> str:
    digest = hashlib.sha256()
    for chunk in sorted(chunks, key=lambda item: item.chunk_id):
        digest.update(json.dumps(chunk.to_dict() if hasattr(chunk, "to_dict") else {
            "chunk_id": chunk.chunk_id,
            "experiment_id": chunk.experiment_id,
            "source": chunk.source,
            "section": chunk.section,
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "source_tier": chunk.source_tier,
            "source_kind": chunk.source_kind,
            "authority": chunk.authority,
            "is_example_data": chunk.is_example_data,
            "text": chunk.text,
        }, ensure_ascii=False, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


def make_run_id(split: str, mode: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}_{split}_{mode}"


def build_run_metadata(
    *,
    run_id: str,
    split: str,
    mode: str,
    questions: list[EvaluationQuestion],
    questions_path: Path,
    chunks: list[Chunk],
    model_name: str,
    embedding_model: str,
    retrieval_config: Any,
    prompt_path: Path,
) -> dict:
    corpus_hash = corpus_fingerprint(chunks)
    source_manifest = Path(__file__).resolve().parents[1] / "b_static" / "knowledge_sources.json"
    return {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "build_id": f"corpus-{corpus_hash[:12]}",
        "git_commit_or_build_id": f"corpus-{corpus_hash[:12]}",
        "model_name": model_name,
        "model_parameters": {"temperature": 0.1, "max_tokens": 8192},
        "prompt_version": f"sha256:{sha256_file(prompt_path)[:16]}",
        "knowledge_base_version": f"sha256:{corpus_hash}",
        "knowledge_source_manifest": {
            "path": str(source_manifest),
            "sha256": sha256_file(source_manifest) if source_manifest.is_file() else None,
        },
        "embedding_model": embedding_model,
        "chunking": {
            "strategy": "online_rag.corpus structure-aware character chunking",
            "chunk_size": retrieval_config.chunk_target_chars,
            "chunk_max": retrieval_config.chunk_max_chars,
            "chunk_overlap": retrieval_config.chunk_overlap_chars,
        },
        "retrieval": {
            "filter_key": "experiment_id",
            "top_k": 5,
            "assistant_retrieval_top_k": 12,
            "candidate_k_before_fusion": retrieval_config.candidate_k,
            "document_embedding_batch_size": retrieval_config.document_embedding_batch_size,
            "experiment_title_boost": retrieval_config.experiment_title_boost,
            "primary_minimum_retrieval_score": retrieval_config.primary_minimum_retrieval_score,
            "primary_minimum_bm25_score": retrieval_config.primary_minimum_bm25_score,
            "source_hierarchy": "primary_only_when_sufficient_else_secondary_fallback",
            "example_data_policy": "explicit_example_intent_only",
            "fusion": "weighted_rrf",
            "reranker": "none",
            "mode": mode,
        },
        "dataset": {
            "benchmark_version": questions[0].version if questions else "1.2",
            "split": split,
            "question_count": len(questions),
            "sha256": sha256_file(questions_path),
        },
        "notes": "本次结果为唯一新基线；未执行Legacy/Online对照。",
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def failure_cases_markdown(report: dict, questions: list[EvaluationQuestion]) -> str:
    by_id = {item.id: item for item in questions}
    failed = [item for item in report["results"] if item["flags"]]
    lines = [
        "# RAG 评测失败案例",
        "",
        "> 自动标记用于定位问题，P0/P1结论仍需人工复核。",
        "",
        f"共 {len(failed)} 题需要复核。",
        "",
    ]
    for item in failed:
        question = by_id[item["id"]]
        lines.extend([
            f"## {item['id']} · {question.question}",
            "",
            f"- split/suite/category：{item['split']} / {item['suite']} / {item['category']}",
            f"- 自动分：{item['auto_score']}",
            f"- 标记：{', '.join(item['flags'])}",
            f"- 首个正确实验排名：{item['retrieval']['first_relevant_rank']}",
            f"- 返回实验：{', '.join(item['retrieval']['returned_experiment_ids'])}",
            f"- 返回资料等级：{', '.join(item['retrieval']['returned_source_tiers'])}",
            "",
        ])
    return "\n".join(lines)


def write_run_artifacts(
    output_dir: str | Path,
    *,
    metadata: dict,
    corpus_audit: dict,
    raw_rows: list[dict],
    predictions: list[Prediction],
    report: dict,
    questions: list[EvaluationQuestion],
) -> Path:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    write_json(destination / "run_metadata.json", metadata)
    write_json(destination / "corpus_audit.json", corpus_audit)
    write_jsonl(destination / "raw.jsonl", raw_rows)
    write_jsonl(destination / "predictions.jsonl", [item.to_dict() for item in predictions])
    write_json(destination / "auto_report.json", report)
    (destination / "failure_cases.md").write_text(
        failure_cases_markdown(report, questions), encoding="utf-8"
    )
    return destination
