# Phase 5 — RAG（检索增强生成）

> Tag: `v0.5-rag`
> 前置依赖: Phase 4
> 博客: 《让 Agent 拥有知识 — RAG 系统的本质》

---

## 目标

让 Agent 能够**检索外部知识**来增强回答质量。RAG（Retrieval Augmented Generation）是 Agent 从"凭记忆回答"到"查资料再回答"的关键一步。

核心问题：如何让 LLM 访问它训练数据之外的知识？

## 核心概念

```
RAG 流程：

文档摄入（离线）：
  文档 → 分块(Chunking) → 向量化(Embedding) → 存入向量数据库

查询检索（在线）：
  用户提问 → 向量化 → 相似度检索 → 获取相关文档片段
      ↓
  拼入 Prompt → LLM 生成回答（带引用来源）

关键组件：
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Chunker    │→ │  Embedder    │→ │ Vector Store │
│  文档分块器   │  │  向量化模型   │  │  向量数据库   │
└──────────────┘  └──────────────┘  └──────────────┘
                                          ↓
                                    ┌──────────────┐
                                    │  Retriever   │
                                    │  检索器       │
                                    └──────────────┘
```

## 功能需求

### F5.1 文档分块（Chunking）

将长文档拆分为适合 Embedding 的小块：

```python
class Chunker(ABC):
    """文档分块策略"""

    @abstractmethod
    def chunk(self, text: str) -> list[Chunk]:
        """将文本分割为多个 Chunk"""

class Chunk(BaseModel):
    """一个文档片段"""
    content: str                    # 片段文本
    metadata: dict[str, Any] = {}   # 来源文件、页码、位置等
    chunk_id: str = ""              # 唯一标识
```

内置策略：

| 策略 | 说明 | 适用场景 |
|---|---|---|
| `FixedSizeChunker` | 按固定字符数 + 重叠窗口分割 | 通用 |
| `RecursiveChunker` | 按分隔符层级（段落→句子→字符）递归分割 | 结构化文档 |
| `MarkdownChunker` | 按 Markdown 标题层级分割 | Markdown 文档 |

### F5.2 向量化（Embedding）

```python
class Embedder(ABC):
    """文本向量化接口"""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """将文本列表转换为向量列表"""

    @abstractmethod
    def dimension(self) -> int:
        """返回向量维度"""
```

内置实现：
- `OpenAIEmbedder` — 使用 `text-embedding-3-small`（1536 维）
- 后续可扩展其他 Provider 的 Embedding 模型

### F5.3 向量存储（Vector Store）

```python
class VectorStore(ABC):
    """向量数据库抽象接口"""

    @abstractmethod
    async def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        """存入向量"""

    @abstractmethod
    async def search(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[SearchResult]:
        """相似度检索"""

    @abstractmethod
    async def delete(self, chunk_ids: list[str]) -> None:
        """删除向量"""

class SearchResult(BaseModel):
    chunk: Chunk
    score: float                    # 相似度分数
```

内置实现：
- `InMemoryVectorStore` — 基于 numpy 余弦相似度，开发/测试用
- 后续可扩展 Chroma、FAISS、Pinecone 等

### F5.4 检索器（Retriever）

将分块、向量化、检索组合为统一接口：

```python
class Retriever:
    """RAG 检索器 — 组合 Chunker + Embedder + VectorStore"""

    def __init__(
        self,
        embedder: Embedder,
        vector_store: VectorStore,
        chunker: Chunker | None = None,
    ) -> None: ...

    async def ingest(self, documents: list[Document]) -> None:
        """摄入文档：分块 → 向量化 → 存储"""

    async def retrieve(self, query: str, top_k: int = 5) -> list[SearchResult]:
        """检索相关文档片段"""

class Document(BaseModel):
    """待摄入的原始文档"""
    content: str
    metadata: dict[str, Any] = {}   # 文件名、来源 URL 等
```

### F5.5 Agent 集成

Agent 新增 retriever 配置，在调用 LLM 前自动检索相关上下文：

```python
agent = Agent(
    name="knowledge_assistant",
    instructions="基于检索到的资料回答问题。如果资料中没有相关信息，请如实说明。",
    retriever=retriever,            # RAG 检索器
)

# 用户提问时，Agent 自动：
# 1. 用问题检索相关文档
# 2. 将检索结果拼入 prompt
# 3. LLM 基于检索上下文生成回答
result = await agent.run("MyAgentFramework 的 Agent Loop 是怎么实现的？")
```

## 不做的事情（显式排除）

- ❌ 高级检索策略（HyDE、Reranking、多跳检索）— 后续扩展
- ❌ 实时网页检索 / Web Search — 可作为 Tool 实现
- ❌ 图数据库 / 知识图谱 — 超出最小 RAG 范围
- ❌ 多模态 RAG（图片、音频）— 后续扩展
- ❌ 生产级向量数据库集成（Pinecone、Weaviate）— Phase 12

## 验收标准

- [ ] FixedSizeChunker 正确按大小+重叠分块
- [ ] RecursiveChunker 按分隔符层级递归分割
- [ ] MarkdownChunker 按标题层级分割
- [ ] OpenAIEmbedder 返回正确维度的向量
- [ ] InMemoryVectorStore 的 add/search/delete 正确
- [ ] Retriever.ingest() 正确完成文档摄入流水线
- [ ] Retriever.retrieve() 返回与查询相关的结果
- [ ] Agent 集成 retriever 后能基于检索上下文回答
- [ ] 全流程可用 Mock Embedder 测试，不依赖真实 API

## 核心文件

```
src/myagent/
├── rag/
│   ├── __init__.py          # 导出 Retriever, Chunker, Embedder, VectorStore
│   ├── chunker.py           # Chunker ABC + 内置策略
│   ├── embedder.py          # Embedder ABC + OpenAIEmbedder
│   ├── vector_store.py      # VectorStore ABC + InMemoryVectorStore
│   ├── retriever.py         # Retriever 组合器
│   └── models.py            # Chunk, Document, SearchResult
├── agent.py                 # 增加 retriever 支持
```

## 技术决策

| 决策 | 选择 | 原因 |
|---|---|---|
| 默认 Embedding 模型 | OpenAI text-embedding-3-small | 性价比最高，1536 维 |
| 默认向量存储 | InMemoryVectorStore + numpy | 零依赖，开发/测试够用 |
| 分块默认大小 | 512 字符，128 重叠 | 业界常见的平衡点 |
| 相似度度量 | 余弦相似度 | Embedding 模型的标准度量 |

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
| Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | RAG 的原始论文 | https://arxiv.org/abs/2005.11401 |
| _开发时补充_ | | |

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
