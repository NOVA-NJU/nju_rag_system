"""Core business logic for the vector store module."""
from __future__ import annotations

import json
import os
from typing import Dict, List

import chromadb
import numpy as np
from chromadb.config import Settings as ChromaSettings
from fastapi import HTTPException
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from .config import VectorSettings, get_settings
from .models import (
    ClearDbResponse,
    DocumentChunk,
    DocumentGetResponse,
    DocumentPayload,
    DocumentUpsertResponse,
    VectorMatch,
    VectorSearchRequest,
    VectorSearchResponse,
)


class VectorService:
    """Encapsulates embedding, chunking and ChromaDB persistence."""

    def __init__(self, settings: VectorSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client = chromadb.PersistentClient(
            path=self.settings.db_path,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
        )
        self._collection = None
        self._embedder = self._init_embedder()

    def _init_embedder(self) -> SentenceTransformer:
        load_kwargs = {"token": self.settings.HF_TOKEN} if self.settings.HF_TOKEN else {}
        return SentenceTransformer(self.settings.embedding_model, **load_kwargs)

    def _get_collection(self):
        if self._collection is None:
            self._collection = self._client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _allocate_id(self) -> str:
        os.makedirs(self.settings.db_path, exist_ok=True)
        counter_path = os.path.join(self.settings.db_path, "counter.json")
        current = 0
        if os.path.exists(counter_path):
            try:
                with open(counter_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    current = int(data.get("value", 0))
            except Exception:
                current = 0
        nxt = current + 1
        with open(counter_path, "w", encoding="utf-8") as handle:
            json.dump({"value": nxt}, handle)
        return str(nxt)

    def exists(self, document_id: str) -> bool:
        collection = self._get_collection()
        direct = collection.get(ids=[document_id])
        if direct and direct.get("ids"):
            return True
        chunks = collection.get(where={"parent_doc": document_id})
        return bool(chunks and chunks.get("ids"))

    def _embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, self.settings.embedding_dim))
        return self._embedder.encode(texts, normalize_embeddings=True)

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        if len(text) <= chunk_size:
            return [text]
        separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            length_function=len,
            separators=separators,
            keep_separator=True,
        )
        return [chunk.strip() for chunk in splitter.split_text(text) if chunk.strip()]

    async def upsert_document(self, payload: DocumentPayload) -> DocumentUpsertResponse:
        collection = self._get_collection()
        base_id = self._allocate_id()
        if len(payload.text) > self.settings.chunk_size:
            chunks = self._chunk_text(payload.text, self.settings.chunk_size, self.settings.chunk_overlap)
            ids: List[str] = []
            embeddings: List[List[float]] = []
            documents: List[str] = []
            metadatas: List[Dict] = []
            for idx, chunk in enumerate(chunks):
                chunk_id = f"{base_id}_chunk_{idx}"
                embedding = self._embed_texts([chunk])[0]
                ids.append(chunk_id)
                embeddings.append(embedding.tolist())
                documents.append(chunk)
                meta = {
                    **payload.metadata,
                    "parent_doc": base_id,
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                }
                if payload.url is not None:
                    meta["url"] = payload.url
                metadatas.append(meta)
            collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
        else:
            embedding = self._embed_texts([payload.text])[0]
            meta = dict(payload.metadata)
            if payload.url is not None:
                meta["url"] = payload.url
            collection.upsert(
                ids=[base_id],
                embeddings=[embedding.tolist()],
                documents=[payload.text],
                metadatas=[meta],
            )
        return DocumentUpsertResponse(document_id=base_id, status="stored")

    async def search(self, request: VectorSearchRequest) -> VectorSearchResponse:
        collection = self._get_collection()
        query_embedding = self._embed_texts([request.query])[0]
        raw = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=request.top_k,
            include=["metadatas", "distances", "documents"],
        )
        matches: List[VectorMatch] = []
        ids_list = raw.get("ids", [[]])
        distances_list = raw.get("distances", [[]])
        metadatas_list = raw.get("metadatas", [[]])
        documents_list = raw.get("documents", [[]])
        if ids_list and ids_list[0]:
            for idx, doc_id in enumerate(ids_list[0]):
                distance = distances_list[0][idx] if distances_list and distances_list[0] else 0.0
                raw_score = 1 - float(distance)
                score = round(raw_score, 4)
                metadata = metadatas_list[0][idx] if metadatas_list and metadatas_list[0] else {}
                document_text = documents_list[0][idx] if documents_list and documents_list[0] else None
                url = metadata.get("url")
                if "url" not in metadata:
                    metadata["url"] = url
                matches.append(VectorMatch(document_id=doc_id, score=score, text=document_text, metadata=metadata))
        else:
            fallback = collection.get(
                where_document={"$contains": request.query},
                include=["documents", "metadatas"],
            )
            f_ids = fallback.get("ids") or []
            f_docs = fallback.get("documents") or []
            f_metas = fallback.get("metadatas") or []
            for idx, doc_id in enumerate(f_ids[: request.top_k]):
                meta = f_metas[idx] if idx < len(f_metas) else {}
                doc_text = f_docs[idx] if idx < len(f_docs) else None
                matches.append(VectorMatch(document_id=doc_id, score=0.0, text=doc_text, metadata=meta))
        return VectorSearchResponse(results=matches, query=request.query, top_k=request.top_k)

    async def get_document_by_id(self, document_id: str) -> DocumentGetResponse:
        collection = self._get_collection()
        result = collection.get(ids=[document_id], include=["documents", "metadatas"])
        ids = result.get("ids") or []
        if ids:
            return DocumentGetResponse(
                document_id=document_id,
                text=(result.get("documents") or [None])[0],
                metadata=(result.get("metadatas") or [{}])[0],
            )
        chunks = collection.get(where={"parent_doc": document_id}, include=["documents", "metadatas"])
        chunk_ids = chunks.get("ids") or []
        if not chunk_ids and document_id.isdigit():
            chunks = collection.get(where={"parent_doc": int(document_id)}, include=["documents", "metadatas"])
            chunk_ids = chunks.get("ids") or []
        if not chunk_ids:
            raise HTTPException(status_code=404, detail="document not found")
        docs = chunks.get("documents") or []
        metas = chunks.get("metadatas") or []
        items: List[tuple] = []
        for idx, chunk_id in enumerate(chunk_ids):
            meta = metas[idx] if idx < len(metas) else {}
            chunk_index = meta.get("chunk_index", idx)
            text = docs[idx] if idx < len(docs) else ""
            items.append((chunk_index, chunk_id, text, meta))
        items.sort(key=lambda item: item[0])
        out_chunks = [DocumentChunk(chunk_id=cid, text=txt, metadata=m) for _, cid, txt, m in items]
        joined_content = "".join(txt for _, _, txt, _ in items if isinstance(txt, str))
        base_meta = items[0][3] if items else {}
        parent_meta = {k: v for k, v in base_meta.items() if k not in {"chunk_index", "total_chunks"}}
        parent_meta["chunk_count"] = len(out_chunks)
        return DocumentGetResponse(document_id=document_id, text=joined_content, chunks=out_chunks, metadata=parent_meta)

    async def clear_db(self) -> ClearDbResponse:
        try:
            self._client.delete_collection("documents")
        except Exception:
            pass
        self._collection = None
        self._get_collection()
        counter_path = os.path.join(self.settings.db_path, "counter.json")
        try:
            if os.path.exists(counter_path):
                os.remove(counter_path)
        except Exception:
            pass
        return ClearDbResponse(status="cleared")


default_service = VectorService()
vector_service = default_service
