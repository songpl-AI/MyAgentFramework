# Phase 9 — 生产化

> Tag: `v0.9-production`
> 前置依赖: Phase 8
> 博客: 《从玩具到生产 — Agent 框架的最后一公里》

---

## 目标

将框架从"能跑"提升到"能上线"。解决生产环境中的关键问题：配置管理、断点恢复、错误恢复、并发控制。这些"不性感"的功能决定了框架能否真正用于商业项目。

## 功能需求

### F9.1 配置驱动的 Agent 定义

用 YAML/JSON 定义 Agent，无需写 Python 代码：

```yaml
# agents/customer_support.yaml
name: customer_support
model: gpt-4o
instructions: |
  你是一个客服助手。
  - 礼貌、专业地回答用户问题
  - 无法解决的问题转交人工
max_steps: 15

tools:
  - name: search_faq
    module: myapp.tools.faq
  - name: create_ticket
    module: myapp.tools.ticket

memory:
  type: token_limit
  max_tokens: 8000

store:
  type: sqlite
  path: ./data/support.db

guardrails:
  input:
    - type: max_length
      max_chars: 5000
    - type: prompt_injection
  output:
    - type: pii_filter

cost_control:
  max_cost_usd: 0.5
  max_tool_calls: 10

handoffs:
  - to: escalation_agent
    description: 复杂问题转交专家
```

```python
from myagent import Agent

# 从配置文件创建 Agent
agent = Agent.from_config("agents/customer_support.yaml")

# 或从字典创建
agent = Agent.from_dict(config_dict)
```

### F9.2 Checkpoint / Resume（断点恢复）

参考 LangGraph 的 Checkpoint 机制，在关键节点保存状态：

```python
class Checkpoint(BaseModel):
    checkpoint_id: str
    session_id: str
    step_number: int
    state: SessionState              # 完整状态快照
    pending_tool_calls: list[ToolCall] | None  # 未完成的工具调用
    created_at: datetime

class CheckpointStore(ABC):
    async def save(self, checkpoint: Checkpoint) -> None: ...
    async def load(self, session_id: str, step: int | None = None) -> Checkpoint | None: ...
    async def list(self, session_id: str) -> list[Checkpoint]: ...
```

Agent 配置：

```python
agent = Agent(
    name="long_task_agent",
    checkpoint_store=SQLiteCheckpointStore("checkpoints.db"),
    checkpoint_every=1,  # 每步保存（或 "tool_call" 仅工具调用后保存）
)

# 从断点恢复
result = await agent.resume(session_id="sess_abc", from_step=5)
```

使用场景：
- Agent 执行到一半进程崩溃 → 从最近 checkpoint 恢复
- Human-in-the-loop：暂停等待人工审批 → 审批通过后恢复

### F9.3 错误恢复策略

```python
class RetryPolicy(BaseModel):
    max_retries: int = 3
    backoff: Literal["fixed", "exponential"] = "exponential"
    base_delay: float = 1.0          # 秒
    max_delay: float = 60.0
    retry_on: list[str] = ["rate_limit", "timeout", "server_error"]

class FallbackPolicy(BaseModel):
    fallback_models: list[str] = []  # 如 ["gpt-4o", "gpt-4o-mini", "claude-haiku"]
    fallback_on: list[str] = ["rate_limit", "model_unavailable"]
```

Agent 集成：

```python
agent = Agent(
    name="resilient_agent",
    model="gpt-4o",
    retry_policy=RetryPolicy(max_retries=3, backoff="exponential"),
    fallback_policy=FallbackPolicy(fallback_models=["gpt-4o-mini"]),
)
```

错误恢复流程：
1. LLM 调用失败 → 检查是否匹配 retry_on
2. 匹配 → 按 backoff 策略重试
3. 重试耗尽 → 检查 fallback_models
4. 有 fallback → 切换模型重试
5. 全部失败 → 抛出异常 / 从最近 checkpoint 恢复

### F9.4 并发控制

