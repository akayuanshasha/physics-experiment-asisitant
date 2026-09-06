"""Versioned pass/fail regression thresholds for release gating."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def evaluate_regression_gate(
    summary: dict[str, Any],
    thresholds_path: str | Path,
    profile: str,
) -> dict[str, Any]:
    config = json.loads(Path(thresholds_path).read_text(encoding="utf-8"))
    thresholds = config.get("profiles", {}).get(profile)
    if not isinstance(thresholds, dict):
        raise ValueError(f"回归阈值中不存在 profile: {profile}")
    checks = []
    for metric, rule in thresholds.items():
        current: Any = summary
        for part in metric.split("."):
            current = current.get(part) if isinstance(current, dict) else None
        minimum = rule.get("min") if isinstance(rule, dict) else None
        maximum = rule.get("max") if isinstance(rule, dict) else None
        passed = current is not None
        if passed and minimum is not None:
            passed = float(current) >= float(minimum)
        if passed and maximum is not None:
            passed = float(current) <= float(maximum)
        checks.append({
            "metric": metric,
            "actual": current,
            "minimum": minimum,
            "maximum": maximum,
            "passed": passed,
        })
    return {
        "version": config.get("version", ""),
        "profile": profile,
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
    }
