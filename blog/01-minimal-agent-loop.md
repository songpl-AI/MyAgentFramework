# 50 行代码实现一个 Agent Loop

> 系列文章第 1 篇 | 对应代码 Tag: `v0.1-agent-loop`
> 仓库地址：https://github.com/songpl-AI/MyAgentFramework

---

## 这篇文章讲什么

上一篇我们搭建了项目骨架。这一篇，我们要实现 Agent 框架最核心的部分 — **Agent Loop**。

Agent Loop 是什么？简单说，就是一个循环：

```
用户输入 → 调用大模型 → 模型回复 → 判断是否结束 → 没结束就继续调 → 直到完成
```

听起来很简单，对吧？确实简单。但这个循环就是 **所有 Agent 框架的心脏**。LangChain、OpenAI Agents SDK、Anthropic SDK，不管它们有多少功能，最核心的那个 `while` 或 `for` 循环，做的就是这件事。

这篇文章会带你走过完整的思考过程：从问题本质出发，独立思考方案，调研四个主流框架的实现，最后做出自己的设计决策。

## 从问题本质出发

在看任何框架代码之前，先问一个问题：

**Agent Loop 要解决的根本问题是什么？**

答案是：**让大模型从"一问一答"变成"持续推理直到完成任务"。**

普通的 LLM 调用是一次性的 — 你发一条消息，它回一条消息，结束。但很多任务需要多步推理：

- 你问"北京今天天气怎么样"，模型需要先调用天气 API，拿到结果，再回答你
- 你说"帮我写一个函数并测试它"，模型需要先写代码，再思考测试用例，再运行

这就是 Agent Loop 存在的意义 — 它让模型可以"思考多步"。

在学术界，这个模式叫 **ReAct**（Reasoning and Acting），来自 2022 年的一篇论文（[ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629)）。核心思想就是：

```
Thought → Action → Observation → Thought → Action → Observation → ... → Final Answer
```

理解了这个本质，我们就可以开始设计了。

## 独立思考：最小设计长什么样

不看任何框架，我先自己想一个最简单的 Agent Loop：

```python
# 伪代码 — 我脑子里的第一版设计
async def run(user_input):
    messages = [system_prompt, user_input]

    for i in range(max_steps):          # 安全上限，防止无限循环
        response = await llm.call(messages)  # 调大模型
        messages.append(response)        # 把回复加到历史

        if response.is_done:             # 模型说"我完成了"
            return response.text

    return "达到最大步数"                  # 兜底
```

这大概 10 行代码。但有几个问题需要回答：

1. **循环用 `for` 还是 `while True`？** — `for` 天然有上限更安全，`while True` 需要额外的 break 和计数
2. **怎么判断模型"完成了"？** — 看 `finish_reason` 字段（OpenAI/Anthropic 都有）
3. **消息格式怎么定义？** — 需要一个通用的 Message 类型，不绑死某个 Provider
4. **LLM 调用怎么抽象？** — 需要一个接口，让测试可以不依赖真实 API

带着这些问题，我去看了四个框架的源码。

## 调研：四个框架怎么做的

### OpenAI Agents SDK — `while True` + NextStep 类型分发