```python
class ConcurrencyConfig(BaseModel):
    max_concurrent_runs: int = 10        # 最大并行 Agent 运行数
    max_concurrent_tool_calls: int = 5   # 最大并行工具调用数
    max_concurrent_llm_calls: int = 3    # 最大并行 LLM 调用数

class AgentPool:
    """Agent 执行池，管理并发"""

    def __init__(self, config: ConcurrencyConfig): ...

    async def submit(self, agent: Agent, input: str) -> AgentResult:
        """提交执行任务，受并发限制"""

    async def submit_batch(self, tasks: list[tuple[Agent, str]]) -> list[AgentResult]:
        """批量提交"""

    @property
    def active_runs(self) -> int: ...
    @property
    def queued_runs(self) -> int: ...
```

### F9.5 环境与配置管理

```python
class AgentConfig:
    """全局配置管理"""

    # 从多种来源加载配置（优先级从高到低）
    # 1. 代码显式设置
    # 2. 环境变量（MYAGENT_*）
    # 3. 配置文件（.myagent.yaml）
    # 4. 默认值

    @classmethod
    def from_env(cls) -> "AgentConfig": ...

    @classmethod
    def from_file(cls, path: str) -> "AgentConfig": ...
```

环境变量映射：
```
MYAGENT_DEFAULT_MODEL=gpt-4o
MYAGENT_OPENAI_API_KEY=sk-...
MYAGENT_ANTHROPIC_API_KEY=sk-ant-...
MYAGENT_LOG_LEVEL=INFO
MYAGENT_TRACE_EXPORTER=console
MYAGENT_CHECKPOINT_STORE=sqlite:///checkpoints.db
```

### F9.6 优雅关停

```python
# Agent 接收到中断信号时优雅关停
import signal

class GracefulShutdown:
    """优雅关停管理器"""

    def __init__(self):
        signal.signal(signal.SIGINT, self._handle)
        signal.signal(signal.SIGTERM, self._handle)

    def _handle(self, sig, frame):
        # 1. 停止接收新任务
        # 2. 等待当前步骤完成
        # 3. 保存 checkpoint
        # 4. 清理资源（关闭 MCP 连接等）
```

## 不做的事情（显式排除）

- ❌ 多租户 / 用户隔离 — 应用层处理
- ❌ RBAC 权限系统 — 应用层处理
- ❌ 分布式部署 / Kubernetes — 超出框架范围
- ❌ Web UI — 独立项目
- ❌ 计费系统 — 应用层处理

## 验收标准

- [ ] 从 YAML 配置文件正确创建 Agent
- [ ] Agent 执行中崩溃后能从 Checkpoint 恢复
- [ ] 恢复后继续执行且结果正确
- [ ] RetryPolicy 按配置重试（指数退避生效）
- [ ] FallbackPolicy 在主模型不可用时切换备选
- [ ] AgentPool 并发限制生效
- [ ] 优雅关停正确保存状态
- [ ] 环境变量配置正确覆盖默认值
- [ ] 配置文件验证（错误的 YAML 给出清晰报错）

## 核心文件

```
src/myagent/
├── config/
│   ├── __init__.py          # 导出 AgentConfig
│   ├── loader.py            # YAML/JSON/ENV 配置加载
│   ├── schema.py            # 配置 Schema（Pydantic 验证）
│   └── defaults.py          # 默认值
├── checkpoint/
│   ├── __init__.py
│   ├── models.py            # Checkpoint 模型
│   └── store.py             # CheckpointStore + SQLite 实现
├── resilience/
│   ├── __init__.py
│   ├── retry.py             # RetryPolicy 实现
│   ├── fallback.py          # FallbackPolicy 实现
│   └── pool.py              # AgentPool 并发控制
└── agent.py                 # 集成所有生产化特性
```

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 配置格式 | YAML（主） + JSON（兼容） | YAML 可读性好，JSON 机器友好 |
| YAML 解析 | PyYAML / ruamel.yaml | 标准选择 |
| 并发控制 | asyncio.Semaphore | 标准库，足够使用 |
| Checkpoint 存储 | 复用 SQLiteStore | 统一存储方案 |

---

## 设计思考

> 从第一性原理出发的设计推理过程

_开发时填写：问题本质 → 独立思考 → 开源框架怎么做 → 我们的选择与理由_

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
