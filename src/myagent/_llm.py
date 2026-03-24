"""Minimal LLM calling layer — temporary, replaced by providers/ in Phase 3.

This module provides a thin abstraction for calling an LLM. It defines a
Protocol so that the Agent can work with both a real OpenAI client and a
mock for testing, without importing any provider SDK at the Agent level.

Design decisions:
- Protocol (structural typing) instead of ABC: lighter, no inheritance needed.
  The Agent depends on the Protocol, not a concrete class.
- OpenAI is the default provider for Phase 1 because it has the widest
  ecosystem and cheapest small models (gpt-4o-mini).
- API key is read from env var at call time, not at init time, so tests
  don't need a key at all (they use MockLLM).

References:
- OpenAI chat completions API: https://platform.openai.com/docs/api-reference/chat
- Python Protocol (PEP 544): https://peps.python.org/pep-0544/
"""

from __future__ import annotations

import os
from typing import Any, Protocol, runtime_checkable

from myagent.models import Message

# ---------------------------------------------------------------------------
# LLM 协议 — Agent 依赖的接口
# ---------------------------------------------------------------------------

@runtime_checkable
class LLMProtocol(Protocol):
    """Structural type for anything that can make an LLM call.

    Any object with a matching `call` method satisfies this protocol,
    including MockLLM for tests and OpenAILLM for real calls.
    """

    async def call(
        self,
        messages: list[Message],
        model: str,
    ) -> LLMResponse: ...


class LLMResponse:
    """The response from a single LLM call.

    Kept as a simple class (not Pydantic) since this is an internal
    intermediate type that doesn't need serialization.

    Attributes:
        content: The text content of the response. May be empty string.
        finish_reason: Why generation stopped ("stop", "length", "tool_calls").
    """

    __slots__ = ("content", "finish_reason")

    def __init__(self, content: str = "", finish_reason: str = "stop") -> None:
        self.content = content
        self.finish_reason = finish_reason


# ---------------------------------------------------------------------------
# OpenAI 实现 — Phase 1 的默认 Provider
# ---------------------------------------------------------------------------

class OpenAILLM:
    """Calls the OpenAI chat completions API.

    This is a minimal implementation for Phase 1. It will be replaced by
    a full OpenAIProvider in Phase 3 with streaming, tool calling, and
    proper error handling.

    Usage:
        llm = OpenAILLM()  # reads OPENAI_API_KEY from env
        response = await llm.call(messages, model="gpt-4o-mini")
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    def _get_client(self) -> Any:
        """Lazy-import openai to avoid hard dependency when using MockLLM."""
        try:
            import openai
        except ImportError as e:
            raise ImportError(
                "openai package is required. Install with: pip install myagent[openai]"
            ) from e

        api_key = self._api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable "
                "or pass api_key to OpenAILLM()."
            )
        return openai.AsyncOpenAI(api_key=api_key)

    async def call(self, messages: list[Message], model: str) -> LLMResponse:
        """Send messages to OpenAI and return the response.

        Converts internal Message format to OpenAI's expected format,
        makes the API call, and converts back.
        """
        client = self._get_client()

        # 将内部 Message 对象转换为 OpenAI 的 dict 格式
        openai_messages = [
            {"role": msg.role, "content": msg.content or ""}
            for msg in messages
        ]

        response = await client.chat.completions.create(
            model=model,
            messages=openai_messages,
        )

        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            finish_reason=choice.finish_reason or "stop",
        )
