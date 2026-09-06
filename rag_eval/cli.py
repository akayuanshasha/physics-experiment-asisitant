"""Command line entry point for the 71-question RAG benchmark."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from online_rag.corpus import load_corpus

from .adapters import OnlineRagAdapter
from .corpus_audit import audit_corpus
from .dataset import (
    DEFAULT_QUESTIONS_PATH,
    DEFAULT_SCHEMA_PATH,
    DatasetValidationError,
    load_questions,
    read_jsonl,
)
from .models import ContextEvidence, Prediction
from .reporting import (
    build_run_metadata,
    failure_cases_markdown,
    make_run_id,
    sha256_file,
    write_json,
    write_jsonl,
    write_run_artifacts,
)
from .scoring import build_report
from .regression import evaluate_regression_gate


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_ROOT = PROJECT_ROOT / "evaluation_reports" / "rag_v1"
DEFAULT_THRESHOLDS_PATH = PROJECT_ROOT / "evaluation" / "rag_v1" / "regression_thresholds.json"


def _configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace")


def _load(args: argparse.Namespace):
    return load_questions(
        args.questions,
        args.schema,
        split=getattr(args, "split", "all"),
    )


def _print_summary(report: dict) -> None:
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))


def _retrieval_runtime_summary(raw_rows: list[dict], retriever) -> dict:
    modes: Counter[str] = Counter()
    dense_nonzero_hit_count = 0
    returned_hit_count = 0
    for row in raw_rows:
        response = row.get("response", {})
        if not isinstance(response, dict):
            continue
        retrieval = response.get("retrieval", response)
        if not isinstance(retrieval, dict):
            continue
        mode = str(retrieval.get("retrieval_mode", "unknown") or "unknown")
        modes[mode] += 1
        hits = retrieval.get("hits", [])
        if not isinstance(hits, list):
            continue
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            returned_hit_count += 1
            try:
                dense_nonzero_hit_count += int(float(hit.get("dense_score") or 0.0) != 0.0)
            except (TypeError, ValueError):
                continue

    question_count = len(raw_rows)
    document_vector_count = len(getattr(retriever, "document_vectors", []) or [])
    expected_document_vector_count = len(getattr(retriever, "chunks", []) or [])
    return {
        "retrieval_mode_counts": dict(sorted(modes.items())),
        "hybrid_query_rate": round(
            modes["hybrid"] / question_count, 4
        ) if question_count else 0.0,
        "bm25_fallback_rate": round(
            modes["bm25_fallback"] / question_count, 4
        ) if question_count else 0.0,
        "unknown_mode_rate": round(
            modes["unknown"] / question_count, 4
        ) if question_count else 0.0,
        "dense_nonzero_hit_count": dense_nonzero_hit_count,
        "dense_nonzero_hit_rate": round(
            dense_nonzero_hit_count / returned_hit_count, 4
        ) if returned_hit_count else 0.0,
        "dense_available": bool(getattr(retriever, "dense_available", False)),
        "document_vector_count": document_vector_count,
        "expected_document_vector_count": expected_document_vector_count,
        "document_vector_coverage": round(
            document_vector_count / expected_document_vector_count, 4
        ) if expected_document_vector_count else 0.0,
    }


def command_validate(args: argparse.Namespace) -> int:
    questions = _load(args)
    counts = {"dev": 0, "test": 0}
    for question in questions:
        counts[question.split] += 1
    print(json.dumps({"question_count": len(questions), "splits": counts}, ensure_ascii=False))
    print("题库完整 Schema 与语义校验通过。")
    return 0


def command_audit(args: argparse.Namespace) -> int:
    questions = _load(args)
    chunks = load_corpus(args.corpus_root)
    report = audit_corpus(questions, chunks)
    if args.output:
        write_json(args.output, report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 1 if report["summary"]["missing_experiment_ids"] else 0


def command_score(args: argparse.Namespace) -> int:
    questions = _load(args)
    predictions = [Prediction.from_dict(item) for item in read_jsonl(args.predictions)]
    report = build_report(questions, predictions)
    write_json(args.output, report)
    _print_summary(report)
    return 0


def _enrich_predictions_with_raw(
    predictions: list[Prediction], raw_rows: list[dict],
) -> list[Prediction]:
    """Migrate legacy output to citation contract v2 without inference calls."""
    raw_by_id = {str(row.get("id", "")): row for row in raw_rows}
    enriched: list[Prediction] = []
    for prediction in predictions:
        raw = raw_by_id.get(prediction.id, {})
        response = raw.get("response", {}) if isinstance(raw, dict) else {}
        evidence_rows = response.get("evidence", []) if isinstance(response, dict) else []
        context_evidence = [
            ContextEvidence.from_dict(item)
            for item in evidence_rows
            if isinstance(item, dict)
        ]
        attached_rows = response.get("citations", []) if isinstance(response, dict) else []
        attached_ids = [
            str(item.get("id", item.get("evidence_id", "")))
            for item in attached_rows
            if isinstance(item, dict) and (item.get("id") or item.get("evidence_id"))
        ]
        enriched.append(replace(
            prediction,
            citations=attached_ids or list(prediction.citations),
            context_evidence=context_evidence or list(prediction.context_evidence),
            # The historical raw artifact contains only the cleaned answer, so
            # actual inline model selections cannot be reconstructed honestly.
            model_citations=None,
            citation_contract_version="2-rescored-legacy",
        ))
    return enriched


def command_rescore(args: argparse.Namespace) -> int:
    questions = _load(args)
    source_dir = args.source_dir.resolve()
    predictions_path = source_dir / "predictions.jsonl"
    raw_path = source_dir / "raw.jsonl"
    old_report_path = source_dir / "auto_report.json"
    for required in (predictions_path, raw_path, old_report_path):
        if not required.is_file():
            raise ValueError(f"缺少重评输入：{required}")

    predictions = [Prediction.from_dict(item) for item in read_jsonl(predictions_path)]
    raw_rows = read_jsonl(raw_path)
    question_ids = {item.id for item in questions}
    prediction_ids = {item.id for item in predictions}
    raw_ids = {str(item.get("id", "")) for item in raw_rows}
    if prediction_ids != question_ids or raw_ids != question_ids:
        raise ValueError(
            "重评输入 ID 与当前数据集不一致；"
            f" questions={len(question_ids)}, predictions={len(prediction_ids)}, raw={len(raw_ids)}"
        )

    enriched = _enrich_predictions_with_raw(predictions, raw_rows)
    report = build_report(questions, enriched)
    old_report = json.loads(old_report_path.read_text(encoding="utf-8"))
    retrieval_runtime = old_report.get("summary", {}).get("retrieval_runtime")
    if isinstance(retrieval_runtime, dict):
        report["summary"]["retrieval_runtime"] = retrieval_runtime
    report["rescore"] = {
        "source_report_dir": str(source_dir),
        "citation_contract_version": "2-rescored-legacy",
        "model_citations": "unavailable_in_historical_artifacts",
        "inference_calls": 0,
    }

    destination = args.output_dir.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"重评输出目录非空，拒绝覆盖：{destination}")
    destination.mkdir(parents=True, exist_ok=True)
    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_report_dir": str(source_dir),
        "source_artifacts": {
            "predictions.jsonl": f"sha256:{sha256_file(predictions_path)}",
            "raw.jsonl": f"sha256:{sha256_file(raw_path)}",
            "auto_report.json": f"sha256:{sha256_file(old_report_path)}",
        },
        "split": args.split,
        "question_count": len(questions),
        "citation_contract_version": "2-rescored-legacy",
        "model_citations": "unavailable_in_historical_artifacts",
        "rag_calls": 0,
        "llm_calls": 0,
        "embedding_calls": 0,
    }
    write_json(destination / "rescore_metadata.json", metadata)
    write_jsonl(destination / "predictions.jsonl", [item.to_dict() for item in enriched])
    write_json(destination / "auto_report.json", report)
    (destination / "failure_cases.md").write_text(
        failure_cases_markdown(report, questions), encoding="utf-8"
    )
    gate = evaluate_regression_gate(report["summary"], args.thresholds, "end_to_end")
    write_json(destination / "regression_gate.json", gate)
    _print_summary(report)
    print(json.dumps({
        "regression_profile": "end_to_end",
        "regression_passed": gate["passed"],
        "failed_metrics": [
            item["metric"] for item in gate["checks"] if not item["passed"]
        ],
        "output_dir": str(destination),
    }, ensure_ascii=False, indent=2))
    return 1 if report["summary"]["prediction_errors"] or not gate["passed"] else 0


def command_run(args: argparse.Namespace) -> int:
    if args.lexical_only and not args.retrieval_only:
        raise ValueError("--lexical-only 只能与 --retrieval-only 一起使用")
    load_dotenv(PROJECT_ROOT / ".env")
    questions = _load(args)
    adapter = OnlineRagAdapter.lexical_only() if args.lexical_only else OnlineRagAdapter.from_env()
    chunks = list(adapter.assistant.retriever.chunks)
    corpus_report = audit_corpus(questions, chunks)
    run_id = args.run_id or make_run_id(args.split, args.mode)
    output_dir = args.output_dir or (DEFAULT_REPORT_ROOT / run_id)
    predictions: list[Prediction] = []
    raw_rows: list[dict] = []
    for index, question in enumerate(questions, 1):
        print(f"[{index}/{len(questions)}] {question.id} {question.question}", flush=True)
        result = (
            adapter.retrieve_only(question, mode=args.mode)
            if args.retrieval_only
            else adapter.predict(question, mode=args.mode)
        )
        predictions.append(result.prediction)
        raw_rows.append({"id": question.id, "mode": args.mode, "response": result.raw})
        if result.prediction.error:
            print(f"  ERROR {result.prediction.error}", flush=True)

    report = build_report(questions, predictions)
    retriever = adapter.assistant.retriever
    retrieval_runtime = _retrieval_runtime_summary(raw_rows, retriever)
    report["summary"]["retrieval_runtime"] = retrieval_runtime
    metadata = build_run_metadata(
        run_id=run_id,
        split=args.split,
        mode=args.mode,
        questions=questions,
        questions_path=Path(args.questions),
        chunks=chunks,
        model_name=str(getattr(adapter.assistant.chat_backend, "model_name", "")),
        embedding_model=str(getattr(retriever.embedding_backend, "model_name", "")),
        retrieval_config=retriever.config,
        prompt_path=PROJECT_ROOT / "online_rag" / "prompts.py",
    )
    metadata["run_scope"] = "retrieval_only" if args.retrieval_only else "end_to_end"
    metadata["lexical_only"] = bool(args.lexical_only)
    metadata["retrieval_runtime"] = retrieval_runtime
    health = getattr(retriever.embedding_backend, "health", None)
    if callable(health):
        metadata["embedding_health"] = health()
    destination = write_run_artifacts(
        output_dir,
        metadata=metadata,
        corpus_audit=corpus_report,
        raw_rows=raw_rows,
        predictions=predictions,
        report=report,
        questions=questions,
    )
    profile = (
        "lexical_retrieval" if args.lexical_only
        else "hybrid_retrieval" if args.retrieval_only
        else "end_to_end"
    )
    gate = evaluate_regression_gate(report["summary"], args.thresholds, profile)
    write_json(destination / "regression_gate.json", gate)
    _print_summary(report)
    print(json.dumps({
        "regression_profile": profile,
        "regression_passed": gate["passed"],
        "failed_metrics": [
            item["metric"] for item in gate["checks"] if not item["passed"]
        ],
    }, ensure_ascii=False, indent=2))
    print(f"评测结果：{destination}")
    return 1 if report["summary"]["prediction_errors"] or not gate["passed"] else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="大学物理实验 AI 助教 RAG 评测")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS_PATH)
    common.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)

    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", parents=[common], help="验证71题数据集")
    validate.set_defaults(handler=command_validate, split="all")

    audit = subparsers.add_parser("audit", parents=[common], help="审计语料和证据锚点")
    audit.add_argument("--split", choices=["all", "dev", "test"], default="all")
    audit.add_argument("--corpus-root", type=Path, default=PROJECT_ROOT / "b_static" / "experiment")
    audit.add_argument("--output", type=Path)
    audit.set_defaults(handler=command_audit)

    score = subparsers.add_parser("score", parents=[common], help="重新评分已有预测")
    score.add_argument("--split", choices=["all", "dev", "test"], default="all")
    score.add_argument("--predictions", type=Path, required=True)
    score.add_argument("--output", type=Path, required=True)
    score.set_defaults(handler=command_score)

    rescore = subparsers.add_parser(
        "rescore", parents=[common], help="离线重评已有端到端结果",
    )
    rescore.add_argument("--split", choices=["dev"], default="dev")
    rescore.add_argument("--source-dir", type=Path, required=True)
    rescore.add_argument("--output-dir", type=Path, required=True)
    rescore.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS_PATH)
    rescore.set_defaults(handler=command_rescore)

    run = subparsers.add_parser("run", parents=[common], help="运行真实online_rag端到端评测")
    run.add_argument("--split", choices=["all", "dev", "test"], default="dev")
    run.add_argument("--mode", choices=["blind", "page-context"], default="blind")
    run.add_argument("--run-id")
    run.add_argument("--output-dir", type=Path)
    run.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS_PATH)
    run.add_argument(
        "--retrieval-only", action="store_true",
        help="只运行检索，不调用聊天生成模型",
    )
    run.add_argument(
        "--lexical-only", action="store_true",
        help="离线诊断：禁用dense检索，只运行BM25",
    )
    run.set_defaults(handler=command_run)
    return parser


def main() -> int:
    _configure_console()
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.handler(args))
    except DatasetValidationError as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
