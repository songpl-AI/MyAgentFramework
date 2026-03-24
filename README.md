# MyAgentFramework

> 从零构建 Agent 框架 — 渐进式学习之旅

从**最小原则**出发，一步步构建一个可用的 Agent 框架。每个阶段都是一个完整可运行的里程碑，同时也是一篇博客教程。

## 为什么做这个项目

市面上的 Agent 框架已经很多（LangChain、LangGraph、CrewAI、OpenAI Agents SDK...），但大多数开发者只是在调 API，并不真正理解 Agent 框架的底层原理。

这个项目的目标是：**通过从零构建的过程，让你（也让我自己）真正理解 Agent 框架的每一个核心机制。**

## 阶段路线图

| Phase | 名称 | Tag | 博客 |
|---|---|---|---|
| 0 | 项目骨架 | `v0.0-skeleton` | [为什么我要从零构建一个 Agent 框架](blog/00-why-build-agent-framework.md) |
| 1 | 最小 Agent Loop | `v0.1-agent-loop` | 50 行代码实现一个 Agent Loop |
| 2 | Tool 系统 | `v0.2-tools` | 让 Agent 拥有双手 — 构建 Tool 系统 |
| 3 | 多 Provider 适配 | `v0.3-providers` | 一套代码接入所有大模型 |
| 4 | Memory 与 State | `v0.4-memory` | 给 Agent 一个记忆 — State 管理的本质 |
| 5 | 多 Agent 编排 | `v0.5-orchestration` | 当一个 Agent 不够用 — 多 Agent 编排 |
| 6 | Guardrails 与安全 | `v0.6-guardrails` | 生产环境的 Agent 需要什么安全措施 |
| 7 | 可观测性 | `v0.7-observability` | Agent 出了问题怎么调试 — 可观测性实战 |
| 8 | MCP 协议 | `v0.8-mcp` | MCP — Agent 工具的通用语言 |
| 9 | 生产化 | `v0.9-production` | 从玩具到生产 — Agent 框架的最后一公里 |
| 10 | 发布 v1.0 | `v1.0-release` | 我们从零构建了一个 Agent 框架 |

你可以 `git checkout <tag>` 切到任意阶段，查看该阶段的完整代码。

## Quick Start

```bash
# 安装
pip install myagent

# 或从源码安装
git clone https://github.com/songpl-AI/MyAgentFramework.git
cd MyAgentFramework
uv sync --all-extras --dev
```

> 完整的使用示例将在 Phase 1 完成后补充。

## 项目结构

```
src/myagent/
├── __init__.py          # 版本号、公开 API
├── agent.py             # Agent 核心循环（Phase 1）
├── tools/               # Tool 系统（Phase 2）
├── providers/           # LLM Provider 适配（Phase 3）
├── memory/              # Memory 与 State（Phase 4）
├── orchestration/       # 多 Agent 编排（Phase 5）
├── guardrails/          # 安全与校验（Phase 6）
├── tracing/             # 可观测性（Phase 7）
└── mcp/                 # MCP 协议（Phase 8）
```

## 文档

- [阶段需求文档](docs/phases/README.md) — 每个阶段的详细设计和需求
- [框架对比分析](docs/agent-frameworks-comparison.md) — 九大主流框架的对比研究
- [开发进度](PROGRESS.md) — 当前开发状态和历史记录

## License

[MIT](LICENSE)
