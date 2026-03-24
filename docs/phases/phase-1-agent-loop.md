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

## 参考实现

> 开发过程中参考的其他框架的具体代码和文档链接

| 参考内容 | 框架 | 链接 |
|---|---|---|
| _开发时填写_ | | |

## 开发日志

> 开发过程中遇到的问题、踩坑记录、设计变更

_开发时填写_

<!-- 格式示例：
### 问题 1：简要描述
- **现象**：发生了什么
- **根因**：为什么发生
- **解决**：怎么解决的
- **参考**：相关链接
-->
