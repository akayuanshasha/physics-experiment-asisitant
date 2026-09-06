"""Shared OpenAI-compatible client for non-RAG AI features."""

from __future__ import annotations

import os

from openai import OpenAI


def create_llm_client_from_env():
    """Create the client used by anomaly, chart and report generation."""
    api_key = os.getenv("LLM_API_KEY", "").strip()
    base_url = os.getenv("LLM_BASE_URL", "").strip()
    model = os.getenv("LLM_MODEL", "glm-5.2").strip() or "glm-5.2"
    missing = [
        name for name, value in (
            ("LLM_API_KEY", api_key),
            ("LLM_BASE_URL", base_url),
        ) if not value
    ]
    if missing:
        raise RuntimeError("缺少 LLM 配置: " + ", ".join(missing))
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=180.0,
    )
    return client, model
