# Agent 框架对比分析

> 调研时间：2026-03-24
> 目的：为构建自有商业级 Agent 框架提供参考基线

---

## 目录

- [一、框架概览](#一框架概览)
- [二、逐框架分析](#二逐框架分析)
- [三、核心维度对比矩阵](#三核心维度对比矩阵)
- [四、六大不变基石](#四六大不变基石)
- [五、各框架独特亮点](#五各框架独特亮点)
- [六、推荐架构分层](#六推荐架构分层)

---

## 一、框架概览

| 框架 | 核心范式 | 主语言 | 定位 |
|---|---|---|---|
| LangChain | 可组合 Runnable（管道操作符） | Python, JS | 模型接口 + 工具层 |
| LangGraph | 有状态图执行 | Python, JS | Agent 编排引擎 |
| Agno (原 PhiData) | 围绕模型的有状态控制循环 | Python | 端到端 Agent 平台 |
| Claude Code | 单 Agent 循环 + 丰富工具集 | TypeScript | 编码助手 / CLI Agent |
| AutoGen | 事件驱动多 Agent 消息传递 | Python, .NET | 多 Agent 对话 |
| Semantic Kernel | Kernel + Plugin 中间件 | C#, Python, Java | 企业 AI 中间件 |
| CrewAI | 角色扮演 Agent + 任务 | Python | 团队协作 Agent |
| Vercel AI SDK | 流式优先函数 SDK | TypeScript/JS | 前端 AI 集成 |
| OpenAI Agents SDK | 轻量 Agent + Handoff | Python | 轻量多 Agent |

---

## 二、逐框架分析

### 2.1 LangChain (v0.3+)

**核心抽象**

- **Runnable 接口 (LCEL)**：统一协议，提供 `invoke()` / `stream()` / `batch()` 及其异步变体
- 所有组件（模型、检索器、工具、输出解析器）都实现 Runnable，通过管道操作符 `|` 组合
- v0.3+ 简化角色：主要负责模型接口和工具层，Agent 编排交给 LangGraph

**Tool 系统**

- `@tool` 装饰器定义工具，docstring 自动变描述，类型提示生成输入 Schema
- 支持 Pydantic BaseModel 或 JSON Schema 定义复杂输入
- 通过 `.bind_tools()` 将工具绑定到模型的原生 function-calling

**Memory**

- 基础对话历史（追加到 prompt）
- 严肃的状态管理委托给 LangGraph 的 Checkpoint 系统

**多 Agent**

- 不再提供自己的多 Agent 编排，完全依赖 LangGraph

**流式**

- 三种流模式：`updates`（每步后的状态）、`messages`（逐 token）、`custom`（通过 `get_stream_writer()` 推送任意数据）
- 统一 v2 格式：每个 chunk 是 `{type, ns, data}` 字典

**错误处理**

- `.with_retry()` 自动重试
- `.with_fallbacks()` 回退链
- LangGraph 的 ToolNode 捕获工具错误并反馈给模型自修正

**可观测性**

- LangSmith 集成，所有 Runnable 自动产生 trace 事件

---

### 2.2 LangGraph

**核心抽象**

- **StateGraph**：接收用户定义的 State Schema（TypedDict / dataclass / Pydantic BaseModel），编译为可执行图
- **Nodes**：Python 函数，接收 `(state, config, runtime)`，自动包装为 RunnableLambda
- **Edges**：普通边（确定性路由）和条件边（路由函数基于状态返回目标节点名）
- **Command**：组合状态更新与控制流（`update`, `goto`, `graph`, `resume`）
- **Reducers**：注解函数控制状态更新方式（如 `Annotated[list[str], add]` 追加而非替换）
- 图必须 `.compile()` 后才能执行，编译时验证结构并附加 checkpointer

**Tool 系统**

- 继承 LangChain 的工具系统
- `ToolNode`：预构建节点，支持并行工具执行 + 错误处理 + 状态注入

**Memory / State — LangGraph 最强差异化**

- **线程级 Checkpoint**：每个 super-step 保存 StateSnapshot（值、下一节点、元数据、时间戳、父引用）
- **Checkpointer 后端**：InMemorySaver（开发）、SqliteSaver（本地）、PostgresSaver（生产）、CosmosDBSaver（Azure）
- **跨线程 Store**：InMemoryStore，命名空间组织 + 可选语义搜索
- **回放与时间旅行**：从任意 checkpoint 重新执行、分叉状态、调试特定步骤
- **Pending Writes**：失败时保留已成功节点的输出，恢复时跳过重新执行
- **加密**：EncryptedSerializer 安全状态持久化

**多 Agent**

- 子图（嵌套 StateGraph）、Supervisor 模式、Command 跨图导航
- Agent 可作为父图中的节点，条件路由在它们之间切换

**错误处理**

- 递归限制防止无限循环
- `RemainingSteps` 主动监控
- 失败的 super-step 保留 pending writes 用于恢复
- Human-in-the-loop 中断允许手动状态修正

---

### 2.3 Agno (原 PhiData)

**核心抽象**

- **Agent**：基本单元 — 初始化时指定 model、tools、instructions、configuration
- **Team**：多 Agent 协作，共享上下文
- **Workflow**：顺序编排，输出馈入后续步骤
- **AgentOS**：部署抽象，将 Agent 转为 FastAPI 应用

**Tool 系统**

- 模块化工具包（CodingTools、DuckDuckGoTools、MCPTools 等）
- 通过 `tools` 参数传入 Agent
- 原生支持 MCP 服务器工具

**Memory — 三层记忆系统**

- **Session Memory**：对话历史（`add_history_to_context=True`）
- **User Memory（长期）**：学习到的用户事实，存储在数据库中
  - 自动模式：`update_memory_on_run=True`
  - Agent 自主模式：`enable_agentic_memory=True`（Agent 自行决定何时创建/更新/删除记忆）
- **Storage 后端**：Postgres、SQLite、MongoDB 等
- 明确区分：Memory 存储学习到的事实，Session History 存储对话消息

**多 Agent**

- Teams：协作式，共享模型上下文，有 Team Leader
- Workflows：顺序式，前一步输出馈入下一步

---

### 2.4 Claude Code

**核心抽象**

- **Agentic Loop**：读取上下文 → 决定行动 → 执行工具 → 迭代直到完成
- **Tools**：文件读写、搜索（Grep/Glob）、Bash 执行、Web 获取、Notebook 编辑、Git 操作
- **CLAUDE.md**：持久化指令文件，启动时读取项目编码标准和上下文
- **Auto Memory**：跨会话自动保存学习成果
- **Skills / 自定义命令**：可打包的可重复工作流
- **Hooks**：Shell 命令在 Claude Code 行动前后执行（如编辑后自动格式化）

**Tool 系统**

- 使用 Anthropic 原生 tool-use 协议
- 模型接收 JSON Schema 工具定义，自主决定调用
- 支持多工具并行调用
- 支持 MCP 服务器工具

**Memory / State**

- CLAUDE.md：项目级持久指令
- Auto Memory：跨会话自动保存的学习成果
- Session Context：当前对话 + 完整工具调用历史
- 无跨会话状态持久化（除 CLAUDE.md 和 auto memory）

**多 Agent**

- Sub-agents：生成多个 Claude Code Agent 并行工作
- Lead Agent 协调、分派子任务、合并结果
- Agent SDK 允许构建自定义 Agent

**错误处理**

- 循环天然处理错误 — 工具失败后模型看到错误消息，修正参数重试或换方案
- 权限模型：破坏性操作需用户批准

---

### 2.5 Microsoft AutoGen

**核心抽象 — 分层架构**

- **Core 层**：事件驱动框架，Agent 间消息传递
- **AgentChat 层**（构建在 Core 上）：高层对话框架，预建 Agent 类型和 Team 模式
- **Extensions**：与外部服务接口的实现

关键原语：
- **AssistantAgent**：可配置的 Agent，含系统消息、工具、模型客户端、反思能力
- **Teams**：群聊容器，编排多个 Agent
- **Runtime**：`GrpcWorkerAgentRuntime` 用于分布式、多语言部署

**Tool 系统**

- 函数通过 `tools` 参数传入 Agent
- 支持 MCP 服务器工具（`McpWorkbench`）
- Docker 代码执行器（`DockerCommandLineCodeExecutor`）
- `reflect_on_tool_use` 参数让 Agent 对工具结果进行推理

**多 Agent — AutoGen 最强差异化**

- **RoundRobinGroupChat**：轮流发言，广播响应
- **SelectorGroupChat**：LLM 动态选择下一个发言者
- **MagenticOneGroupChat**：通用多 Agent 系统，处理复杂 Web 和文件任务
- **Swarm**：使用 HandoffMessage 显式 Agent 间转移

**终止条件**：TextMentionTermination、ExternalTermination 等，可用位运算组合

**可观测性**

- OpenTelemetry 兼容的 tracing
- 事件驱动架构天然提供 Agent 间消息的审计轨迹

---

### 2.6 Microsoft Semantic Kernel

**核心抽象**

- **Kernel**：中央编排器，持有 plugins、services、configuration
- **KernelPlugin**：暴露给 AI 的函数组，映射企业服务/API 模式，支持依赖注入
- **KernelFunction**：用 `@kernel_function`（Python）或 `[KernelFunction]`（C#）注解的函数
- **AI Services / Connectors**：标准化 LLM 供应商连接
- **ChatHistory**：对话状态对象

三种导入 Plugin 的方式：原生代码（注解类）、OpenAPI 规范、MCP Servers

**Auto Function Calling — Semantic Kernel 的定义特性**

1. 所有 `KernelFunction` 序列化为 JSON Schema
2. Schema 与聊天历史一起发送给模型
3. 模型生成函数调用；SK 将输入编组到正确类型并调用
4. 结果发回模型；循环重复直到文本响应或达到最大迭代

`FunctionChoiceBehavior` 控制策略：`.Auto()`、`.Required()`、`.None()`

**多 Agent**

- 侧重单 Agent + Plugin 编排，而非多 Agent 模式
- Kernel 可将 plugins 导出为 MCP Server 供其他 Agent 消费

**可观测性**

- 内建遥测支持
- Hooks 和 Filters 在函数调用管道的每一步提供日志、审计、安全检查

---

### 2.7 CrewAI

**核心抽象 — 角色扮演模型**

- **Flows**：结构化、事件驱动的工作流（状态持久化、条件逻辑、循环、分支）
- **Crews**：自主 Agent 团队协作

Agent 原语：
- **Role**：定义专长（如"高级研究分析师"）
- **Goal**：引导决策的个人目标
- **Backstory**：上下文和性格
- **Task**：带描述、预期输出、工具、指定 Agent 的具体任务
- **Crew**：编排 Agent 和任务的容器

**Memory — 统一 Memory 架构**

- 层级作用域（文件系统式路径：`/project/alpha`、`/agent/researcher`）
- 复合评分（语义相似度 + 时效性 + 重要性）
- LLM 驱动的分析（自动作用域推断和内容分类）
- 记忆合并防止重复
- 隐私标志：私有记忆仅源匹配时可见

**多 Agent**

- 顺序流程：任务按序执行
- 层级流程：基于 Agent 角色动态分配任务
- 委派：`allow_delegation` 让 Agent 将任务分配给同事
- 异步执行：非阻塞任务处理

---

### 2.8 Vercel AI SDK

**核心抽象 — 流式优先**

- `generateText()` / `streamText()`：文本生成
- `generateObject()` / `streamObject()`：结构化输出 + Schema 校验
- `tool()` / `dynamicTool()`：函数定义
- `embed()` / `embedMany()`：向量生成
- Provider 抽象：20+ 供应商统一代码路径

**Tool 系统**

- `tool()` 定义：名称、描述、参数（Zod / JSON Schema / Valibot）、`execute` 函数
- SDK 自动管理工具调用循环（LLM 生成调用 → 执行 → 结果反馈 → 重复直到完成或 `maxSteps`）

**流式 — Vercel AI SDK 的定义特性**

- 逐 token 流式（文本、工具结果、结构化对象）
- `useChat()` / `useCompletion()` React Hooks 实时 UI 更新
- `useObject()` 流式结构化数据
- 自定义数据负载
- `onStepFinish` 回调用于步级审查

**Memory**

- SDK 本身无状态，状态管理交给应用层（React state、数据库等）

---

### 2.9 OpenAI Agents SDK (原 Swarm)

**核心抽象 — 轻量、有主见**

- **Agent**：带 instructions、tools、handoffs 的 LLM
- **Runner**：执行引擎，管理同步运行和跨调用状态
- **Handoff**：定义模式 — Agent 像工具一样委派给其他 Agent
- **Guardrails**：输入、输出、工具三层防护
- **Tracing**：内建可观测性

**Tool 系统 — 三种工具类型**

- **Function tools**：Python 函数 + 自动 JSON Schema 生成 + Pydantic 校验
- **MCP server tools**：与 function tools 一致的集成方式
- **Agents-as-tools**：其他 Agent 可作为工具调用（与 handoff 不同：调用方保留控制权）

**Handoff 模式 — OpenAI SDK 的定义特性**

- Agent 通过 `handoffs` 参数声明 handoff 目标
- Handoff 作为工具暴露给 LLM（如 `transfer_to_refund_agent`）
- 调用时控制权完全转移给目标 Agent
- 可通过 `handoff()` 定制：工具命名、回调（`on_handoff`）、运行时启用（`is_enabled`）、输入类型 Schema

**Guardrails — 安全机制**

- **Input guardrails**：Agent 运行前校验用户输入，支持并行（默认）或阻塞执行
- **Output guardrails**：校验最终输出
- **Tool guardrails**：包装函数工具，执行前后校验
- **Tripwire 模式**：校验失败立即中止执行

**可观测性**

- 内建 tracing：捕获 LLM 生成、工具调用、handoff、guardrails、自定义事件
- Trace 含 workflow_name、trace_id、group_id
- 集成 OpenAI Traces 仪表板
- 20+ 生态合作伙伴（W&B、Arize、MLflow、LangSmith、Langfuse、PostHog）
- 敏感数据捕获可通过 `trace_include_sensitive_data` 配置

---

## 三、核心维度对比矩阵

| 维度 | LangChain | LangGraph | Agno | Claude Code | AutoGen | Semantic Kernel | CrewAI | Vercel AI SDK | OpenAI Agents SDK |
|---|---|---|---|---|---|---|---|---|---|
| **核心范式** | 可组合 Runnable | 有状态图执行 | 有状态控制循环 | 单 Agent 循环 | 事件驱动消息传递 | Kernel + Plugin | 角色扮演 + 任务 | 流式优先 SDK | 轻量 Agent + Handoff |
| **主语言** | Python, JS | Python, JS | Python | TypeScript | Python, .NET | C#, Python, Java | Python | TypeScript/JS | Python |
| **Tool 机制** | `@tool` + Pydantic + `.bind_tools()` | 继承 LangChain + ToolNode | 模块化工具包 + MCP | Anthropic tool-use + MCP | `tools` 参数 + MCP + Docker | `@kernel_function` + Plugin + OpenAPI + MCP | CrewAI 工具包 + LangChain 工具 | `tool()` + Zod/JSON Schema | Function tools + MCP + Agent-as-tool |
| **State/Memory** | 基础对话历史 | Checkpoint + Store + 加密 + 语义搜索 | 三层（会话/用户/Agent 自主） | CLAUDE.md + Auto Memory | Team 级对话状态 | ChatHistory + DI | 统一 Memory（层级 + 复合评分） | 无状态（应用层管理） | 对话历史随 Handoff 转移 |
| **多 Agent** | 委托 LangGraph | 子图 + Supervisor + Command | Teams + Workflows | Sub-agents + Lead | RoundRobin / Selector / Swarm | 单 Agent 为主 | 顺序 + 层级 + 委派 | Subagents（基础） | Handoff（P2P 或 Manager） |
| **流式** | 3 模式 | 同 LangChain | `stream=True` | 逐 token + 工具进度 | `run_stream()` | 流式补全 | 支持 + verbose | **定义特性** | `run_stream()` |
| **错误处理** | `.with_retry()` + `.with_fallbacks()` | 递归限制 + pending writes + 恢复 | 模型循环重试 | 模型看到错误自修正 | 终止条件 + 外部关停 | 最大迭代 + hooks/filters | `max_iter` + guardrails | `maxSteps` | Guardrails + Tripwire |
| **可观测性** | LangSmith | LangSmith | AgentOS | Verbose + Git 审计 | OpenTelemetry | 遥测 + Hooks | Verbose + Callbacks | DevTools + `onStepFinish` | 内建 Tracing + 20+ 集成 |

---

## 四、六大不变基石

以下模式在**所有九个框架中都以某种形式存在**，是构建 Agent 框架的必选项。

### 基石 1：Agent Loop（代理循环）

```
Prompt → Model 决策 → 执行 Action → 结果反馈 → 重复
```

- 每个框架都是这个循环的变体
- 差异在于循环结构：显式图（LangGraph）、隐式循环（OpenAI SDK）、紧密单循环（Claude Code）
- **必须实现**：可配置的 ReAct 循环，支持最大步数限制、中止条件、流式输出

### 基石 2：Tool 系统

- 所有框架收敛到 **JSON Schema 描述函数 → 模型决定调用** 的模式
- **MCP 协议**正在成为通用工具标准（6/9 框架已支持）
- **必须实现**：`@tool` 装饰器 + Schema 自动生成 + MCP 兼容

### 基石 3：Provider 抽象层

- 所有框架都提供多 LLM 供应商的统一接口
- **必须实现**：统一 LLM 接口，切换 OpenAI/Anthropic/本地模型零改动

### 基石 4：多 Agent 编排 = 路由问题

无论叫什么名字，本质都是 **"当前状态下，下一个该谁行动？"**

| 路由机制 | 代表框架 |
|---|---|
| 条件边 / 图路由 | LangGraph |
| LLM 选择发言者 | AutoGen (SelectorGroupChat) |
| Handoff（移交控制权） | OpenAI Agents SDK |
| 层级委派 | CrewAI |
| Lead Agent 分派 | Claude Code |

- **必须实现**：顺序、并行、条件路由 三种基础编排模式

### 基石 5：流式输出

- 不是可选项，是必须项
- 趋势：从逐 token 流 → 结构化流（工具调用结果、状态更新、自定义事件都流出来）
- **必须实现**：从 Day 1 设计为流式原生

### 基石 6：可观测性

- 每次 LLM 调用、工具调用、Agent 切换都需要有记录
- 两个方向：自建 Tracing（OpenAI SDK）或集成标准（AutoGen 用 OpenTelemetry）
- **必须实现**：Trace 链路 + 成本追踪

---

## 五、各框架独特亮点

值得深入借鉴的差异化设计：

| 框架 | 独特亮点 | 借鉴价值 |
|---|---|---|
| **LangGraph** | 图编排 + Checkpoint（断点恢复、时间旅行、状态加密） | State 管理的黄金标准 |
| **OpenAI Agents SDK** | Handoff 模式 + Guardrails（输入/输出/工具三层防护 + Tripwire） | 安全机制设计 |
| **Claude Code** | CLAUDE.md 持久指令 + Auto Memory + Hooks 系统 | 持久化上下文 + 可扩展性 |
| **Semantic Kernel** | Plugin = 企业 API 自然映射 + 依赖注入 + FunctionChoiceBehavior | 企业集成友好 |
| **CrewAI** | 角色扮演 + 统一 Memory（层级作用域 + 复合评分 + 隐私标志） | Memory 架构 |
| **Vercel AI SDK** | `streamText()` / `useChat()` React Hooks + 结构化输出流 | 前端 DX 极致体验 |
| **Agno** | 三层 Memory（会话/用户/Agent 自主记忆）+ AgentOS 一键部署 | 端到端方案 |
| **AutoGen** | 多种 Team 模式（RoundRobin/Selector/MagneticOne/Swarm） | 多 Agent 编排多样性 |
| **LangChain** | Runnable 统一接口 + LCEL 管道组合 | 组合性设计 |

---

## 六、推荐架构分层

基于以上分析，自有框架的最小可行架构应包含 5 层：

```
┌──────────────────────────────────────────────┐
│            Orchestration Layer                │
│  顺序 / 并行 / 条件路由 / Handoff / 子图      │
├──────────────────────────────────────────────┤
│            Agent Core Layer                  │
│  Agent Loop + Instructions + Memory + State  │
├──────────────────────────────────────────────┤
│            Tool Layer                        │
│  @tool + MCP + Guardrails + Agent-as-Tool    │
├──────────────────────────────────────────────┤
│            Model Adapter Layer               │
│  多 Provider 统一接口 + 流式 + 结构化输出      │
├──────────────────────────────────────────────┤
│            Infrastructure Layer              │
│  Streaming / Tracing / State 持久化 / 安全    │
└──────────────────────────────────────────────┘
```

### 差异化方向（四选一深耕）

1. **极致开发者体验** — 像 Vercel AI SDK 般简洁，但完整支持 Python 生态
2. **生产安全** — Guardrails + Checkpoint + 可观测做到极致
3. **行业垂直** — 针对金融/医疗/法律等特定场景深度优化
4. **混合编排** — 结合 LangGraph 的图 + OpenAI 的 Handoff，做更灵活的编排引擎

---

## 附录：适用场景速查

| 如果你需要... | 推荐参考 |
|---|---|
| 最大程度控制 Agent 流程 + 持久化和回放 | LangGraph |
| 企业中间件 + C#/Java 生态 | Semantic Kernel |
| 快速原型 + 丰富模型集成 | LangChain + LangGraph |
| 角色化团队协作 + 内建 Memory | CrewAI |
| 轻量多 Agent + Handoff 模式 | OpenAI Agents SDK |
| 复杂多 Agent 对话 + 动态路由 | AutoGen |
| 流式优先 TypeScript/React 应用 | Vercel AI SDK |
| 生产部署 + 内建基础设施 | Agno (AgentOS) |
| Agent 编码助手 / CLI 自动化 | Claude Code |
