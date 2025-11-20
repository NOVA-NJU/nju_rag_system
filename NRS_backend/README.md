# NRS Unified Backend

统一后的后端将 `NRS_data`（爬虫）、`NRS_vector`（向量数据库）与最新的 `NRS_rag`（RAG 问答服务）合并为一个 FastAPI 进程，全部通过 **8000** 端口向前端暴露 API。

```
┌────────────┐        ┌────────────────┐        ┌──────────────┐
│  Frontend  │◄──────►│  FastAPI (8000)│◄──────►│  ChromaDB     │
└────────────┘        │   ├─ /api/crawl│        │  (本地嵌入)   │
               │   ├─ /vectors/*│        └──────────────┘
               │   └─ /api/rag  │                 ▲
               └────────────────┘                 │
                    ▲                        LLM (Ollama / OpenAI)
                    │
                  Scheduler + OCR
```

## 目录结构

```
NRS_backend/
├─ main.py                  # FastAPI 入口，挂载全部子模块
├─ requirements.txt         # 统一依赖清单
├─ crawler/                 # 爬虫服务（原 NRS_data）
│   ├─ config.py            # 抓取站点、OCR、调度配置
│   ├─ lifecycle.py         # 开机自启的定时任务（默认每小时）
│   ├─ models.py / router.py / services.py
│   └─ storage/database.py  # SQLite 持久化
├─ vector_store/            # 向量存储（原 NRS_vector）
│   ├─ config.py / models.py / router.py / services.py
│   └─ bridge.py            # In-process store/search 辅助函数
└─ rag/                     # 新增 RAG 子模块（原 NRS_rag）
   ├─ config.py            # LLM、Top-K、阈值等配置
   ├─ models.py
   ├─ router.py            # `/api/rag` 路由
   └─ service.py           # 检索 + Prompt + LLM 调用
```

## 工作流概览

1. **Crawler**
  - 轮询 `crawler/config.py` 中列出的南京大学官网栏目（默认 `bksy_ggtz`）。
  - 抽取正文 + 附件 + OCR 文本，计算内容哈希，写入 SQLite 并通过 `vector_store.bridge.store_document` 推送到 ChromaDB。
2. **Vector Store**
  - 负责文本分块、向量化、向量检索以及 REST API (`/vectors/search`, `/vectors/documents`, `/vectors/cleardb` 等)。
  - 同时暴露 `search_documents()` 等内部函数，供其他模块直接调用以避免 HTTP Hop。
3. **RAG Service**
  - `POST /api/rag` 接收用户问题 → 调用向量搜索（优先走进程内 bridge，可回退到 `VECTOR_SERVICE_URL` 外部地址）→ 基于模板生成 Prompt → 调用 LLM（默认 Ollama 的 `qwen3:8b`）→ 返回答案与引用来源。

## 快速上手

```powershell
cd NRS_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# 如需本地 LLM，请先启动 Ollama 并 pull 对应模型
python -m uvicorn NRS_backend.main:app --host 0.0.0.0 --port 8000 --reload
```

运行后：

- Swagger 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health
- 爬虫触发接口：`POST /api/crawl`
- 向量检索接口：`POST /vectors/search`
- RAG 问答接口：`POST /api/rag`

## 关键环境变量（可写入仓库根目录 `.env`）

