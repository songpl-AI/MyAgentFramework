"""Core data models for the Agent framework.

This module defines the internal message format and result types that are
independent of any specific LLM provider. The design follows two principles:

1. **Provider-agnostic**: Message uses a unified role/content structure that
   can be converted to/from OpenAI, Anthropic, or any other provider format.
2. **Full traceability**: AgentResult captures the complete execution history
   (every step, every message) for debugging and observability.

References:
- OpenAI message format: role in {system, user, assistant, tool}
- Anthropic message format: role in {user, assistant}, system is separate
- We use the OpenAI convention as our internal standard since it's more explicit.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Message — the universal unit of conversation
# ---------------------------------------------------------------------------

class Message(BaseModel):
    """A single message in a conversation.

    This is the internal representation used throughout the framework.
    Provider adapters (Phase 3) will convert between this format and
    provider-specific formats.

    Attributes:
        role: The sender of the message. "tool" role is reserved for Phase 2.
        content: The text content. May be None for assistant messages that
            only contain tool calls (Phase 2).
    """

    role: Literal["system", "user", "assistant", "tool"] = "user"
    content: str | None = None

    # -- Phase 2 will add these fields: --
    # tool_calls: list[ToolCall] | None = None
    # tool_call_id: str | None = None


# ---------------------------------------------------------------------------
# StepResult — one iteration of the agent loop
# ---------------------------------------------------------------------------

class StepResult(BaseModel):
    """The outcome of a single step in the agent loop.

    Each step corresponds to one LLM call. The step records what the model
    returned and why the loop continued or stopped.

    Attributes:
        message: The assistant's response message.
        finish_reason: Why the model stopped generating.
            - "stop": natural completion (model is done)
            - "tool_calls": model wants to call tools (Phase 2)
            - "length": hit max_tokens limit
            - "max_steps": loop reached max_steps bound
        step_number: 1-indexed position within the run.
    """

    message: Message
    finish_reason: str = "stop"
    step_number: int = 1


# ---------------------------------------------------------------------------
# AgentResult — the complete output of an agent run
# ---------------------------------------------------------------------------

class AgentResult(BaseModel):
    """The complete result of an Agent.run() invocation.

    Contains both the final output and the full execution trace, enabling
    debugging, logging, and future observability features (Phase 7).

    Attributes:
        output: The final text response from the agent.
        messages: The complete conversation history including system prompt,
            user input, and all assistant responses.
        steps: Ordered list of every step the agent executed.
        total_steps: How many LLM calls were made.
        finish_reason: Why the agent stopped. Same semantics as StepResult
            but at the run level.
        metadata: Extensible dict for provider-specific data (e.g., token usage).
    """

    output: str = ""
    messages: list[Message] = Field(default_factory=list)
    steps: list[StepResult] = Field(default_factory=list)
    total_steps: int = 0
    finish_reason: str = "stop"
    metadata: dict[str, Any] = Field(default_factory=dict)
