"""三组（LLM Only / BM25 RAG / Hybrid RAG）离线统一评价与对比。

完全离线：不调用 LLM/RAG/Embedding，不重跑任何题，不修改冻结预测和系统。
复用冻结 scorer (rag_eval.scoring) 的判定函数，保持既有 rubric 和判定标准。

Answer Score 构造（公平共同总分，归一化到 100）：
  从冻结 scorer 的 6 个组件中取 4 个不依赖检索/citation 的回答维度：
    Factual Correctness   30 分  (required_term_coverage，forbidden 命中则归 0)
    Completeness          15 分  (required_term_coverage，无答案则 0)
    Boundary/Answerability 10 分 (boundary_ok 且无 forbidden 命中)
    Clarity                5 分  (答案非空且 ≤ max_answer_chars)
  合计 60 分，归一化 ×(100/60) → Answer Score /100。
  Retrieval(20) 与 Grounded/Citation(20) 不计入共同总分（LLM Only 天生不适用）。
"""

from __future__ import annotations

import json
from pathlib import Path

from rag_eval.dataset import load_questions
from rag_eval.models import Prediction
from rag_eval.scoring import (
    _REFUSAL_MARKERS,
    _REFUSAL_PATTERN,
    _boundary_assessment,
    _forbidden_matches,
    normalized,
)

REPORT_ROOT = Path("evaluation_reports/rag_v1")
GROUPS = [
    ("LLM Only", "test_e2e_llm_only_20260905_final"),
    ("BM25 RAG", "test_e2e_bm25_20260905_final"),
    ("Hybrid RAG", "test_e2e_hybrid_20260905_final"),
]
MAX_ANSWER_CHARS = 1800  # 与冻结 scorer score_prediction 默认一致


def _answer_components(question, prediction):
    """复用冻结 scorer 判定，返回 4 个回答维度组件分（未归一化，满分60）。"""
    answer_norm = normalized(prediction.answer)
    group_hits = [
        any(normalized(term) in answer_norm for term in group)
        for group in question.required_term_groups
    ]
    required_term_coverage = sum(group_hits) / len(group_hits) if group_hits else 1.0
    forbidden_hits, forbidden_suspicions = _forbidden_matches(
        prediction.answer, question.forbidden_claims
    )
    refusal_detected = (
        any(normalized(marker) in answer_norm for marker in _REFUSAL_MARKERS)
        or bool(_REFUSAL_PATTERN.search(prediction.answer))
    )
    boundary_ok, boundary_class = _boundary_assessment(
        question, prediction.answer, refusal_detected,
    )

    factual_points = 30.0 * required_term_coverage
    if forbidden_hits:
        factual_points = 0.0
    completeness_points = 15.0 * required_term_coverage if answer_norm else 0.0
    boundary_points = 10.0 if boundary_ok and not forbidden_hits else 0.0
    clarity_points = 5.0 if answer_norm and len(prediction.answer) <= MAX_ANSWER_CHARS else 0.0
    raw_total = round(factual_points + completeness_points + boundary_points + clarity_points, 2)
    answer_score = round(raw_total * (100.0 / 60.0), 2)

    return {
        "factual": factual_points,
        "completeness": completeness_points,
        "boundary": boundary_points,
        "clarity": clarity_points,
        "raw_total_60": raw_total,
        "answer_score_100": answer_score,
        "term_coverage": round(required_term_coverage, 4),
        "forbidden_hits": forbidden_hits,
        "forbidden_suspicions": forbidden_suspicions,
        "refusal_detected": refusal_detected if not question.answerable else None,
        "boundary_ok": boundary_ok,
        "boundary_class": boundary_class,
        "answer_chars": len(prediction.answer),
    }


def _load_predictions(report_dir: Path) -> dict[str, Prediction]:
    preds = {}
    from rag_eval.dataset import read_jsonl
    for row in read_jsonl(report_dir / "predictions.jsonl"):
        p = Prediction.from_dict(row)
        preds[p.id] = p
    return preds


def _load_summary(report_dir: Path) -> dict:
    return json.loads((report_dir / "auto_report.json").read_text(encoding="utf-8"))["summary"]


