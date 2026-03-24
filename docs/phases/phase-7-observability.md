# Phase 7 — 可观测性

> Tag: `v0.7-observability`
> 前置依赖: Phase 6
> 博客: 《Agent 出了问题怎么调试 — 可观测性实战》

---

## 目标

让 Agent 的每一步执行都**可追踪、可度量、可调试**。生产环境中，Agent 的行为是非确定性的（同样的输入可能产生不同的工具调用序列），没有可观测性就是在盲飞。

## 核心概念

```
Trace（一次完整的 Agent 执行）
  └── Span（一个操作单元）
        ├── LLM Call Span        （模型调用：prompt、response、tokens、耗时）
        ├── Tool Execution Span  （工具执行：名称、参数、结果、耗时）
        ├── Guardrail Span       （安全校验：类型、通过/拒绝）
        └── Agent Span           （子 Agent / Handoff 执行）

每个 Span 记录：
  - trace_id      全局唯一追踪 ID
  - span_id       本操作唯一 ID
  - parent_id     父 Span ID（构成树结构）
  - name          操作名称
  - start_time    开始时间
  - end_time      结束时间
  - attributes    键值对属性
  - events        时间点事件列表
  - status        成功 / 失败
```

## 功能需求

### F7.1 Trace 与 Span 模型

```python
class Span(BaseModel):
    trace_id: str
    span_id: str
    parent_id: str | None = None
    name: str
    kind: Literal["llm", "tool", "guardrail", "agent", "orchestration", "custom"]
    start_time: datetime
    end_time: datetime | None = None
    status: Literal["ok", "error"] = "ok"
    attributes: dict[str, Any] = {}
    events: list[SpanEvent] = []

class SpanEvent(BaseModel):
    name: str
    timestamp: datetime
    attributes: dict[str, Any] = {}

class Trace(BaseModel):
    trace_id: str
    root_span: Span
    spans: list[Span]
    metadata: dict[str, Any] = {}       # agent_name, model, session_id 等
```

### F7.2 Tracer 接口

```python
class Tracer:
    """Trace 收集器"""

    def start_trace(self, name: str, metadata: dict = {}) -> TraceContext: ...
    def start_span(self, name: str, kind: str, parent: Span | None = None) -> Span: ...
    def end_span(self, span: Span, status: str = "ok") -> None: ...
    def add_event(self, span: Span, name: str, attributes: dict = {}) -> None: ...
    def end_trace(self) -> Trace: ...
```

Context Manager 用法：

```python
async with tracer.trace("agent.run") as trace:
    async with trace.span("llm.call", kind="llm") as span:
        span.set_attribute("model", "gpt-4o")
        span.set_attribute("prompt_tokens", 150)
        response = await provider.chat(messages)
        span.set_attribute("completion_tokens", 50)
```

### F7.3 自动埋点

Agent Loop 的关键操作自动产生 Span，无需手动埋点：

| 操作 | Span Kind | 自动记录的属性 |
|---|---|---|
| agent.run() | agent | agent_name, model, input, output, total_steps |
| provider.chat() | llm | model, prompt_tokens, completion_tokens, finish_reason, latency_ms |
| tool.execute() | tool | tool_name, arguments, result, latency_ms, error |
| guardrail.check() | guardrail | guardrail_name, passed, reason |
| pipeline/parallel/router | orchestration | pattern, agents_involved, routing_decision |
| handoff | agent | from_agent, to_agent, reason |

### F7.4 Trace Exporter

```python
class TraceExporter(ABC):
    """Trace 导出器接口"""

    @abstractmethod
    async def export(self, trace: Trace) -> None: ...

# 内置导出器
class ConsoleExporter(TraceExporter):
    """打印到控制台（开发调试用）"""
    def __init__(self, verbose: bool = True): ...

class JSONFileExporter(TraceExporter):
    """导出为 JSON 文件"""
    def __init__(self, output_dir: str = "./traces"): ...

class CallbackExporter(TraceExporter):
    """自定义回调导出"""
    def __init__(self, callback: Callable[[Trace], None]): ...
```

