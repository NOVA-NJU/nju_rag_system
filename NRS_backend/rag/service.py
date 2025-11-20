"""Core RAG orchestration logic."""
from __future__ import annotations

import logging
from typing import Iterable, List, Sequence

import httpx

from .config import RagSettings, get_settings
from .models import AnswerResponse, SourceDocument
from ..vector_store.bridge import search_documents as bridge_search
from ..vector_store.models import VectorMatch, VectorSearchResponse

logger = logging.getLogger(__name__)


class RAGService:
    """High-level RAG flow: retrieve supporting docs, craft prompt, call LLM."""

    def __init__(self, settings: RagSettings | None = None) -> None:
        self.settings = settings or get_settings()

    async def _search_via_http(self, question: str, top_k: int) -> Sequence[VectorMatch]:
        if not self.settings.vector_service_url:
            return []
        base = self.settings.vector_service_url.rstrip("/")
        endpoint = self.settings.vector_search_endpoint
        url = f"{base}{endpoint}"
        payload = {"query": question, "top_k": top_k}
        timeout = httpx.Timeout(self.settings.vector_request_timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        result = VectorSearchResponse(**data)
        return result.results

    async def search_vector_db(self, question: str, top_k: int | None = None) -> Sequence[VectorMatch]:
        size = top_k or self.settings.top_k
        if self.settings.vector_service_url:
            try:
                matches = await self._search_via_http(question, size)
                if matches:
                    return matches
                logger.warning("External vector service returned no results, falling back to in-process bridge")
            except Exception as exc:  # noqa: BLE001
                logger.warning("External vector service failed: %s", exc)
        response = await bridge_search(question, size)
        return response.results

    async def call_llm(self, prompt: str) -> str:
        provider = self.settings.llm_provider.lower()
        if provider == "ollama":
            return await self._call_ollama(prompt)
        if provider == "openai":
            return await self._call_openai(prompt)
        raise ValueError(f"Unsupported LLM provider: {self.settings.llm_provider}")

    async def _call_ollama(self, prompt: str) -> str:
        url = self.settings.ollama_base_url.rstrip("/") + "/api/generate"
        payload = {"model": self.settings.ollama_model, "prompt": prompt, "stream": False}
        timeout = httpx.Timeout(self.settings.ollama_timeout)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        answer = (data.get("response") or data.get("output") or "").strip()
        if not answer:
            raise RuntimeError("Ollama returned an empty response")
        return answer

    async def _call_openai(self, prompt: str) -> str:  # pragma: no cover - optional provider
        api_key = self.settings.openai_api_key
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        try:
            from openai import AsyncOpenAI  # type: ignore
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("The openai package is not installed") from exc
        client = AsyncOpenAI(api_key=api_key, base_url=self.settings.openai_base_url)
        response = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    def build_prompt(self, question: str, matches: Sequence[VectorMatch]) -> str:
        parts: List[str] = []
        for idx, match in enumerate(matches, start=1):
            snippet = match.text or match.metadata.get("summary") or "(无文本内容)"
            parts.append(f"[{idx}] {snippet}")
        context = "\n\n".join(parts) if parts else "暂无相关上下文信息"
        return self.settings.prompt_template.format(question=question, context=context)

    def format_sources(self, matches: Iterable[VectorMatch]) -> List[SourceDocument]:
        sources: List[SourceDocument] = []
        for match in matches:
            score = match.score or 0.0
            metadata = match.metadata or {}
            url = metadata.get("url") or metadata.get("source") or metadata.get("link")
            title = metadata.get("title") or metadata.get("source_name") or match.document_id
            sources.append(
                SourceDocument(
                    text=match.text or metadata.get("summary") or "",
                    url=url,
                    title=title,
                    score=score,
                )
            )
        return sources

    async def generate_answer(self, question: str) -> AnswerResponse:
        question = question.strip()
        if not question:
            raise ValueError("问题不能为空")
        matches = await self.search_vector_db(question)
        if not matches:
            return AnswerResponse(code="404", answer="抱歉，没有检索到相关的参考信息。", sources=[])
        prompt = self.build_prompt(question, matches)
        answer = await self.call_llm(prompt)
        sources = self.format_sources(matches)
        return AnswerResponse(answer=answer, sources=sources)


rag_service = RAGService()
