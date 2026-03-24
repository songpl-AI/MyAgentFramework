# MyAgentFramework — 项目指南

> 从零构建 Agent 框架的完整旅程

---

## 项目愿景

从**最小原则**出发，一步步构建一个可用的 Agent 框架。每个阶段都是一个完整的、可运行的里程碑，同时也是一篇可发表的博客教程，让更多人能跟着这条路径学习 Agent 框架的本质。

## 核心理念

- **最小原则**：每个阶段只引入必要的复杂度，不提前过度设计
- **可运行优先**：每个阶段结束时都是一个可独立运行的版本
- **教学驱动**：代码即教程，每一步都要让读者理解"为什么"
- **渐进式复杂度**：从单 Agent 单工具 → 多 Agent 多模型的自然演进

## 技术栈

- **语言**：Python 3.11+
- **类型系统**：Pydantic v2（Schema 校验 + 结构化输出）
- **异步**：asyncio 原生
- **包管理**：uv（快速、现代）
- **测试**：pytest + pytest-asyncio
- **文档**：每阶段一篇博客（Markdown）

## 版本管理策略

- 每个阶段对应一个 **Git Tag**（如 `v0.1-agent-loop`）
- 开发在 `main` 分支线性推进
- 重大阶段可创建 **分支** 用于实验性特性
- Tag 命名规则：`v{phase}.{sub}-{feature-name}`

---

## 阶段路线图

### Phase 0 — 项目骨架 `v0.0-skeleton`

- [ ] 项目结构初始化（src/tests/docs/blog）
- [ ] uv 包管理配置
- [ ] 基础 CI（linting + type check）
- [ ] README + LICENSE
- [ ] 博客 #0：《为什么我要从零构建一个 Agent 框架》

### Phase 1 — 最小 Agent Loop `v0.1-agent-loop`

- [ ] 最简 ReAct 循环（think → act → observe → repeat）
- [ ] 单一 LLM Provider 接入（先做 OpenAI 或 Anthropic）
- [ ] 硬编码的 system prompt
- [ ] 终止条件（max_steps + 模型自主结束）
- [ ] 博客 #1：《50 行代码实现一个 Agent Loop》

### Phase 2 — Tool 系统 `v0.2-tools`

- [ ] `@tool` 装饰器：自动提取函数签名生成 JSON Schema
- [ ] 工具注册表（ToolRegistry）
- [ ] 工具执行 + 结果反馈循环
- [ ] 内置基础工具（calculator、web_search mock）
- [ ] 博客 #2：《让 Agent 拥有双手 — 构建 Tool 系统》

### Phase 3 — 多 Provider 适配 `v0.3-providers`

- [ ] Provider 抽象接口（BaseProvider）
- [ ] OpenAI Provider
- [ ] Anthropic Provider
- [ ] 统一的消息格式（内部表示 ↔ Provider 格式转换）
- [ ] 流式输出支持
- [ ] 博客 #3：《一套代码接入所有大模型》

### Phase 4 — Memory 与 State `v0.4-memory`

- [ ] 对话历史管理（滑动窗口 / Token 截断）
- [ ] 结构化 State（Pydantic Model）
- [ ] 持久化接口（内存 / SQLite）
- [ ] 博客 #4：《给 Agent 一个记忆 — State 管理的本质》

### Phase 5 — 多 Agent 编排 `v0.5-orchestration`

- [ ] Agent 间消息传递协议
- [ ] 顺序编排（Pipeline）
- [ ] 并行编排（Fan-out / Fan-in）
- [ ] 条件路由（Router Agent）
- [ ] Handoff 模式
- [ ] 博客 #5：《当一个 Agent 不够用 — 多 Agent 编排》

### Phase 6 — Guardrails 与安全 `v0.6-guardrails`

- [ ] 输入校验（Input Guardrails）
- [ ] 输出校验（Output Guardrails）
- [ ] 工具执行沙箱
- [ ] 速率限制 + 成本控制
- [ ] 博客 #6：《生产环境的 Agent 需要什么安全措施》

### Phase 7 — 可观测性 `v0.7-observability`

- [ ] Trace 系统（Span / Event）
- [ ] 成本追踪（token 使用 + API 费用）
- [ ] 结构化日志
- [ ] 可选 OpenTelemetry 导出
- [ ] 博客 #7：《Agent 出了问题怎么调试 — 可观测性实战》

### Phase 8 — MCP 协议支持 `v0.8-mcp`

- [ ] MCP Client 实现
- [ ] MCP Server 实现（将自己的工具暴露为 MCP）
- [ ] 与外部 MCP 工具集成测试
- [ ] 博客 #8：《MCP — Agent 工具的通用语言》

### Phase 9 — 生产化 `v0.9-production`

- [ ] 配置驱动的 Agent 定义（YAML/JSON）
- [ ] Checkpoint / Resume（断点恢复）
- [ ] 错误恢复策略
- [ ] 并发控制
- [ ] 博客 #9：《从玩具到生产 — Agent 框架的最后一公里》

### Phase 10 — 发布 `v1.0-release`

- [ ] API 稳定化
- [ ] 完整文档站
- [ ] PyPI 发布
- [ ] 示例集合（Cookbook）
- [ ] 博客 #10：《我们从零构建了一个 Agent 框架》

---

## 项目结构（预期）

```
MyAgentFramework/
├── CLAUDE.md              # 本文件 — 项目指南
├── README.md              # 公开说明
├── pyproject.toml         # 包配置
├── src/
│   └── myagent/
│       ├── __init__.py
│       ├── agent.py       # Agent 核心循环
│       ├── tools/         # Tool 系统
│       ├── providers/     # LLM Provider 适配
│       ├── memory/        # Memory 与 State
│       ├── orchestration/ # 多 Agent 编排
│       ├── guardrails/    # 安全与校验
│       └── tracing/       # 可观测性
├── tests/
├── docs/                  # 参考文档
│   └── agent-frameworks-comparison.md
├── blog/                  # 博客文章
│   ├── 00-why-build-agent-framework.md
│   ├── 01-minimal-agent-loop.md
│   └── ...
└── examples/              # 使用示例
```

## 编码规范

- 类型注解：所有公开 API 必须有完整类型注解
- 文档字符串：公开类和函数使用 Google 风格 docstring
- 异步优先：核心 API 提供 async 版本，sync 版本为包装
- 错误处理：自定义异常层级，不吞没错误
- 测试覆盖：每个 Phase 的核心功能必须有测试

## 博客写作规范

- 每篇博客对应一个 Phase 的完整实现
- 结构：动机 → 设计思考 → 核心代码 → 运行示例 → 总结与下一步
- 代码片段必须可直接运行（从对应 tag checkout 后）
- 面向有 Python 基础但不了解 Agent 框架的读者

## 参考资料

- [框架对比分析](docs/agent-frameworks-comparison.md)