Console 输出示例：

```
[Trace abc123] agent.run "math_agent" (3.2s, 850 tokens, $0.003)
  ├── [llm] gpt-4o-mini (0.8s, 350 tokens)
  │     prompt: "计算 2^10 ..."
  │     response: [tool_call: calculate("2**10")]
  ├── [tool] calculate (0.001s)
  │     args: {"expression": "2**10"}
  │     result: "1024"
  ├── [llm] gpt-4o-mini (0.6s, 200 tokens)
  │     response: "2^10 = 1024"
  └── [done] output: "2^10 = 1024"
```

### F7.5 Metrics 收集

```python
class Metrics:
    """聚合指标收集"""

    # 单次 run 级别
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    total_cost_usd: float
    total_latency_ms: float
    llm_calls: int
    tool_calls: int
    steps: int

    # 工具级别
    tool_call_counts: dict[str, int]       # 每个工具被调用次数
    tool_latencies: dict[str, list[float]] # 每个工具的耗时列表
    tool_errors: dict[str, int]            # 每个工具的错误次数

    # 模型级别
    model_token_usage: dict[str, Usage]    # 每个模型的 token 用量
```

### F7.6 Agent 集成

```python
agent = Agent(
    name="my_agent",
    instructions="...",
    trace_exporters=[
        ConsoleExporter(verbose=True),
        JSONFileExporter(output_dir="./traces"),
    ],
)

result = await agent.run("你好")
print(result.metrics.total_cost_usd)  # 查看费用
print(result.trace)                    # 访问完整 Trace
```

### F7.7 可选 OpenTelemetry 导出

```python
# 作为可选扩展（不强制依赖 opentelemetry）
class OTelExporter(TraceExporter):
    """导出到 OpenTelemetry Collector"""
    def __init__(self, endpoint: str = "http://localhost:4317"): ...
    # 将内部 Span 映射为 OTel Span
```

## 不做的事情（显式排除）

- ❌ Web UI 仪表板 — 后续独立项目
- ❌ 实时监控告警 — 生产化阶段
- ❌ A/B 测试 / 评估框架 — 独立功能
- ❌ Prometheus metrics 导出 — OTel 可覆盖

## 验收标准

- [ ] 每次 agent.run() 自动生成完整 Trace
- [ ] Trace 包含所有 LLM 调用、工具调用、Guardrail 检查的 Span
- [ ] Span 父子关系正确（树结构可视化）
- [ ] ConsoleExporter 输出可读的执行轨迹
- [ ] JSONFileExporter 产出有效 JSON 文件
- [ ] Metrics 正确统计 token 用量和费用
- [ ] 多 Agent 编排场景的 Trace 关联正确
- [ ] Tracing overhead < 5ms per span
- [ ] OTelExporter 作为可选依赖，不影响核心功能

## 核心文件

```
src/myagent/
├── tracing/
│   ├── __init__.py          # 导出 Tracer, Trace, Span
│   ├── models.py            # Trace, Span, SpanEvent, Metrics
│   ├── tracer.py            # Tracer 实现
│   ├── exporters/
│   │   ├── __init__.py
│   │   ├── console.py       # ConsoleExporter
│   │   ├── json_file.py     # JSONFileExporter
│   │   └── otel.py          # OTelExporter（可选）
│   └── auto.py              # 自动埋点装饰器/中间件
├── agent.py                 # 集成 Tracing
└── models.py                # AgentResult 增加 metrics, trace 字段
```

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| Trace 模型 | 自定义（不直接用 OTel SDK） | 轻量，学习目的，OTel 作为可选导出 |
| 自动埋点 | 装饰器/Context Manager | Pythonic，非侵入式 |
| 费用计算 | 内置价格表 | 实用，定期手动更新即可 |
| 必选 vs 可选 | Console + JSON 必选；OTel 可选 | 零配置可用，高级用户可扩展 |

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
