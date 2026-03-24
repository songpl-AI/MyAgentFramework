# Phase 11 — A2A 协议（Agent-to-Agent）

> Tag: `v0.11-a2a`
> 前置依赖: Phase 10
> 博客: 《A2A — 让不同框架的 Agent 互相协作》

---

## 目标

支持 **Google A2A（Agent-to-Agent）协议**，让我们的 Agent 能够与其他框架构建的 Agent 发现彼此、通信和协作。A2A 与 MCP 互补：MCP 解决 Agent→Tool 的连接，A2A 解决 Agent→Agent 的连接。

核心问题：如何让不同框架、不同公司、不同服务器上的 Agent 像同事一样协作？

## 核心概念

```
A2A 协议的核心模型：

              发现                      协作
Client Agent ──────→ Agent Card ──────→ Remote Agent
     │                 │                    │
     │   "你能做什么？"  │  JSON 能力描述     │  "帮我分析这份数据"
     │                 │                    │
     └─── JSON-RPC 2.0 over HTTP(S) ───────┘

关键概念：
┌──────────────┐
│  Agent Card  │  Agent 的"名片"— 描述能力、端点、认证方式
├──────────────┤
│    Task      │  一次协作的完整生命周期（提交→处理→完成）
├──────────────┤
│   Message    │  Task 中的单条消息（支持多模态 Part）
├──────────────┤
│   Artifact   │  Task 的输出产物（文件、数据等）
└──────────────┘

MCP vs A2A 的边界：
┌─────────────────────────────────────────┐
│  MCP:  Agent ←→ Tool/Data Source        │
│        Agent 调用工具，获取数据           │
│        Agent 知道工具的内部细节          │
├─────────────────────────────────────────┤
│  A2A:  Agent ←→ Agent                   │
│        Agent 之间协作，互不透明          │
│        不暴露内部状态、记忆、工具        │
└─────────────────────────────────────────┘
```

## 功能需求

### F11.1 Agent Card（能力声明）

```python
class AgentCard(BaseModel):
    """Agent 的能力名片，符合 A2A 规范"""
    name: str                               # Agent 名称
    description: str                        # Agent 能力描述
    url: str                                # Agent 的 HTTP 端点
    version: str = "1.0"                    # A2A 协议版本
    capabilities: AgentCapabilities = ...   # 支持的能力
    skills: list[AgentSkillInfo] = []       # Agent 擅长的技能列表
    authentication: AuthInfo | None = None  # 认证方式

class AgentCapabilities(BaseModel):
    streaming: bool = False                 # 是否支持流式
    push_notifications: bool = False        # 是否支持异步推送

class AgentSkillInfo(BaseModel):
    """A2A 中的 Skill 描述（注意：与 Agent Skills 格式不同）"""
    id: str
    name: str
    description: str
    tags: list[str] = []
```

### F11.2 A2A Client（调用远程 Agent）

```python
class A2AClient:
    """A2A 协议客户端 — 发现和调用远程 Agent"""

    async def discover(self, url: str) -> AgentCard:
        """获取远程 Agent 的 Agent Card"""
        # GET {url}/.well-known/agent.json

    async def send_task(self, agent_url: str, task: TaskRequest) -> TaskResponse:
        """向远程 Agent 提交任务"""
        # POST {url}/tasks/send — JSON-RPC 2.0

    async def get_task(self, agent_url: str, task_id: str) -> TaskResponse:
        """查询任务状态"""

    async def cancel_task(self, agent_url: str, task_id: str) -> None:
        """取消任务"""
```

### F11.3 A2A Server（暴露为远程 Agent）

```python
class A2AServer:
    """将本地 Agent 暴露为 A2A 兼容的远程服务"""

    def __init__(self, agent: Agent, card: AgentCard) -> None: ...

    async def handle_discover(self) -> AgentCard:
        """处理 Agent Card 发现请求"""

    async def handle_send_task(self, request: TaskRequest) -> TaskResponse:
        """处理任务提交：将 A2A 消息转换为 Agent.run() 调用"""

    def serve(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """启动 HTTP 服务器"""
```

