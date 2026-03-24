# Phase 6 — 多 Agent 编排

> Tag: `v0.6-orchestration`
> 前置依赖: Phase 5
> 博客: 《当一个 Agent 不够用 — 多 Agent 编排》

---

## 目标

实现多个 Agent 之间的**协作与编排**。这是 Agent 框架从"单兵"到"军团"的跨越。核心问题：如何让多个 Agent 分工协作，如何路由任务，如何传递上下文？

## 核心概念

```
四种编排模式：

1. Pipeline（顺序）    A → B → C
2. Parallel（并行）    A ──┬── B
                           └── C  → Merge
3. Router（路由）      Input → Router → A or B or C
4. Handoff（移交）     A ──handoff──→ B（控制权转移）
```

## 功能需求

### F5.1 Pipeline（顺序编排）

Agent 按固定顺序依次执行，前一个的输出作为后一个的输入：

```python
from myagent import Agent, Pipeline

researcher = Agent(name="researcher", instructions="你是一个研究员。搜索并整理相关信息。")
writer = Agent(name="writer", instructions="你是一个作家。基于研究资料撰写文章。")
editor = Agent(name="editor", instructions="你是一个编辑。润色和校对文章。")

pipeline = Pipeline(agents=[researcher, writer, editor])
result = await pipeline.run("写一篇关于 Agent 框架的技术博客")
# researcher 输出 → writer 输入 → editor 输入 → 最终结果
```

```python
class Pipeline:
    def __init__(
        self,
        agents: list[Agent],
        pass_full_history: bool = False,  # True: 传递完整历史; False: 只传上一步输出
    ): ...

    async def run(self, input: str) -> PipelineResult: ...

class PipelineResult(BaseModel):
    output: str                           # 最终输出
    steps: list[AgentResult]              # 每个 Agent 的执行结果
    total_steps: int
    total_tokens: int
```

### F5.2 Parallel（并行编排）

多个 Agent 同时处理同一输入，结果由聚合函数合并：

```python
from myagent import Agent, Parallel

analyst_a = Agent(name="tech_analyst", instructions="从技术角度分析...")
analyst_b = Agent(name="market_analyst", instructions="从市场角度分析...")
analyst_c = Agent(name="risk_analyst", instructions="从风险角度分析...")

parallel = Parallel(
    agents=[analyst_a, analyst_b, analyst_c],
    merge_strategy="concatenate",  # 或 "summarize"（用 LLM 合并）
)
result = await parallel.run("分析 AI Agent 市场的前景")
```

```python
class Parallel:
    def __init__(
        self,
        agents: list[Agent],
        merge_strategy: Literal["concatenate", "summarize"] = "concatenate",
        merge_agent: Agent | None = None,   # summarize 模式下用于合并的 Agent
        max_concurrency: int | None = None, # 最大并发数
    ): ...

    async def run(self, input: str) -> ParallelResult: ...
```

### F5.3 Router（条件路由）

根据输入内容，将任务路由到最合适的 Agent：

```python
from myagent import Agent, Router

code_agent = Agent(name="coder", instructions="你是一个编程助手...")
math_agent = Agent(name="math", instructions="你是一个数学助手...")
general_agent = Agent(name="general", instructions="你是一个通用助手...")

router = Router(
    agents=[code_agent, math_agent, general_agent],
    strategy="llm",  # 用 LLM 来决定路由
    # 或 strategy="rule", rules={"code": ["编程", "代码"], "math": ["计算", "数学"]}
)
result = await router.run("帮我写一个快速排序")  # → 路由到 code_agent
```

```python
class Router:
    def __init__(
        self,
        agents: list[Agent],
        strategy: Literal["llm", "rule"] = "llm",
        router_model: str | None = None,     # 路由用的模型（可以用便宜的）
        rules: dict[str, list[str]] | None = None,  # rule 模式的关键词映射
    ): ...

    async def route(self, input: str) -> Agent:
        """决定使用哪个 Agent"""

    async def run(self, input: str) -> RouterResult: ...
```

LLM 路由实现：
- 构造一个特殊 prompt，列出所有可选 Agent 的名称和描述
- 要求模型返回结构化的路由决策（agent_name + reason）
- 使用便宜的小模型来做路由决策（如 gpt-4o-mini）

### F5.4 Handoff（控制权移交）

Agent 在执行过程中主动将控制权移交给另一个 Agent（参考 OpenAI Agents SDK）：

