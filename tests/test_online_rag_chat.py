from __future__ import annotations

import io
import json
import unittest
from urllib.error import HTTPError, URLError
from unittest.mock import Mock, patch

from online_rag import (
    ChatConfig,
    ChatServiceError,
    EmbeddingConfig,
    RemoteChatBackend,
    create_assistant_from_env,
)


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def response(body: dict) -> Response:
    return Response(json.dumps(body, ensure_ascii=False).encode("utf-8"))


class ChatConfigTest(unittest.TestCase):
    def test_chat_specific_environment_overrides_shared_llm_values(self):
        env = {
            "LLM_BASE_URL": "https://shared.test/v1",
            "LLM_API_KEY": "shared-key",
            "LLM_MODEL": "shared-model",
            "CHAT_BASE_URL": "https://chat.test/v1",
            "CHAT_API_KEY": "chat-key",
            "CHAT_MODEL": "glm-5.2-107",
        }
        with patch.dict("os.environ", env, clear=True):
            config = ChatConfig.from_env()
        self.assertEqual(config.base_url, "https://chat.test/v1")
        self.assertEqual(config.api_key, "chat-key")
        self.assertEqual(config.model, "glm-5.2-107")
        self.assertEqual(config.proxy_mode, "direct")

    def test_proxy_and_retry_environment_are_parsed(self):
        env = {
            "LLM_BASE_URL": "https://shared.test/v1",
            "LLM_API_KEY": "shared-key",
            "LLM_MODEL": "shared-model",
            "CHAT_PROXY_MODE": "custom",
            "CHAT_PROXY_URL": "http://proxy.test:8080",
            "CHAT_TIMEOUT_SECONDS": "45",
            "CHAT_MAX_ATTEMPTS": "3",
        }
        with patch.dict("os.environ", env, clear=True):
            config = ChatConfig.from_env()
        self.assertEqual(config.proxy_mode, "custom")
        self.assertEqual(config.proxy_url, "http://proxy.test:8080")
        self.assertEqual(config.timeout_seconds, 45)
        self.assertEqual(config.max_attempts, 3)

    def test_missing_model_is_reported_before_any_request(self):
        with patch.dict("os.environ", {
            "LLM_BASE_URL": "https://chat.test/v1",
            "LLM_API_KEY": "key",
        }, clear=True):
            with self.assertRaisesRegex(ChatServiceError, "LLM_MODEL"):
                ChatConfig.from_env()


