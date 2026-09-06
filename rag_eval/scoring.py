"""Deterministic pre-scoring for retrieval, answers and citations."""

from __future__ import annotations

import re
import statistics
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from typing import Iterable

from .corpus_audit import anchor_terms
from .models import EvaluationQuestion, Prediction, RetrievedEvidence


_REFUSAL_MARKERS = (
    "无法确定", "不能确定", "无法给出", "不能给出", "资料不足", "资料未提供",
    "未给出", "没有提供", "缺少", "需要补充", "请补充", "需要提供", "请提供",
    "需实测", "需要实测", "应以现场", "不得假设", "不能凭空", "无法从现有资料",
)

_REFUSAL_PATTERN = re.compile(
    r"(?:无法|不能)(?:直接|准确|具体|仅凭.{0,12})?"
    r"(?:确定|给出|提供|计算|判断|获取|得知)"
)

_INSUFFICIENCY_PATTERN = re.compile(
    r"(?:现有|当前|正式)?(?:实验|课程)?资料.{0,18}"
    r"(?:不足|未提供|没有提供|未给出|没有给出|不包含)"
    r"|(?:无法|不能).{0,16}(?:确定|给出|提供|计算|算出|判断|获取|得知|回答)"
    r"|资料不足|需要补充|请补充|需要提供|请提供|需实测|需要实测"
)

_ASSERTED_DETAIL_PATTERN = re.compile(
    r"(?:一定|必然|就是|明确规定|确定为).{0,32}"
    r"(?:对应|等于|为|采用|使用)"
    r"|(?:分别)?对应(?:关系)?(?:就是|为|如下)"
)

_QUALIFIED_SUPPLEMENT_PATTERN = re.compile(
    r"通常|一般(?:情况下|来说|性)?|仅供参考|作为参考|"
    r"可类比|可以类比|可能|假设|若|如果|在.{0,18}条件下|"
    r"通用知识|从.{0,12}(?:通用|一般)原理|不代表课程结论|"
    r"并非.{0,12}课程结论"
)

_LATEX_SYMBOLS = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ",
    "epsilon": "ε", "varepsilon": "ε", "theta": "θ", "lambda": "λ",
    "mu": "μ", "nu": "ν", "pi": "π", "rho": "ρ", "sigma": "σ",
    "omega": "ω", "phi": "φ", "varphi": "φ", "Delta": "δ",
    "Gamma": "γ", "Lambda": "λ", "Omega": "ω", "Phi": "φ",
}

_SYNONYM_PATTERNS = (
    (re.compile(r"不可以|不能"), "无法"),
    (re.compile(r"资料不足|无法确定"), "证据不足"),
    (re.compile(r"没有提供|未能?提供|没有给出|未给出"), "资料未提供"),
    (re.compile(r"无法(?:直接)?(?:计算|算出)"), "无法计算"),
    (re.compile(r"重新(?:进行|做)?(?:校准|标定)|重新校正"), "重新标定"),
    (re.compile(r"(?:实验)?现场(?:进行)?测量|实地测量"), "现场测量"),
    (re.compile(r"测量数据|实测数据"), "读数"),
    (re.compile(r"累计"), "累积"),
    (re.compile(r"粘滞"), "黏滞"),
    (re.compile(r"合力(?:等于|为)0|合力为零"), "受力平衡"),
    (re.compile(r"直线拟合"), "线性拟合"),
    (re.compile(r"线性工作范围"), "线性范围"),
    (re.compile(r"多个周期"), "多周期"),
    (re.compile(r"不确定度传递"), "不确定度传播"),
    (re.compile(r"校准"), "标定"),
    (re.compile(r"选做"), "选作"),
    (re.compile(r"不少于|不低于"), "至少"),
    (re.compile(r"功率(?:降低|降至|为|等于).{0,6}(?:一半|1/2)"), "半功率"),
    (re.compile(r"0[.]707(?:1)?"), "1/sqrt2"),
    (re.compile(r"励磁电动势|激励电动势"), "激发电势"),
    (re.compile(r"比例(?=对切)|比列|比莱特|billet", re.I), "billet"),
    (re.compile(r"梅思林|梅斯林|maslin", re.I), "maslin"),
    (re.compile(r"物距p(?=[^a-z]|$)"), "物距u"),
    (re.compile(r"像距p['′]?"), "像距v"),
    (re.compile(r"温度差值"), "温差"),
    (re.compile(r"基本保持不变|大致不变"), "基本恒定"),
)