```python
from myagent import Agent, handoff

support_agent = Agent(
    name="support",
    instructions="你是一线客服。处理简单问题，复杂问题转交专家。",
    handoffs=[
        handoff(to=tech_agent, description="技术问题转交技术专家"),
        handoff(to=billing_agent, description="账单问题转交财务专家"),
    ],
)
```

```python
class Handoff(BaseModel):
    to: Agent                          # 目标 Agent
    description: str                   # 何时触发移交的描述
    transfer_history: bool = True      # 是否传递对话历史

def handoff(to: Agent, description: str, **kwargs) -> Handoff: ...
```

Handoff 实现机制：
- Handoff 在 LLM 调用时作为 Tool 暴露（如 `transfer_to_tech_agent`）
- 模型决定调用 handoff tool 时，Agent Loop 将控制权完全转移
- 目标 Agent 接收对话历史（可选），从自己的 system prompt 继续执行
- Handoff 是**控制权转移**，不是工具调用（调用方不会收到返回值）

### F5.5 Agent 间消息协议

```python
class AgentMessage(BaseModel):
    """Agent 间通信的标准消息"""
    from_agent: str                    # 发送方 Agent name
    to_agent: str                      # 接收方 Agent name
    content: str                       # 消息内容
    context: dict[str, Any] = {}       # 附加上下文
    history: list[Message] | None = None  # 可选的对话历史
```

### F5.6 编排结果追踪

所有编排模式共享统一的结果结构，记录完整执行轨迹：

```python
class OrchestrationResult(BaseModel):
    output: str                              # 最终输出
    agent_results: dict[str, AgentResult]    # 每个 Agent 的执行结果
    execution_order: list[str]               # Agent 执行顺序
    total_tokens: int                        # 总 token 用量
    handoff_chain: list[str] | None = None   # Handoff 链路
```

## 不做的事情（显式排除）

- ❌ 图编排（DAG）— 可用 Pipeline + Parallel 组合近似
- ❌ 动态 Agent 创建（运行时生成新 Agent）
- ❌ 分布式 Agent（跨进程/机器）— Phase 12
- ❌ Agent 间共享 Memory — 通过 history 传递替代
- ❌ 复杂的终止策略（如 AutoGen 的组合条件）— 保持简单

## 验收标准

- [ ] Pipeline：3 个 Agent 按序执行，输出正确传递
- [ ] Parallel：3 个 Agent 并行执行，结果正确合并
- [ ] Parallel：max_concurrency 限制生效
- [ ] Router (LLM)：正确路由到合适的 Agent
- [ ] Router (rule)：关键词匹配路由正确
- [ ] Handoff：Agent A 能移交控制权给 Agent B
- [ ] Handoff：对话历史正确传递
- [ ] Handoff 链：A → B → C 的多级移交正常工作
- [ ] OrchestrationResult 完整记录执行轨迹
- [ ] 所有编排模式的单元测试（Mock Agent）

## 核心文件

```
src/myagent/
├── orchestration/
│   ├── __init__.py          # 导出 Pipeline, Parallel, Router, handoff
│   ├── pipeline.py          # Pipeline 顺序编排
│   ├── parallel.py          # Parallel 并行编排
│   ├── router.py            # Router 条件路由
│   ├── handoff.py           # Handoff 控制权移交
│   └── models.py            # OrchestrationResult, AgentMessage
└── agent.py                 # 增加 handoffs 参数
```

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 并行实现 | asyncio.gather / TaskGroup | Python 原生，无需额外依赖 |
| 路由模型 | 默认 gpt-4o-mini | 路由决策不需要大模型，省钱 |
| Handoff 机制 | 伪装为 Tool | 参考 OpenAI SDK，模型已经理解 tool calling |
| 历史传递 | 可选（默认 True） | 某些场景下不需要历史（如独立子任务） |

---

## 设计思考

> 从第一性原理出发的设计推理过程

_开发时填写：问题本质 → 独立思考 → 开源框架怎么做 → 我们的选择与理由_

---
## 参考实现

> 开发过程中参考的论文、博客和开源代码

### 学术论文 / 技术报告
| 论文 | 关联 | 链接 |
|---|---|---|
| _开发时填写_ | | |

### 博客文章 / 技术文档
| 文章 | 关联 | 链接 |
|---|---|---|
| _开发时填写_ | | |

### 开源代码
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
