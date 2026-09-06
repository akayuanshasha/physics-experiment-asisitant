"""LLM Only 对照实验：完全关闭检索，仅用生成模型回答 15 题。

公平性约束（与 Hybrid / BM25 一致）：
- 同一 15 题 test split、同一生成模型 glm-5.2-107、同一生成参数（temp 0.1, max 8192）。
- 完全关闭知识库检索：不调用 BM25 / Dense / Embedding / RRF / Reranker，不注入检索 context。
- Prompt 只移除必须依赖检索 context / evidence / citation 的部分，其余任务规范保持一致，
  避免人为削弱 LLM Only。
- 不修改冻结的 Hybrid / BM25 / 评分规则 / 15 题测试集 / prompts.py。
- 逐题即时落盘（fsync）+ 断点续跑；仅异常重试，不因答案质量重跑。
- 预测全部完成后冻结，再用同一套冻结 scorer 离线评分。
- 检索专属指标（Recall@K / MRR / citation / context evidence）对 LLM Only 标记 N/A，
  不人为赋 0。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from online_rag.chat import ChatConfig, RemoteChatBackend
from online_rag.prompts import SYSTEM_PROMPT
from online_rag.retriever import RetrievalConfig

from .adapters import OnlineRagAdapter  # noqa: F401  (仅用于类型参照，不在此路径使用)
from .corpus_audit import audit_corpus
from .dataset import DEFAULT_QUESTIONS_PATH, DEFAULT_SCHEMA_PATH, load_questions
from .models import ContextEvidence, EvaluationQuestion, Prediction, RetrievedEvidence
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
PROMPT_PATH = PROJECT_ROOT / "online_rag" / "prompts.py"

MAX_ATTEMPTS = 3
RETRY_BACKOFF = 5.0


# LLM Only 的 system prompt：复用冻结 SYSTEM_PROMPT，移除规则 9（该规则约束 <evidence> 块，
# LLM Only 不注入 evidence，保留会误导模型以为有 evidence 输入）。其余 9 条任务规范全部保留。
_LLM_ONLY_SYSTEM_PROMPT = "\n".join(
    line for line in SYSTEM_PROMPT.splitlines()
    if not line.strip().startswith("9. ")
) + "\n"


def _llm_only_messages(question: str) -> list[dict[str, str]]:
    """构造 LLM Only 消息：无 <evidence> 块，通用知识回答指令（与冻结 NO_EVIDENCE_NOTICE 路径一致）。"""
    user_prompt = (
        f"学生当前问题：\n{question.strip()}\n\n"
        "当前没有可用的实验资料，请直接基于可靠的通用物理知识回答。"
        "不要说明信息来自资料还是通用知识。"
    )
    return [
        {"role": "system", "content": _LLM_ONLY_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


class LlmOnlyBackend:
    """只生成、不检索的最小后端，复用冻结 RemoteChatBackend 与 ChatConfig.from_env。"""

    def __init__(self) -> None:
        self.chat = RemoteChatBackend(ChatConfig.from_env())
        self.model_name = self.chat.model_name
        self.temperature = 0.1
        self.max_tokens = 8192

    def predict(self, question: EvaluationQuestion, *, mode: str = "blind") -> tuple[Prediction, dict]:
        started = time.perf_counter()
        messages = _llm_only_messages(question.question)
        answer = self.chat.complete(
            messages, temperature=self.temperature, max_tokens=self.max_tokens,
        )
        total_ms = (time.perf_counter() - started) * 1000
        answer = (answer or "").strip()
        prediction = Prediction(
            id=question.id,
            mode=mode,
            answer=answer,
            retrieved_evidence=[],
            citations=[],
            grounded=False,
            warnings=["llm_only: 检索已关闭，无 evidence/context"],
            timings_ms={"generation": total_ms, "total": total_ms},
            context_evidence=[],
            model_citations=None,
            citation_contract_version="2-llm-only",
        )
        raw = {
            "question": question.question,
            "answer": answer,
            "messages": messages,
            "retrieval": {"retrieval_mode": "none", "hits": []},
            "evidence": [],
            "citations": [],
            "grounded": False,
            "timings_ms": {"generation": total_ms, "total": total_ms},
            "generation_mode": "llm_only",
        }
        return prediction, raw


def _atomic_write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl_fsync(path: Path, row: dict) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM Only 对照实验（15题，无检索）")
    parser.add_argument("--split", default="test", choices=["test", "dev", "all"])
    parser.add_argument("--mode", default="blind", choices=["blind", "page-context"])
    parser.add_argument("--run-id")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS_PATH)
    parser.add_argument("--max-attempts", type=int, default=MAX_ATTEMPTS)
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / ".env")
    questions = load_questions(args.questions, args.schema, split=args.split)
    run_id = args.run_id or make_run_id(args.split, args.mode) + "_llm_only"
    output_dir = args.output_dir or (DEFAULT_REPORT_ROOT / run_id)
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_path = output_dir / "raw.jsonl"
    pred_path = output_dir / "predictions.jsonl"
    checkpoint_path = output_dir / "checkpoint_state.json"

    checkpoint = {"completed_ids": [], "completed_count": 0, "status": "running"} if args.fresh else _load_checkpoint(checkpoint_path)
    completed_ids: list[str] = list(checkpoint.get("completed_ids", []))
    completed_set = set(completed_ids)

    print("=== LLM Only 对照实验 ===", flush=True)
    print(f"run_id      : {run_id}", flush=True)
    print(f"output_dir  : {output_dir}", flush=True)
    print(f"split/mode  : {args.split} / {args.mode}", flush=True)
    print(f"questions   : {len(questions)}", flush=True)
    print(f"检索        : 完全关闭（无 BM25/Dense/Embedding/RRF/Reranker/Context）", flush=True)
    print(f"已断点完成  : {len(completed_set)} 题 -> {completed_ids}", flush=True)
    print(f"重试上限    : 每题最多 {args.max_attempts} 次（仅异常重试）", flush=True)
    print(f"冻结文件    : 不修改 Hybrid/BM25/评分规则/prompts.py", flush=True)
    print(flush=True)

    backend = LlmOnlyBackend()
    print(f"backend 就绪：model={backend.model_name} temp={backend.temperature} "
          f"max_tokens={backend.max_tokens}", flush=True)
    print(f"system_prompt 规则数：{sum(1 for l in _LLM_ONLY_SYSTEM_PROMPT.splitlines() if l.strip()[:2].rstrip('.') in {str(i) for i in range(1,20)} and l.strip()[2:3]=='.')} (已移除规则9)", flush=True)
    print(flush=True)

    total = len(questions)
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
            try:
                prediction, raw = backend.predict(question, mode=args.mode)
                last_err = prediction.error
                if last_err is None:
                    break
                print(f"  尝试 {attempt}/{args.max_attempts} 异常: {last_err}", flush=True)
            except Exception as exc:
                last_err = f"{type(exc).__name__}: {exc}"
                prediction = None
                raw = None
                print(f"  尝试 {attempt}/{args.max_attempts} 未捕获异常: {last_err}", flush=True)
            if attempt < args.max_attempts:
                time.sleep(RETRY_BACKOFF)

        if prediction is None:
            t0 = time.perf_counter()
            prediction = Prediction(
                id=qid, mode=args.mode, answer="", retrieved_evidence=[],
                citations=[], grounded=False,
                timings_ms={"total": (time.perf_counter() - t0) * 1000},
                error=last_err or "unknown_error",
            )
            raw = {"error": last_err or "unknown_error"}

        _append_jsonl_fsync(raw_path, {"id": qid, "mode": args.mode, "response": raw})
        _append_jsonl_fsync(pred_path, prediction.to_dict())
        completed_ids.append(qid)
        completed_set.add(qid)
        _save_checkpoint(checkpoint_path, {
            "run_id": run_id, "split": args.split, "mode": args.mode,
            "run_scope": "end_to_end", "status": "running",
            "completed_count": len(completed_ids), "completed_ids": completed_ids,
            "last_completed_id": qid,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "error": last_err,
        })

        if last_err:
            failures.append({"id": qid, "error": last_err})
            print(f"  => 最终失败（已记录，不重跑）: {last_err}", flush=True)
        else:
            ans_preview = (prediction.answer or "").replace("\n", " ")[:80]
            print(f"  => 完成 answer={ans_preview!r}", flush=True)

    # 汇总所有预测
    print(flush=True)
    print("=== 汇总所有预测用于离线评分 ===", flush=True)
    from .dataset import read_jsonl
    all_predictions: list[Prediction] = []
    all_raw_rows: list[dict] = []
    if raw_path.is_file():
        raw_by_id = {str(r.get("id", "")): r for r in read_jsonl(raw_path)}
        pred_by_id = {str(r.get("id", "")): Prediction.from_dict(r) for r in read_jsonl(pred_path)}
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

    write_jsonl(raw_path, all_raw_rows)
    write_jsonl(pred_path, [p.to_dict() for p in all_predictions])

    # ===== 离线评分（冻结 scorer）=====
    print(flush=True)
    print("=== 离线评分（冻结 scorer，不调用 RAG/LLM/Embedding）===", flush=True)
    report = build_report(questions, all_predictions)
    # LLM Only 检索专属指标置 N/A（不人为赋 0）。
    report["summary"]["retrieval_runtime"] = {
        "retrieval_mode_counts": {"none": len(all_predictions)},
        "note": "LLM Only：检索完全关闭，检索专属指标为 N/A",
        "hybrid_query_rate": "N/A",
        "bm25_fallback_rate": "N/A",
        "dense_nonzero_hit_count": "N/A",
        "dense_available": False,
        "document_vector_coverage": "N/A",
    }

    # corpus_audit 仍按冻结口径跑（LLM Only 不用检索，但保留语料审计以保持产物一致）。
    from online_rag.corpus import load_corpus
    chunks = list(load_corpus("b_static/experiment"))
    corpus_report = audit_corpus(questions, chunks)

    # LLM Only 不检索；传默认 RetrievalConfig 仅供 metadata 记录 chunk 参数
    # （与冻结基线 700/1000/100 一致），不参与任何检索逻辑，不改变实验语义。
    _metadata_retrieval_config = RetrievalConfig()
    metadata = build_run_metadata(
        run_id=run_id, split=args.split, mode=args.mode,
        questions=questions, questions_path=Path(args.questions), chunks=chunks,
        model_name=backend.model_name,
        embedding_model="none (LLM Only: retrieval disabled)",
        retrieval_config=_metadata_retrieval_config,
        prompt_path=PROMPT_PATH,
    )
    metadata["run_scope"] = "end_to_end"
    metadata["lexical_only"] = False
    metadata["retrieval_mode_baseline"] = "llm_only"
    metadata["dense_weight"] = "N/A"
    metadata["retrieval_disabled"] = True
    metadata["prompt_note"] = "复用冻结 SYSTEM_PROMPT，仅移除规则9（依赖<evidence>块），其余任务规范保持一致"
    metadata["checkpointing"] = "fsync_after_each_completed_question"
    metadata["max_attempts_per_question"] = args.max_attempts
    metadata["retry_policy"] = "retry_only_on_exception_not_on_quality"

    destination = write_run_artifacts(
        output_dir,
        metadata=metadata, corpus_audit=corpus_report,
        raw_rows=all_raw_rows, predictions=all_predictions,
        report=report, questions=questions,
    )

    gate = evaluate_regression_gate(report["summary"], args.thresholds, "end_to_end")
    write_json(destination / "regression_gate.json", gate)

    _save_checkpoint(checkpoint_path, {
        "run_id": run_id, "split": args.split, "mode": args.mode,
        "run_scope": "end_to_end",
        "status": "complete" if fail_count == 0 else "complete_with_errors",
        "completed_count": len(all_predictions),
        "completed_ids": [q.id for q in questions],
        "last_completed_id": questions[-1].id if questions else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "error": None, "success_count": success_count, "fail_count": fail_count,
        "failed_questions": failures,
    })

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
