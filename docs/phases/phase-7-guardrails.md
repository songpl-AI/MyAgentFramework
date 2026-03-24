# Phase 7 — Guardrails 与安全

> Tag: `v0.7-guardrails`
> 前置依赖: Phase 6
> 博客: 《生产环境的 Agent 需要什么安全措施》

---

## 目标

让 Agent 具备**生产级别的安全防护**。没有 Guardrails 的 Agent 就像没有刹车的汽车 — 功能强大但不可控。实现输入/输出/工具三层防护 + 速率限制 + 成本控制。

## 核心概念

```
User Input
    ↓
┌─── Input Guardrails ───┐    ← 第一道防线：过滤恶意/违规输入
│   内容审核 / 注入检测    │
└─────────┬───────────────┘
          ↓
    Agent Loop
          │
    ┌─── Tool Guardrails ──┐   ← 第二道防线：控制工具执行
    │  权限校验 / 参数验证   │
    └─────────┬─────────────┘
              ↓
┌─── Output Guardrails ──┐    ← 第三道防线：校验最终输出
│   格式验证 / 敏感信息过滤 │
└─────────┬───────────────┘
          ↓
    Final Response

速率限制 & 成本控制         ← 横切关注点：全程生效
```

## 功能需求

### F6.1 Guardrail 基础接口

```python
class GuardrailResult(BaseModel):
    passed: bool                           # 是否通过
    reason: str | None = None              # 未通过的原因
    modified_content: str | None = None    # 可选的修正内容

class InputGuardrail(ABC):
    @abstractmethod
    async def check(self, input: str, context: dict) -> GuardrailResult: ...

class OutputGuardrail(ABC):
    @abstractmethod
    async def check(self, output: str, context: dict) -> GuardrailResult: ...

class ToolGuardrail(ABC):
    @abstractmethod
    async def before_execute(self, tool_name: str, args: dict) -> GuardrailResult: ...

    async def after_execute(self, tool_name: str, args: dict, result: str) -> GuardrailResult:
        """可选的执行后校验"""
        return GuardrailResult(passed=True)
```

### F6.2 内置 Input Guardrails

```python
# 内容长度限制
class MaxLengthGuardrail(InputGuardrail):
    def __init__(self, max_chars: int = 10000): ...

# Prompt 注入检测（基础规则 + 可选 LLM 检测）
class PromptInjectionGuardrail(InputGuardrail):
    def __init__(self, use_llm: bool = False, detector_model: str = "gpt-4o-mini"): ...
    # 规则检测：检查常见注入模式（"ignore previous instructions" 等）
    # LLM 检测：用小模型判断输入是否包含注入意图

# 关键词黑名单
class KeywordBlockGuardrail(InputGuardrail):
    def __init__(self, blocked_keywords: list[str]): ...
```

### F6.3 内置 Output Guardrails

```python
# 敏感信息过滤（PII）
class PIIFilterGuardrail(OutputGuardrail):
    """检测并遮盖输出中的手机号、邮箱、身份证号等"""
    def __init__(self, patterns: dict[str, str] | None = None): ...
    # 默认正则：手机号、邮箱、身份证号
    # 检测到时用 [REDACTED] 替换

# JSON 格式验证
class JSONSchemaGuardrail(OutputGuardrail):
    """验证输出是否符合指定的 JSON Schema"""
    def __init__(self, schema: dict): ...

# 自定义验证函数
class CustomGuardrail(OutputGuardrail):
    def __init__(self, check_fn: Callable[[str], bool], reason: str = ""): ...
```

### F6.4 Tool Guardrails

```python
# 工具白名单
class AllowedToolsGuardrail(ToolGuardrail):
    """只允许指定的工具被调用"""
    def __init__(self, allowed: list[str]): ...

# 工具调用频率限制
class ToolRateLimitGuardrail(ToolGuardrail):
    """限制单个工具在一次 run 中的最大调用次数"""
    def __init__(self, limits: dict[str, int]): ...
    # 如 {"web_search": 5, "calculate": 10}

# 参数验证（额外的安全校验）
class ToolArgsSanitizerGuardrail(ToolGuardrail):
    """清理工具参数中的潜在危险内容"""
    # 如：检查 file_path 是否有路径遍历（../）
    # 如：检查 shell_command 是否包含危险命令
```

