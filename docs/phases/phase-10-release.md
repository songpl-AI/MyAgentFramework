# Phase 10 — 发布 v1.0

> Tag: `v1.0-release`
> 前置依赖: Phase 9
> 博客: 《我们构建了一个商业级 Agent 框架》

---

## 目标

将框架打磨为**可发布的开源产品**。API 稳定化、完整文档、PyPI 发布、示例集合。这不是新功能开发，而是将已有功能抛光到可以让陌生人直接上手使用的程度。

## 功能需求

### F10.1 API 稳定化与审查

- 审查所有公开 API，确保命名一致性
- 标记实验性 API（`@experimental` 装饰器）
- 确定 deprecation 策略
- 编写 CHANGELOG.md（从 Phase 0 到 Phase 9 的变更记录）
- 语义化版本号：v1.0.0

**公开 API 表面检查清单**：

| 模块 | 核心导出 |
|---|---|
| `myagent` | `Agent`, `AgentResult`, `tool` |
| `myagent.tools` | `Tool`, `ToolRegistry`, `tool` |
| `myagent.providers` | `BaseProvider`, `OpenAIProvider`, `AnthropicProvider`, `create_provider` |
| `myagent.memory` | `WorkingMemory`, `TokenLimitMemory`, `StateStore`, `SQLiteStore` |
| `myagent.orchestration` | `Pipeline`, `Parallel`, `Router`, `handoff` |
| `myagent.guardrails` | `InputGuardrail`, `OutputGuardrail`, `ToolGuardrail` |
| `myagent.tracing` | `Tracer`, `Trace`, `Span`, `ConsoleExporter` |
| `myagent.mcp` | `MCPClient`, `MCPServer` |
| `myagent.config` | `AgentConfig` |

### F10.2 文档站

使用 MkDocs + Material 主题构建文档站：

```
docs-site/
├── index.md                 # 首页
├── getting-started/
│   ├── installation.md      # 安装指南
│   ├── quickstart.md        # 5 分钟快速上手
│   └── concepts.md          # 核心概念
├── guides/
│   ├── agent-loop.md        # Agent Loop 详解
│   ├── tools.md             # Tool 系统
│   ├── providers.md         # 多 Provider
│   ├── memory.md            # Memory 与 State
│   ├── orchestration.md     # 多 Agent 编排
│   ├── guardrails.md        # 安全防护
│   ├── observability.md     # 可观测性
│   └── mcp.md               # MCP 协议
├── api-reference/           # 自动生成的 API 文档
├── examples/                # 示例索引
└── blog/                    # 博客系列链接
```

### F10.3 示例集合 (Cookbook)

```
examples/
├── 01-basic-agent/           # 最简 Agent
├── 02-tool-usage/            # 使用工具
├── 03-multi-provider/        # 切换模型
├── 04-conversation/          # 多轮对话 + Memory
├── 05-pipeline/              # 顺序编排
├── 06-parallel-analysis/     # 并行分析
├── 07-customer-support/      # 客服路由 + Handoff
├── 08-safe-agent/            # Guardrails 完整示例
├── 09-mcp-integration/       # MCP 集成
├── 10-production-config/     # 生产配置示例
└── README.md                 # 示例索引
```

每个示例包含：
- `README.md`：场景说明 + 运行方法
- `main.py`：完整可运行代码
- `requirements.txt` 或 `pyproject.toml`（如需额外依赖）

### F10.4 PyPI 发布

```toml
# pyproject.toml 完善
[project]
name = "myagent"
version = "1.0.0"
description = "A commercial-grade Agent framework built from first principles"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.11"
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]

[project.optional-dependencies]
openai = ["openai>=1.0"]
anthropic = ["anthropic>=0.30"]
all = ["myagent[openai,anthropic]"]

[project.urls]
Homepage = "https://github.com/songpl-AI/MyAgentFramework"
Documentation = "https://songpl-AI.github.io/MyAgentFramework"
```

发布流程：
1. `uv build` — 构建 wheel 和 sdist
2. `uv publish` — 发布到 PyPI
3. GitHub Release — 创建 v1.0.0 Release

### F10.5 CI/CD 完善

```yaml
# .github/workflows/ci.yml
# 已有基础上增加：
- 多 Python 版本测试（3.11, 3.12, 3.13）
- 自动发布到 PyPI（tag 触发）
- 自动构建文档站
- 自动生成 CHANGELOG
```

### F10.6 README.md 完善

最终版 README 结构：
- 一句话介绍 + 徽章（PyPI version, Python version, License, CI status）
- 特性列表（带 emoji 的核心功能）
- Quick Start（3 个代码片段：基础 Agent → 带工具 → 多 Agent）
- 安装指南
- 架构图
- 博客系列链接
- Contributing 指南
- License

## 验收标准

- [ ] 所有公开 API 命名一致、类型注解完整
- [ ] `pip install myagent` 可以正常安装
- [ ] Quick Start 示例可以直接运行
- [ ] 文档站可以正常访问
- [ ] 10 个示例全部可运行
- [ ] CI 在 Python 3.11/3.12/3.13 全部通过
- [ ] CHANGELOG 记录完整
- [ ] GitHub Release 创建成功
- [ ] 博客系列 10 篇全部完成

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 文档工具 | MkDocs + Material | Python 生态标准，美观 |
| API 文档 | mkdocstrings | 自动从 docstring 生成 |
| 发布工具 | uv build + uv publish | 统一工具链 |
| CI | GitHub Actions | 仓库已在 GitHub |
