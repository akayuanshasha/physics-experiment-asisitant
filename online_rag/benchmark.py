"""Reproducible hybrid-retrieval benchmarks and before/after comparisons."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .corpus import load_corpus
from .embeddings import EmbeddingConfig, RemoteEmbeddingBackend
from .evaluation import EvaluationCase, load_evaluation_cases
from .models import Chunk
from .retriever import HybridRetriever, RetrievalConfig
from query_aliases import build_query_variants, should_include_related_expansions


SCHEMA_VERSION = 1
DEFAULT_CASES_PATH = Path("tests/fixtures/online_rag_retrieval_cases.json")
DEFAULT_REPORT_DIR = Path("evaluation_reports/online_rag")
DEFAULT_QUERY_CACHE_PATH = Path(".cache/online_rag/benchmark_query_embeddings.json")


def build_benchmark_query_variants(
    query: str, retrieval_config: RetrievalConfig,
) -> list[str]:
    """Mirror the online retriever's query expansion for cache prewarming."""

    return build_query_variants(
        query,
        include_related=should_include_related_expansions(query),
        max_variants=retrieval_config.max_query_variants,
    )


class BenchmarkQueryEmbeddingBackend:
    """Persistent exact-query cache with resumable, rate-limited prewarming."""

    def __init__(
        self,
        backend: RemoteEmbeddingBackend,
        path: str | Path = DEFAULT_QUERY_CACHE_PATH,
    ):
        self.backend = backend
        self.model_name = backend.model_name
        self.path = Path(path)
        self.entries: dict[str, list[float]] = {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("model") == self.model_name and isinstance(data.get("entries"), dict):
                self.entries = {
                    str(key): [float(value) for value in vector]
                    for key, vector in data["entries"].items()
                    if isinstance(vector, list)
                }
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    @staticmethod
    def _key(text: str) -> str:
        return _sha256_bytes(text.encode("utf-8"))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps({
            "version": 1,
            "model": self.model_name,
            "entries": self.entries,
        }, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.path)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.backend.embed_documents(texts)

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        missing = [text for text in texts if self._key(text) not in self.entries]
        if missing:
            self.prewarm(missing)
        return [self.entries[self._key(text)] for text in texts]

    def prewarm(
        self,
        texts: list[str],
        *,
        batch_size: int = 32,
        batch_delay_seconds: float = 2.0,
        rate_limit_retries: int = 4,
    ) -> dict[str, int]:
        unique_missing: list[str] = []
        seen: set[str] = set()
        for text in texts:
            key = self._key(text)
            if key not in self.entries and key not in seen:
                unique_missing.append(text)
                seen.add(key)
        initial_cached = len(texts) - len(unique_missing)
        for start in range(0, len(unique_missing), batch_size):
            batch = unique_missing[start:start + batch_size]
            for attempt in range(rate_limit_retries + 1):
                try:
                    vectors = self.backend.embed_queries(batch)
                    break
                except Exception as exc:
                    if "429" not in str(exc) or attempt >= rate_limit_retries:
                        raise
                    time.sleep(5.0 * (2 ** attempt))
            if len(vectors) != len(batch):
                raise ValueError("评估查询向量数量不正确")
            for text, vector in zip(batch, vectors):
                self.entries[self._key(text)] = vector
            self._save()
            if start + batch_size < len(unique_missing) and batch_delay_seconds > 0:
                time.sleep(batch_delay_seconds)
        return {"cached": initial_cached, "embedded": len(unique_missing)}

    def snapshot(self, required_texts: list[str]) -> dict[str, Any]:
        required_keys = {self._key(text) for text in required_texts}
        entry_keys = set(self.entries)
        return {
            "path": str(self.path),
            "exists": self.path.is_file(),
            "bytes": self.path.stat().st_size if self.path.is_file() else 0,
            "model": self.model_name,
            "entries": len(entry_keys),
            "required_entries": len(required_keys),
            "missing_required_entries": len(required_keys - entry_keys),
            "stale_entries": len(entry_keys - required_keys),
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_hash(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(payload)


def _chunk_record(chunk: Chunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "experiment_id": chunk.experiment_id,
        "experiment_name": chunk.experiment_name,
        "source": chunk.source,
        "section": chunk.section,
        "page_start": chunk.page_start,
        "page_end": chunk.page_end,
        "source_tier": chunk.source_tier,
        "source_kind": chunk.source_kind,
        "authority": chunk.authority,
        "is_example_data": chunk.is_example_data,
        "text": chunk.text,
    }


def build_corpus_snapshot(chunks: list[Chunk]) -> dict[str, Any]:
    """Fingerprint all content plus each experiment independently."""
    ordered = sorted(chunks, key=lambda chunk: chunk.chunk_id)
    by_experiment: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in ordered:
        by_experiment[chunk.experiment_id].append(chunk)
    experiment_fingerprints = {
        experiment_id: _json_hash([_chunk_record(chunk) for chunk in group])
        for experiment_id, group in sorted(by_experiment.items())
    }
    by_text_hash: dict[str, list[Chunk]] = defaultdict(list)
    for chunk in ordered:
        by_text_hash[_sha256_bytes(chunk.text.encode("utf-8"))].append(chunk)
    duplicate_groups = []
    for text_hash, group in sorted(by_text_hash.items()):
        experiment_ids = sorted({chunk.experiment_id for chunk in group})
        if len(experiment_ids) <= 1:
            continue
        duplicate_groups.append({
            "text_sha256": text_hash,
            "characters": len(group[0].text),
            "chunks": len(group),
            "experiment_ids": experiment_ids,
            "chunk_ids": sorted(chunk.chunk_id for chunk in group),
        })
    return {
        "fingerprint": _json_hash([_chunk_record(chunk) for chunk in ordered]),
        "chunks": len(ordered),
        "experiments": len(by_experiment),
        "characters": sum(len(chunk.text) for chunk in ordered),
        "sources": len({chunk.source for chunk in ordered}),
        "source_tier_counts": dict(sorted(Counter(
            chunk.source_tier for chunk in ordered
        ).items())),
        "chunks_with_pages": sum(chunk.page_start is not None for chunk in ordered),
        "section_counts": dict(sorted(Counter(
            chunk.section for chunk in ordered
        ).items())),
        "experiment_chunk_counts": {
            key: len(value) for key, value in sorted(by_experiment.items())
        },
        "experiment_fingerprints": experiment_fingerprints,
        "cross_experiment_exact_duplicate_groups": len(duplicate_groups),
        "cross_experiment_exact_duplicate_chunks": sum(
            group["chunks"] for group in duplicate_groups
        ),
        "cross_experiment_exact_duplicates": duplicate_groups,
    }


def build_cache_snapshot(
    cache_path: str | Path, chunks: list[Chunk], model_name: str,
) -> dict[str, Any]:
    path = Path(cache_path)
    current_ids = {chunk.chunk_id for chunk in chunks}
    entries: dict[str, Any] = {}
    cache_model: str | None = None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cache_model = data.get("model") if isinstance(data, dict) else None
        raw_entries = data.get("entries") if isinstance(data, dict) else None
        if isinstance(raw_entries, dict) and cache_model == model_name:
            entries = raw_entries
    except (OSError, json.JSONDecodeError):
        pass
    entry_ids = set(entries)
    return {
        "path": str(path),
        "exists": path.is_file(),
        "bytes": path.stat().st_size if path.is_file() else 0,
        "model": cache_model,
        "entries": len(entries),
        "current_entries": len(entry_ids & current_ids),
        "missing_current_entries": len(current_ids - entry_ids),
        "stale_entries": len(entry_ids - current_ids),
    }


def _rank(experiment_ids: list[str], expected: tuple[str, ...]) -> int | None:
    return next((
        index for index, experiment_id in enumerate(experiment_ids, start=1)
        if experiment_id in expected
    ), None)


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _recall(ranks: list[int | None], cutoff: int) -> float:
    return sum(rank is not None and rank <= cutoff for rank in ranks) / len(ranks) if ranks else 0.0


def _mrr(ranks: list[int | None], cutoff: int) -> float:
    return sum(
        1.0 / rank if rank is not None and rank <= cutoff else 0.0
        for rank in ranks
    ) / len(ranks) if ranks else 0.0


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def evaluate_hybrid_retriever(
    retriever: HybridRetriever,
    cases: list[EvaluationCase],
    *,
    top_k: int = 10,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if top_k <= 0:
        raise ValueError("top_k 必须大于 0")
    details: list[dict[str, Any]] = []
    chunk_ranks: list[int | None] = []
    experiment_ranks: list[int | None] = []
    latencies: list[float] = []

    for case_number, case in enumerate(cases, start=1):
        result = retriever.retrieve(case.query, top_k=top_k)
        chunk_experiments = [hit.chunk.experiment_id for hit in result.hits]
        unique_experiments = _unique(chunk_experiments)
        chunk_rank = _rank(chunk_experiments, case.expected_experiments)
        experiment_rank = _rank(unique_experiments, case.expected_experiments)
        latency = float(result.timings_ms.get("total", 0.0))
        chunk_ranks.append(chunk_rank)
        experiment_ranks.append(experiment_rank)
        latencies.append(latency)
        details.append({
            "case_id": f"R{case_number:03d}",
            "query": case.query,
            "expected_experiments": list(case.expected_experiments),
            "chunk_rank": chunk_rank,
            "experiment_rank": experiment_rank,
            "query_variants": list(result.query_variants),
            "latency_ms": latency,
            "hits": [{
                "rank": rank,
                "chunk_id": hit.chunk.chunk_id,
                "experiment_id": hit.chunk.experiment_id,
                "experiment_name": hit.chunk.experiment_name,
                "section": hit.chunk.section,
                "page_start": hit.chunk.page_start,
                "page_end": hit.chunk.page_end,
                "source": hit.chunk.source,
                "source_tier": hit.chunk.source_tier,
                "source_kind": hit.chunk.source_kind,
                "authority": hit.chunk.authority,
                "is_example_data": hit.chunk.is_example_data,
                "score": hit.score,
                "lexical_score": hit.lexical_score,
                "dense_score": hit.dense_score,
                "matched_variants": list(hit.matched_variants),
            } for rank, hit in enumerate(result.hits, start=1)],
        })

    cutoffs = sorted({value for value in (1, 3, 5, top_k) if value <= top_k})
    metrics: dict[str, Any] = {"cases": len(cases), "top_k": top_k}
    for cutoff in cutoffs:
        metrics[f"chunk_recall_at_{cutoff}"] = _recall(chunk_ranks, cutoff)
        metrics[f"experiment_recall_at_{cutoff}"] = _recall(experiment_ranks, cutoff)
    metrics[f"chunk_mrr_at_{top_k}"] = _mrr(chunk_ranks, top_k)
    metrics[f"experiment_mrr_at_{top_k}"] = _mrr(experiment_ranks, top_k)
    metrics[f"chunk_misses_at_{top_k}"] = sum(rank is None for rank in chunk_ranks)
    metrics[f"experiment_misses_at_{top_k}"] = sum(rank is None for rank in experiment_ranks)
    metrics["latency_ms_mean"] = statistics.fmean(latencies) if latencies else 0.0
    metrics["latency_ms_p50"] = _percentile(latencies, 0.50)
    metrics["latency_ms_p95"] = _percentile(latencies, 0.95)
    metrics["latency_ms_max"] = max(latencies, default=0.0)
    return metrics, details


def _json_ready(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    return value


def build_benchmark_report(
    retriever: HybridRetriever,
    cases: list[EvaluationCase],
    *,
    cases_path: str | Path,
    label: str,
    top_k: int = 10,
    index_build_seconds: float = 0.0,
    query_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    metrics, details = evaluate_hybrid_retriever(retriever, cases, top_k=top_k)
    path = Path(cases_path)
    corpus = build_corpus_snapshot(retriever.chunks)
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "schema_version": SCHEMA_VERSION,
        "run": {
            "label": label,
            "created_at_utc": created_at,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "index_build_seconds": index_build_seconds,
            "evaluation_seconds": time.perf_counter() - started,
        },
        "corpus": corpus,
        "evaluation_set": {
            "path": str(path),
            "sha256": _sha256_bytes(path.read_bytes()),
            "cases": len(cases),
        },
        "embedding": {"model": retriever.embedding_backend.model_name},
        "retrieval_config": _json_ready(asdict(retriever.config)),
        "cache": build_cache_snapshot(
            retriever.config.cache_path, retriever.chunks,
            retriever.embedding_backend.model_name,
        ),
        "query_cache": query_cache or {},
        "metrics": metrics,
        "cases": details,
    }


def save_report(report: dict[str, Any], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    temporary.replace(output)
    return output


def load_report(path: str | Path) -> dict[str, Any]:
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    if report.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("不支持的评估报告版本")
    return report


def _rank_outcome(before: int | None, after: int | None) -> str:
    if before is None and after is not None:
        return "improved"
    if before is not None and after is None:
        return "regressed"
    if before is None or after is None or before == after:
        return "unchanged"
    return "improved" if after < before else "regressed"


def compare_reports(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_metrics = before["metrics"]
    after_metrics = after["metrics"]
    metric_deltas = {
        key: after_metrics[key] - before_metrics[key]
        for key in sorted(set(before_metrics) & set(after_metrics))
        if isinstance(before_metrics[key], (int, float))
        and isinstance(after_metrics[key], (int, float))
        and key not in {"cases", "top_k"}
    }
    before_cases = {item["case_id"]: item for item in before.get("cases", [])}
    after_cases = {item["case_id"]: item for item in after.get("cases", [])}
    case_changes: list[dict[str, Any]] = []
    for case_id in sorted(set(before_cases) & set(after_cases)):
        old = before_cases[case_id]
        new = after_cases[case_id]
        outcome = _rank_outcome(old.get("chunk_rank"), new.get("chunk_rank"))
        if outcome != "unchanged":
            case_changes.append({
                "case_id": case_id,
                "query": new.get("query"),
                "outcome": outcome,
                "before_chunk_rank": old.get("chunk_rank"),
                "after_chunk_rank": new.get("chunk_rank"),
                "before_experiment_rank": old.get("experiment_rank"),
                "after_experiment_rank": new.get("experiment_rank"),
            })

    before_corpus = before["corpus"]
    after_corpus = after["corpus"]
    old_fingerprints = before_corpus.get("experiment_fingerprints", {})
    new_fingerprints = after_corpus.get("experiment_fingerprints", {})
    old_ids, new_ids = set(old_fingerprints), set(new_fingerprints)
    changed = sorted(
        experiment_id for experiment_id in old_ids & new_ids
        if old_fingerprints[experiment_id] != new_fingerprints[experiment_id]
    )
    compatible = {
        "evaluation_set": before["evaluation_set"].get("sha256")
        == after["evaluation_set"].get("sha256"),
        "embedding_model": before["embedding"].get("model")
        == after["embedding"].get("model"),
        "retrieval_config": before.get("retrieval_config")
        == after.get("retrieval_config"),
    }
    return {
        "compatible": compatible,
        "strictly_comparable": all(compatible.values()),
        "corpus_change": {
            "before_fingerprint": before_corpus.get("fingerprint"),
            "after_fingerprint": after_corpus.get("fingerprint"),
            "chunk_delta": after_corpus.get("chunks", 0) - before_corpus.get("chunks", 0),
            "character_delta": after_corpus.get("characters", 0) - before_corpus.get("characters", 0),
            "added_experiments": sorted(new_ids - old_ids),
            "removed_experiments": sorted(old_ids - new_ids),
            "changed_experiments": changed,
            "unchanged_experiments": len(old_ids & new_ids) - len(changed),
        },
        "metric_deltas": metric_deltas,
        "case_changes": case_changes,
        "improved_cases": sum(item["outcome"] == "improved" for item in case_changes),
        "regressed_cases": sum(item["outcome"] == "regressed" for item in case_changes),
    }


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip()).strip("-")
    return cleaned or "run"


def _run_command(args: argparse.Namespace) -> int:
    cases_path = Path(args.cases)
    cases = load_evaluation_cases(cases_path)
    retrieval_config = RetrievalConfig()
    remote_embedding_backend = RemoteEmbeddingBackend(EmbeddingConfig.from_env())
    embedding_backend = BenchmarkQueryEmbeddingBackend(
        remote_embedding_backend, args.query_cache,
    )
    all_query_variants: list[str] = []
    for case in cases:
        all_query_variants.extend(
            build_benchmark_query_variants(case.query, retrieval_config)
        )
    prewarm = embedding_backend.prewarm(
        all_query_variants,
        batch_size=args.query_batch_size,
        batch_delay_seconds=args.query_batch_delay,
        rate_limit_retries=args.rate_limit_retries,
    )
    build_started = time.perf_counter()
    retriever = HybridRetriever.from_corpus(embedding_backend, retrieval_config)
    build_seconds = time.perf_counter() - build_started
    report = build_benchmark_report(
        retriever, cases, cases_path=cases_path, label=args.label,
        top_k=args.top_k, index_build_seconds=build_seconds,
        query_cache={
            **embedding_backend.snapshot(all_query_variants),
            "prewarm_cached": prewarm["cached"],
            "prewarm_embedded": prewarm["embedded"],
        },
    )
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = Path(args.output) if args.output else (
        DEFAULT_REPORT_DIR
        / f"{timestamp}_{_slug(args.label)}_{report['corpus']['fingerprint'][:12]}.json"
    )
    save_report(report, output)
    print(json.dumps({
        "report": str(output),
        "corpus_fingerprint": report["corpus"]["fingerprint"],
        "metrics": report["metrics"],
        "cache": report["cache"],
        "query_cache": report["query_cache"],
    }, ensure_ascii=False, indent=2))
    return 0


def _compare_command(args: argparse.Namespace) -> int:
    comparison = compare_reports(load_report(args.before), load_report(args.after))
    print(json.dumps(comparison, ensure_ascii=False, indent=2))
    if args.output:
        save_report({"schema_version": SCHEMA_VERSION, "comparison": comparison}, args.output)
    return 0 if comparison["strictly_comparable"] else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Online RAG hybrid retrieval benchmark")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="run and save a real hybrid benchmark")
    run.add_argument("--label", default="baseline")
    run.add_argument("--cases", default=str(DEFAULT_CASES_PATH))
    run.add_argument("--top-k", type=int, default=10)
    run.add_argument("--output")
    run.add_argument("--query-cache", default=str(DEFAULT_QUERY_CACHE_PATH))
    run.add_argument("--query-batch-size", type=int, default=32)
    run.add_argument("--query-batch-delay", type=float, default=2.0)
    run.add_argument("--rate-limit-retries", type=int, default=4)
    run.set_defaults(function=_run_command)
    compare = subparsers.add_parser("compare", help="compare two saved reports")
    compare.add_argument("before")
    compare.add_argument("after")
    compare.add_argument("--output")
    compare.set_defaults(function=_compare_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.function(args))


if __name__ == "__main__":
    sys.exit(main())
