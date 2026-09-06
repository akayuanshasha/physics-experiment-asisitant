"""运行冻结 RAG 的 15 题最终测试（Hybrid 或 BM25 baseline）。

设计目标（来自 FROZEN_BASELINE_20260905.md 公平性约束）：
- 只读调用当前冻结系统，不修改任何冻结文件（Prompt/Embedding/Chunk/Dense/BM25/RRF/Top-K/Reranker/Context/Boundary/评分）。
- 只对 test split 运行 blind 模式，与 dev 冻结基线同一套生成/检索参数。
- 严格变量控制：Hybrid 与 BM25 唯一核心差异是是否启用 Dense/RRF。BM25 baseline 通过
  `RAG_EMBEDDING_BACKEND=bm25`（factory 自动置 dense_weight=0.0）实现，知识库/Prompt/
  生成模型与参数/Top-K/Context construction/评分规则全部与 Hybrid 一致。
- 预测阶段不读取 expected_answer / expected_points / source / rubric 等答案字段。
- 每完成一题立即落盘（fsync），支持异常后断点续跑：已成功完成的题跳过。
- 仅对发生异常（网络/API 等非模型能力问题）的题重试，不因答案质量重跑。
- 预测全部生成并保存后，视为冻结结果；之后再调用冻结 scorer 离线评分。

复用 rag_eval.adapters / reporting / scoring / regression，与 CLI `rag_eval run` 同口径。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from online_rag.corpus import load_corpus
from online_rag.factory import create_assistant_from_env

from .adapters import OnlineRagAdapter
from .corpus_audit import audit_corpus
from .dataset import DEFAULT_QUESTIONS_PATH, DEFAULT_SCHEMA_PATH, load_questions
from .models import Prediction
from .regression import evaluate_regression_gate
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_ROOT = PROJECT_ROOT / "evaluation_reports" / "rag_v1"
DEFAULT_THRESHOLDS_PATH = PROJECT_ROOT / "evaluation" / "rag_v1" / "regression_thresholds.json"

MAX_ATTEMPTS = 3          # 单题异常重试上限（仅针对网络/API 等非模型能力异常）
RETRY_BACKOFF = 5.0       # 重试间隔秒数


def _retrieval_runtime_summary(raw_rows: list[dict], retriever) -> dict:
    """与 cli._retrieval_runtime_summary 同口径，避免 import 私有函数。"""
    from collections import Counter

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
        "hybrid_query_rate": round(modes["hybrid"] / question_count, 4) if question_count else 0.0,
        "bm25_fallback_rate": round(modes["bm25_fallback"] / question_count, 4) if question_count else 0.0,
        "unknown_mode_rate": round(modes["unknown"] / question_count, 4) if question_count else 0.0,
        "dense_nonzero_hit_count": dense_nonzero_hit_count,
        "dense_nonzero_hit_rate": round(dense_nonzero_hit_count / returned_hit_count, 4) if returned_hit_count else 0.0,
        "dense_available": bool(getattr(retriever, "dense_available", False)),
        "document_vector_count": document_vector_count,
        "expected_document_vector_count": expected_document_vector_count,
        "document_vector_coverage": round(document_vector_count / expected_document_vector_count, 4) if expected_document_vector_count else 0.0,
    }


def _atomic_write_json(path: Path, value) -> None:
    """先写临时文件再替换，保证落盘原子性。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl_fsync(path: Path, row: dict) -> None:
    """以追加方式写一行 jsonl 并 fsync，保证单题落盘后断电不丢。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _load_checkpoint(path: Path) -> dict:
    if not path.is_file():
        return {"completed_ids": [], "completed_count": 0, "status": "running"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"completed_ids": [], "completed_count": 0, "status": "running"}


def _save_checkpoint(path: Path, state: dict) -> None:
    _atomic_write_json(path, state)


def _run_one(adapter: OnlineRagAdapter, question, *, mode: str) -> tuple[Prediction, dict, str | None]:
    """运行单题，返回 (prediction, raw, exception_text_or_none)。

    adapter.predict 自身捕获异常并写入 prediction.error；但为支持题级重试，
    这里额外探测 result.prediction.error，将其视为可重试异常。
    """
    result = adapter.predict(question, mode=mode)
    err = result.prediction.error
    return result.prediction, result.raw, err


def main() -> int:
    parser = argparse.ArgumentParser(description="冻结 Hybrid RAG 15题最终测试（断点续跑）")
    parser.add_argument("--split", default="test", choices=["test", "dev", "all"])
    parser.add_argument("--mode", default="blind", choices=["blind", "page-context"])
    parser.add_argument(
        "--retrieval-mode", default="hybrid", choices=["hybrid", "bm25"],
        help="hybrid=冻结 Hybrid（Dense+BM25+RRF）；bm25=仅 BM25 baseline（dense_weight=0）",
    )
    parser.add_argument("--run-id")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS_PATH)
    parser.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS)
    parser.add_argument("--resume", action="store_true", help="允许跳过已成功完成的题（默认即如此）")
    parser.add_argument("--fresh", action="store_true", help="忽略已有 checkpoint，从头跑（仍不覆盖已有结果目录除非指定）")
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")

    questions = load_questions(args.questions, args.schema, split=args.split)
    run_id = args.run_id or make_run_id(args.split, args.mode)
    output_dir = args.output_dir or (DEFAULT_REPORT_ROOT / run_id)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_path = output_dir / "raw.jsonl"
    pred_path = output_dir / "predictions.jsonl"
    checkpoint_path = output_dir / "checkpoint_state.json"

    # 断点续跑：读取已完成题。--fresh 时忽略。
    checkpoint = {"completed_ids": [], "completed_count": 0, "status": "running"} if args.fresh else _load_checkpoint(checkpoint_path)
    completed_ids: list[str] = list(checkpoint.get("completed_ids", []))
    completed_set = set(completed_ids)

    print(f"=== 冻结 RAG 最终测试 ===", flush=True)
    print(f"retrieval   : {args.retrieval_mode}（{'Dense+BM25+RRF' if args.retrieval_mode == 'hybrid' else '仅 BM25，dense_weight=0'}）", flush=True)
    print(f"run_id      : {run_id}", flush=True)
    print(f"output_dir  : {output_dir}", flush=True)
    print(f"split/mode  : {args.split} / {args.mode}", flush=True)
    print(f"questions   : {len(questions)}", flush=True)
    print(f"已断点完成  : {len(completed_set)} 题 -> {completed_ids}", flush=True)
    print(f"重试上限    : 每题最多 {args.max_attempts} 次（仅异常重试）", flush=True)
    print(f"冻结文件    : 不修改任何冻结系统文件", flush=True)
    print(flush=True)

    # 构建 adapter。Hybrid 走 from_env（.env 中 RAG_EMBEDDING_BACKEND=auto→remote Dense）。
    # BM25 baseline 通过临时置 RAG_EMBEDDING_BACKEND=bm25 让 factory 返回
    # BM25OnlyEmbeddingBackend 并自动置 dense_weight=0.0；其余 config/Prompt/chat 全部不变。
    if args.retrieval_mode == "bm25":
        prior = os.environ.get("RAG_EMBEDDING_BACKEND")
        os.environ["RAG_EMBEDDING_BACKEND"] = "bm25"
        try:
            assistant = create_assistant_from_env()
        finally:
            if prior is None:
                os.environ.pop("RAG_EMBEDDING_BACKEND", None)
            else:
                os.environ["RAG_EMBEDDING_BACKEND"] = prior
        adapter = OnlineRagAdapter(assistant)
    else:
        adapter = OnlineRagAdapter.from_env()
    chunks = list(adapter.assistant.retriever.chunks)
    retriever = adapter.assistant.retriever
    dense_weight = float(getattr(retriever.config, "dense_weight", 1.0))
    print(f"adapter 就绪：dense_available={getattr(retriever, 'dense_available', None)} "
          f"dense_weight={dense_weight} embedding_backend="
          f"{getattr(retriever.embedding_backend, 'model_name', '?')}", flush=True)

    total = len(questions)
    new_raw_rows: list[dict] = []
    new_predictions: list[Prediction] = []
    failures: list[dict] = []

    for index, question in enumerate(questions, 1):
        qid = question.id
        if qid in completed_set:
            print(f"[{index}/{total}] {qid} 已断点完成，跳过", flush=True)
            continue

        print(f"[{index}/{total}] {qid} {question.question[:60]}", flush=True)
        prediction = None
        raw = None
        last_err = None
        for attempt in range(1, args.max_attempts + 1):
            t0 = time.perf_counter()
            try:
                prediction, raw, err = _run_one(adapter, question, mode=args.mode)
                last_err = err
                if err is None:
                    break
                print(f"  尝试 {attempt}/{args.max_attempts} 异常: {err}", flush=True)
            except Exception as exc:  # 兜底：adapter 未捕获的异常
                last_err = f"{type(exc).__name__}: {exc}"
                prediction = None
                raw = None
                print(f"  尝试 {attempt}/{args.max_attempts} 未捕获异常: {last_err}", flush=True)
            if attempt < args.max_attempts:
                time.sleep(RETRY_BACKOFF)

        if prediction is None:
            # 所有尝试都未拿到 prediction 对象，构造一个错误占位
            prediction = Prediction(
                id=qid, mode=args.mode, answer="", retrieved_evidence=[],
                citations=[], grounded=False,
                timings_ms={"total": (time.perf_counter() - t0) * 1000},
                error=last_err or "unknown_error",
            )
            raw = {"error": last_err or "unknown_error"}

        # 立即落盘：追加 raw / predictions，更新 checkpoint。
        _append_jsonl_fsync(raw_path, {"id": qid, "mode": args.mode, "response": raw})
        _append_jsonl_fsync(pred_path, prediction.to_dict())
        completed_ids.append(qid)
        completed_set.add(qid)
        checkpoint_state = {
            "run_id": run_id,
            "split": args.split,
            "mode": args.mode,
            "run_scope": "end_to_end",
            "status": "running",
            "completed_count": len(completed_ids),
            "completed_ids": completed_ids,
            "last_completed_id": qid,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "error": last_err,
        }
        _save_checkpoint(checkpoint_path, checkpoint_state)

        new_raw_rows.append({"id": qid, "mode": args.mode, "response": raw})
        new_predictions.append(prediction)

        if last_err:
            failures.append({"id": qid, "error": last_err})
            print(f"  => 最终失败（已记录，不重跑）: {last_err}", flush=True)
        else:
            ans_preview = (prediction.answer or "").replace("\n", " ")[:80]
            print(f"  => 完成 answer={ans_preview!r}", flush=True)

    # 全部题目处理完毕。汇总所有预测（含断点续跑已落盘的）。
    print(flush=True)
    print("=== 汇总所有预测（含断点已落盘）用于离线评分 ===", flush=True)
    all_predictions: list[Prediction] = []
    all_raw_rows: list[dict] = []
    # 重新从落盘文件读取，保证完整且顺序与 questions 一致。
    if raw_path.is_file():
        from .dataset import read_jsonl
        raw_by_id = {str(r.get("id", "")): r for r in read_jsonl(raw_path)}
        pred_rows = read_jsonl(pred_path)
        pred_by_id = {str(r.get("id", "")): Prediction.from_dict(r) for r in pred_rows}
        for question in questions:
            qid = question.id
            if qid in pred_by_id:
                all_predictions.append(pred_by_id[qid])
                all_raw_rows.append(raw_by_id.get(qid, {"id": qid, "mode": args.mode, "response": {}}))
            else:
                all_predictions.append(Prediction(
                    id=qid, mode=args.mode, answer="", retrieved_evidence=[],
                    citations=[], grounded=False, error="missing_prediction",
                ))
                all_raw_rows.append({"id": qid, "mode": args.mode, "response": {}})

    success_count = sum(1 for p in all_predictions if not p.error)
    fail_count = sum(1 for p in all_predictions if p.error)
    print(f"完成: {len(all_predictions)}/{total}, 成功 {success_count}, 失败 {fail_count}", flush=True)

    # 重建全量 raw.jsonl / predictions.jsonl（按 questions 顺序覆盖写）。
    write_jsonl(raw_path, all_raw_rows)
    write_jsonl(pred_path, [p.to_dict() for p in all_predictions])

    # ===== 离线评分（冻结 scorer）=====
    print(flush=True)
    print("=== 离线评分（冻结 scorer，不调用 RAG/LLM/Embedding）===", flush=True)
    report = build_report(questions, all_predictions)
    retrieval_runtime = _retrieval_runtime_summary(all_raw_rows, retriever)
    report["summary"]["retrieval_runtime"] = retrieval_runtime

    metadata = build_run_metadata(
        run_id=run_id, split=args.split, mode=args.mode,
        questions=questions, questions_path=Path(args.questions), chunks=chunks,
        model_name=str(getattr(adapter.assistant.chat_backend, "model_name", "")),
        embedding_model=str(getattr(retriever.embedding_backend, "model_name", "")),
        retrieval_config=retriever.config,
        prompt_path=PROJECT_ROOT / "online_rag" / "prompts.py",
    )
    metadata["run_scope"] = "end_to_end"
    metadata["lexical_only"] = False
    metadata["retrieval_mode_baseline"] = args.retrieval_mode
    metadata["dense_weight"] = dense_weight
    metadata["retrieval_runtime"] = retrieval_runtime
    metadata["checkpointing"] = "fsync_after_each_completed_question"
    metadata["max_attempts_per_question"] = args.max_attempts
    metadata["retry_policy"] = "retry_only_on_exception_not_on_quality"
    health = getattr(retriever.embedding_backend, "health", None)
    if callable(health):
        metadata["embedding_health"] = health()

    corpus_report = audit_corpus(questions, chunks)
    destination = write_run_artifacts(
        output_dir,
        metadata=metadata, corpus_audit=corpus_report,
        raw_rows=all_raw_rows, predictions=all_predictions,
        report=report, questions=questions,
    )

    gate = evaluate_regression_gate(report["summary"], args.thresholds, "end_to_end")
    write_json(destination / "regression_gate.json", gate)

    # 更新 checkpoint 为完成态。
    checkpoint_state = {
        "run_id": run_id, "split": args.split, "mode": args.mode,
        "run_scope": "end_to_end",
        "status": "complete" if fail_count == 0 else "complete_with_errors",
        "completed_count": len(all_predictions),
        "completed_ids": [q.id for q in questions],
        "last_completed_id": questions[-1].id if questions else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "error": None,
        "success_count": success_count,
        "fail_count": fail_count,
        "failed_questions": failures,
    }
    _save_checkpoint(checkpoint_path, checkpoint_state)

    # 摘要输出。
    print(flush=True)
    print("=== 评分摘要 ===", flush=True)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2), flush=True)
    print(flush=True)
    print(json.dumps({
        "regression_profile": "end_to_end",
        "regression_passed": gate["passed"],
        "failed_metrics": [c["metric"] for c in gate["checks"] if not c["passed"]],
    }, ensure_ascii=False, indent=2), flush=True)
    print(flush=True)
    print(f"评测结果：{destination}", flush=True)
    return 1 if fail_count or not gate["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
