# Phase 10 — Agent Skills 支持

> Tag: `v0.10-skills`
> 前置依赖: Phase 9
> 博客: 《Agent Skills — 让 Agent 按需加载专业能力》

---

## 目标

支持 **Agent Skills 开放格式**（[agentskills.io](https://agentskills.io)），让 Agent 能够发现、加载和使用 SKILL.md 定义的能力包。Agent Skills 是 Anthropic 发起的开放标准，已被 30+ 主流 Agent 产品采纳。

核心问题：如何让 Agent 按需获取它不具备的专业知识和操作流程？

## 核心概念

```
Agent Skills 的三层结构（渐进式上下文加载）：

1. 元数据（~100 tokens）  → 启动时加载所有 Skill 的 name + description
2. 指令（<5000 tokens）   → 激活时加载 SKILL.md 正文
3. 资源（按需）           → 需要时加载 scripts/、references/、assets/

SKILL.md 结构：
┌─────────────────────────────┐
│  ---                        │
│  name: code-review          │  ← YAML frontmatter（元数据）
│  description: ...           │
│  ---                        │
│                             │
│  ## 步骤                    │  ← Markdown body（指令）
│  1. 检查代码风格...          │
│  2. 分析安全漏洞...          │
│                             │
│  参考: references/rules.md  │  ← 引用外部文件
└─────────────────────────────┘
```

## 功能需求

### F10.1 Skill 数据模型

```python
class SkillMetadata(BaseModel):
    """SKILL.md frontmatter 解析结果"""
    name: str                               # 技能名称（小写 + 连字符）
    description: str                        # 技能描述（何时使用）
    license: str | None = None              # 许可证
    compatibility: str | None = None        # 环境要求
    metadata: dict[str, str] = {}           # 自定义元数据
    allowed_tools: list[str] = []           # 预授权工具列表

class Skill(BaseModel):
    """加载后的完整 Skill"""
    meta: SkillMetadata
    instructions: str                       # SKILL.md body（Markdown 指令）
    path: Path                              # Skill 目录路径
    files: dict[str, str] = {}              # 引用文件内容（按需加载）
```

### F10.2 Skill 加载器

```python
class SkillLoader:
    """从文件系统发现和加载 Skills"""

    def discover(self, search_paths: list[Path]) -> list[SkillMetadata]:
        """扫描目录，发现所有 SKILL.md 并解析元数据"""

    def load(self, skill_path: Path) -> Skill:
        """加载完整 Skill（元数据 + 指令 + 引用文件）"""

    def load_reference(self, skill: Skill, ref_path: str) -> str:
        """按需加载 Skill 引用的文件（scripts/、references/ 等）"""
```

搜索路径约定：
- 项目目录下的 `.skills/`
- 用户级 `~/.agent-skills/`
- 可配置的额外路径

### F10.3 Skill 匹配与激活

```python
class SkillMatcher:
    """根据用户输入决定激活哪些 Skills"""

    def match(
        self,
        query: str,
        available_skills: list[SkillMetadata],
        max_skills: int = 3,
    ) -> list[SkillMetadata]:
        """基于描述匹配返回最相关的 Skills"""
```

匹配策略：
- **关键词匹配**：基于 description 字段的关键词
- **LLM 匹配**（可选）：让 LLM 从 Skill 列表中选择最相关的

### F10.4 Agent 集成

```python
agent = Agent(
    name="assistant",
    instructions="You are a helpful coding assistant.",
    skill_paths=[Path(".skills"), Path("~/.agent-skills")],  # Skill 搜索路径
)

# Agent 启动时：加载所有 Skill 元数据（轻量）
# 用户提问时：匹配最相关的 Skill → 加载指令 → 拼入 system prompt
result = await agent.run("帮我做一下代码审查")
# → 自动激活 code-review Skill，加载审查流程指令
```

### F10.5 SKILL.md 解析与校验

```python
class SkillParser:
    """解析 SKILL.md 文件"""

    def parse(self, content: str) -> tuple[SkillMetadata, str]:
        """解析 YAML frontmatter + Markdown body"""

    def validate(self, skill_path: Path) -> list[str]:
        """校验 Skill 格式是否符合规范，返回错误列表"""
```

校验规则（遵循 agentskills.io 规范）：
- name: 1-64 字符，小写字母+数字+连字符，不以连字符开头/结尾
- description: 1-1024 字符，非空
- 目录名必须与 name 字段一致
- SKILL.md body 建议 < 500 行

## 不做的事情（显式排除）

- ❌ 远程 Skill 仓库 / Skill Marketplace — 后续扩展
- ❌ Skill 版本管理和依赖解析 — 过于复杂
- ❌ Skill 运行时隔离 / 沙箱 — Phase 7 Guardrails 可补充
- ❌ Skill 编写 CLI 工具 — 可后续添加

## 验收标准

- [ ] SkillParser 正确解析 YAML frontmatter + Markdown body
- [ ] SkillLoader.discover() 正确扫描目录发现 Skills
- [ ] SkillLoader.load() 正确加载完整 Skill
- [ ] SkillMatcher 根据关键词正确匹配相关 Skill
- [ ] Agent 集成后能自动激活匹配的 Skill
- [ ] Skill 指令正确拼入 LLM prompt
- [ ] 引用文件（references/、scripts/）按需加载
- [ ] 校验器正确检查 SKILL.md 格式合规性
- [ ] 与 agentskills.io 规范示例兼容

## 核心文件

```
src/myagent/
├── skills/
│   ├── __init__.py          # 导出 Skill, SkillLoader, SkillMatcher
│   ├── models.py            # SkillMetadata, Skill
│   ├── parser.py            # SkillParser（YAML + Markdown 解析）
│   ├── loader.py            # SkillLoader（发现 + 加载）
│   └── matcher.py           # SkillMatcher（匹配 + 激活）
├── agent.py                 # 增加 skill_paths 支持
```

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| YAML 解析库 | PyYAML（标准库级别） | SKILL.md frontmatter 是标准 YAML |
| 匹配策略 | 先关键词，可选 LLM | 关键词够用且快，LLM 匹配作为高级选项 |
| Skill 加载时机 | 元数据启动时加载，指令按需加载 | 遵循 Agent Skills 规范的渐进式加载 |
| 搜索路径 | 项目级 + 用户级 + 自定义 | 覆盖个人、团队、项目三个层级 |

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
| Agent Skills 官方规范 | SKILL.md 格式定义 | https://agentskills.io/specification |
| Agent Skills 概述 | 什么是 Agent Skills、为什么需要 | https://agentskills.io/what-are-skills |

### 开源代码
| 参考内容 | 框架 | 链接 |
|---|---|---|
| Agent Skills 官方仓库 | agentskills | https://github.com/agentskills/agentskills |
| Anthropic 示例 Skills | Anthropic | https://github.com/anthropics/skills |
| skills-ref 校验库 | agentskills | https://github.com/agentskills/agentskills/tree/main/skills-ref |

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
