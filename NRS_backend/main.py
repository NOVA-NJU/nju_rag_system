"""
NJU Unified Backend 主入口

本文件负责：
1. 创建 FastAPI 应用实例
2. 挂载所有子模块（爬虫、向量库、RAG 问答）到主应用
3. 提供统一健康检查接口
4. 支持直接运行（开发模式）
"""
from __future__ import annotations


from fastapi import FastAPI
# 导入爬虫模块的 lifespan 生命周期管理器
from .crawler.lifecycle import crawler_lifespan  # 用于定时任务生命周期管理

# 导入各子模块的路由注册函数
from .crawler import setup_crawler      # 挂载爬虫相关 API（/api/crawl）
from .rag import setup_rag              # 挂载 RAG 问答 API（/api/rag）
from .vector_store import setup_vector_store  # 挂载向量库 API（/vectors/*）


# 创建主 FastAPI 应用，指定 lifespan 参数实现定时任务自动管理
app = FastAPI(title="NJU Unified Backend", version="1.0.0", lifespan=crawler_lifespan)

# 挂载各子服务到主应用
setup_crawler(app)         # 注册 /api/crawl 路由
setup_vector_store(app)    # 注册 /vectors/* 路由
setup_rag(app)             # 注册 /api/rag 路由

# 健康检查接口，前端/监控可用
@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    返回后端整体健康状态。
    用于前端或监控系统探测服务是否可用。
    """
    return {"status": "ok"}

# 提供给 ASGI/Uvicorn 的应用实例获取方法
def get_app() -> FastAPI:
    return app

# 支持直接运行本文件（开发调试用）
if __name__ == "__main__":
    import uvicorn
    # 启动 FastAPI 服务，监听 8000 端口，支持热重载
    uvicorn.run("NRS_backend.main:app", host="0.0.0.0", port=8000, reload=True)
