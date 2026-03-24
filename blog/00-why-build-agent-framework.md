# 为什么我要从零构建一个 Agent 框架

> 系列文章第 0 篇 | 对应代码 Tag: `v0.0-skeleton`
> 仓库地址：https://github.com/songpl-AI/MyAgentFramework

---

## 背景：Agent 框架已经这么多了，为什么还要自己造？

2025-2026 年，AI Agent 框架进入了爆发期。LangChain、LangGraph、CrewAI、OpenAI Agents SDK、Microsoft AutoGen、Semantic Kernel、Agno、Vercel AI SDK……市面上的选择已经多到让人眼花缭乱。

作为一个开发者，你可能已经用过其中一两个。写几行代码，调几个 API，Agent 就能跑起来。感觉很神奇。

但我发现一个问题：**大多数时候，我们只是在调 API，并不真正理解 Agent 框架在做什么。**

- Agent Loop 到底是怎么循环的？
- `@tool` 装饰器背后的 JSON Schema 是怎么生成的？
- 多个 Agent 之间是如何传递上下文和移交控制权的？
- 为什么需要 Guardrails？MCP 协议解决了什么问题？

当 Agent 行为不符合预期时，你可能会发现自己无法调试。因为你不知道框架内部发生了什么。

**这就是我决定从零构建一个 Agent 框架的原因。**

不是为了造一个更好的轮子，而是为了**理解轮子是怎么转的**。

## 我做了什么准备

在动手写代码之前，我先系统地研究了市面上 9 个主流 Agent 框架：

| 框架 | 核心特点 |
|---|---|
| LangChain | 可组合的 Runnable 管道，模型接口层 |
| LangGraph | 图驱动的状态管理，Checkpoint 断点恢复 |
| OpenAI Agents SDK | 轻量 Handoff 模式，三层 Guardrails |
| Claude Code | 单 Agent 循环 + 持久化指令（CLAUDE.md）+ Hooks |
| AutoGen | 事件驱动的多 Agent 消息传递 |
| Semantic Kernel | 企业级 Plugin 中间件，依赖注入 |
| CrewAI | 角色扮演 Agent，统一 Memory 架构 |
| Vercel AI SDK | 流式优先，React Hooks 集成 |
| Agno | 三层记忆系统，AgentOS 一键部署 |

详细的对比分析在这里：[框架对比文档](../docs/agent-frameworks-comparison.md)

### 我发现了什么

研究完这 9 个框架之后，我发现了一个很有意思的事实：**它们的底层模式是高度趋同的。**

不管框架叫什么名字，用什么语言写，它们都有这六个核心机制：

1. **Agent Loop** — 思考 → 行动 → 观察 → 循环
2. **Tool 系统** — JSON Schema 描述函数，模型决定调用
3. **Provider 抽象** — 一套接口适配多个大模型
4. **多 Agent 编排** — 本质是路由问题：下一步该谁行动？
5. **流式输出** — 不是可选项，是必选项
6. **可观测性** — 非确定性系统必须可追踪

这意味着，只要我理解并实现了这些核心机制，就等于理解了所有 Agent 框架的本质。

## 这个系列要做什么

我计划分 **10 个阶段**，从一个空目录开始，逐步构建一个功能完整的 Agent 框架。

```
Phase 0  项目骨架         ← 你在这里
Phase 1  最小 Agent Loop   ← 最核心的 50 行代码
Phase 2  Tool 系统         ← @tool 装饰器 + JSON Schema
Phase 3  多 Provider 适配  ← OpenAI + Anthropic + 流式
Phase 4  Memory 与 State   ← 对话历史 + 持久化
Phase 5  多 Agent 编排     ← Pipeline / Parallel / Router / Handoff
Phase 6  Guardrails        ← 输入/输出/工具三层防护
Phase 7  可观测性          ← Trace / Metrics / 成本追踪
Phase 8  MCP 协议          ← Agent 工具的通用标准
Phase 9  生产化            ← 配置驱动 + 断点恢复 + 错误恢复
Phase 10 发布 v1.0         ← 文档 + PyPI + 示例
```

每个阶段都遵循三个原则：

- **最小原则**：只引入必要的复杂度，不提前过度设计
- **可运行优先**：每个阶段结束时都是一个可独立运行的版本
- **教学驱动**：代码即教程，每一步都要让你理解"为什么"

## 技术选型

| 选择 | 原因 |
|---|---|
| Python 3.11+ | Agent 生态最成熟的语言；match 语法、TaskGroup 等新特性 |
| Pydantic v2 | 类型校验 + JSON Schema 生成 + 序列化，Agent 框架的基础设施 |
| asyncio | Agent 天然是 IO 密集型，异步是正确选择 |
| uv | 现代 Python 包管理器，替代 pip + venv + poetry |
| ruff | 替代 flake8 + black + isort，统一工具链 |

## Phase 0 做了什么

这一篇对应的代码是项目骨架的搭建，没有业务逻辑，但为后续所有阶段打下基础：

```
MyAgentFramework/
├── src/myagent/           # 主包（src layout，PyPI 发布标准）
│   ├── __init__.py        # 版本号
│   ├── py.typed           # PEP 561 类型标记
│   ├── tools/             # 预留的子包目录
│   ├── providers/
│   ├── memory/
│   ├── orchestration/
│   ├── guardrails/
│   ├── tracing/
│   └── mcp/
├── tests/                 # 测试
├── docs/                  # 需求文档 + 框架对比分析
├── blog/                  # 博客文章（你正在读的）
├── pyproject.toml         # 包配置 + 工具链配置
├── PROGRESS.md            # 开发进度追踪
├── CLAUDE.md              # 项目指南
└── README.md
```

验收结果：

```bash
$ uv run ruff check src/    # All checks passed!
$ uv run mypy src/           # Success: no issues found in 8 source files
$ uv run pytest -v           # 1 passed
```

一个干净的、工具链完备的起点。

## 如何跟着学

1. **Clone 仓库**：
   ```bash
   git clone https://github.com/songpl-AI/MyAgentFramework.git
   cd MyAgentFramework
   ```

2. **切到对应阶段**：
   ```bash
   git checkout v0.0-skeleton  # Phase 0
   git checkout v0.1-agent-loop  # Phase 1（待发布）
   ```

3. **阅读需求文档**：
   每个阶段都有详细的需求文档在 `docs/phases/` 目录下，包含设计思路、代码示例、验收标准。

4. **自己动手实现**：
   最好的学习方式是在看完需求文档后，先自己尝试实现，再对比我的代码。

## 下一步

Phase 1 将实现 Agent 框架的**心脏** — Agent Loop。我们会用大约 50 行核心代码实现一个最小的 ReAct 循环：

- 接收用户输入
- 调用大模型
- 解析响应，判断是否结束
- 循环或返回结果

这 50 行代码就是所有 Agent 框架最核心的部分。理解了它，你就理解了 Agent 的本质。

下一篇：《50 行代码实现一个 Agent Loop》

---

*如果这个系列对你有帮助，欢迎在 [GitHub](https://github.com/songpl-AI/MyAgentFramework) 上 Star 支持。*