class RemoteChatBackendTest(unittest.TestCase):
    def backend(self, opener=None):
        return RemoteChatBackend(self.config, opener=opener or Mock())

    def test_streaming_request_yields_sse_deltas(self):
        stream = Response(
            b'data: {"choices":[{"delta":{"content":"first "}}]}\n\n'
            b'data: {"choices":[{"delta":{"content":"second"}}]}\n\n'
            b'data: [DONE]\n\n'
        )
        opener = Mock()
        opener.open.return_value = stream
        parts = list(self.backend(opener).stream_complete(self.messages))

        self.assertEqual(parts, ["first ", "second"])
        payload = json.loads(opener.open.call_args.args[0].data.decode("utf-8"))
        self.assertTrue(payload["stream"])
        self.assertEqual(
            payload["chat_template_kwargs"], {"enable_thinking": False},
        )

    def test_streaming_clean_eof_after_content_is_partial_failure(self):
        stream = Response(
            b'data: {"choices":[{"delta":{"content":"partial"}}]}\n\n'
        )
        opener = Mock()
        opener.open.return_value = stream

        with self.assertRaises(ChatServiceError) as caught:
            list(self.backend(opener).stream_complete(self.messages))

        self.assertEqual(caught.exception.stage, "stream_read")
        self.assertTrue(caught.exception.partial)
        self.assertEqual(opener.open.call_count, 1)

    def test_streaming_finish_reason_completes_without_done_marker(self):
        stream = Response(
            b'data: {"choices":[{"delta":{"content":"complete"},'
            b'"finish_reason":"stop"}]}\n\n'
        )
        opener = Mock()
        opener.open.return_value = stream

        parts = list(self.backend(opener).stream_complete(self.messages))

        self.assertEqual(parts, ["complete"])

    def setUp(self):
        self.config = ChatConfig(
            base_url="https://chat.test/v1",
            api_key="secret",
            model="glm-5.2-107",
            timeout_seconds=10,
            max_attempts=2,
        )
        self.messages = [{"role": "user", "content": "问题"}]

    def test_successful_request_uses_chat_completions_contract(self):
        body = {"choices": [{"message": {"content": "回答。[E1]"}}]}
        opener = Mock()
        opener.open.return_value = response(body)
        answer = self.backend(opener).complete(
            self.messages, temperature=0.2, max_tokens=456,
        )

        self.assertEqual(answer, "回答。[E1]")
        http_request = opener.open.call_args.args[0]
        self.assertEqual(http_request.full_url, "https://chat.test/v1/chat/completions")
        self.assertEqual(http_request.get_header("Authorization"), "Bearer secret")
        payload = json.loads(http_request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "glm-5.2-107")
        self.assertEqual(payload["messages"], self.messages)
        self.assertEqual(payload["temperature"], 0.2)
        self.assertEqual(payload["max_tokens"], 456)
        self.assertFalse(payload["stream"])
        self.assertEqual(
            payload["chat_template_kwargs"], {"enable_thinking": False},
        )

    def test_endpoint_is_not_appended_twice(self):
        config = ChatConfig(
            "https://chat.test/v1/chat/completions", "secret", "glm-5.2-107",
        )
        body = {"choices": [{"message": {"content": "回答"}}]}
        opener = Mock()
        opener.open.return_value = response(body)
        RemoteChatBackend(config, opener=opener).complete(self.messages)
        self.assertEqual(
            opener.open.call_args.args[0].full_url,
            "https://chat.test/v1/chat/completions",
        )

    def test_list_style_content_is_supported(self):
        body = {"choices": [{"message": {"content": [
            {"type": "text", "text": "第一段"},
            {"type": "text", "text": "第二段"},
        ]}}]}
        opener = Mock()
        opener.open.return_value = response(body)
        answer = self.backend(opener).complete(self.messages)
        self.assertEqual(answer, "第一段第二段")

    def test_transient_network_failure_is_retried(self):
        body = {"choices": [{"message": {"content": "重试成功"}}]}
        opener = Mock()
        opener.open.side_effect = [URLError("temporary"), response(body)]
        with patch("online_rag.chat.time.sleep") as sleep:
            answer = self.backend(opener).complete(self.messages)
        self.assertEqual(answer, "重试成功")
        self.assertEqual(opener.open.call_count, 2)
        sleep.assert_called_once()

    def test_streaming_failure_before_content_is_retried(self):
        stream = Response(
            b'data: {"choices":[{"delta":{"content":"retry ok"}}]}\n\n'
            b'data: [DONE]\n\n'
        )
        opener = Mock()
        opener.open.side_effect = [URLError("temporary"), stream]
        with patch("online_rag.chat.time.sleep") as sleep:
            parts = list(self.backend(opener).stream_complete(self.messages))
        self.assertEqual(parts, ["retry ok"])
        self.assertEqual(opener.open.call_count, 2)
        sleep.assert_called_once()

    def test_authentication_failure_is_not_retried_and_keeps_provider_message(self):
        error_body = json.dumps({"error": {"message": "invalid key"}}).encode("utf-8")
        error = HTTPError(
            "https://chat.test", 401, "Unauthorized", {}, io.BytesIO(error_body),
        )
        opener = Mock()
        opener.open.side_effect = error
        with self.assertRaisesRegex(ChatServiceError, "HTTP 401: invalid key"):
            self.backend(opener).complete(self.messages)
        self.assertEqual(opener.open.call_count, 1)

    def test_direct_mode_builds_opener_without_proxies(self):
        with patch("online_rag.chat.build_opener") as build:
            build.return_value = Mock()
            RemoteChatBackend(self.config)
        handler = build.call_args.args[0]
        self.assertEqual(handler.proxies, {})

    def test_custom_mode_uses_configured_proxy(self):
        config = ChatConfig(
            "https://chat.test/v1", "secret", "model",
            proxy_mode="custom", proxy_url="http://proxy.test:8080",
        )
        with patch("online_rag.chat.build_opener") as build:
            build.return_value = Mock()
            RemoteChatBackend(config)
        self.assertEqual(build.call_args.args[0].proxies, {
            "http": "http://proxy.test:8080",
            "https": "http://proxy.test:8080",
        })

    def test_malformed_response_raises_domain_error(self):
        opener = Mock()
        opener.open.return_value = response({"choices": []})
        with self.assertRaisesRegex(ChatServiceError, "choices"):
            self.backend(opener).complete(self.messages)


class FactoryTest(unittest.TestCase):
    def test_factory_wires_remote_backends_without_calling_chat_api(self):
        embedding_config = EmbeddingConfig(
            "https://embedding.test/v1", "embedding-key", "embedding-model",
        )
        chat_config = ChatConfig(
            "https://chat.test/v1", "chat-key", "glm-5.2-107",
        )
        fake_retriever = object()
        with patch(
            "online_rag.factory.HybridRetriever.from_corpus",
            return_value=fake_retriever,
        ) as build_retriever:
            assistant = create_assistant_from_env(
                embedding_config=embedding_config,
                chat_config=chat_config,
            )
        self.assertIs(assistant.retriever, fake_retriever)
        self.assertIsInstance(assistant.chat_backend, RemoteChatBackend)
        self.assertEqual(assistant.chat_backend.model_name, "glm-5.2-107")
        self.assertEqual(
            build_retriever.call_args.args[0].model_name, "embedding-model",
        )

    def test_factory_validates_all_configuration_before_building_index(self):
        embedding_config = EmbeddingConfig(
            "https://embedding.test/v1", "embedding-key", "embedding-model",
        )
        with patch.dict("os.environ", {}, clear=True), patch(
            "online_rag.factory.HybridRetriever.from_corpus",
        ) as build_retriever:
            with self.assertRaises(ChatServiceError):
                create_assistant_from_env(embedding_config=embedding_config)
        build_retriever.assert_not_called()


if __name__ == "__main__":
    unittest.main()
