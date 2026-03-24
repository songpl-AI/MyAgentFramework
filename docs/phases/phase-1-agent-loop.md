# Phase 1 — 最小 Agent Loop

> Tag: `v0.1-agent-loop`
> 前置依赖: Phase 0
> 博客: 《50 行代码实现一个 Agent Loop》

---

## 目标

实现 Agent 的**最核心机制** — ReAct 循环。这是所有 Agent 框架的心脏：模型思考、决定行动、执行、观察结果、循环往复。这个阶段不涉及工具系统，Agent 只能"思考"和"回答"。

## 核心概念

```
User Input
    ↓
┌─────────────────────┐
│   Agent Loop        │
│                     │
│   1. 构造 Prompt    │ ← system prompt + 对话历史 + 用户输入
│   2. 调用 LLM       │ ← 发送给模型，获取响应
│   3. 解析响应        │ ← 判断：最终回答 or 需要继续？
│   4. 检查终止条件    │ ← max_steps? 模型说"完成了"?
│   └── 循环或结束    │
└─────────────────────┘
    ↓
Final Response
```

## 功能需求

### F1.1 Agent 基类

```python
class Agent:
    """最小 Agent 实现"""

    def __init__(
        self,
        name: str,                    # Agent 名称
        instructions: str,            # System prompt
        model: str = "gpt-4o-mini",   # 模型标识
        max_steps: int = 10,          # 最大循环步数
    ): ...

    async def run(self, input: str) -> AgentResult:
        """执行 Agent 循环，返回最终结果"""

    async def step(self, messages: list[Message]) -> StepResult:
        """执行单步：调用模型 → 解析响应"""
```

**设计要点**：
- Agent 是有状态的（持有 instructions），但每次 `run()` 是独立执行
- `step()` 是可覆写的扩展点，子类可以自定义单步逻辑
- 异步优先，但提供 `run_sync()` 同步包装

### F1.2 消息模型

```python
class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class StepResult(BaseModel):
    message: Message               # 模型的响应消息
    finish_reason: str             # "stop" | "tool_calls" | "length"
    step_number: int               # 当前步数

class AgentResult(BaseModel):
    output: str                    # 最终文本输出
    messages: list[Message]        # 完整对话历史
    steps: list[StepResult]        # 所有步骤记录
    total_steps: int               # 总步数
```

**设计要点**：
- 使用 Pydantic BaseModel 保证类型安全和序列化能力
- `Message` 是内部统一格式，不绑定任何 Provider
- `AgentResult` 包含完整的执行轨迹，方便调试和后续 Tracing

### F1.3 最简 LLM 调用

这个阶段只做**硬编码的单 Provider** 调用（OpenAI 或 Anthropic 二选一），不做抽象层：

```python
async def _call_llm(self, messages: list[Message]) -> Message:
    """直接调用 LLM API，返回响应消息"""
```

- 仅支持文本输入/输出（不支持工具调用，Phase 2 加）
- 仅支持非流式（流式在 Phase 3 加）
- API Key 从环境变量读取

### F1.4 终止条件

Agent Loop 在以下任一条件满足时终止：

| 条件 | 说明 |
|---|---|
| 模型返回 finish_reason="stop" | 模型认为已完成 |
| 达到 max_steps | 防止无限循环 |
| 模型返回空内容 | 异常保护 |

终止时返回 `AgentResult`，包含终止原因。

### F1.5 基础示例

```python
import asyncio
from myagent import Agent

agent = Agent(
    name="assistant",
    instructions="你是一个有帮助的助手。用简洁的中文回答问题。",
)

result = asyncio.run(agent.run("什么是 Agent？请用一句话解释。"))
print(result.output)
```

## 不做的事情（显式排除）

- ❌ Tool / Function Calling — Phase 2
- ❌ 多 Provider 支持 — Phase 3
- ❌ 流式输出 — Phase 3
- ❌ Memory 持久化 — Phase 4
- ❌ 多 Agent 编排 — Phase 5
- ❌ 错误重试 / Fallback — Phase 6

## 验收标准

- [ ] `Agent.run("你好")` 返回有效的 `AgentResult`
- [ ] 对话历史正确记录每一步
- [ ] max_steps=1 时只执行一步就终止
- [ ] max_steps=3 的多轮思考场景正常工作
- [ ] 模型返回 stop 时正确终止
- [ ] 单元测试覆盖核心循环逻辑（Mock LLM 响应）

## 测试策略

