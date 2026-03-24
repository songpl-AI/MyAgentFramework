# Phase 3 — 多 Provider 适配

> Tag: `v0.3-providers`
> 前置依赖: Phase 2
> 博客: 《一套代码接入所有大模型》

---

## 目标

将 Phase 1 中硬编码的单一 LLM 调用抽象为**可插拔的 Provider 层**。实现 OpenAI 和 Anthropic 两个 Provider，统一消息格式转换，并支持流式输出。用户切换模型只需改一个参数。

## 核心概念

```
Agent
  ↓ 内部统一消息格式
Provider Adapter
  ├─ OpenAIProvider    → OpenAI API 格式 ↔ 内部格式
  ├─ AnthropicProvider → Anthropic API 格式 ↔ 内部格式
  └─ (未来扩展...)
```

## 功能需求

### F3.1 Provider 抽象接口

```python
from abc import ABC, abstractmethod

class BaseProvider(ABC):
    """LLM Provider 的抽象基类"""

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> ProviderResponse: ...

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]: ...
```

### F3.2 统一响应模型

```python
class ProviderResponse(BaseModel):
    message: Message              # 统一格式的响应消息
    finish_reason: str            # "stop" | "tool_calls" | "length"
    usage: Usage | None = None    # Token 用量

class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class StreamChunk(BaseModel):
    delta_content: str | None = None       # 增量文本
    delta_tool_calls: list[ToolCall] | None = None  # 增量工具调用
    finish_reason: str | None = None       # 仅最后一个 chunk 有
    usage: Usage | None = None             # 仅最后一个 chunk 有
```

### F3.3 OpenAI Provider

```python
class OpenAIProvider(BaseProvider):
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,       # 默认从环境变量
        base_url: str | None = None,      # 支持兼容 API（如 DeepSeek）
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ): ...
```

负责：
- 内部 `Message` → OpenAI `ChatCompletionMessage` 格式转换
- 工具 Schema → OpenAI `tools` 参数格式
- OpenAI 响应 → 内部 `ProviderResponse` 转换
- 流式 → `AsyncIterator[StreamChunk]`

### F3.4 Anthropic Provider

```python
class AnthropicProvider(BaseProvider):
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,          # Anthropic 必须指定
    ): ...
```

负责：
- 内部 `Message` → Anthropic 格式（system 单独传，不在 messages 中）
- 工具 Schema → Anthropic `tools` 参数格式（`input_schema` 字段名不同）
- tool_use / tool_result 的 content block 格式转换
- 流式 SSE → `AsyncIterator[StreamChunk]`

### F3.5 消息格式转换

各 Provider 的消息格式差异很大，需要双向转换器：

| 差异点 | OpenAI | Anthropic |
|---|---|---|
| System prompt | messages 中 role="system" | 独立的 `system` 参数 |
| 工具调用 | `tool_calls` 字段 | `content` 中的 `tool_use` block |
| 工具结果 | role="tool" 消息 | role="user" 中的 `tool_result` block |
| 多内容 | 不支持 | content 是 block 数组 |

```python
class MessageConverter:
    @staticmethod
    def to_openai(messages: list[Message]) -> list[dict]: ...

    @staticmethod
    def from_openai(response: dict) -> ProviderResponse: ...

    @staticmethod
    def to_anthropic(messages: list[Message]) -> tuple[str, list[dict]]: ...

    @staticmethod
    def from_anthropic(response: dict) -> ProviderResponse: ...
```

### F3.6 流式输出

Agent 的 `run` 方法新增流式变体：

```python
async def run_stream(self, input: str) -> AsyncIterator[StreamEvent]:
    """流式执行 Agent，逐步产出事件"""

class StreamEvent(BaseModel):
    type: Literal["text_delta", "tool_call", "tool_result", "done"]
    content: str | None = None
    tool_call: ToolCall | None = None
    result: AgentResult | None = None   # 仅 type="done" 时有
```

### F3.7 Provider 工厂

```python
def create_provider(model: str, **kwargs) -> BaseProvider:
    """根据模型名自动选择 Provider

    规则：
    - "gpt-*" / "o1-*" → OpenAIProvider
    - "claude-*"       → AnthropicProvider
    - 其他             → 尝试 OpenAI 兼容模式（base_url）
    """
```

Agent 使用方式：

```python
# 自动选择 Provider
agent = Agent(name="bot", instructions="...", model="claude-sonnet-4-20250514")
agent = Agent(name="bot", instructions="...", model="gpt-4o")

# 手动指定 Provider
provider = OpenAIProvider(model="deepseek-chat", base_url="https://api.deepseek.com")
agent = Agent(name="bot", instructions="...", provider=provider)
```

## 不做的事情（显式排除）

- ❌ 本地模型支持（Ollama 等）— 可通过 base_url 兼容
- ❌ 多模态（图片/音频输入）— 后续扩展
- ❌ 速率限制 / 重试 — Phase 7
- ❌ 成本追踪 — Phase 8
- ❌ Provider 级别的 Fallback — Phase 7

## 验收标准

- [ ] OpenAI Provider 正确调用 API 并返回 ProviderResponse
- [ ] Anthropic Provider 正确调用 API 并返回 ProviderResponse
- [ ] 消息格式双向转换准确无误（特别是工具调用场景）
- [ ] 流式输出逐 token 产出
- [ ] `model="gpt-4o"` 和 `model="claude-sonnet-4-20250514"` 自动路由到正确 Provider
- [ ] 同一个 Agent（不改 instructions 和 tools）切换模型后功能一致
- [ ] Provider 测试使用 Mock HTTP 响应，不依赖真实 API
- [ ] Usage（token 用量）正确统计

## 核心文件

```
src/myagent/
├── providers/
│   ├── __init__.py          # 导出 BaseProvider, create_provider
│   ├── base.py              # BaseProvider ABC + ProviderResponse
│   ├── openai.py            # OpenAIProvider
│   ├── anthropic.py         # AnthropicProvider
│   ├── converters.py        # 消息格式转换器
│   └── stream.py            # StreamChunk, StreamEvent
├── agent.py                 # 增加 run_stream(), provider 参数
└── _llm.py                  # 删除（替换为 providers/）
```

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| HTTP 客户端 | 使用官方 SDK（openai, anthropic） | 减少维护成本，流式支持成熟 |
| 流式实现 | AsyncIterator + yield | Python 原生异步生成器，最自然 |
| Provider 选择 | 模型名前缀推断 + 手动覆盖 | 简单直观，覆盖提供灵活性 |
| 先做哪两个 | OpenAI + Anthropic | 市场份额最大的两个 |

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
