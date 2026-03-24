"""Tests for the Agent core loop.

All tests use MockLLM to avoid real API calls, ensuring deterministic
and fast test execution. The mock returns pre-defined responses in order.

Test structure follows the verification criteria from Phase 1:
- Agent.run("你好") returns a valid AgentResult
- Conversation history is correctly recorded
- max_steps=1 terminates after one step
- Multi-step scenarios work correctly
- Model returning "stop" correctly terminates
- Edge cases: empty response, max_steps exhaustion
"""

from __future__ import annotations

import pytest

from myagent import Agent, AgentResult, Message, StepResult
from myagent._llm import LLMResponse

# ---------------------------------------------------------------------------
# MockLLM — 用于测试的确定性 LLM
# ---------------------------------------------------------------------------

class MockLLM:
    """A mock LLM that returns pre-defined responses in sequence.

    Satisfies LLMProtocol via structural typing (duck typing) — no need
    to inherit from anything. This is the Protocol pattern in action.

    Args:
        responses: List of LLMResponse objects to return in order.
            If the agent calls more times than responses provided,
            StopIteration is raised (which indicates a test bug).
    """

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = iter(responses)
        self.call_count = 0
        self.call_history: list[list[Message]] = []

    async def call(self, messages: list[Message], model: str) -> LLMResponse:
        """Return the next pre-defined response."""
        self.call_count += 1
        # 保存消息副本，用于测试断言
        self.call_history.append(list(messages))
        return next(self._responses)


# ---------------------------------------------------------------------------
# 辅助函数：快速创建 MockLLM
# ---------------------------------------------------------------------------

def make_mock(*texts: str, finish_reasons: list[str] | None = None) -> MockLLM:
    """Create a MockLLM from simple text strings.

    Args:
        *texts: Response texts in order.
        finish_reasons: Optional list of finish reasons (defaults to "stop" for all).
    """
    reasons = finish_reasons or ["stop"] * len(texts)
    responses = [
        LLMResponse(content=text, finish_reason=reason)
        for text, reason in zip(texts, reasons)
    ]
    return MockLLM(responses)


# ---------------------------------------------------------------------------
# 测试：基础功能
# ---------------------------------------------------------------------------

class TestAgentBasic:
    """Test basic Agent functionality."""

    @pytest.mark.asyncio
    async def test_simple_run(self) -> None:
        """Agent.run() returns a valid AgentResult with the model's response."""
        mock = make_mock("Hello! How can I help you?")
        agent = Agent(name="test", instructions="Be helpful.", llm=mock)

        result = await agent.run("Hi there")

        assert isinstance(result, AgentResult)
        assert result.output == "Hello! How can I help you?"
        assert result.total_steps == 1
        assert result.finish_reason == "stop"

    @pytest.mark.asyncio
    async def test_conversation_history(self) -> None:
        """Messages list contains system, user, and assistant messages."""
        mock = make_mock("I'm an AI assistant.")
        agent = Agent(name="test", instructions="You are helpful.", llm=mock)

        result = await agent.run("What are you?")

        assert len(result.messages) == 3
        assert result.messages[0].role == "system"
        assert result.messages[0].content == "You are helpful."
        assert result.messages[1].role == "user"
        assert result.messages[1].content == "What are you?"
        assert result.messages[2].role == "assistant"
        assert result.messages[2].content == "I'm an AI assistant."

    @pytest.mark.asyncio
    async def test_steps_recorded(self) -> None:
        """Each LLM call is recorded as a StepResult."""
        mock = make_mock("Response 1")
        agent = Agent(name="test", llm=mock)

        result = await agent.run("Hello")

        assert len(result.steps) == 1
        step = result.steps[0]
        assert isinstance(step, StepResult)
        assert step.step_number == 1
        assert step.finish_reason == "stop"
        assert step.message.content == "Response 1"

    def test_run_sync(self) -> None:
        """run_sync() works as a synchronous wrapper."""
        mock = make_mock("Sync response")
        agent = Agent(name="test", llm=mock)

        result = agent.run_sync("Hello")

        assert result.output == "Sync response"


# ---------------------------------------------------------------------------
# 测试：终止条件
# ---------------------------------------------------------------------------