### F6.5 Tripwire 模式

参考 OpenAI Agents SDK，Guardrail 失败时的处理策略：

```python
class TripwirePolicy(str, Enum):
    RAISE = "raise"         # 抛出异常，立即终止
    WARN = "warn"           # 记录警告，继续执行
    MODIFY = "modify"       # 使用修正内容继续
    RETRY = "retry"         # 要求用户重新输入
```

### F6.6 Agent 集成

```python
agent = Agent(
    name="safe_agent",
    instructions="...",
    input_guardrails=[
        MaxLengthGuardrail(max_chars=5000),
        PromptInjectionGuardrail(use_llm=True),
    ],
    output_guardrails=[
        PIIFilterGuardrail(),
    ],
    tool_guardrails=[
        AllowedToolsGuardrail(["calculate", "web_search"]),
        ToolRateLimitGuardrail({"web_search": 3}),
    ],
    tripwire_policy=TripwirePolicy.RAISE,  # 默认策略
)
```

### F6.7 速率限制

```python
class RateLimiter:
    """API 调用速率限制"""

    def __init__(
        self,
        max_requests_per_minute: int = 60,
        max_tokens_per_minute: int = 100_000,
    ): ...

    async def acquire(self, estimated_tokens: int = 0) -> None:
        """获取调用许可，超限时等待"""

    def remaining(self) -> dict:
        """返回剩余配额"""
```

### F6.8 成本控制

```python
class CostController:
    """单次 run 的成本控制"""

    def __init__(
        self,
        max_total_tokens: int = 50_000,       # 最大总 token 数
        max_cost_usd: float = 1.0,            # 最大美元成本
        max_tool_calls: int = 20,             # 最大工具调用次数
    ): ...

    def check(self, current_usage: Usage) -> bool:
        """检查是否超限"""

    def estimate_cost(self, usage: Usage, model: str) -> float:
        """估算 API 费用"""
```

## 不做的事情（显式排除）

- ❌ 完整的内容审核系统（接入 OpenAI Moderation 等）— 扩展
- ❌ 代码执行沙箱（Docker 隔离）— 可作为 Tool Guardrail 扩展
- ❌ RBAC 权限系统 — Phase 12
- ❌ 审计日志 — Phase 8（可观测性中处理）

## 验收标准

- [ ] MaxLengthGuardrail 正确拦截超长输入
- [ ] PromptInjectionGuardrail 检测基础注入模式
- [ ] PIIFilterGuardrail 正确遮盖手机号、邮箱
- [ ] AllowedToolsGuardrail 拒绝未授权工具
- [ ] ToolRateLimitGuardrail 超限后拒绝调用
- [ ] TripwirePolicy.RAISE 正确抛出 GuardrailTripwireError
- [ ] TripwirePolicy.MODIFY 使用修正内容继续
- [ ] RateLimiter 正确限速（模拟高频调用测试）
- [ ] CostController 在超限时终止 Agent Loop
- [ ] Guardrails 不影响正常请求的性能（< 50ms overhead）

## 核心文件

```
src/myagent/
├── guardrails/
│   ├── __init__.py          # 导出所有 Guardrail
│   ├── base.py              # ABC + GuardrailResult + TripwirePolicy
│   ├── input.py             # Input Guardrails
│   ├── output.py            # Output Guardrails
│   ├── tool.py              # Tool Guardrails
│   ├── rate_limiter.py      # RateLimiter
│   └── cost.py              # CostController
├── agent.py                 # 集成 Guardrails 到 Agent Loop
└── exceptions.py            # GuardrailTripwireError
```

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| PII 检测 | 正则表达式 | 简单、快速、无外部依赖；精确方案用 NER 模型是过度设计 |
| 注入检测 | 规则 + 可选 LLM | 规则处理明显案例，LLM 处理高级注入 |
| 速率限制算法 | 滑动窗口 | 比固定窗口更平滑，实现不复杂 |
| 成本计算 | 硬编码价格表 + 定期更新 | 实用主义，价格变动不频繁 |

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
