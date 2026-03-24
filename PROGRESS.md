# 开发进度追踪

> 最后更新：2026-03-24

本文档记录项目的开发进度，方便跨会话回顾和继续开发。

---

## 当前状态

**当前阶段**：Phase 1 — 最小 Agent Loop（已完成）
**下一阶段**：Phase 2 — Tool 系统
**最新 Tag**：`v0.1-agent-loop`

---

## 进度总览

| Phase | 名称 | 状态 | Tag | 完成日期 | 备注 |
|---|---|---|---|---|---|
| 0 | 项目骨架 | ✅ 已完成 | `v0.0-skeleton` | 2026-03-24 | 骨架 + 博客 #0 |
| 1 | 最小 Agent Loop | ✅ 已完成 | `v0.1-agent-loop` | 2026-03-24 | 核心循环 + 15 个测试 |
| 2 | Tool 系统 | ⏳ 未开始 | - | - | |
| 3 | 多 Provider 适配 | ⏳ 未开始 | - | - | |
| 4 | Memory 与 State | ⏳ 未开始 | - | - | |
| 5 | RAG | ⏳ 未开始 | - | - | 新增：检索增强生成 |
| 6 | 多 Agent 编排 | ⏳ 未开始 | - | - | 原 Phase 5 |
| 7 | Guardrails 与安全 | ⏳ 未开始 | - | - | 原 Phase 6 |
| 8 | 可观测性 | ⏳ 未开始 | - | - | 原 Phase 7 |
| 9 | MCP 协议 | ⏳ 未开始 | - | - | 原 Phase 8 |
| 10 | Agent Skills | ⏳ 未开始 | - | - | 新增：agentskills.io 格式 |
| 11 | A2A 协议 | ⏳ 未开始 | - | - | 新增：Agent 互操作协议 |
| 12 | 生产化 | ⏳ 未开始 | - | - | 原 Phase 9 |
| 13 | 发布 v1.0 | ⏳ 未开始 | - | - | 原 Phase 10 |

---

## Phase 0 — 项目骨架 详细进度

### 已完成

- [x] 项目结构初始化（src layout）
- [x] uv 包管理配置（pyproject.toml）
- [x] 开发依赖安装（ruff, mypy, pytest, pytest-asyncio）
- [x] 可选依赖分组（openai, anthropic, all, dev）
- [x] Ruff lint 配置（E/W/F/I/UP/RUF 规则）
- [x] Mypy strict 模式配置
- [x] Pytest + asyncio 配置
- [x] 子包目录创建（tools, providers, memory, orchestration, guardrails, tracing, mcp）
- [x] README.md（项目介绍 + 路线图 + Quick Start）
- [x] LICENSE（MIT）
- [x] .gitignore
- [x] 第一个测试（test_version）通过
- [x] GitHub 仓库创建（songpl-AI/MyAgentFramework）
- [x] 阶段需求文档（Phase 0-10 共 11 份）
- [x] 框架对比分析文档
- [x] CLAUDE.md 项目指南
- [x] 开发进度追踪文档（本文件）

### 进行中

_无 — Phase 0 已全部完成_

### 验收检查

- [x] `uv sync` 正常安装所有依赖
- [x] `uv run ruff check src/` 通过
- [x] `uv run mypy src/` 通过
- [x] `uv run pytest` 通过（1 test passed）
- [x] 项目可通过 `uv pip install -e .` 安装

---

## Phase 1 — 最小 Agent Loop 详细进度

### 已完成

- [x] 调研 OpenAI Agents SDK、Anthropic SDK、Agno、LangGraph 的循环实现
- [x] 调研 ReAct 论文和理论基础
- [x] 设计思考：循环结构（for vs while）、循环位置（Agent 层 vs Model 层）、LLM 注入方式
- [x] 实现 `Message` / `StepResult` / `AgentResult` 数据模型 (Pydantic v2)
- [x] 实现 `LLMProtocol` + `LLMResponse` + `OpenAILLM` (lazy import)
- [x] 实现 `Agent` 类：for 循环核心 loop、step() 扩展点、run_sync() 同步包装
- [x] 实现 `MockLLM` 测试工具
- [x] 15 个测试覆盖：基础功能(4) + 终止条件(5) + 多步执行(2) + 配置(3) + 版本(1)
- [x] ruff / mypy / pytest 全部通过
- [x] 更新 phase-1 开发日志（记录 3 个开发问题）
- [x] 更新 PROGRESS.md

### 验收检查

- [x] `Agent.run("你好")` 返回 `AgentResult` 且包含正确 output
- [x] 对话历史正确记录（system + user + assistant）
- [x] `max_steps=1` 正确终止
- [x] 多步场景消息正确累积
- [x] `finish_reason="stop"` / `"length"` / `"max_steps"` 正确处理
- [x] 空响应安全处理

---

## 变更记录

### 2026-03-24

- 项目启动
- 完成九大 Agent 框架对比分析
- 创建 CLAUDE.md 项目指南，定义 10 个阶段路线图
- 创建 Phase 0-10 详细需求文档
- 初始化项目骨架：uv + ruff + mypy + pytest
- 创建 GitHub 仓库 songpl-AI/MyAgentFramework
- 撰写博客 #0：《为什么我要从零构建一个 Agent 框架》
- 创建 PROGRESS.md 开发进度追踪文档
- Phase 0 完成，打 Tag `v0.0-skeleton`
- 开始 Phase 1：调研 OpenAI Agents SDK、Anthropic SDK、Agno、LangGraph 的 Agent Loop 实现
- Phase 1 设计思考完成：选择 for 循环 + Protocol 注入 + Agent 层控制
- Phase 1 实现完成：Agent, Message, StepResult, AgentResult, LLMProtocol, OpenAILLM
- 15 个测试全部通过（ruff + mypy + pytest 三项检查通过）
- Phase 1 完成，打 Tag `v0.1-agent-loop`
