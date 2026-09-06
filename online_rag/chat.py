"""Model-independent chat interface and OpenAI-compatible remote adapter."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


class ChatServiceError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        stage: str = "request",
        retryable: bool = False,
        partial: bool = False,
    ):
        super().__init__(message)
        self.stage = stage
        self.retryable = retryable
        self.partial = partial


class ChatBackend(Protocol):
    model_name: str

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1200,
    ) -> str: ...


@dataclass(frozen=True)
class ChatConfig:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 90.0
    max_attempts: int = 2
    proxy_mode: str = "direct"
    proxy_url: str = ""

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            raise ChatServiceError("Chat API 地址不能为空")
        if not self.api_key.strip():
            raise ChatServiceError("Chat API Key 不能为空")
        if not self.model.strip():
            raise ChatServiceError("Chat 模型名称不能为空")
        if self.timeout_seconds <= 0:
            raise ChatServiceError("Chat 超时时间必须大于 0")
        if self.max_attempts <= 0:
            raise ChatServiceError("Chat 最大尝试次数必须大于 0")
        proxy_mode = self.proxy_mode.strip().lower()
        proxy_url = self.proxy_url.strip()
        if proxy_mode not in {"direct", "system", "custom"}:
            raise ChatServiceError(
                "CHAT_PROXY_MODE 必须是 direct、system 或 custom"
            )
        if proxy_mode == "custom" and not proxy_url:
            raise ChatServiceError("CHAT_PROXY_MODE=custom 时必须配置 CHAT_PROXY_URL")
        object.__setattr__(self, "proxy_mode", proxy_mode)
        object.__setattr__(self, "proxy_url", proxy_url)

    @classmethod
    def from_env(cls) -> "ChatConfig":
        base_url = os.getenv("CHAT_BASE_URL") or os.getenv("LLM_BASE_URL", "")
        api_key = os.getenv("CHAT_API_KEY") or os.getenv("LLM_API_KEY", "")
        model = os.getenv("CHAT_MODEL") or os.getenv("LLM_MODEL", "")
        missing = [name for name, value in (
            ("CHAT_BASE_URL/LLM_BASE_URL", base_url),
            ("CHAT_API_KEY/LLM_API_KEY", api_key),
            ("CHAT_MODEL/LLM_MODEL", model),
        ) if not value]
        if missing:
            raise ChatServiceError("缺少 Chat 配置: " + ", ".join(missing))
        try:
            timeout_seconds = float(os.getenv("CHAT_TIMEOUT_SECONDS", "90"))
            max_attempts = int(os.getenv("CHAT_MAX_ATTEMPTS", "2"))
        except ValueError as exc:
            raise ChatServiceError(
                "CHAT_TIMEOUT_SECONDS 必须是数字，CHAT_MAX_ATTEMPTS 必须是整数"
            ) from exc
        return cls(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
            proxy_mode=os.getenv("CHAT_PROXY_MODE", "direct"),
            proxy_url=os.getenv("CHAT_PROXY_URL", ""),
        )


def _content_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str):
                parts.append(text)
        return "".join(parts).strip()
    return ""


class RemoteChatBackend:
    """Call a GLM/OpenAI-compatible ``/chat/completions`` endpoint."""

    def __init__(self, config: ChatConfig, *, opener=None):
        self.config = config
        self.model_name = config.model
        self._opener = opener or self._build_opener(config)

    @staticmethod
    def _build_opener(config: ChatConfig):
        if config.proxy_mode == "direct":
            return build_opener(ProxyHandler({}))
        if config.proxy_mode == "custom":
            proxies = {"http": config.proxy_url, "https": config.proxy_url}
            return build_opener(ProxyHandler(proxies))
        return build_opener(ProxyHandler())

    def _endpoint(self) -> str:
        base = self.config.base_url.rstrip("/")
        return base if base.endswith("/chat/completions") else base + "/chat/completions"

    @staticmethod
    def _parse_response(body: object) -> str:
        if not isinstance(body, dict):
            raise ChatServiceError("Chat 响应不是 JSON 对象")
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ChatServiceError("Chat 响应缺少 choices")
        choice = choices[0]
        if not isinstance(choice, dict) or not isinstance(choice.get("message"), dict):
            raise ChatServiceError("Chat 响应缺少 message")
        content = _content_text(choice["message"].get("content"))
        if not content:
            raise ChatServiceError("Chat 响应正文为空")
        return content

    @staticmethod
    def _http_error(exc: HTTPError) -> ChatServiceError:
        detail = ""
        try:
            raw = exc.read(2048).decode("utf-8", errors="replace")
            parsed = json.loads(raw)
            error = parsed.get("error", {}) if isinstance(parsed, dict) else {}
            message = error.get("message") if isinstance(error, dict) else None
            if isinstance(message, str) and message.strip():
                detail = ": " + message.strip()
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
        return ChatServiceError(
            f"Chat HTTP {exc.code}{detail}",
            stage="http",
            retryable=exc.code == 429 or exc.code >= 500,
        )

    def _payload(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float,
        max_tokens: int,
        stream: bool,
    ) -> bytes:
        return json.dumps({
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            "chat_template_kwargs": {"enable_thinking": False},
        }, ensure_ascii=False).encode("utf-8")

    def _request(self, payload: bytes, *, stream: bool) -> Request:
        return Request(self._endpoint(), data=payload, method="POST", headers={
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if stream else "application/json",
        })

    @staticmethod
    def _retry_delay(attempt: int) -> float:
        return 0.5 * (2 ** attempt)

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1200,
    ) -> str:
        if not messages:
            raise ChatServiceError("Chat messages 不能为空")
        if max_tokens <= 0:
            raise ChatServiceError("max_tokens 必须大于 0")
        payload = self._payload(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )

        last_error: ChatServiceError | None = None
        for attempt in range(self.config.max_attempts):
            request = self._request(payload, stream=False)
            try:
                with self._opener.open(
                    request, timeout=self.config.timeout_seconds,
                ) as response:
                    body = json.load(response)
                return self._parse_response(body)
            except HTTPError as exc:
                last_error = self._http_error(exc)
            except (URLError, TimeoutError, OSError) as exc:
                last_error = ChatServiceError(
                    f"Chat 请求失败: {exc}",
                    stage="transport",
                    retryable=True,
                )
            except (UnicodeError, json.JSONDecodeError) as exc:
                last_error = ChatServiceError(
                    f"Chat 响应解析失败: {exc}",
                    stage="response",
                    retryable=True,
                )
            except ChatServiceError as exc:
                last_error = exc

            if not last_error.retryable or attempt + 1 >= self.config.max_attempts:
                break
            time.sleep(self._retry_delay(attempt))

        if last_error is not None:
            raise last_error
        raise ChatServiceError("Chat 请求失败", stage="transport")

    def stream_complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1200,
    ):
        """Yield text deltas from an OpenAI-compatible SSE response."""
        if not messages:
            raise ChatServiceError("Chat messages 不能为空")
        payload = self._payload(
            messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        last_error: ChatServiceError | None = None
        for attempt in range(self.config.max_attempts):
            emitted = False
            completion_received = False
            request = self._request(payload, stream=True)
            try:
                with self._opener.open(
                    request, timeout=self.config.timeout_seconds,
                ) as response:
                    for raw_line in response:
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            completion_received = True
                            break
                        try:
                            event = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        choices = event.get("choices") if isinstance(event, dict) else None
                        if not isinstance(choices, list) or not choices:
                            continue
                        choice = choices[0]
                        if not isinstance(choice, dict):
                            continue
                        delta = choice.get("delta", {})
                        if not isinstance(delta, dict):
                            continue
                        content = delta.get("content")
                        if isinstance(content, str):
                            text = content
                        elif isinstance(content, list):
                            text = "".join(
                                str(part.get("text", ""))
                                for part in content if isinstance(part, dict)
                            )
                        else:
                            text = ""
                        if text:
                            emitted = True
                            yield text
                        if choice.get("finish_reason") is not None:
                            completion_received = True
                            break
                if completion_received and emitted:
                    return
                if emitted:
                    raise ChatServiceError(
                        "Chat 流式传输提前结束，未收到完成标记",
                        stage="stream_read",
                        partial=True,
                    )
                last_error = ChatServiceError(
                    "Chat 流式响应正文为空",
                    stage="stream_response",
                    retryable=True,
                )
            except HTTPError as exc:
                last_error = self._http_error(exc)
            except (URLError, TimeoutError, OSError) as exc:
                if emitted:
                    raise ChatServiceError(
                        f"Chat 流式传输中断: {exc}",
                        stage="stream_read",
                        partial=True,
                    ) from exc
                last_error = ChatServiceError(
                    f"Chat 流式请求失败: {exc}",
                    stage="stream_connect",
                    retryable=True,
                )

            if last_error is None:
                break
            if not last_error.retryable or attempt + 1 >= self.config.max_attempts:
                raise last_error
            time.sleep(self._retry_delay(attempt))

        if last_error is not None:
            raise last_error
        raise ChatServiceError("Chat 流式请求失败", stage="stream_connect")
