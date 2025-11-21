"""
爬虫模块初始化与挂载

本文件负责：
1. 定义 setup_crawler(app) 方法，将爬虫相关路由和生命周期钩子挂载到主 FastAPI 应用。
2. 通过 include_router 注册 /api/crawl 路由（见 router.py），供前端或其他服务调用。
3. 注册定时任务等生命周期钩子（见 lifecycle.py），支持自动化抓取。

API整合流程：
- 主应用调用 setup_crawler(app)，本方法会自动注册爬虫路由和后台任务。
- 所有爬虫相关 API 都通过 /api/crawl 暴露。
"""
from fastapi import FastAPI  # 导入 FastAPI 主类，用于类型标注和应用实例传递

from .router import router as crawler_router  # 导入爬虫路由对象，定义了 /api/crawl 相关接口
from .lifecycle import crawler_lifespan  # 导入新版lifespan生命周期管理器


def setup_crawler(app: FastAPI) -> None:
        """
        挂载爬虫路由到主 FastAPI 应用。
        参数：app —— 主 FastAPI 应用实例。
        作用：
            1. 注册 /api/crawl 路由（由 router.py 提供），实现爬虫 API。
            2. 生命周期钩子已由 lifespan 统一管理，无需单独注册。
        """
        app.include_router(crawler_router)  # 注册爬虫路由到主应用，所有 /api/crawl 请求由 router.py 处理


__all__ = ["setup_crawler", "crawler_router"]  # 模块导出，供主应用或其他模块引用
