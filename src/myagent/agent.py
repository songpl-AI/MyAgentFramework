"""The core Agent class — the heart of the framework.

An Agent is a loop that repeatedly calls an LLM until it produces a final
answer or hits a safety bound. This is the ReAct pattern distilled to its
essence: the model reasons, optionally acts (Phase 2), observes results,
and repeats.

Architecture:
    Agent.run(input)
        → build initial messages (system + user)
        → for each step up to max_steps:
            → call LLM with current messages
            → append assistant response to messages
            → check if done (finish_reason == "stop" or empty content)
            → if done, return AgentResult
        → if max_steps exceeded, return with finish_reason="max_steps"

Design decisions (see docs/phases/phase-1-agent-loop.md for full rationale):
- Loop uses `for range(max_steps)` instead of `while True` for built-in safety.
- Loop lives in the Agent layer (not Model layer like Agno) so the Agent owns
  the full execution lifecycle — easier to add Guardrails/Tracing later.
- LLM is injected via Protocol, enabling zero-dependency testing with MockLLM.
- `step()` is a separate method and extension point for subclasses.

References:
- ReAct paper: https://arxiv.org/abs/2210.03629
- Anthropic "Building effective agents": start simple, add complexity only when needed
- OpenAI Agents SDK: NextStep pattern for loop control
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from myagent._llm import LLMResponse, OpenAILLM
from myagent.models import AgentResult, Message, StepResult

if TYPE_CHECKING:
    from myagent._llm import LLMProtocol


class Agent:
    """A minimal agent that runs an LLM in a loop.

    The agent holds a system prompt (instructions) and optionally a set of
    tools (Phase 2). Each call to `run()` starts a fresh conversation,
    iterating until the model produces a final answer or max_steps is reached.

    Args:
        name: A human-readable name for this agent (used in logging/tracing).
        instructions: The system prompt that defines the agent's behavior.
        model: The model identifier (e.g., "gpt-4o-mini", "claude-sonnet-4-20250514").
        max_steps: Maximum number of LLM calls per run. Prevents infinite loops.
        llm: An LLM implementation satisfying LLMProtocol. If None, defaults
            to OpenAILLM. Pass a MockLLM for testing.

    Example:
        >>> agent = Agent(
        ...     name="assistant",
        ...     instructions="You are a helpful assistant.",
        ... )
        >>> result = asyncio.run(agent.run("What is 2+2?"))
        >>> print(result.output)
    """

    def __init__(
        self,
        name: str,
        instructions: str = "You are a helpful assistant.",
        model: str = "gpt-4o-mini",
        max_steps: int = 10,
        llm: LLMProtocol | None = None,
    ) -> None:
        self.name = name
        self.instructions = instructions
        self.model = model
        self.max_steps = max_steps
        self._llm: LLMProtocol = llm or OpenAILLM()

    # -------------------------------------------------------------------
    # 公开 API
    # -------------------------------------------------------------------

    async def run(self, input: str) -> AgentResult:
        """Execute the agent loop and return the result.

        Builds the initial message list (system prompt + user input), then
        iterates: call LLM → check termination → append to history → repeat.

        Args:
            input: The user's message to the agent.

        Returns:
            AgentResult containing the final output, full message history,
            and step-by-step execution trace.
        """
        # 构建初始对话：系统提示 + 用户消息
        messages: list[Message] = [
            Message(role="system", content=self.instructions),
            Message(role="user", content=input),
        ]
        steps: list[StepResult] = []

        # -- Agent 核心循环 --
        # 用 `for` + max_steps 实现天然的安全上限（不需要 `while True`）。
        # 每次迭代 = 一次 LLM 调用 = 一个 "step"。
        for step_number in range(1, self.max_steps + 1):
            step_result = await self.step(messages, step_number)
            steps.append(step_result)

            # 将助手的回复追加到对话历史
            messages.append(step_result.message)

            # 检查终止条件：模型说"完成了"或返回空内容
            if self._should_stop(step_result):
                return self._build_result(
                    messages=messages,
                    steps=steps,
                    finish_reason=step_result.finish_reason,
                )

        # 达到最大步数 — 返回当前结果并标记 finish_reason
        return self._build_result(
            messages=messages,
            steps=steps,
            finish_reason="max_steps",
        )

    def run_sync(self, input: str) -> AgentResult:
        """Synchronous wrapper around run() for convenience.

        Uses asyncio.run() to execute the async loop. Do not call this
        from within an already-running event loop — use `await run()` instead.
        """
        return asyncio.run(self.run(input))

    # -------------------------------------------------------------------
    # 单步执行 — 子类扩展点
    # -------------------------------------------------------------------

    async def step(self, messages: list[Message], step_number: int) -> StepResult:
        """Execute a single step: call the LLM and wrap the response.

        This is the primary extension point for subclasses. Override this
        to add pre/post processing, custom routing, or tool execution (Phase 2).

        Args:
            messages: The full conversation history up to this point.
            step_number: 1-indexed position of this step in the run.

        Returns:
            StepResult wrapping the model's response and finish reason.
        """
        response: LLMResponse = await self._llm.call(
            messages=messages,
            model=self.model,
        )

        return StepResult(
            message=Message(role="assistant", content=response.content),
            finish_reason=response.finish_reason,
            step_number=step_number,
        )

    # -------------------------------------------------------------------
    # 私有辅助方法
    # -------------------------------------------------------------------

    @staticmethod
    def _should_stop(step_result: StepResult) -> bool:
        """Determine if the agent loop should terminate after this step.

        Termination conditions (from the ReAct pattern):
        1. Model returned finish_reason="stop" — it's done reasoning.
        2. Model returned empty content — nothing useful to continue with.

        In Phase 2, we'll add: finish_reason="tool_calls" → don't stop,
        execute the tools and continue.
        """
        # 自然结束：模型完成了推理
        if step_result.finish_reason == "stop":
            return True

        # 空响应：异常情况，继续也没有意义
        if not step_result.message.content:
            return True

        # finish_reason == "length" 表示模型达到了 max_tokens 上限 —
        # Phase 1 中直接停止（后续阶段可能会用 follow-up prompt 继续）。
        if step_result.finish_reason == "length":
            return True

        return False

    @staticmethod
    def _build_result(
        messages: list[Message],
        steps: list[StepResult],
        finish_reason: str,
    ) -> AgentResult:
        """Construct the final AgentResult from accumulated state.

        The output is the content of the last assistant message, which is
        the model's final response to the user.
        """
        # 从消息历史中找到最后一条助手消息作为输出
        output = ""
        for msg in reversed(messages):
            if msg.role == "assistant" and msg.content:
                output = msg.content
                break

        return AgentResult(
            output=output,
            messages=messages,
            steps=steps,
            total_steps=len(steps),
            finish_reason=finish_reason,
        )

    # -------------------------------------------------------------------
    # 魔术方法
    # -------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Agent(name={self.name!r}, model={self.model!r}, max_steps={self.max_steps})"
