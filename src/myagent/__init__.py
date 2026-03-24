"""MyAgent — A minimal Agent framework built from first principles."""

__version__ = "0.1.0"

from myagent.agent import Agent
from myagent.models import AgentResult, Message, StepResult

__all__ = [
    "Agent",
    "AgentResult",
    "Message",
    "StepResult",
]