```python
# 用 Mock 替代真实 LLM 调用，实现确定性测试
class MockProvider:
    def __init__(self, responses: list[str]):
        self.responses = iter(responses)

    async def chat(self, messages):
        return Message(role="assistant", content=next(self.responses))
```

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 先接哪个 Provider | OpenAI（gpt-4o-mini） | 生态最广，便宜，方便测试 |
| 消息格式 | 自定义 Message | 不绑定 Provider SDK，为多 Provider 铺路 |
| 同步/异步 | async 为主 | Agent 天然是 IO 密集型，async 是正确选择 |
| 配置方式 | 构造函数参数 | 最简单，不引入配置文件复杂度 |

## 核心文件

```
src/myagent/
├── __init__.py          # 导出 Agent, AgentResult
├── agent.py             # Agent 类 + run loop
├── models.py            # Message, StepResult, AgentResult
└── _llm.py              # 直接的 LLM API 调用（临时，Phase 3 重构）
```

---

## 设计思考

### 问题本质

Agent Loop 要解决的根本问题是：**如何让 LLM 从"一次性问答"变成"持续推理直到完成任务"？**

一次普通的 LLM 调用是无状态的 — 你问一个问题，模型回答，结束。但真实任务往往需要多步推理：查找信息、执行计算、基于结果继续分析。Agent Loop 就是把这个多步过程自动化的机制。

用 Anthropic 的话说：**"LLMs using tools based on environmental feedback in a loop."**

### 独立思考：最小循环应该长什么样？

从最简单的角度思考，一个 Agent Loop 只需要：

```
messages = [system_prompt, user_input]
for i in range(max_steps):
    response = llm.call(messages)
    messages.append(response)
    if response.is_final:  # 模型认为可以结束了
        return response.text
raise MaxStepsExceeded
```

这就是全部。核心问题只有两个：
1. **何时继续**：模型返回了工具调用 → 执行工具 → 将结果加入历史 → 继续
2. **何时停止**：模型返回最终文本（无工具调用）or 达到步数上限

### 开源框架怎么做

调研了 4 个框架的 Agent Loop 实现，发现了有意思的分化：

**OpenAI Agents SDK** — `while True` + NextStep 类型分发
- 循环在 `src/agents/run.py` 的 `AgentRunner.run()` 中
- 每次迭代是一个"turn"（一次 LLM 调用 + 工具执行）
- 通过 4 种 NextStep 类型决定下一步：FinalOutput / RunAgain / Handoff / Interruption
- 用 `return` 退出循环，不用 `break`
- 设计重：1600+ 行，处理了 Guardrails、Handoff、Streaming、Resume 等所有场景

**Anthropic SDK** — 最简洁的 `while True`
- 手动模式：检查 `stop_reason == "tool_use"` 继续，否则退出
- SDK 内置 Tool Runner（`_beta_runner.py`）：`while not self._should_stop()` 循环
- 关键差异：Anthropic 只有 user/assistant 两种角色，tool_result 嵌在 user 消息中
- 内置 Context Compaction（超过 100k tokens 时自动总结压缩）

**Agno** — 两层循环架构
- 外层 `Agent._run()` 是单次编排（session 管理、hooks、后处理）
- 内层 `Model.response()` 才是真正的 `while True` 工具调用循环
- 循环放在 Model 层而非 Agent 层 — 简化了 Agent 代码但耦合了迭代逻辑
- 终止条件最丰富：tool_call_limit、stop_after_tool_call、HITL 等

**LangGraph** — 图执行（完全不同的范式）
- 不是 while 循环，而是 BSP（Bulk Synchronous Parallel）模型
- `agent` 节点 → 条件边 `should_continue` → `tools` 节点 → 回到 `agent`
- 终止 = 条件边返回 END（无工具调用时）
- 强大但复杂度高，不适合作为最小实现的参考

### 我们的选择

**循环结构：简洁的 `for` 循环 + 明确退出**

不用 `while True`（需要额外的 break/max 检查），用 `for i in range(max_steps)` — 天然自带步数限制，更安全。

**循环放在 Agent 层**

不像 Agno 那样放在 Model 层。原因：
- Agent 层控制循环 = Agent 拥有完整的执行权（后续加 Guardrails、Tracing 更自然）
- Model 层应该只负责"调用一次 LLM"— 单一职责

**消息格式：自定义 Message，预留 tool 扩展**

参考 Anthropic 的 content block 思路，但 Phase 1 先用最简单的 `role + content` 结构。Message 的 role 预留 `"tool"` 给 Phase 2，但本阶段不实现。

**终止判断：基于 finish_reason**

