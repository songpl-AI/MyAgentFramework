# Phase 2 — Tool 系统

> Tag: `v0.2-tools`
> 前置依赖: Phase 1
> 博客: 《让 Agent 拥有双手 — 构建 Tool 系统》

---

## 目标

让 Agent 能**调用工具**。这是 Agent 区别于普通 Chatbot 的关键 — 不只是生成文本，还能执行动作、获取信息。实现 `@tool` 装饰器，自动生成 JSON Schema，完成"模型决定调用 → 执行 → 结果反馈"的完整闭环。

## 核心概念

```
User Input
    ↓
┌─────────────────────────────┐
│   Agent Loop (增强版)        │
│                             │
│   1. 构造 Prompt + Tools    │ ← 附带工具定义的 JSON Schema
│   2. 调用 LLM              │
│   3. 解析响应               │
│      ├─ 文本回答 → 结束     │
│      └─ 工具调用 → 步骤 4   │
│   4. 执行工具               │ ← 调用对应函数，获取结果
│   5. 将结果注入消息历史      │ ← tool result 消息
│   └── 回到步骤 2            │
└─────────────────────────────┘
    ↓
Final Response
```

## 功能需求

### F2.1 `@tool` 装饰器

```python
from myagent import tool

@tool
def calculate(expression: str) -> str:
    """计算数学表达式并返回结果。

    Args:
        expression: 要计算的数学表达式，如 "2 + 3 * 4"
    """
    return str(eval(expression))  # 示例，生产中需沙箱
```

装饰器自动完成：
- 从函数签名提取参数名、类型、默认值
- 从 docstring 提取函数描述和参数描述
- 生成符合 OpenAI function calling 规范的 JSON Schema
- 包装为 `Tool` 对象

**支持的参数类型**：
- 基础类型：`str`, `int`, `float`, `bool`
- 可选类型：`Optional[str]`（映射为非 required）
- 枚举：`Literal["a", "b", "c"]`（映射为 enum）
- 复杂类型：`Pydantic BaseModel`（映射为嵌套 object）

### F2.2 Tool 模型

```python
class Tool(BaseModel):
    name: str                          # 工具名称（函数名）
    description: str                   # 工具描述（docstring）
    parameters: dict                   # JSON Schema 格式的参数定义
    fn: Callable                       # 实际的可调用函数

    def to_schema(self) -> dict:
        """输出 OpenAI function calling 格式的 Schema"""

    async def execute(self, **kwargs) -> str:
        """执行工具，返回字符串结果"""
```

### F2.3 ToolRegistry

```python
class ToolRegistry:
    """工具注册表，管理所有可用工具"""

    def register(self, tool: Tool) -> None: ...
    def get(self, name: str) -> Tool: ...
    def list_schemas(self) -> list[dict]: ...  # 所有工具的 Schema 列表
```

### F2.4 Agent 集成

Agent 构造函数新增 `tools` 参数：

```python
agent = Agent(
    name="math_agent",
    instructions="你是一个数学助手。用 calculate 工具来计算。",
    tools=[calculate, web_search],  # 直接传入 @tool 装饰的函数
)
```

Agent Loop 增强：
1. 调用 LLM 时附带 tools schema
2. 解析响应中的 `tool_calls`
3. 执行对应工具
4. 将 `tool` role 消息（含调用结果）加入历史
5. 重新调用 LLM（模型看到工具结果后决定下一步）

### F2.5 消息模型扩展

```python
class ToolCall(BaseModel):
    id: str                # 工具调用 ID
    name: str              # 工具名称
    arguments: dict        # 解析后的参数

class ToolResult(BaseModel):
    tool_call_id: str      # 对应的调用 ID
    content: str           # 工具执行结果

# Message 扩展
class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] | None = None     # assistant 消息可能包含
    tool_call_id: str | None = None              # tool 消息需要
```

### F2.6 内置示例工具

提供 2-3 个示例工具用于测试和演示：

```python
@tool
def get_current_time() -> str:
    """获取当前时间"""

@tool
def calculate(expression: str) -> str:
    """计算数学表达式"""

@tool
def read_file(path: str) -> str:
    """读取文件内容（仅用于演示）"""
```

### F2.7 工具执行错误处理

工具执行可能失败，需要优雅处理：

```python
async def execute(self, **kwargs) -> str:
    try:
        result = self.fn(**kwargs)
        if asyncio.iscoroutine(result):
            result = await result
        return str(result)
    except Exception as e:
        return f"Tool execution error: {type(e).__name__}: {e}"
```

- 工具异常**不中断 Agent Loop**
- 错误信息作为 tool result 返回给模型
- 模型可以根据错误信息决定重试或换策略

## 不做的事情（显式排除）

- ❌ 并行工具调用 — 本阶段按顺序执行
- ❌ 工具权限控制 — Phase 6
- ❌ 工具执行沙箱 — Phase 6
- ❌ MCP 协议支持 — Phase 8
- ❌ 动态工具（运行时添加/移除）— Phase 5

## 验收标准

- [ ] `@tool` 装饰器正确生成 JSON Schema
- [ ] 支持 str/int/float/bool/Optional/Literal 参数类型
- [ ] Pydantic BaseModel 参数正确映射为嵌套 Schema
- [ ] Agent 能调用工具并获得结果
- [ ] 工具调用结果正确反馈给模型
- [ ] 模型能基于工具结果给出最终回答
- [ ] 一次 run 中能连续多次调用工具
- [ ] 工具执行异常不会中断 Agent Loop
- [ ] 单元测试：Schema 生成 + 工具执行 + 完整循环（Mock LLM）

## 测试用例

```python
# 测试 1：Schema 生成
def test_tool_schema():
    @tool
    def greet(name: str, excited: bool = False) -> str:
        """打招呼"""
    assert greet.tool.parameters == {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "excited": {"type": "boolean", "default": False}
        },
        "required": ["name"]
    }

# 测试 2：完整循环（Mock）
async def test_agent_with_tools():
    # Mock LLM 先返回 tool_call，再返回最终回答
    agent = Agent(tools=[calculate], llm=mock_llm)
    result = await agent.run("1+1等于几？")
    assert "2" in result.output
```

## 核心文件

```
src/myagent/
├── tools/
│   ├── __init__.py      # 导出 tool, Tool, ToolRegistry
│   ├── decorator.py     # @tool 装饰器实现
│   ├── schema.py        # Python 类型 → JSON Schema 转换
│   ├── registry.py      # ToolRegistry
│   └── builtins.py      # 内置示例工具
├── models.py            # 扩展 Message（+ToolCall, ToolResult）
└── agent.py             # 增强 Agent Loop 支持工具调用
```

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| Schema 生成方式 | 自己实现（基于 inspect + typing） | 学习目的；避免引入 LangChain 依赖 |
| 工具返回类型 | 统一为 str | 最简单，模型只理解文本；结构化输出是 Provider 的事 |
| 异步工具支持 | 同时支持 sync 和 async 函数 | 灵活性，自动检测 |
| 错误策略 | 错误作为结果返回给模型 | 让模型自主决策，参考 LangGraph ToolNode 模式 |

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
