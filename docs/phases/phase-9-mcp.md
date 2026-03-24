# Phase 9 — MCP 协议支持

> Tag: `v0.9-mcp`
> 前置依赖: Phase 8
> 博客: 《MCP — Agent 工具的通用语言》

---

## 目标

接入 **Model Context Protocol (MCP)** — Anthropic 发起的开放标准，正在成为 Agent 工具调用的通用协议。实现 MCP Client（消费外部 MCP Server 的工具）和 MCP Server（将自己的工具暴露为 MCP 服务）。

## 核心概念

```
MCP 架构：

┌───────────┐    MCP Protocol    ┌───────────┐
│  MCP Host │ ←──────────────── │ MCP Server│
│ (我们的    │    JSON-RPC 2.0   │ (外部工具  │
│  Agent)   │ ──────────────→  │  提供方)   │
└───────────┘                   └───────────┘

双向角色：
1. 作为 MCP Client：调用外部 MCP Server 的工具（如 Figma、GitHub、数据库）
2. 作为 MCP Server：将自己的 @tool 暴露给其他 MCP Client（如 Claude Code、Cursor）
```

## 功能需求

### F8.1 MCP Client — 连接外部工具

```python
from myagent import Agent
from myagent.mcp import MCPClient

# 通过 stdio 连接本地 MCP Server
github_tools = MCPClient(
    command="npx",
    args=["-y", "@modelcontextprotocol/server-github"],
    env={"GITHUB_TOKEN": "..."},
)

# 通过 SSE 连接远程 MCP Server
db_tools = MCPClient(
    url="http://localhost:8080/mcp",
    transport="sse",
)

agent = Agent(
    name="dev_agent",
    instructions="...",
    mcp_clients=[github_tools, db_tools],  # MCP 工具自动注册
)
```

### F8.2 MCPClient 实现

```python
class MCPClient:
    """MCP Client — 连接并消费 MCP Server"""

    def __init__(
        self,
        # stdio 模式
        command: str | None = None,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        # SSE/HTTP 模式
        url: str | None = None,
        transport: Literal["stdio", "sse"] = "stdio",
    ): ...

    async def connect(self) -> None:
        """建立与 MCP Server 的连接"""

    async def list_tools(self) -> list[Tool]:
        """获取 Server 提供的工具列表，转为内部 Tool 格式"""

    async def call_tool(self, name: str, arguments: dict) -> str:
        """调用 Server 的工具"""

    async def list_resources(self) -> list[MCPResource]:
        """获取 Server 提供的资源列表"""

    async def read_resource(self, uri: str) -> str:
        """读取 Server 的资源"""

    async def disconnect(self) -> None:
        """关闭连接"""
```

MCP 工具 → 内部 Tool 的自动转换：
- MCP `tools/list` 返回的 `inputSchema` → 内部 `Tool.parameters`
- MCP tool 的 `name` 和 `description` 直接映射
- 调用时通过 `tools/call` JSON-RPC 方法执行

### F8.3 MCP Server — 暴露自己的工具

```python
from myagent.mcp import MCPServer

server = MCPServer(
    name="my-agent-tools",
    version="1.0.0",
)

# 注册 @tool 装饰的函数为 MCP 工具
server.register_tool(calculate)
server.register_tool(web_search)

# 也可以注册整个 Agent 的工具
server.register_agent_tools(my_agent)

# 启动 stdio 模式
server.run_stdio()

# 或启动 SSE 模式
server.run_sse(host="0.0.0.0", port=8080)
```

### F8.4 MCPServer 实现

```python
class MCPServer:
    """MCP Server — 将工具暴露为 MCP 服务"""

    def __init__(self, name: str, version: str = "1.0.0"): ...

    def register_tool(self, tool: Tool | Callable) -> None:
        """注册工具"""

    def register_agent_tools(self, agent: Agent) -> None:
        """注册 Agent 的所有工具"""

    async def handle_request(self, request: dict) -> dict:
        """处理 JSON-RPC 2.0 请求"""
        # initialize → 返回 capabilities
        # tools/list → 返回工具列表
        # tools/call → 执行工具并返回结果

    def run_stdio(self) -> None:
        """以 stdio 模式运行（stdin/stdout JSON-RPC）"""

    def run_sse(self, host: str = "localhost", port: int = 8080) -> None:
        """以 SSE 模式运行（HTTP Server-Sent Events）"""
```

### F8.5 MCP 资源支持

```python
class MCPResource(BaseModel):
    uri: str                    # 资源 URI（如 "file:///path/to/doc"）
    name: str                   # 显示名称
    description: str | None     # 描述
    mime_type: str | None       # MIME 类型
```

Agent 可以通过 MCP Client 读取外部资源并注入到上下文中。

### F8.6 Agent 集成

MCP Client 的工具透明地融入 Agent 的 Tool 系统：

```python
# Agent 看不到 MCP 和本地 Tool 的区别
agent = Agent(
    tools=[calculate],                    # 本地工具
    mcp_clients=[github_tools, db_tools], # MCP 工具
)
# 所有工具统一呈现给 LLM，调用路径自动路由
```

## 不做的事情（显式排除）

- ❌ MCP Prompts 资源类型 — 仅实现 Tools 和 Resources
- ❌ MCP Sampling — 让 Server 调用 Client 的 LLM（复杂度高）
- ❌ 自定义传输协议 — 仅 stdio 和 SSE
- ❌ MCP Server 鉴权 — 后续扩展

## 验收标准

- [ ] MCPClient 能通过 stdio 连接本地 MCP Server
- [ ] MCPClient 能通过 SSE 连接远程 MCP Server
- [ ] MCP 工具正确转换为内部 Tool 格式
- [ ] Agent 能透明地调用 MCP 工具
- [ ] MCPServer 正确响应 initialize / tools/list / tools/call
- [ ] MCPServer stdio 模式可被 Claude Code 连接
- [ ] 多个 MCP Client 同时使用不冲突
- [ ] 连接断开时优雅处理（不崩溃，给出错误信息）
- [ ] MCP 工具调用在 Trace 中有对应的 Span

## 核心文件

```
src/myagent/
├── mcp/
│   ├── __init__.py          # 导出 MCPClient, MCPServer
│   ├── client.py            # MCPClient 实现
│   ├── server.py            # MCPServer 实现
│   ├── transport/
│   │   ├── stdio.py         # stdio 传输层
│   │   └── sse.py           # SSE 传输层
│   ├── protocol.py          # JSON-RPC 2.0 消息模型
│   └── converter.py         # MCP Schema ↔ 内部 Tool 转换
└── agent.py                 # 增加 mcp_clients 参数
```

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| MCP SDK | 自己实现核心协议 | 学习目的；MCP 协议本身不复杂（JSON-RPC 2.0）|
| SSE 服务器 | starlette / uvicorn | 轻量，异步原生 |
| stdio 通信 | asyncio.subprocess | 标准库，无额外依赖 |
| 工具集成方式 | 透明融入 ToolRegistry | 对 Agent 和 LLM 完全透明 |

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