- OpenAI 用 `finish_reason: "stop"` 表示自然结束
- Anthropic 用 `stop_reason: "end_turn"` 表示自然结束
- 我们统一为 `finish_reason` 字段，由 Provider 适配层（Phase 3）负责翻译

**LLM 调用：先硬编码 OpenAI，但通过 Protocol 预留接口**

不做完整 Provider 抽象（Phase 3 的事），但用 Python Protocol 定义调用签名，让 Mock 和真实 Provider 有统一接口。这样测试可以完全不依赖真实 API。

---

## 参考实现

### 学术论文 / 技术报告
| 论文 | 关联 | 链接 |
|---|---|---|
| ReAct: Synergizing Reasoning and Acting in Language Models | Agent Loop 的理论基础 — Thought→Action→Observation 循环 | https://arxiv.org/abs/2210.03629 |
| Chain-of-Thought Prompting Elicits Reasoning in LLMs | CoT 是 ReAct 的前身，理解"模型可以多步推理" | https://arxiv.org/abs/2201.11903 |

### 博客文章 / 技术文档
| 文章 | 关联 | 链接 |
|---|---|---|
| Lilian Weng: LLM Powered Autonomous Agents | Agent 系统全景综述：Planning + Memory + Tool Use 三要素 | https://lilianweng.github.io/posts/2023-06-23-agent/ |
| Anthropic: Building effective agents | "Find the simplest solution possible" — 简洁优先的设计哲学 | https://www.anthropic.com/research/building-effective-agents |
| OpenAI: A practical guide to building agents | Agent 执行流程的官方描述 | https://platform.openai.com/docs/guides/agents |
| Anthropic: Tool use documentation | Anthropic 消息格式和 stop_reason 机制 | https://docs.anthropic.com/en/docs/build-with-claude/tool-use |

### 开源代码
| 参考内容 | 框架 | 链接 |
|---|---|---|
| AgentRunner.run() — while True 主循环 + NextStep 分发 | OpenAI Agents SDK | https://github.com/openai/openai-agents-python/blob/main/src/agents/run.py |
| _beta_runner.py — SDK 内置的 Tool Runner 循环 | Anthropic SDK | https://github.com/anthropics/anthropic-sdk-python/blob/main/src/anthropic/lib/tools/_beta_runner.py |
| Model.response() — while True 工具调用循环 | Agno | https://github.com/agno-agi/agno/blob/main/libs/agno/agno/models/base.py |
| create_react_agent() — 图节点 + 条件边构建 | LangGraph | https://github.com/langchain-ai/langgraph/blob/main/libs/prebuilt/langgraph/prebuilt/chat_agent_executor.py |
| run_steps.py — NextStep 类型定义 | OpenAI Agents SDK | https://github.com/openai/openai-agents-python/blob/main/src/agents/run_internal/run_steps.py |

## 开发日志

### 2026-03-24

**已实现**
- `src/myagent/models.py` — Message, StepResult, AgentResult (Pydantic v2)
- `src/myagent/_llm.py` — LLMProtocol, LLMResponse, OpenAILLM (lazy import)
- `src/myagent/agent.py` — Agent 类，for 循环核心 loop，step() 扩展点
- `tests/test_agent.py` — 14 个测试 + 1 个版本测试，MockLLM 实现
- `src/myagent/__init__.py` — 公开 API 导出

**遇到的问题**

1. **Ruff UP037 与 F821 冲突**：`_get_client(self) -> "openai.AsyncOpenAI"` 带引号的类型注解被 ruff UP037 规则自动去掉引号，但去掉后因为 openai 是懒加载导入，ruff F821 报 undefined name。解决：将返回类型改为 `Any`，因为 openai 是可选依赖，用 `Any` 更符合实际语义。

2. **pytest-asyncio 与 `asyncio.run()` 冲突**：`test_run_sync` 测试标记了 `@pytest.mark.asyncio`，测试函数在事件循环内运行，而 `run_sync()` 内部调用 `asyncio.run()` 不能嵌套事件循环。解决：去掉该测试的 `async` 标记，作为纯同步测试运行。

3. **Ruff I001 import sorting**：`from __future__ import annotations` 与后续 import 之间的排序问题，3 个文件受影响。解决：`ruff check --fix` 自动修复。

4. **Ruff RUF003 与中文注释冲突**：将代码注释改为中文后，ruff RUF003 规则报 22 个错误，将中文全角标点（`：`、`，`、`（`、`）`）标记为"歧义字符"。解决：在 `pyproject.toml` 中 `ignore = ["RUF003"]`，这是项目级别的决策——我们选择中文注释作为编码规范。