| 模块 | 变量 | 说明 | 默认值 |
|------|------|------|--------|
| Crawler | `CRAWL_INTERVAL` | 定时抓取间隔（秒） | 3600 |
| | `AUTO_CRAWL_ENABLED` | 是否随服务启动定时任务 | true |
| | `TESSERACT_CMD` / `TESSDATA_DIR` | OCR 所需的 Tesseract 路径 | 为空则禁用 OCR |
| | `VECTOR_SYNC_ENABLED` | 是否把抓取结果写入向量库 | true |
| Vector Store | `VECTOR_db_path` | ChromaDB 持久化目录 | `./chroma_db` |
| | `VECTOR_embedding_model` | SentenceTransformer 模型 | `BAAI/bge-large-zh-v1.5` |
| | `VECTOR_similarity_threshold` | 统一的最低相似度阈值（供 Vector/RAG 共用） | `0.0` |
| RAG | `LLM_PROVIDER` | `ollama` 或 `openai` | `ollama` |
| | `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | 本地 LLM 地址及模型名 | `http://localhost:11434` / `qwen3:8b` |
| | `OPENAI_API_KEY` / `OPENAI_MODEL` | 仅在 provider=openai 时需要 | - |
| | `OPENAI_BASE_URL` | OpenAI 兼容 API 地址，可指向通义千问云端 | `https://api.openai.com/v1` |
| | `TOP_K` | 检索结果条数 | 3 |
| | `SIMILARITY_THRESHOLD` | 过滤结果的最低相似度（默认继承 Vector 配置） | 0.0 |
| | `VECTOR_SERVICE_URL` | 不走内存桥时可指定外部向量服务 | 空（默认为内联调用） |

> 示例 `.env`

```
CRAWL_INTERVAL=1800
TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
TESSDATA_DIR=C:\\Program Files\\Tesseract-OCR\\tessdata
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2:7b
TOP_K=5
SIMILARITY_THRESHOLD=0.65
```

## API 摘要

| 路径 | 方法 | 描述 |
|------|------|------|
| `/api/crawl` | `POST` | 触发指定 `source`（如 `bksy_ggtz`）的抓取。未知源返回 404。|
| `/vectors/search` | `POST` | 通过向量检索返回 `VectorMatch` 列表。|
| `/vectors/documents` | `POST` | 写入原始文档并自动切片、嵌入。|
| `/vectors/cleardb` | `POST` | 清空 ChromaDB。|
| `/api/rag` | `POST` | 输入 `{"question": "..."}`，返回 LLM 答案与引用。|
| `/api/rag/health` | `GET` | RAG 子系统健康检查。|

## 定时任务与去重策略

- `crawler/lifecycle.py` 在 FastAPI 启动时拉起后台任务，按 `CRAWL_INTERVAL` 轮询 `TARGET_SOURCES` 列表。每轮按顺序抓取，避免对目标站点造成压力。
- `crawler/services.py` 使用页面内容（或回退到 URL）计算 SHA256 作为主键，插入 SQLite 前会调用 `record_exists()`，再配合 `INSERT OR IGNORE` 杜绝重复写入。若正文被站方更新，新的哈希会视作独立记录。

## RAG 模块要点

- 通过 `vector_store.bridge.search_documents()` 直接复用内存中的 SentenceTransformer 和 ChromaDB 客户端；若设置了 `VECTOR_SERVICE_URL` 则可以改走 HTTP。
- Prompt 模板、Top-K、相似度阈值等均可在 `.env` 中覆盖，便于快速调参。
- 默认调用本地 Ollama，可通过 `LLM_PROVIDER=openai` 切换成云端接口（需安装 `openai` 包并配置密钥）。
- `sources` 数组会返回每个引用片段的 `text`、`title`、`url` 与 `score`，前端可直接展示出处。

## 开发提示

1. **联调前准备**：
  - 确保 SQLite (`data/crawler.db`) 与 ChromaDB (`chroma_db/`) 目录具备写入权限。
  - OCR 需要在 Windows 安装 Tesseract 并设置 `TESSERACT_CMD`；若暂时不需要 OCR，可设为空字符串避免 WARN。
  - RAG 需要本地 Ollama 或可用的 OpenAI Key。
2. **扩展站点**：在 `crawler/config.py` 的 `TARGET_SOURCES` 数组中新增配置，字段与现有示例保持一致即可。
3. **批量爬取**：可在外部脚本中枚举 `TARGET_SOURCES` 的 `id`，依次调用 `/api/crawl`；或在 `lifecycle.py` 中自定义调度策略（并发/分频率等）。
4. **调试 RAG**：通过 `/api/rag` 观察 `sources` 是否为空来判断是检索失败还是 LLM 输出不佳；必要时开启 `VECTOR_SERVICE_URL` 指向远端实例排查差异。

## 许可证

后端沿用仓库整体授权，默认遵循 MIT License。如需向外部部署，请遵守南京大学及数据来源站点的使用规范。
