# Phase 0 — 项目骨架

> Tag: `v0.0-skeleton`
> 博客: 《为什么我要从零构建一个 Agent 框架》

---

## 目标

搭建一个规范的 Python 项目结构，配置好工具链，确保后续每个阶段都有干净的开发基础。

## 功能需求

### F0.1 项目结构初始化

创建标准 Python 包结构：

```
MyAgentFramework/
├── src/myagent/          # 主包
│   ├── __init__.py       # 版本号、公开 API 导出
│   └── py.typed          # PEP 561 类型标记
├── tests/                # 测试目录
│   ├── __init__.py
│   └── conftest.py       # pytest 全局 fixtures
├── docs/                 # 文档（已有）
├── blog/                 # 博客文章
├── examples/             # 使用示例
├── pyproject.toml        # 包配置（PEP 621）
├── CLAUDE.md             # 项目指南（已有）
├── README.md             # 公开说明
├── LICENSE               # MIT License
└── .gitignore            # 忽略规则
```

### F0.2 包管理配置 (uv)

- 使用 `uv` 作为包管理器
- `pyproject.toml` 定义：
  - 包元数据（name=myagent, version=0.0.1）
  - Python 版本要求 >=3.11
  - 开发依赖分组：`dev`（pytest, ruff, mypy）
  - 可选依赖分组预留：`openai`, `anthropic`（Phase 3 启用）

### F0.3 代码质量工具链

| 工具 | 用途 | 配置位置 |
|---|---|---|
| ruff | Linting + Formatting | pyproject.toml `[tool.ruff]` |
| mypy | 类型检查 | pyproject.toml `[tool.mypy]` |
| pytest | 测试框架 | pyproject.toml `[tool.pytest.ini_options]` |
| pytest-asyncio | 异步测试支持 | 同上 |

Ruff 规则要求：
- `E`, `W`：基础 PEP8
- `F`：pyflakes
- `I`：import 排序
- `UP`：pyupgrade（使用现代 Python 语法）
- `RUF`：ruff 专有规则
- line-length: 100

### F0.4 README.md

内容包含：
- 项目简介（一句话说明）
- 愿景说明
- 阶段路线图（链接到各 Phase 文档）
- Quick Start（占位，Phase 1 后补全）
- 博客系列目录
- License

### F0.5 博客 #0 草稿

《为什么我要从零构建一个 Agent 框架》大纲：
- 背景：Agent 框架百花齐放，但大多数开发者只会调 API
- 问题：不理解底层原理 = 无法调试、无法定制、无法优化
- 方案：从 50 行代码开始，逐步构建完整框架
- 路线图预览：10 个阶段的简要说明
- 行动号召：follow 仓库，跟着一起学

## 验收标准

- [ ] `uv sync` 可以正常安装所有依赖
- [ ] `uv run ruff check src/` 通过
- [ ] `uv run mypy src/` 通过
- [ ] `uv run pytest` 可以运行（哪怕 0 个测试）
- [ ] 项目可通过 `uv pip install -e .` 安装

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 包管理器 | uv | 速度快、现代、替代 pip+venv+poetry |
| 项目布局 | src layout | 防止意外导入本地包，PyPI 发布标准 |
| 格式化 | ruff format | 替代 black，统一工具链 |
| 最低 Python | 3.11 | match 语法、TaskGroup、更好的类型提示 |

---

## 设计思考

> 从第一性原理出发的设计推理过程

_开发时填写：问题本质 → 独立思考 → 开源框架怎么做 → 我们的选择与理由_

---
## 参考实现

> 开发过程中参考的其他框架的具体代码和文档链接

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