class TestTermination:
    """Test that the agent loop terminates correctly under various conditions."""

    @pytest.mark.asyncio
    async def test_stop_on_finish_reason_stop(self) -> None:
        """Loop stops when model returns finish_reason='stop'."""
        mock = make_mock("Done!", finish_reasons=["stop"])
        agent = Agent(name="test", llm=mock, max_steps=10)

        result = await agent.run("Do something")

        assert result.total_steps == 1
        assert result.finish_reason == "stop"
        assert mock.call_count == 1

    @pytest.mark.asyncio
    async def test_stop_on_max_steps(self) -> None:
        """Loop stops when max_steps is reached.

        Simulates a scenario where the model never returns "stop" — e.g.,
        it keeps wanting to call tools (finish_reason="tool_calls").
        In Phase 1 without tool support, this is an edge case safety test.
        """
        # 所有响应的 finish_reason="tool_calls"（模型持续请求工具调用）
        mock = make_mock(
            "Thinking...", "Still thinking...", "More thinking...",
            finish_reasons=["tool_calls", "tool_calls", "tool_calls"],
        )
        agent = Agent(name="test", llm=mock, max_steps=3)

        result = await agent.run("Complex question")

        assert result.total_steps == 3
        assert result.finish_reason == "max_steps"
        assert mock.call_count == 3

    @pytest.mark.asyncio
    async def test_stop_on_empty_content(self) -> None:
        """Loop stops when model returns empty content (abnormal case)."""
        mock = MockLLM([LLMResponse(content="", finish_reason="stop")])
        agent = Agent(name="test", llm=mock, max_steps=5)

        result = await agent.run("Hello")

        assert result.total_steps == 1
        assert result.output == ""

    @pytest.mark.asyncio
    async def test_stop_on_length(self) -> None:
        """Loop stops when model hits max_tokens (finish_reason='length')."""
        mock = make_mock("Truncated respo", finish_reasons=["length"])
        agent = Agent(name="test", llm=mock, max_steps=5)

        result = await agent.run("Tell me a long story")

        assert result.total_steps == 1
        assert result.finish_reason == "length"

    @pytest.mark.asyncio
    async def test_max_steps_one(self) -> None:
        """max_steps=1 executes exactly one step regardless of finish_reason."""
        # finish_reason 是 "tool_calls" 但 max_steps=1 强制终止
        mock = make_mock("Need tools", finish_reasons=["tool_calls"])
        agent = Agent(name="test", llm=mock, max_steps=1)

        result = await agent.run("Do something")

        assert result.total_steps == 1
        assert mock.call_count == 1


# ---------------------------------------------------------------------------
# 测试：多步执行中的消息累积
# ---------------------------------------------------------------------------

class TestMultiStep:
    """Test multi-step scenarios where the loop runs more than once."""

    @pytest.mark.asyncio
    async def test_multi_step_accumulates_messages(self) -> None:
        """Messages accumulate correctly across multiple steps.

        Simulates: model wants tools (2 steps) then stops.
        Verifies the LLM sees the growing conversation history.
        """
        mock = make_mock(
            "Let me think about that...",
            "After consideration, the answer is 42.",
            finish_reasons=["tool_calls", "stop"],
        )
        agent = Agent(name="test", llm=mock, max_steps=5)

        result = await agent.run("What is the meaning of life?")

        # 应该执行了 2 步
        assert result.total_steps == 2
        assert result.finish_reason == "stop"
        assert result.output == "After consideration, the answer is 42."

        # 验证消息历史：system + user + assistant1 + assistant2
        assert len(result.messages) == 4
        assert result.messages[0].role == "system"
        assert result.messages[1].role == "user"
        assert result.messages[2].role == "assistant"
        assert result.messages[3].role == "assistant"

        # 验证 LLM 在第二次调用时看到了累积的历史
        # 第一次调用：[system, user]
        assert len(mock.call_history[0]) == 2
        # 第二次调用：[system, user, assistant1]
        assert len(mock.call_history[1]) == 3

    @pytest.mark.asyncio
    async def test_three_step_execution(self) -> None:
        """Three-step scenario: model iterates before concluding."""
        mock = make_mock(
            "Step 1: Analyzing...",
            "Step 2: Processing...",
            "Step 3: The final answer is X.",
            finish_reasons=["tool_calls", "tool_calls", "stop"],
        )
        agent = Agent(name="test", llm=mock, max_steps=10)

        result = await agent.run("Complex task")

        assert result.total_steps == 3
        assert result.finish_reason == "stop"
        assert "final answer" in result.output

        # 验证消息增长：LLM 分别看到 2、3、4 条消息
        assert len(mock.call_history[0]) == 2
        assert len(mock.call_history[1]) == 3
        assert len(mock.call_history[2]) == 4


# ---------------------------------------------------------------------------
# 测试：Agent 配置
# ---------------------------------------------------------------------------

class TestAgentConfig:
    """Test agent configuration and metadata."""

    @pytest.mark.asyncio
    async def test_custom_instructions(self) -> None:
        """Custom instructions are used as the system prompt."""
        mock = make_mock("我是一个中文助手。")
        agent = Agent(
            name="chinese_bot",
            instructions="你是一个中文助手。用简洁的中文回答。",
            llm=mock,
        )

        result = await agent.run("你好")

        assert result.messages[0].content == "你是一个中文助手。用简洁的中文回答。"

    @pytest.mark.asyncio
    async def test_model_passed_to_llm(self) -> None:
        """The model identifier is forwarded to the LLM call."""
        calls_received: list[str] = []

        class ModelTrackingLLM:
            async def call(self, messages: list[Message], model: str) -> LLMResponse:
                calls_received.append(model)
                return LLMResponse(content="ok", finish_reason="stop")

        agent = Agent(name="test", model="custom-model-v1", llm=ModelTrackingLLM())
        await agent.run("test")

        assert calls_received == ["custom-model-v1"]

    def test_repr(self) -> None:
        """Agent has a useful repr."""
        mock = make_mock("x")
        agent = Agent(name="bot", model="gpt-4o", max_steps=5, llm=mock)
        assert repr(agent) == "Agent(name='bot', model='gpt-4o', max_steps=5)"