def normalized(value: object) -> str:
    """Canonicalize prose and common math notation for deterministic matching."""
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"\\(?:operatorname|mathrm|mathbf|mathit|text)\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\sqrt\{([^{}]*)\}", r"sqrt\1", text)
    text = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r"\1/\2", text)
    text = re.sub(
        r"\\([A-Za-z]+)",
        lambda match: _LATEX_SYMBOLS.get(match.group(1), match.group(0)),
        text,
    )
    text = re.sub(r"\\(?:left|right|quad|qquad)\b|\\[,;!:]", "", text)
    text = text.replace("√", "sqrt")
    text = re.sub(r"\^\{?([+-]?\d+)\}?", r"\1", text)
    text = re.sub(r"_\{?([A-Za-z0-9Ͱ-Ͽ]+)\}?", r"\1", text)
    text = text.lower()
    for pattern, replacement in _SYNONYM_PATTERNS:
        text = pattern.sub(replacement, text)
    # Connectors and presentation punctuation do not change a short formula's meaning.
    text = re.sub(r"(?<=[a-z0-9Ͱ-Ͽ])(?:与|和|对)(?=[a-z0-9Ͱ-Ͽ])", "", text)
    text = re.sub(r"[\s$`*_{}\\()[\]（）,，。；;:：—–\-]", "", text)
    # A second pass catches phrase aliases that were separated by Markdown or
    # LaTeX presentation characters (for example ``物距 $p$``).
    for pattern, replacement in _SYNONYM_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _boundary_assessment(
    question: EvaluationQuestion, answer: str, refusal_detected: bool,
) -> tuple[bool, str]:
    """Classify boundary behavior, including qualified post-refusal help."""
    if not answer.strip():
        return False, "empty_answer"
    if question.answerable:
        return True, "answerable_response"
    if not refusal_detected:
        return False, "unqualified_answer"

    insufficiency = _INSUFFICIENCY_PATTERN.search(answer)
    if insufficiency is None:
        # Legacy refusal markers such as “应以现场…为准” are still valid,
        # but do not provide a reliable split point for post-refusal analysis.
        return True, "insufficient_only"
    supplement = answer[insufficiency.end():].strip()
    if not supplement:
        return True, "insufficient_only"

    asserted_detail = _ASSERTED_DETAIL_PATTERN.search(supplement)
    if asserted_detail is None:
        if _QUALIFIED_SUPPLEMENT_PATTERN.search(supplement):
            return True, "insufficient_with_qualified_supplement"
        return True, "insufficient_only"
    prefix = supplement[:asserted_detail.start()]
    if _QUALIFIED_SUPPLEMENT_PATTERN.search(prefix):
        return True, "insufficient_with_qualified_supplement"
    return False, "insufficient_then_unqualified_claim"


def _rank_of_relevant(
    evidence: list[RetrievedEvidence], relevant_ids: set[str], limit: int | None = None,
) -> int | None:
    rows = evidence if limit is None else evidence[:limit]
    return next(
        (index for index, item in enumerate(rows, 1) if item.experiment_id in relevant_ids),
        None,
    )


def _source_metadata_complete(item: RetrievedEvidence) -> bool:
    return all((
        item.experiment_id, item.source_file, item.section, item.chunk_id,
        item.source_tier, item.source_kind, item.authority,
    ))


