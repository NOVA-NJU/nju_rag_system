"""
爬虫模块API用到的所有Pydantic数据模型定义。
用于请求体、响应体、错误体、爬取结果、附件等结构化数据交互。
所有字段均有详细注释，便于前后端联调和理解。
"""
from __future__ import annotations  # 兼容未来类型注解语法

from datetime import datetime  # 时间类型，用于发布时间
from typing import List, Optional  # 类型注解：列表、可选

from pydantic import BaseModel, HttpUrl  # Pydantic基类和URL类型


class CrawlRequest(BaseModel):
        """
        前端/客户端发起爬虫请求时的请求体结构。
        字段：
            source: str  # 要爬取的目标源ID（如 'bksy_ggtz'）
        """
        source: str  # 目标源ID


class Attachments(BaseModel):
        """
        详情页解析出的附件结构体。
        字段：
            url: HttpUrl         # 附件下载链接
            filename: str        # 附件文件名（可选）
            mime_type: str       # 附件类型（如pdf、docx等，可选）
            text: str            # 附件OCR或文本内容（可选）
        """
        url: HttpUrl  # 附件下载链接
        filename: Optional[str] = None  # 附件文件名
        mime_type: Optional[str] = None  # 附件类型
        text: Optional[str] = None  # 附件文本内容


class CrawlItem(BaseModel):
        """
        单条爬取结果（如一篇公告/文章），包含所有聚合信息。
        字段：
            id: str                  # 唯一ID
            title: str               # 标题
            content: str             # 正文内容
            url: HttpUrl             # 详情页链接
            publish_time: datetime   # 发布时间
            source: str              # 来源ID
            attachments: List[...]   # 附件列表（可选）
            extra_meta: dict         # 额外元数据（可选）
        """
        id: str  # 唯一ID
        title: str  # 标题
        content: str  # 正文内容
        url: HttpUrl  # 详情页链接
        publish_time: datetime  # 发布时间
        source: str  # 来源ID
        attachments: Optional[List[Attachments]] = None  # 附件列表
        extra_meta: Optional[dict] = None  # 额外元数据


class ErrorResponse(BaseModel):
        """
        API统一错误响应体。
        字段：
            error: str  # 错误信息描述
            code: str   # 错误码（如404、502等）
        """
        error: str  # 错误信息
        code: str = "404"  # 错误码，默认404


class CrawlResponse(BaseModel):
        """
        /api/crawl接口的成功响应体。
        字段：
            code: str         # 状态码（200表示成功）
            data: List[...]   # 爬取结果列表
        """
        code: str = "200"  # 状态码
        data: List[CrawlItem]  # 爬取结果列表