### F11.4 Task 模型（协作生命周期）

```python
class TaskState(str, Enum):
    SUBMITTED = "submitted"     # 已提交
    WORKING = "working"         # 处理中
    INPUT_REQUIRED = "input-required"  # 需要更多输入
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"           # 失败
    CANCELED = "canceled"       # 已取消

class TaskRequest(BaseModel):
    id: str
    messages: list[A2AMessage]
    metadata: dict[str, Any] = {}

class TaskResponse(BaseModel):
    id: str
    state: TaskState
    messages: list[A2AMessage] = []
    artifacts: list[Artifact] = []

class A2AMessage(BaseModel):
    role: Literal["user", "agent"]
    parts: list[Part]                   # 支持多模态

class Part(BaseModel):
    """消息的一个部分（文本、文件等）"""
    type: Literal["text", "file", "data"]
    content: str | bytes | dict
```

### F11.5 Agent 集成

```python
# 作为 Client — 调用远程 Agent
agent = Agent(
    name="coordinator",
    instructions="你是一个协调者，可以委托任务给专家 Agent。",
    remote_agents=[                         # A2A 远程 Agent 列表
        "https://data-analyst.example.com",
        "https://code-reviewer.example.com",
    ],
)

# 作为 Server — 暴露自己
agent = Agent(name="data_analyst", instructions="...")
server = A2AServer(agent, card=AgentCard(
    name="data-analyst",
    description="Analyzes datasets and generates insights.",
    url="https://data-analyst.example.com",
))
server.serve(port=8000)
```

## 不做的事情（显式排除）

- ❌ Push Notification（异步回调）— 复杂度高，先做同步+流式
- ❌ 多模态消息（图片、音频）— Phase 1 只做文本
- ❌ Agent 市场 / 注册中心 — 先做点对点发现
- ❌ 复杂认证（OAuth、mTLS）— 先做 API Key 基础认证
- ❌ ACP 协议兼容 — ACP 已合并入 A2A，无需单独支持

## 验收标准

- [ ] AgentCard 正确序列化/反序列化为 JSON
- [ ] A2AClient.discover() 正确获取远程 Agent Card
- [ ] A2AClient.send_task() 正确提交任务并获取结果
- [ ] A2AServer 正确处理 discover 和 send_task 请求
- [ ] Agent 内部消息格式与 A2A 消息格式正确互转
- [ ] Task 状态机正确流转（submitted → working → completed/failed）
- [ ] 两个本地 Agent 通过 A2A 协议成功协作（集成测试）
- [ ] 可用 Mock HTTP 服务器进行单元测试

## 核心文件

```
src/myagent/
├── a2a/
│   ├── __init__.py          # 导出 A2AClient, A2AServer, AgentCard
│   ├── models.py            # AgentCard, Task, A2AMessage, Part, Artifact
│   ├── client.py            # A2AClient
│   ├── server.py            # A2AServer
│   └── converter.py         # 内部 Message ↔ A2A Message 转换
├── agent.py                 # 增加 remote_agents 支持
```

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 传输协议 | JSON-RPC 2.0 over HTTP | A2A 规范要求 |
| HTTP 框架 | 轻量级（starlette 或 httpx） | 不引入 FastAPI 等重框架 |
| Agent Card 路径 | `/.well-known/agent.json` | A2A 规范的发现约定 |
| 初始交互模式 | 同步 + 流式 | 先不做 Push Notification |

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
| A2A 官方文档 | 协议规范和概念介绍 | https://github.com/google/A2A |
| A2A and MCP | A2A 与 MCP 的关系说明 | https://google.github.io/A2A/topics/a2a-and-mcp |
| ACP 迁移指南 | ACP → A2A 合并说明 | https://agentcommunicationprotocol.dev |

### 开源代码
| 参考内容 | 框架 | 链接 |
|---|---|---|
| A2A 协议规范 | Google A2A | https://github.com/google/A2A/blob/main/specification.md |
| A2A Python SDK | Google A2A | https://github.com/google/A2A/tree/main/samples/python |

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