def _forbidden_matches(answer: str, claims: Iterable[str]) -> tuple[list[str], list[str]]:
    answer_norm = normalized(answer)
    exact: list[str] = []
    suspected: list[str] = []
    for claim in claims:
        claim_norm = normalized(claim)
        if not claim_norm:
            continue
        if claim_norm in answer_norm:
            exact.append(claim)
            continue
        if len(claim_norm) >= 8:
            windows = [
                answer_norm[index:index + len(claim_norm) + 6]
                for index in range(0, max(1, len(answer_norm) - len(claim_norm) + 1), 3)
            ]
            similarity = max(
                (SequenceMatcher(None, claim_norm, window).ratio() for window in windows),
                default=0.0,
            )
            if similarity >= 0.78:
                suspected.append(claim)
    return exact, suspected


def _anchor_recall(question: EvaluationQuestion, evidence: list[RetrievedEvidence]) -> float:
    relevant = set(question.relevant_experiment_ids)
    text = normalized("\n".join(
        item.text for item in evidence[:5] if item.experiment_id in relevant
    ))
    checks: list[bool] = []
    for source in question.source:
        terms = anchor_terms(source.anchor)
        if terms:
            checks.append(any(normalized(term) in text for term in terms))
    return sum(checks) / len(checks) if checks else 1.0


