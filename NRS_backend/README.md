# NRS Unified Backend

该目录融合了原有的 `NRS_data`（爬虫）与 `NRS_vector`（向量存储）两个后端模块，统一为单个 FastAPI 应用并监听 `8000` 端口。

## 目录结构

```
NRS_backend/
├─ main.py                        # FastAPI 统一入口
├─ requirements.txt               # 组合依赖
├─ crawler/                       # 由 NRS_data 迁移而来
│   ├─ config.py
│   ├─ models.py
│   ├─ router.py
│   ├─ services.py
│   ├─ lifecycle.py               # 周期性任务注册
│   └─ storage/database.py
└─ vector_store/                  # 由 NRS_vector 迁移而来
    ├─ config.py
    ├─ models.py
    ├─ router.py
    ├─ services.py
    └─ bridge.py                  # 供内部直接调用的函数
```

## 关键变更

- **跨模块函数调用**：`crawler.services` 直接通过 `vector_store.bridge.store_document` 写入向量库，不再通过 HTTP 客户端。
- **统一路由**：
  - `/api/crawl`：触发异步爬虫并写入数据库+向量库。
  - `/vectors/*`：保持与上游向量服务一致（支持 `/vectors/search`、`/vectors/documents`、`/vectors/search/{id}`、`/vectors/cleardb` 等接口）。
- **单进程部署**：使用 `uvicorn NRS_backend.main:app --port 8000` 即可同时托管爬虫与向量接口，便于协同开发与部署。
- **可选同步**：通过环境变量 `VECTOR_SYNC_ENABLED=false` 可以暂时关闭爬虫写向量库的行为，方便单独调试。
- **自动 ID 分配**：向量服务不再要求客户端提供 `document_id`，会自动递增生成 ID；爬虫将原始哈希写入元数据 `original_id` 字段以便追踪。

## 本地运行

```powershell
cd NRS_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

运行后：
- Swagger 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 参数与配置

- 所有爬虫相关配置位于 `crawler/config.py`，可通过环境变量覆盖（如 `CRAWL_INTERVAL`、`TESSERACT_CMD` 等）。
- 向量服务配置位于 `vector_store/config.py`，前缀为 `VECTOR_`（如 `VECTOR_db_path`、`VECTOR_embedding_model`）。
- 统一 `.env` 可放在仓库根目录，既能被爬虫读取（标准 `os.getenv`），也能被向量服务的 `pydantic-settings` 加载。

## 后续扩展

- 当 RAG 模块准备就绪，可在 `NRS_backend` 内继续新增子包并在 `main.py` 中挂载对应路由即可。
- 如果仍需独立部署，可针对 `crawler` 或 `vector_store` 单独编写 CLI/入口文件，但默认推荐使用统一服务以简化内部通信。