> 源码：[run.py](https://github.com/openai/openai-agents-python/blob/main/src/agents/run.py)

OpenAI SDK 的循环在 `AgentRunner.run()` 中，结构是 `while True`：

```python
# OpenAI 的模式（简化）
while True:
    response = await model.call(...)
    next_step = determine_next_step(response)  # 返回 NextStep 类型

    match next_step:
        case FinalOutput():  return result
        case RunAgain():     continue
        case Handoff():      switch_agent(...)
```

关键设计是 **NextStep 类型分发** — 用 4 种不同的 NextStep 类型（FinalOutput / RunAgain / Handoff / Interruption）来决定循环的走向。这让控制流非常清晰，但也很重 — `run.py` 有 1600+ 行代码。

### Anthropic SDK — 最简洁的 `while True`

> 源码：[_beta_runner.py](https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/lib/tools/_beta_runner.py)

Anthropic 的方式最直接：

```python
# Anthropic 的模式（简化）
while True:
    response = await client.messages.create(...)

    if response.stop_reason == "end_turn":
        break  # 模型说完了
    elif response.stop_reason == "tool_use":
        execute_tools(response)
        continue
```

注意一个关键差异：Anthropic 只有 `user` 和 `assistant` 两种消息角色，tool 的结果嵌在 user 消息中。这和 OpenAI 的 `tool` 角色不同。

### Agno — 两层循环架构

> 源码：[base.py](https://github.com/agno-agi/agno/blob/main/libs/agno/agno/models/base.py)

Agno 的设计很有意思 — 循环不在 Agent 层，而在 **Model 层**：

```python
# Agno 的模式（简化）
class Agent:
    async def _run(self):
        response = await self.model.response(messages)  # 单次调用
        # 但 model.response() 内部有自己的 while True 循环！

class Model:
    async def response(self, messages):
        while True:  # 工具调用循环在这里
            response = await self.invoke(messages)
            if no_tool_calls(response):
                break
            execute_tools(response)
```

这简化了 Agent 代码，但把迭代逻辑耦合进了 Model 层。如果你想在每一步之间加 Guardrails 或 Tracing，就会比较尴尬。

### LangGraph — 图执行（完全不同的范式）

> 源码：[chat_agent_executor.py](https://github.com/langchain-ai/langgraph/blob/main/libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py)

LangGraph 根本不用循环，用的是**图**：

```python
# LangGraph 的模式（简化）
graph = StateGraph()
graph.add_node("agent", call_model)
graph.add_node("tools", execute_tools)
graph.add_conditional_edges("agent", should_continue, {
    "continue": "tools",
    "end": END,
})
graph.add_edge("tools", "agent")
```

它用 BSP（Bulk Synchronous Parallel）模型执行：`agent` 节点 → 条件边判断 → `tools` 节点 → 回到 `agent`。强大，但对于最小实现来说过于复杂。

### 调研总结

| 框架 | 循环结构 | 循环位置 | 终止方式 |
|---|---|---|---|
| OpenAI SDK | `while True` + NextStep | Agent 层 | return（类型分发） |
| Anthropic SDK | `while True` | Agent 层 | break（stop_reason） |
| Agno | `while True` | Model 层 | break（无工具调用） |
| LangGraph | 图执行 | Graph 引擎 | 条件边 → END |

## 我们的设计决策

综合独立思考和框架调研，我做了以下选择：

### 1. 循环结构：`for` 循环，不用 `while True`

```python
# 我们的选择
for step_number in range(1, self.max_steps + 1):
    ...

# 不用这种
while True:
    if step >= max_steps: break
    ...
```

原因：`for range(max_steps)` **天然自带安全上限**，不需要额外的计数器和 break。代码更简洁，也更难写出无限循环的 bug。

### 2. 循环放在 Agent 层，不放在 Model 层

借鉴 OpenAI SDK 和 Anthropic SDK，不学 Agno。

原因：Agent 层控制循环 = Agent 拥有完整的执行生命周期。后续加 Guardrails（Phase 6）和 Tracing（Phase 7）时，可以自然地在循环中插入拦截点，不需要深入 Model 内部。

### 3. LLM 通过 Protocol 注入

```python
from typing import Protocol

class LLMProtocol(Protocol):
    async def call(self, messages: list[Message], model: str) -> LLMResponse: ...
```

这是 Python 的[结构化类型](https://peps.python.org/pep-0544/)（PEP 544）。Agent 依赖 Protocol，不依赖具体的 OpenAI 类。好处是测试时可以传一个 MockLLM，**完全不需要真实的 API Key**。

### 4. 终止判断基于 `finish_reason`

统一用 `finish_reason` 字段：

- `"stop"` — 模型自然结束，返回结果
- `"tool_calls"` — 模型想调用工具（Phase 2 处理，Phase 1 继续循环）
- `"length"` — 达到 max_tokens 上限，Phase 1 直接停止
- `"max_steps"` — 我们自己的安全阀，达到循环上限

## 核心实现

### 数据模型（models.py）

先定义三个核心类型：

```python
from pydantic import BaseModel, Field
from typing import Any, Literal

class Message(BaseModel):
    """对话的基本单元。Provider 无关的统一格式。"""
    role: Literal["system", "user", "assistant", "tool"] = "user"
    content: str | None = None

class StepResult(BaseModel):
    """Agent 循环的单次迭代结果。"""
    message: Message
    finish_reason: str = "stop"
    step_number: int = 1

class AgentResult(BaseModel):
    """Agent 一次运行的完整输出。包含最终回复和完整执行轨迹。"""
    output: str = ""
    messages: list[Message] = Field(default_factory=list)
    steps: list[StepResult] = Field(default_factory=list)
    total_steps: int = 0
    finish_reason: str = "stop"
    metadata: dict[str, Any] = Field(default_factory=dict)
```

为什么用 Pydantic 而不是 dataclass？因为 Pydantic 提供 JSON Schema 自动生成，Phase 2 的 Tool 系统会大量用到这个能力。现在用 Pydantic 也没有额外负担。

### LLM 抽象层（_llm.py）

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class LLMProtocol(Protocol):
    """Agent 依赖的接口。MockLLM 和 OpenAILLM 都满足此协议。"""
    async def call(self, messages: list[Message], model: str) -> LLMResponse: ...

class LLMResponse:
    """单次 LLM 调用的响应。"""
    __slots__ = ("content", "finish_reason")

    def __init__(self, content: str = "", finish_reason: str = "stop") -> None:
        self.content = content
        self.finish_reason = finish_reason
```

`LLMResponse` 用 `__slots__` 而非 Pydantic，因为它是内部中间类型，不需要序列化能力，轻量就好。

OpenAI 的具体实现通过 **lazy import** 避免硬依赖：

```python
class OpenAILLM:
    def _get_client(self) -> Any:
        """懒加载 openai，避免未安装时导入报错。"""
        try:
            import openai
        except ImportError as e:
            raise ImportError(
                "openai package is required. Install with: pip install myagent[openai]"
            ) from e
        # ...
```

### Agent 核心循环（agent.py）

这是整个框架的心脏，核心代码不到 50 行：

```python
class Agent:
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

    async def run(self, input: str) -> AgentResult:
        # 构建初始对话：系统提示 + 用户消息
        messages: list[Message] = [
            Message(role="system", content=self.instructions),
            Message(role="user", content=input),
        ]
        steps: list[StepResult] = []

        # -- Agent 核心循环 --
        # 用 for + max_steps 实现天然的安全上限
        for step_number in range(1, self.max_steps + 1):
            step_result = await self.step(messages, step_number)
            steps.append(step_result)
            messages.append(step_result.message)

            if self._should_stop(step_result):
                return self._build_result(messages, steps, step_result.finish_reason)

        # 达到最大步数
        return self._build_result(messages, steps, "max_steps")
```

注意 `step()` 是一个独立方法：

```python
    async def step(self, messages: list[Message], step_number: int) -> StepResult:
        """单步执行：调用 LLM 并包装响应。这是子类的主要扩展点。"""
        response: LLMResponse = await self._llm.call(
            messages=messages, model=self.model,
        )
        return StepResult(
            message=Message(role="assistant", content=response.content),
            finish_reason=response.finish_reason,
            step_number=step_number,
        )
```

把 `step()` 单独拆出来是刻意的设计 — 后续 Phase 2 添加 Tool 执行时，只需要 override `step()` 方法，不需要改动 `run()` 的循环逻辑。

终止判断也很清晰：

```python
    @staticmethod
    def _should_stop(step_result: StepResult) -> bool:
        # 自然结束：模型完成了推理
        if step_result.finish_reason == "stop":
            return True
        # 空响应：异常情况，继续也没有意义
        if not step_result.message.content:
            return True
        # 达到 max_tokens 上限
        if step_result.finish_reason == "length":
            return True
        return False
```

Phase 2 加工具调用后，当 `finish_reason == "tool_calls"` 时不停止，执行工具后继续循环。

## 测试：不需要 API Key 的完整验证

测试是这个阶段最有价值的部分之一。通过 MockLLM，我们可以**完全确定性地**验证 Agent 的行为，不需要真实的 API 调用。

```python
class MockLLM:
    """用于测试的确定性 LLM，按顺序返回预定义响应。"""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = iter(responses)
        self.call_count = 0
        self.call_history: list[list[Message]] = []

    async def call(self, messages: list[Message], model: str) -> LLMResponse:
        self.call_count += 1
        self.call_history.append(list(messages))
        return next(self._responses)
```

MockLLM 通过 Protocol 的结构化类型机制，自动满足 `LLMProtocol` 接口 — 不需要继承任何基类。这就是 Python Protocol 的优雅之处。

测试覆盖了所有关键场景（15 个测试）：

```python
# 基础功能：run() 返回正确结果
async def test_simple_run():
    mock = make_mock("Hello!")
    agent = Agent(name="test", llm=mock)
    result = await agent.run("Hi")
    assert result.output == "Hello!"
    assert result.total_steps == 1

# 终止条件：max_steps 正确触发
async def test_stop_on_max_steps():
    mock = make_mock(
        "Thinking...", "Still thinking...", "More...",
        finish_reasons=["tool_calls", "tool_calls", "tool_calls"],
    )
    agent = Agent(name="test", llm=mock, max_steps=3)
    result = await agent.run("Complex question")
    assert result.total_steps == 3
    assert result.finish_reason == "max_steps"

# 多步执行：消息历史正确累积
async def test_multi_step_accumulates_messages():
    mock = make_mock(
        "Let me think...", "The answer is 42.",
        finish_reasons=["tool_calls", "stop"],
    )
    agent = Agent(name="test", llm=mock, max_steps=5)
    result = await agent.run("What is the meaning of life?")
    assert result.total_steps == 2
    # LLM 第二次调用时能看到之前的对话历史
    assert len(mock.call_history[1]) == 3  # [system, user, assistant1]
```

运行结果：

```bash
$ uv run pytest tests/ -v
15 passed in 0.15s
```

## 开发过程中踩的坑

记录三个实际遇到的问题，这些在文档里不会告诉你。

### 坑 1：Ruff 的 UP037 和 F821 规则冲突

`_get_client` 方法的返回类型最初写成：

```python
def _get_client(self) -> "openai.AsyncOpenAI":
```

带引号是因为 `openai` 是在方法内部 lazy import 的，模块级别没有这个名字。但 ruff 的 UP037 规则（Remove unnecessary quotes from type annotation）会自动去掉引号，去掉后 F821 规则又会报 `Undefined name 'openai'`。

**解决方案**：返回类型改为 `Any`。因为 openai 是可选依赖，用 `Any` 更符合实际语义 — 调用方不应该依赖 openai 的具体类型。

### 坑 2：pytest-asyncio 与 `asyncio.run()` 的嵌套冲突

`run_sync()` 是一个同步包装方法：

```python
def run_sync(self, input: str) -> AgentResult:
    return asyncio.run(self.run(input))
```

测试时把它写成了 `async def test_run_sync`，加了 `@pytest.mark.asyncio`。结果报错：

```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

原因：pytest-asyncio 在 `asyncio_mode = "auto"` 时会在事件循环中运行 async 测试，而 `asyncio.run()` 不能在已有事件循环中嵌套调用。

**解决方案**：这个测试本来就该是同步的 — `run_sync` 就是给同步场景用的，测试它当然要在同步上下文中。去掉 `async` 和 `@pytest.mark.asyncio` 就好了。

### 坑 3：Ruff RUF003 规则不兼容中文注释

当我把代码注释改为中文后，ruff 的 RUF003 规则（Ambiguous unicode character）报了 22 个错误 — 它把中文的全角标点（`：`、`，`、`（`、`）`）标记为"歧义字符"。

**解决方案**：在 `pyproject.toml` 中忽略 RUF003：

```toml
[tool.ruff.lint]
ignore = [
    "RUF003",  # 允许中文注释中的全角标点
]
```

这是一个项目级别的决策 — 我们选择中文注释作为规范，所以需要适配工具链。

## 架构全景

Phase 1 完成后的文件结构：

```
src/myagent/
├── __init__.py      # 公开 API: Agent, Message, StepResult, AgentResult
├── agent.py         # Agent 类 — 核心循环（~50 行核心代码）
├── models.py        # 数据模型 — Message, StepResult, AgentResult
├── _llm.py          # LLM 抽象 — Protocol + OpenAI 实现
└── (tools/ providers/ memory/ ... 预留目录)

tests/
├── test_agent.py    # 14 个 Agent 测试
└── test_version.py  # 版本号测试
```

类之间的依赖关系：

```
Agent  ──depends on──>  LLMProtocol  <──implements──  MockLLM (测试)
  │                         │                          OpenAILLM (生产)
  │                         │
  └── uses ──> Message, StepResult, AgentResult, LLMResponse
```

全部检查通过：

```bash
$ uv run ruff check src/ tests/   # All checks passed!
$ uv run mypy src/                  # Success: no issues found
$ uv run pytest tests/ -v           # 15 passed in 0.15s
```

## 总结

这一篇我们实现了 Agent 框架的心脏 — Agent Loop。核心代码不到 50 行，但覆盖了所有基本场景：

| 特性 | 状态 |
|---|---|
| for 循环 + max_steps 安全上限 | ✅ |
| finish_reason 终止判断 | ✅ |
| Protocol 注入 LLM（可 Mock 测试） | ✅ |
| 消息历史正确累积 | ✅ |
| step() 作为子类扩展点 | ✅ |
| 同步 run_sync() 包装 | ✅ |
| 15 个测试全部通过 | ✅ |

**关键学习**：
- Agent Loop 的本质是让 LLM 从一问一答变成持续推理
- `for` 循环比 `while True` 更安全，天然有上限
- Protocol 模式让测试可以完全脱离真实 API
- 循环放在 Agent 层（而非 Model 层），为后续扩展留出空间

## 下一步

Phase 2 将实现 **Tool 系统** — 让 Agent 不只是"说"，还能"做"。

- `@tool` 装饰器：自动从 Python 函数生成 JSON Schema
- 工具注册表：管理 Agent 可用的工具集
- 工具执行循环：模型请求调用 → 执行 → 返回结果 → 继续推理

这是 Agent 从"聊天机器人"变成"能干活的助手"的关键一步。

下一篇：《让 Agent 拥有双手 — 构建 Tool 系统》

## 参考资料

- [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629) — Agent Loop 的理论基础
- [Chain-of-Thought Prompting Elicits Reasoning](https://arxiv.org/abs/2201.11903) — CoT 是 ReAct 的前身
- [Lilian Weng: LLM Powered Autonomous Agents](https://lilianweng.github.io/posts/2023-06-23-agent/) — Agent 系统全景综述
- [Anthropic: Building effective agents](https://www.anthropic.com/research/building-effective-agents) — "Find the simplest solution possible"
- [OpenAI: A practical guide to building agents](https://platform.openai.com/docs/guides/agents) — Agent 执行流程的官方描述
- [OpenAI Agents SDK 源码 — run.py](https://github.com/openai/openai-agents-python/blob/main/src/agents/run.py)
- [Anthropic SDK 源码 — _beta_runner.py](https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/lib/tools/_beta_runner.py)
- [Agno 源码 — base.py](https://github.com/agno-agi/agno/blob/main/libs/agno/agno/models/base.py)
- [LangGraph 源码 — chat_agent_executor.py](https://github.com/langchain-ai/langgraph/blob/main/libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py)
- [Python Protocol (PEP 544)](https://peps.python.org/pep-0544/) — 结构化类型的基础

---

*如果这个系列对你有帮助，欢迎在 [GitHub](https://github.com/songpl-AI/MyAgentFramework) 上 Star 支持。*