def score_prediction(
    question: EvaluationQuestion,
    prediction: Prediction,
    *,
    max_answer_chars: int = 1800,
) -> dict:
    evidence = sorted(prediction.retrieved_evidence, key=lambda item: item.rank)
    relevant_ids = set(question.relevant_experiment_ids)
    rank = _rank_of_relevant(evidence, relevant_ids)
    returned_ids = [item.experiment_id for item in evidence]
    unique_relevant = set(returned_ids[:5]) & relevant_ids
    multi_coverage = len(unique_relevant) / len(relevant_ids) if relevant_ids else 1.0
    top5 = evidence[:5]
    expected_source_tiers = set(question.expected_source_tiers)
    expected_source_tier_rate = (
        sum(item.source_tier in expected_source_tiers for item in top5) / len(top5)
        if top5 else 0.0
    )
    secondary_source_leak_rate = (
        sum(item.source_tier == "secondary" for item in top5) / len(top5)
        if top5 and not question.secondary_source_allowed else 0.0
    )
    example_data_misuse = bool(
        not question.example_data_allowed
        and any(item.is_example_data or item.source_tier == "example" for item in top5)
    )
    irrelevant_ratio = (
        sum(item.experiment_id not in relevant_ids for item in top5) / len(top5)
        if top5 else 0.0
    )
    metadata_rate = (
        sum(_source_metadata_complete(item) for item in top5) / len(top5)
        if top5 else 0.0
    )

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

    retrieved_evidence_by_id = {
        item.evidence_id: item for item in evidence if item.evidence_id
    }
    context_evidence_by_id = {
        item.evidence_id: item for item in prediction.context_evidence if item.evidence_id
    }
    legal_evidence_by_id = dict(retrieved_evidence_by_id)
    legal_evidence_by_id.update(context_evidence_by_id)
    valid_citations = [item for item in prediction.citations if item in legal_evidence_by_id]
    invalid_citations = [item for item in prediction.citations if item not in legal_evidence_by_id]
    citation_valid_rate = (
        len(valid_citations) / len(prediction.citations) if prediction.citations else 0.0
    )
    model_citations_available = prediction.model_citations is not None
    model_citations = prediction.model_citations or []
    valid_model_citations = [
        item for item in model_citations if item in legal_evidence_by_id
    ]
    invalid_model_citations = [
        item for item in model_citations if item not in legal_evidence_by_id
    ]
    cited_relevant = (
        bool(valid_model_citations) and all(
            legal_evidence_by_id[item].experiment_id in relevant_ids
            for item in valid_model_citations
        )
        if model_citations_available else None
    )
    context_has_relevant_evidence = any(
        item.experiment_id in relevant_ids for item in legal_evidence_by_id.values()
    )
    anchor_recall = _anchor_recall(question, evidence)

    retrieval_points = 20.0 * multi_coverage if rank and rank <= 5 else 0.0
    factual_points = 30.0 * required_term_coverage
    if forbidden_hits:
        factual_points = 0.0
    if model_citations_available:
        grounded_points = 20.0 * (
            len(valid_model_citations) / len(model_citations)
            if model_citations and cited_relevant else 0.0
        )
    else:
        grounded_points = (
            20.0 * citation_valid_rate
            if prediction.grounded and context_has_relevant_evidence else 0.0
        )
    completeness_points = 15.0 * required_term_coverage if answer_norm else 0.0
    boundary_points = 10.0 if boundary_ok and not forbidden_hits else 0.0
    clarity_points = 5.0 if answer_norm and len(prediction.answer) <= max_answer_chars else 0.0
    total = round(
        retrieval_points + factual_points + grounded_points
        + completeness_points + boundary_points + clarity_points,
        2,
    )

    flags: list[str] = []
    if prediction.error:
        flags.append("prediction_error")
    if question.top_k_hit_required and (rank is None or rank > 5):
        flags.append("retrieval_miss_at_5")
    if irrelevant_ratio > 0.6:
        flags.append("retrieval_noise")
    if required_term_coverage < 1.0:
        flags.append("missing_answer_points")
    if forbidden_hits:
        flags.append("forbidden_claim")
    if forbidden_suspicions:
        flags.append("possible_forbidden_paraphrase")
    if not boundary_ok:
        flags.append("boundary_failure")
    if invalid_citations:
        flags.append("invalid_citation")
    if model_citations_available and model_citations and not cited_relevant:
        flags.append("citation_wrong_experiment")
    if invalid_model_citations:
        flags.append("invalid_model_citation")
    if model_citations_available and not model_citations:
        flags.append("missing_citation")
    if len(prediction.answer) > max_answer_chars:
        flags.append("answer_too_long")
    if expected_source_tier_rate < 1.0:
        flags.append("unexpected_source_tier")
    if secondary_source_leak_rate > 0.0:
        flags.append("secondary_source_leak")
    if example_data_misuse:
        flags.append("example_data_misuse")

    return {
        "id": question.id,
        "split": question.split,
        "suite": question.suite,
        "category": question.category,
        "mode": prediction.mode,
        "auto_score": total,
        "retrieval": {
            "first_relevant_rank": rank,
            "recall_at_1": bool(rank == 1),
            "recall_at_3": bool(rank and rank <= 3),
            "recall_at_5": bool(rank and rank <= 5),
            "reciprocal_rank": round(1.0 / rank, 6) if rank else 0.0,
            "multi_experiment_coverage_at_5": round(multi_coverage, 4),
            "irrelevant_chunk_ratio_at_5": round(irrelevant_ratio, 4),
            "source_metadata_complete_rate_at_5": round(metadata_rate, 4),
            "anchor_recall_at_5": round(anchor_recall, 4),
            "returned_experiment_ids": returned_ids,
            "returned_source_tiers": [item.source_tier for item in evidence],
            "expected_source_tier_rate_at_5": round(expected_source_tier_rate, 4),
            "secondary_source_leak_rate_at_5": round(secondary_source_leak_rate, 4),
            "example_data_misuse": example_data_misuse,
        },
        "answer": {
            "required_term_coverage": round(required_term_coverage, 4),
            "missing_term_groups": [
                list(group) for group, hit in zip(question.required_term_groups, group_hits)
                if not hit
            ],
            "forbidden_hits": forbidden_hits,
            "forbidden_suspicions": forbidden_suspicions,
            "refusal_detected": refusal_detected if not question.answerable else None,
            "boundary_ok": boundary_ok,
            "boundary_class": boundary_class,
            "answer_chars": len(prediction.answer),
        },
        "citations": {
            "scope": "attached_context_evidence",
            "count": len(prediction.citations),
            "valid_count": len(valid_citations),
            "invalid_ids": invalid_citations,
            "valid_rate": round(citation_valid_rate, 4),
            "all_cited_evidence_from_relevant_experiments": cited_relevant,
            "legal_context_evidence_count": len(legal_evidence_by_id),
            "context_expansion_evidence_count": len(context_evidence_by_id),
            "model_citations": {
                "available": model_citations_available,
                "count": len(model_citations) if model_citations_available else None,
                "valid_count": (
                    len(valid_model_citations) if model_citations_available else None
                ),
                "invalid_ids": (
                    invalid_model_citations if model_citations_available else None
                ),
            },
            "grounded": prediction.grounded,
        },
        "timings_ms": dict(prediction.timings_ms),
        "error": prediction.error,
        "flags": flags,
        "manual_review_required": True,
    }


