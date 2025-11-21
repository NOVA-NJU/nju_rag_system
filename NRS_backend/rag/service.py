"""Core RAG orchestration logic."""  # RAG核心编排逻辑模块
from __future__ import annotations  # 兼容未来类型注解语法

import logging  # 日志记录，用于异常追踪
from typing import Iterable, List, Sequence  # 类型注解：Iterable用于迭代，List和Sequence用于序列

import httpx  # HTTP客户端，用于调用外部向量服务和LLM API

# 配置：RAG设置类和获取函数
from .config import RagSettings, get_settings  # 导入配置类和工厂函数
# 数据模型：回答响应和源文档
from .models import AnswerResponse, SourceDocument  # 导入Pydantic数据模型
# 向量存储桥接：搜索文档函数
from ..vector_store.bridge import search_documents as bridge_search  # 导入向量搜索桥接函数
# 向量存储模型：向量匹配和搜索响应
from ..vector_store.models import VectorMatch, VectorSearchResponse  # 导入向量存储数据模型

logger = logging.getLogger(__name__)  # 获取当前模块日志对象


class RAGService:
    """High-level RAG flow: retrieve supporting docs, craft prompt, call LLM."""  # 高层RAG流程：检索支持文档，构建提示，调用LLM

    def __init__(self, settings: RagSettings | None = None) -> None:
        self.settings = settings or get_settings()  # 初始化设置，如果未提供则使用默认配置

    async def _search_via_http(self, question: str, top_k: int) -> Sequence[VectorMatch]:
        if not self.settings.vector_service_url:  # 如果未配置外部向量服务URL，直接返回空结果
            return []
        base = self.settings.vector_service_url.rstrip("/")  # 移除URL末尾斜杠
        endpoint = self.settings.vector_search_endpoint  # 获取搜索端点路径
        url = f"{base}{endpoint}"  # 构建完整搜索URL
        payload = {"query": question, "top_k": top_k}  # 构建请求载荷
        timeout = httpx.Timeout(self.settings.vector_request_timeout)  # 设置请求超时
        async with httpx.AsyncClient(timeout=timeout) as client:  # 创建异步HTTP客户端
            response = await client.post(url, json=payload)  # 发送POST请求
            response.raise_for_status()  # 检查响应状态，如果失败则抛出异常
            data = response.json()  # 解析JSON响应
        result = VectorSearchResponse(**data)  # 将响应数据转换为VectorSearchResponse对象
        return result.results  # 返回搜索结果列表

    async def search_vector_db(self, question: str, top_k: int | None = None) -> Sequence[VectorMatch]:
        size = top_k or self.settings.top_k  # 确定搜索结果数量，默认使用配置值
        if self.settings.vector_service_url:  # 如果配置了外部向量服务
            try:
                matches = await self._search_via_http(question, size)  # 尝试通过HTTP调用外部服务
                if matches:  # 如果获得结果，直接返回
                    return matches
                logger.warning("External vector service returned no results, falling back to in-process bridge")  # 记录警告：外部服务无结果，回退到本地桥接
            except Exception as exc:  # noqa: BLE001  # 捕获异常，忽略特定代码质量检查
                logger.warning("External vector service failed: %s", exc)  # 记录警告：外部服务失败
        response = await bridge_search(question, size)  # 调用本地向量搜索桥接函数
        return response.results  # 返回搜索结果

    async def call_llm(self, prompt: str) -> str:
        provider = self.settings.llm_provider.lower()  # 获取LLM提供商名称，转小写
        if provider == "ollama":  # 如果是Ollama提供商
            return await self._call_ollama(prompt)  # 调用Ollama接口
        if provider == "openai":  # 如果是OpenAI提供商
            return await self._call_openai(prompt)  # 调用OpenAI接口
        raise ValueError(f"Unsupported LLM provider: {self.settings.llm_provider}")  # 抛出异常：不支持的提供商

    async def _call_ollama(self, prompt: str) -> str:
        url = self.settings.ollama_base_url.rstrip("/") + "/api/generate"  # 构建Ollama生成API URL
        payload = {"model": self.settings.ollama_model, "prompt": prompt, "stream": False}  # 构建请求载荷
        timeout = httpx.Timeout(self.settings.ollama_timeout)  # 设置超时
        async with httpx.AsyncClient(timeout=timeout) as client:  # 创建异步HTTP客户端
            response = await client.post(url, json=payload)  # 发送POST请求
            response.raise_for_status()  # 检查响应状态
            data = response.json()  # 解析JSON响应
        answer = (data.get("response") or data.get("output") or "").strip()  # 提取回答内容
        if not answer:  # 如果回答为空
            raise RuntimeError("Ollama returned an empty response")  # 抛出运行时异常
        return answer  # 返回回答

    async def _call_openai(self, prompt: str) -> str:  # pragma: no cover - optional provider  # 调用OpenAI接口（可选提供商）
        api_key = self.settings.openai_api_key  # 获取API密钥
        if not api_key:  # 如果未配置API密钥
            raise RuntimeError("OPENAI_API_KEY is not configured")  # 抛出运行时异常
        try:
            from openai import AsyncOpenAI  # type: ignore  # 动态导入OpenAI客户端
        except ImportError as exc:  # pragma: no cover - optional dependency  # 捕获导入异常
            raise RuntimeError("The openai package is not installed") from exc  # 抛出运行时异常
        client = AsyncOpenAI(api_key=api_key, base_url=self.settings.openai_base_url)  # 创建OpenAI客户端
        response = await client.chat.completions.create(  # 调用聊天完成API
            model=self.settings.openai_model,  # 指定模型
            messages=[{"role": "user", "content": prompt}],  # 构建消息列表
            temperature=0.2,  # 设置温度参数
        )
        return response.choices[0].message.content.strip()  # 返回第一个选择的内容

    def build_prompt(self, question: str, matches: Sequence[VectorMatch]) -> str:
        parts: List[str] = []  # 初始化部分列表
        for idx, match in enumerate(matches, start=1):  # 遍历匹配结果，从1开始编号
            snippet = match.text or match.metadata.get("summary") or "(无文本内容)"  # 获取文本片段
            parts.append(f"[{idx}] {snippet}")  # 添加编号的片段
        context = "\n\n".join(parts) if parts else "暂无相关上下文信息"  # 构建上下文，如果无结果则使用默认消息
        return self.settings.prompt_template.format(question=question, context=context)  # 使用模板格式化提示

    def format_sources(self, matches: Iterable[VectorMatch]) -> List[SourceDocument]:
        sources: List[SourceDocument] = []  # 初始化源文档列表
        for match in matches:  # 遍历匹配结果
            score = match.score or 0.0  # 获取匹配分数，默认0.0
            metadata = match.metadata or {}  # 获取元数据，默认空字典
            url = metadata.get("url") or metadata.get("source") or metadata.get("link")  # 从元数据中提取URL
            title = metadata.get("title") or metadata.get("source_name") or match.document_id  # 从元数据中提取标题
            sources.append(  # 添加源文档到列表
                SourceDocument(  # 创建SourceDocument对象
                    text=match.text or metadata.get("summary") or "",  # 设置文本内容
                    url=url,  # 设置URL
                    title=title,  # 设置标题
                    score=score,  # 设置匹配分数
                )
            )
        return sources  # 返回源文档列表

    async def generate_answer(self, question: str) -> AnswerResponse:
        question = question.strip()  # 去除问题首尾空白字符
        if not question:  # 如果问题为空
            raise ValueError("问题不能为空")  # 抛出值错误异常
        matches = await self.search_vector_db(question)  # 搜索向量数据库获取相关文档
        if not matches:  # 如果没有找到匹配的文档
            return AnswerResponse(code="404", answer="抱歉，没有检索到相关的参考信息。", sources=[])  # 返回无结果响应
        prompt = self.build_prompt(question, matches)  # 基于问题和匹配结果构建提示
        answer = await self.call_llm(prompt)  # 调用LLM生成回答
        sources = self.format_sources(matches)  # 格式化源文档列表
        return AnswerResponse(answer=answer, sources=sources)  # 返回包含回答和源文档的响应


# 创建RAG服务实例，供路由器使用
rag_service = RAGService()  # 实例化RAGService类，默认使用配置


rag_service = RAGService()
