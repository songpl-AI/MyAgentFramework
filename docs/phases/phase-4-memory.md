# Phase 4 — Memory 与 State

> Tag: `v0.4-memory`
> 前置依赖: Phase 3
> 博客: 《给 Agent 一个记忆 — State 管理的本质》

---

## 目标

让 Agent 拥有**记忆能力**。解决两个核心问题：
1. **对话历史管理**：当对话超过上下文窗口时如何处理？
2. **状态持久化**：Agent 重启后能否恢复之前的状态？

## 核心概念

```
Memory 系统三层架构：

┌─────────────────────┐
│   Working Memory    │  ← 当前对话历史（短期）
├─────────────────────┤
│   Session Store     │  ← 单次会话的完整状态（中期）
├─────────────────────┤
│   Persistent Store  │  ← 跨会话持久化（长期）
└─────────────────────┘
```

## 功能需求

### F4.1 Working Memory（对话历史管理）

当前对话历史可能超出模型上下文窗口，需要策略来管理：

```python
class WorkingMemory(ABC):
    """对话历史管理策略"""

    @abstractmethod
    def apply(self, messages: list[Message], max_tokens: int) -> list[Message]:
        """将消息列表裁剪到 max_tokens 以内"""
```

提供三种内置策略：

| 策略 | 说明 | 适用场景 |
|---|---|---|
| `SlidingWindowMemory` | 保留最近 N 条消息 | 简单对话 |
| `TokenLimitMemory` | 按 token 数截断，保留 system + 最近消息 | 通用 |
| `SummaryMemory` | 超出限制时用 LLM 总结旧消息 | 长对话 |

```python
# SlidingWindowMemory
class SlidingWindowMemory(WorkingMemory):
    def __init__(self, max_messages: int = 20): ...

# TokenLimitMemory
class TokenLimitMemory(WorkingMemory):
    def __init__(self, max_tokens: int = 8000): ...
    # 始终保留: system prompt + 最近的消息
    # 截断方向: 从最旧的非 system 消息开始

# SummaryMemory
class SummaryMemory(WorkingMemory):
    def __init__(self, max_tokens: int = 8000, summary_provider: BaseProvider): ...
    # 当超出限制时，将前半部分消息用 LLM 总结为一条 system 消息
```

### F4.2 Session State（会话状态）

每次 `agent.run()` 的完整执行状态，支持检查和恢复：

```python
class SessionState(BaseModel):
    session_id: str                   # 唯一标识
    agent_name: str                   # Agent 名称
    messages: list[Message]           # 完整消息历史
    steps: list[StepResult]           # 执行步骤记录
    metadata: dict[str, Any] = {}     # 自定义元数据
    created_at: datetime
    updated_at: datetime
    status: Literal["running", "completed", "failed"]
```

### F4.3 State Store 接口

```python
class StateStore(ABC):
    """状态持久化的抽象接口"""

    @abstractmethod
    async def save(self, state: SessionState) -> None: ...

    @abstractmethod
    async def load(self, session_id: str) -> SessionState | None: ...

    @abstractmethod
    async def list_sessions(
        self, agent_name: str | None = None, limit: int = 10
    ) -> list[SessionState]: ...

    @abstractmethod
    async def delete(self, session_id: str) -> None: ...
```

### F4.4 内置 Store 实现

```python
# 开发用 — 内存存储
class InMemoryStore(StateStore):
    """进程内字典存储，重启即失"""

# 本地持久化 — SQLite 存储
class SQLiteStore(StateStore):
    """基于 SQLite 的本地持久化"""
    def __init__(self, db_path: str = "agent_state.db"): ...
```

SQLite 表结构：
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    agent_name TEXT NOT NULL,
    state_json TEXT NOT NULL,        -- SessionState 序列化
    status TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
CREATE INDEX idx_agent_name ON sessions(agent_name);
CREATE INDEX idx_updated_at ON sessions(updated_at);
```

### F4.5 Agent 集成

Agent 新增 memory 和 store 配置：

```python
agent = Agent(
    name="assistant",
    instructions="...",
    memory=TokenLimitMemory(max_tokens=8000),   # 对话历史管理
    store=SQLiteStore("my_agent.db"),            # 状态持久化
)

# 新会话
result = await agent.run("你好")
print(result.session_id)  # "sess_abc123"

# 继续已有会话
result = await agent.run("刚才说了什么？", session_id="sess_abc123")
```

### F4.6 Token 计数

精确的 token 计数对于 Memory 管理至关重要：

```python
class TokenCounter:
    """Token 计数器"""

    def count(self, text: str, model: str = "gpt-4o") -> int:
        """计算文本的 token 数"""

    def count_messages(self, messages: list[Message], model: str = "gpt-4o") -> int:
        """计算消息列表的总 token 数（含格式 overhead）"""
```

- OpenAI 模型：使用 `tiktoken`
- Anthropic 模型：使用近似估算（字符数 / 4）或 Anthropic 的 token counting API

## 不做的事情（显式排除）

- ❌ 向量存储 / RAG — 独立的扩展功能
- ❌ 跨 Agent 共享 Memory — Phase 5
- ❌ Agent 自主记忆管理（像 Agno 那样）— 后续扩展
- ❌ 加密存储 — Phase 9
- ❌ 分布式存储（Redis / Postgres）— Phase 9

## 验收标准

- [ ] SlidingWindowMemory 正确保留最近 N 条消息
- [ ] TokenLimitMemory 按 token 限制截断，始终保留 system prompt
- [ ] SummaryMemory 在超出限制时正确总结（Mock LLM 测试）
- [ ] SessionState 正确序列化/反序列化
- [ ] InMemoryStore CRUD 操作正确
- [ ] SQLiteStore CRUD 操作正确，重启后数据保留
- [ ] Agent 能恢复已有 session 继续对话
- [ ] 恢复的对话上下文连贯（模型能引用之前的内容）
- [ ] Token 计数误差在 5% 以内

## 核心文件

```
src/myagent/
├── memory/
│   ├── __init__.py          # 导出 WorkingMemory, StateStore
│   ├── working.py           # SlidingWindow, TokenLimit, Summary
│   ├── state.py             # SessionState 模型
│   ├── store.py             # StateStore ABC
│   ├── in_memory.py         # InMemoryStore
│   ├── sqlite.py            # SQLiteStore
│   └── tokens.py            # TokenCounter
├── agent.py                 # 增加 memory, store, session_id 支持
└── models.py                # SessionState 如果放这里
```

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| Token 计数库 | tiktoken（OpenAI）+ 近似（其他） | tiktoken 精确且快，其他模型无公开 tokenizer |
| 持久化格式 | JSON 序列化存 SQLite | 简单，可读，调试方便 |
| Session ID | UUID v4 | 全局唯一，无需协调 |
| 默认 Memory | TokenLimitMemory(8000) | 对大多数场景够用的安全默认值 |

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