def _average(values: list[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] * (1 - fraction) + ordered[upper] * fraction, 2)


def _summarize(results: list[dict]) -> dict:
    if not results:
        return {
            "question_count": 0,
            "average_auto_score": 0.0,
            "recall_at_1": 0.0,
            "recall_at_3": 0.0,
            "recall_at_5": 0.0,
            "mrr": 0.0,
        }
    retrieval = [item["retrieval"] for item in results]
    total_ms = [
        float(item.get("timings_ms", {}).get("total", 0.0))
        for item in results if item.get("timings_ms", {}).get("total") is not None
    ]
    return {
        "question_count": len(results),
        "average_auto_score": round(statistics.fmean(item["auto_score"] for item in results), 2),
        "recall_at_1": _average([float(item["recall_at_1"]) for item in retrieval]),
        "recall_at_3": _average([float(item["recall_at_3"]) for item in retrieval]),
        "recall_at_5": _average([float(item["recall_at_5"]) for item in retrieval]),
        "mrr": _average([float(item["reciprocal_rank"]) for item in retrieval]),
        "anchor_recall_at_5": _average([item["anchor_recall_at_5"] for item in retrieval]),
        "irrelevant_chunk_ratio_at_5": _average([
            item["irrelevant_chunk_ratio_at_5"] for item in retrieval
        ]),
        "source_metadata_complete_rate_at_5": _average([
            item["source_metadata_complete_rate_at_5"] for item in retrieval
        ]),
        "expected_source_tier_rate_at_5": _average([
            item["expected_source_tier_rate_at_5"] for item in retrieval
        ]),
        "secondary_source_leak_rate_at_5": _average([
            item["secondary_source_leak_rate_at_5"] for item in retrieval
        ]),
        "example_data_misuse_count": sum(
            bool(item["example_data_misuse"]) for item in retrieval
        ),
        "citation_valid_rate": _average([
            item["citations"]["valid_rate"] for item in results
        ]),
        "model_citation_observation_rate": _average([
            float(item["citations"]["model_citations"]["available"])
            for item in results
        ]),
        "boundary_pass_rate": _average([
            float(item["answer"]["boundary_ok"])
            for item in results if item["answer"]["refusal_detected"] is not None
        ]),
        "prediction_errors": sum(bool(item["error"]) for item in results),
        "flagged_questions": sum(bool(item["flags"]) for item in results),
        "latency_ms": {
            "average": round(statistics.fmean(total_ms), 2) if total_ms else 0.0,
            "p50": _percentile(total_ms, 0.50),
            "p95": _percentile(total_ms, 0.95),
        },
    }


def build_report(
    questions: Iterable[EvaluationQuestion], predictions: Iterable[Prediction],
) -> dict:
    question_list = list(questions)
    by_id = {item.id: item for item in predictions}
    results: list[dict] = []
    for question in question_list:
        prediction = by_id.get(question.id) or Prediction(
            id=question.id,
            mode="blind",
            answer="",
            retrieved_evidence=[],
            citations=[],
            grounded=False,
            error="缺少预测记录",
        )
        results.append(score_prediction(question, prediction))

    grouped: dict[str, dict[str, list[dict]]] = {
        "by_split": defaultdict(list),
        "by_suite": defaultdict(list),
        "by_category": defaultdict(list),
    }
    for result in results:
        grouped["by_split"][result["split"]].append(result)
        grouped["by_suite"][result["suite"]].append(result)
        grouped["by_category"][result["category"]].append(result)
    return {
        "benchmark_version": question_list[0].version if question_list else "1.2",
        "notice": "自动评分用于定位问题，物理事实正确性与P0/P1仍需人工复核。",
        "summary": _summarize(results),
        "breakdowns": {
            name: {key: _summarize(items) for key, items in sorted(values.items())}
            for name, values in grouped.items()
        },
        "results": results,
    }
