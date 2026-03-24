# 开发阶段需求文档总览

> 从零构建 Agent 框架 — 详细需求与设计文档

---

## 阶段总览

| Phase | 名称 | Tag | 核心交付 | 博客 |
|---|---|---|---|---|
| [Phase 0](phase-0-skeleton.md) | 项目骨架 | `v0.0-skeleton` | 项目结构、工具链、CI | 《为什么我要从零构建一个 Agent 框架》 |
| [Phase 1](phase-1-agent-loop.md) | 最小 Agent Loop | `v0.1-agent-loop` | ReAct 循环、终止条件 | 《50 行代码实现一个 Agent Loop》 |
| [Phase 2](phase-2-tools.md) | Tool 系统 | `v0.2-tools` | @tool 装饰器、Schema 生成、工具执行闭环 | 《让 Agent 拥有双手 — 构建 Tool 系统》 |
| [Phase 3](phase-3-providers.md) | 多 Provider 适配 | `v0.3-providers` | OpenAI/Anthropic 适配、流式输出 | 《一套代码接入所有大模型》 |
| [Phase 4](phase-4-memory.md) | Memory 与 State | `v0.4-memory` | 对话历史管理、状态持久化 | 《给 Agent 一个记忆 — State 管理的本质》 |
| [Phase 5](phase-5-orchestration.md) | 多 Agent 编排 | `v0.5-orchestration` | Pipeline/Parallel/Router/Handoff | 《当一个 Agent 不够用 — 多 Agent 编排》 |
| [Phase 6](phase-6-guardrails.md) | Guardrails 与安全 | `v0.6-guardrails` | 三层防护、速率限制、成本控制 | 《生产环境的 Agent 需要什么安全措施》 |
| [Phase 7](phase-7-observability.md) | 可观测性 | `v0.7-observability` | Trace/Span、Metrics、Exporters | 《Agent 出了问题怎么调试 — 可观测性实战》 |
| [Phase 8](phase-8-mcp.md) | MCP 协议支持 | `v0.8-mcp` | MCP Client + Server | 《MCP — Agent 工具的通用语言》 |
| [Phase 9](phase-9-production.md) | 生产化 | `v0.9-production` | 配置驱动、断点恢复、错误恢复 | 《从玩具到生产 — Agent 框架的最后一公里》 |
| [Phase 10](phase-10-release.md) | 发布 v1.0 | `v1.0-release` | API 稳定、文档、PyPI、示例 | 《我们从零构建了一个 Agent 框架》 |

## 复杂度曲线

```
Phase:  0    1    2    3    4    5    6    7    8    9    10
        │    │    │    │    │    │    │    │    │    │    │
难度:   ▪    ▪▪   ▪▪▪  ▪▪▪  ▪▪▪  ▪▪▪▪ ▪▪▪  ▪▪▪  ▪▪▪▪ ▪▪▪▪ ▪▪
代码量: ~50  ~200 ~400 ~500 ~400 ~600 ~400 ~500 ~500 ~400 ~200
累计:   ~50  ~250 ~650 ~1.1K ~1.5K ~2.1K ~2.5K ~3K ~3.5K ~3.9K ~4.1K
```

## 依赖关系

```
Phase 0 (骨架)
   └── Phase 1 (Agent Loop)
          └── Phase 2 (Tools)
                 └── Phase 3 (Providers)
                        ├── Phase 4 (Memory)
                        │      └── Phase 5 (Orchestration)
                        │             └── Phase 6 (Guardrails)
                        │                    └── Phase 7 (Observability)
                        │                           └── Phase 8 (MCP)
                        │                                  └── Phase 9 (Production)
                        │                                         └── Phase 10 (Release)
                        └── (Phase 4-10 也可独立阅读)
```

## 每个阶段文档结构

每份需求文档包含以下标准章节：

1. **目标** — 这个阶段要解决什么问题
2. **核心概念** — 架构图或流程图
3. **功能需求** — 详细的功能点（含代码示例）
4. **不做的事情** — 显式排除的范围（避免范围蔓延）
5. **验收标准** — 可检查的完成清单
6. **测试策略** — 如何验证正确性
7. **核心文件** — 预期的文件结构
8. **技术决策** — 关键选型及原因

## 如何使用这些文档

### 作为开发者（自己开发）
1. 按顺序阅读每个 Phase 文档
2. 完成验收标准中的所有检查项
3. 打 Tag → 写博客 → 进入下一 Phase

### 作为读者（学习跟随）
1. `git checkout v0.1-agent-loop` — 切到对应阶段
2. 阅读对应 Phase 文档了解设计思路
3. 阅读代码理解实现
4. 阅读博客获取完整叙事

### 作为评审者（决策参考）
1. 阅读本总览了解全景
2. 深入感兴趣的 Phase 文档
3. 评估每个阶段的复杂度和价值
4. 决定是否值得投入
