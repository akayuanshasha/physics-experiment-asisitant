"""Load and strictly validate the versioned JSONL benchmark."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from .models import EvaluationQuestion


DEFAULT_DATASET_DIR = Path(__file__).resolve().parents[1] / "evaluation" / "rag_v1" / "dataset"
DEFAULT_QUESTIONS_PATH = DEFAULT_DATASET_DIR / "rag_eval_questions.jsonl"
DEFAULT_SCHEMA_PATH = DEFAULT_DATASET_DIR / "rag_eval_schema.json"
EXPECTED_QUESTION_COUNT = 71
EXPECTED_SPLITS = Counter({"dev": 56, "test": 15})


class DatasetValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("题库校验失败：\n" + "\n".join(f"- {item}" for item in errors))


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetValidationError([
                f"{source}:{line_number} 不是有效 JSON：{exc.msg}"
            ]) from exc
        if not isinstance(value, dict):
            raise DatasetValidationError([f"{source}:{line_number} 必须是 JSON 对象"])
        rows.append(value)
    return rows


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _validate_schema(value: Any, schema: dict[str, Any], path: str, errors: list[str]) -> None:
    expected_type = schema.get("type")
    if expected_type and not _type_matches(value, expected_type):
        errors.append(f"{path}: 应为 {expected_type}")
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: 值 {value!r} 不在允许范围 {schema['enum']!r}")
    if isinstance(value, str):
        if len(value) < int(schema.get("minLength", 0)):
            errors.append(f"{path}: 字符串长度小于 {schema['minLength']}")
        pattern = schema.get("pattern")
        if pattern and re.fullmatch(pattern, value) is None:
            errors.append(f"{path}: 不符合格式 {pattern}")
    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)):
            errors.append(f"{path}: 项目数少于 {schema['minItems']}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate_schema(item, item_schema, f"{path}[{index}]", errors)
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}: 缺少字段 {required}")
        if schema.get("additionalProperties") is False:
            for key in sorted(set(value) - set(properties)):
                errors.append(f"{path}: 存在未声明字段 {key}")
        for key, child_schema in properties.items():
            if key in value:
                _validate_schema(value[key], child_schema, f"{path}.{key}", errors)


def validate_questions(
    rows: list[dict[str, Any]],
    schema: dict[str, Any],
    *,
    expected_count: int | None = EXPECTED_QUESTION_COUNT,
) -> list[str]:
    errors: list[str] = []
    for index, row in enumerate(rows, 1):
        _validate_schema(row, schema, f"第{index}题", errors)
    ids = [str(row.get("id", "")) for row in rows]
    duplicates = sorted(item for item, count in Counter(ids).items() if item and count > 1)
    if duplicates:
        errors.append("题目 ID 重复：" + ", ".join(duplicates))
    if expected_count is not None and len(rows) != expected_count:
        errors.append(f"题目总数应为 {expected_count}，实际为 {len(rows)}")
    split_counts = Counter(str(row.get("split", "")) for row in rows)
    if expected_count == EXPECTED_QUESTION_COUNT and split_counts != EXPECTED_SPLITS:
        errors.append(f"数据划分应为 dev=56、test=15，实际为 {dict(split_counts)}")
    for row in rows:
        if not isinstance(row.get("retrieval_expectation"), dict):
            continue
        expected = {
            str(item) for item in row["retrieval_expectation"].get(
                "relevant_experiment_ids", []
            )
        }
        declared = {str(item) for item in row.get("experiment_ids", [])}
        declared_with_shared_parents = declared | {
            item.rsplit("_", 1)[0]
            for item in declared
            if re.fullmatch(r"exp\d+_[a-z]", item, re.I)
        }
        if not expected.issubset(declared_with_shared_parents):
            errors.append(
                f"{row.get('id', '?')}: retrieval_expectation 含未在 experiment_ids 声明的编号"
            )
    return errors


def load_questions(
    questions_path: str | Path = DEFAULT_QUESTIONS_PATH,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
    *,
    split: str = "all",
    expected_count: int | None = EXPECTED_QUESTION_COUNT,
) -> list[EvaluationQuestion]:
    rows = read_jsonl(questions_path)
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8-sig"))
    errors = validate_questions(rows, schema, expected_count=expected_count)
    if errors:
        raise DatasetValidationError(errors)
    questions = [EvaluationQuestion.from_dict(row) for row in rows]
    if split not in {"all", "dev", "test"}:
        raise ValueError("split 必须是 all、dev 或 test")
    return questions if split == "all" else [item for item in questions if item.split == split]