def main():
    questions = load_questions(split="test")
    qmap = {q.id: q for q in questions}

    # 逐题逐组计算 Answer Score
    per_qid = {}  # qid -> {group: components}
    for gname, gdir in GROUPS:
        preds = _load_predictions(REPORT_ROOT / gdir)
        for qid, q in qmap.items():
            p = preds.get(qid)
            if p is None:
                continue
            comp = _answer_components(q, p)
            per_qid.setdefault(qid, {})[gname] = comp

    # 汇总 Answer Score
    group_answer_scores = {g[0]: [] for g in GROUPS}
    for qid, gcomps in per_qid.items():
        for gname, _ in GROUPS:
            if gname in gcomps:
                group_answer_scores[gname].append(gcomps[gname]["answer_score_100"])

    print("=" * 90)
    print("三组统一 Answer Score（离线，复用冻结 scorer 判定，归一化到 100）")
    print("维度：Factual 30 + Completeness 15 + Boundary 10 + Clarity 5 = 60 → ×100/60")
    print("=" * 90)
    for gname, _ in GROUPS:
        vals = group_answer_scores[gname]
        avg = sum(vals) / len(vals) if vals else 0.0
        print(f"  {gname:10s}: 平均 Answer Score = {round(avg,2)}  (逐题: {[round(v,1) for v in vals]})")
    print()

    # 逐题三系统对比表
    print("=" * 90)
    print("15题逐题三系统对比")
    print("=" * 90)
    order = [q.id for q in questions]
    header = f"{'题号':6s} {'suite':14s} {'category':16s} | {'LLM AS':7s} {'BM25 AS':8s} {'Hybrid AS':9s} | {'LLM term':8s} {'BM25 term':9s} {'Hybrid term':10s}"
    print(header)
    print("-" * len(header))
    for qid in order:
        q = qmap[qid]
        gc = per_qid.get(qid, {})
        def fmt(g, key, w):
            v = gc.get(g, {}).get(key)
            return f"{v}".ljust(w) if v is not None else "N/A".ljust(w)
        def fmtf(g, key, w):
            v = gc.get(g, {}).get(key)
            return f"{v:.2f}".ljust(w) if v is not None else "N/A".ljust(w)
        line = (
            f"{qid:6s} {q.suite:14s} {q.category:16s} | "
            + fmtf("LLM Only", "answer_score_100", 7) + " "
            + fmtf("BM25 RAG", "answer_score_100", 8) + " "
            + fmtf("Hybrid RAG", "answer_score_100", 9) + " | "
            + fmtf("LLM Only", "term_coverage", 8) + " "
            + fmtf("BM25 RAG", "term_coverage", 9) + " "
            + fmtf("Hybrid RAG", "term_coverage", 10)
        )
        print(line)
    print()

    # B007 自动 vs 语义冲突复核
    print("=" * 90)
    print("人工复核建议：自动规则与语义判断冲突的题（保留自动结果，单独给人工结论）")
    print("=" * 90)
    review = []
    for qid in order:
        q = qmap[qid]
        gc = per_qid.get(qid, {})
        for gname, _ in GROUPS:
            c = gc.get(gname)
            if not c:
                continue
            # boundary 语义冲突：unqualified_answer 但语义上拒答；或 answerable 误拒答
            conflict = False
            note = ""
            if qid == "B007" and c["boundary_class"] == "unqualified_answer":
                conflict = True
                note = "模型语义上正确拒答示例数据误用，但措辞未命中冻结 scorer refusal 关键词"
            # forbidden_suspicions 但无硬命中（Hybrid R061）
            if gname == "Hybrid RAG" and qid == "R061" and c["forbidden_suspicions"] and not c["forbidden_hits"]:
                conflict = True
                note = "疑似改写禁用公式但未硬命中，自动判 PASS；建议人工确认是否构成禁用主张"
            if conflict:
                review.append({
                    "题号": qid, "系统": gname,
                    "auto_boundary_ok": c["boundary_ok"],
                    "auto_boundary_class": c["boundary_class"],
                    "auto_forbidden_hits": c["forbidden_hits"],
                    "auto_forbidden_suspicions": c["forbidden_suspicions"],
                    "建议人工结论": note,
                })
    for r in review:
        print(json.dumps(r, ensure_ascii=False))
    print()

    # LLM Only → BM25 提升题
    print("=" * 90)
    print("LLM Only → BM25 RAG 的提升题（Answer Score 上升）")
    print("=" * 90)
    llm_to_bm25 = []
    for qid in order:
        gc = per_qid.get(qid, {})
        a = gc.get("LLM Only", {}).get("answer_score_100")
        b = gc.get("BM25 RAG", {}).get("answer_score_100")
        if a is not None and b is not None:
            delta = round(b - a, 2)
            llm_to_bm25.append((qid, a, b, delta))
    llm_to_bm25.sort(key=lambda x: -x[3])
    print(f"{'题号':6s} {'LLM':7s} {'BM25':7s} {'Δ':7s}")
    for qid, a, b, d in llm_to_bm25:
        mark = "↑" if d > 0 else ("↓" if d < 0 else "=")
        print(f"{qid:6s} {a:<7} {b:<7} {mark} {d}")
    up = [x for x in llm_to_bm25 if x[3] > 0]
    same = [x for x in llm_to_bm25 if x[3] == 0]
    down = [x for x in llm_to_bm25 if x[3] < 0]
    print(f"  提升 {len(up)} 题，持平 {len(same)} 题，下降 {len(down)} 题")
    print()

    # BM25 → Hybrid 提升/退化题
    print("=" * 90)
    print("BM25 RAG → Hybrid RAG 的提升/退化题（Answer Score 变化）")
    print("=" * 90)
    bm25_to_hybrid = []
    for qid in order:
        gc = per_qid.get(qid, {})
        b = gc.get("BM25 RAG", {}).get("answer_score_100")
        h = gc.get("Hybrid RAG", {}).get("answer_score_100")
        if b is not None and h is not None:
            delta = round(h - b, 2)
            bm25_to_hybrid.append((qid, b, h, delta))
    bm25_to_hybrid.sort(key=lambda x: -x[3])
    print(f"{'题号':6s} {'BM25':7s} {'Hybrid':7s} {'Δ':7s} {'说明':s}")
    notes = {
        "R061": "BM25 硬命中禁用公式(forbidden_claim)→Hybrid 仅疑似，Answer Score 大幅回升",
        "R058": "BM25 术语全覆盖→Hybrid 缺1项",
        "B007": "两者回答都正确拒答，Answer Score 相同；检索层差异见检索指标",
    }
    for qid, b, h, d in bm25_to_hybrid:
        mark = "↑" if d > 0 else ("↓" if d < 0 else "=")
        print(f"{qid:6s} {b:<7} {h:<7} {mark} {d:<7} {notes.get(qid,'')}")
    up2 = [x for x in bm25_to_hybrid if x[3] > 0]
    same2 = [x for x in bm25_to_hybrid if x[3] == 0]
    down2 = [x for x in bm25_to_hybrid if x[3] < 0]
    print(f"  Hybrid 提升 {len(up2)} 题，持平 {len(same2)} 题，退化 {len(down2)} 题")
    print()

    # 检索指标（仅 BM25 vs Hybrid）
    print("=" * 90)
    print("检索能力对比（仅 BM25 vs Hybrid；LLM Only 为 N/A）")
    print("=" * 90)
    summ = {g[0]: _load_summary(REPORT_ROOT / g[1]) for g in GROUPS}
    for metric in ["recall_at_1", "recall_at_3", "recall_at_5", "mrr", "anchor_recall_at_5"]:
        b = summ["BM25 RAG"].get(metric)
        h = summ["Hybrid RAG"].get(metric)
        print(f"  {metric:20s}: BM25={b}  Hybrid={h}  LLM Only=N/A")
    print()

    # Citation（仅适用 RAG 系统）
    print("=" * 90)
    print("Citation 指标（仅 RAG 系统适用；实际定义说明）")
    print("=" * 90)
    print("  实际定义：citation_valid_rate = 答案附带的 context evidence ID 存在于合法")
    print("  Context 集合（retrieved ∪ context_expansion）中的比例；不是模型真实逐结论引用准确率。")
    print("  model_citation_observation_rate = 模型 [E#] 选择可观测比例；adapter 置 None，故 0.0。")
    for gname, _ in GROUPS:
        s = summ[gname]
        if gname == "LLM Only":
            print(f"  {gname:10s}: citation_valid_rate = N/A (无 context/citation)")
        else:
            print(f"  {gname:10s}: citation_valid_rate = {s.get('citation_valid_rate')}  "
                  f"model_citation_observation_rate = {s.get('model_citation_observation_rate')}")
    print()

    # 保存完整结果到 JSON
    out = {
        "answer_score_definition": "Factual30+Completeness15+Boundary10+Clarity5=60, ×100/60归一化",
        "group_answer_score_avg": {
            g: round(sum(group_answer_scores[g]) / len(group_answer_scores[g]), 2)
            for g in group_answer_scores
        },
        "per_question": {
            qid: {g: per_qid[qid].get(g) for g, _ in GROUPS}
            for qid in order
        },
        "retrieval_metrics": {
            "BM25 RAG": {m: summ["BM25 RAG"].get(m) for m in ["recall_at_1","recall_at_3","recall_at_5","mrr","anchor_recall_at_5"]},
            "Hybrid RAG": {m: summ["Hybrid RAG"].get(m) for m in ["recall_at_1","recall_at_3","recall_at_5","mrr","anchor_recall_at_5"]},
            "LLM Only": "N/A",
        },
        "manual_review": review,
        "llm_to_bm25": [{"id":q,"llm":a,"bm25":b,"delta":d} for q,a,b,d in llm_to_bm25],
        "bm25_to_hybrid": [{"id":q,"bm25":b,"hybrid":h,"delta":d} for q,b,h,d in bm25_to_hybrid],
    }
    out_path = REPORT_ROOT / "three_way_offline_analysis.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完整结果已保存：{out_path}")


if __name__ == "__main__":
    main()
