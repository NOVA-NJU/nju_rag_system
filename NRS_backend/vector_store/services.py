"""Core business logic for the vector store module."""  # 向量存储模块的核心业务逻辑
from __future__ import annotations  # 兼容未来类型注解语法

import json  # JSON数据处理
import os  # 操作系统接口，用于文件操作
from typing import Dict, List  # 类型注解：Dict字典，List列表

import chromadb  # ChromaDB向量数据库客户端
import numpy as np  # NumPy数组处理
from chromadb.config import Settings as ChromaSettings  # ChromaDB配置设置
from fastapi import HTTPException  # FastAPI HTTP异常
from langchain_text_splitters import RecursiveCharacterTextSplitter  # 递归字符文本分割器
from sentence_transformers import SentenceTransformer  # 句子变换器，用于文本嵌入

from .config import VectorSettings, get_settings  # 导入配置类和工厂函数
from .models import (  # 导入数据模型
    ClearDbResponse,  # 清库响应
    DocumentChunk,  # 文档分块
    DocumentGetResponse,  # 文档获取响应
    DocumentPayload,  # 文档载荷
    DocumentUpsertResponse,  # 文档插入响应
    VectorMatch,  # 向量匹配
    VectorSearchRequest,  # 向量搜索请求
    VectorSearchResponse,  # 向量搜索响应
)


class VectorService:
    """Encapsulates embedding, chunking and ChromaDB persistence."""  # 封装嵌入、分块和ChromaDB持久化的服务类

    def __init__(self, settings: VectorSettings | None = None) -> None:
        self.settings = settings or get_settings()  # 初始化设置，如果未提供则使用默认配置
        self._client = chromadb.PersistentClient(  # 创建持久化ChromaDB客户端
            path=self.settings.db_path,  # 指定数据库路径
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),  # 配置设置：禁用匿名遥测，允许重置
        )
        self._collection = None  # 集合对象，延迟初始化
        self._embedder = self._init_embedder()  # 初始化嵌入器

    def _init_embedder(self) -> SentenceTransformer:
        load_kwargs = {"token": self.settings.HF_TOKEN} if self.settings.HF_TOKEN else {}  # 如果有HF令牌则添加到加载参数
        return SentenceTransformer(self.settings.embedding_model, **load_kwargs)  # 创建句子变换器实例

    def _get_collection(self):
        if self._collection is None:  # 如果集合未初始化
            self._collection = self._client.get_or_create_collection(  # 获取或创建集合
                name="documents",  # 集合名称
                metadata={"hnsw:space": "cosine"},  # 元数据：使用余弦相似度
            )
        return self._collection  # 返回集合对象

    def _allocate_id(self) -> str:
        os.makedirs(self.settings.db_path, exist_ok=True)  # 确保数据库目录存在
        counter_path = os.path.join(self.settings.db_path, "counter.json")  # 计数器文件路径
        current = 0  # 当前计数器值
        if os.path.exists(counter_path):  # 如果计数器文件存在
            try:
                with open(counter_path, "r", encoding="utf-8") as handle:  # 读取计数器文件
                    data = json.load(handle)  # 解析JSON数据
                    current = int(data.get("value", 0))  # 获取当前值
            except Exception:  # 异常处理
                current = 0  # 默认值为0
        nxt = current + 1  # 计算下一个ID
        with open(counter_path, "w", encoding="utf-8") as handle:  # 写入新的计数器值
            json.dump({"value": nxt}, handle)  # 保存为JSON
        return str(nxt)  # 返回字符串形式的ID

    def exists(self, document_id: str) -> bool:
        collection = self._get_collection()  # 获取集合
        direct = collection.get(ids=[document_id])  # 直接查询文档
        if direct and direct.get("ids"):  # 如果找到直接文档
            return True  # 返回True
        chunks = collection.get(where={"parent_doc": document_id})  # 查询分块文档
        return bool(chunks and chunks.get("ids"))  # 返回是否存在分块

    def _embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:  # 如果文本列表为空
            return np.empty((0, self.settings.embedding_dim))  # 返回空数组
        return self._embedder.encode(texts, normalize_embeddings=True)  # 编码文本并归一化嵌入

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        if len(text) <= chunk_size:  # 如果文本长度小于等于分块大小
            return [text]  # 直接返回原文本
        separators = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]  # 定义分隔符列表
        splitter = RecursiveCharacterTextSplitter(  # 创建递归字符分割器
            chunk_size=chunk_size,  # 分块大小
            chunk_overlap=overlap,  # 分块重叠
            length_function=len,  # 长度函数
            separators=separators,  # 分隔符
            keep_separator=True,  # 保留分隔符
        )
        return [chunk.strip() for chunk in splitter.split_text(text) if chunk.strip()]  # 分割文本并清理空白

    async def upsert_document(self, payload: DocumentPayload) -> DocumentUpsertResponse:
        collection = self._get_collection()  # 获取集合
        base_id = self._allocate_id()  # 分配基础ID
        if len(payload.text) > self.settings.chunk_size:  # 如果文本长度超过分块大小
            chunks = self._chunk_text(payload.text, self.settings.chunk_size, self.settings.chunk_overlap)  # 分割文本
            ids: List[str] = []  # ID列表
            embeddings: List[List[float]] = []  # 嵌入列表
            documents: List[str] = []  # 文档列表
            metadatas: List[Dict] = []  # 元数据列表
            for idx, chunk in enumerate(chunks):  # 遍历分块
                chunk_id = f"{base_id}_chunk_{idx}"  # 生成分块ID
                embedding = self._embed_texts([chunk])[0]  # 计算嵌入
                ids.append(chunk_id)  # 添加ID
                embeddings.append(embedding.tolist())  # 添加嵌入
                documents.append(chunk)  # 添加文档
                meta = {  # 构建元数据
                    **payload.metadata,  # 复制原始元数据
                    "parent_doc": base_id,  # 父文档ID
                    "chunk_index": idx,  # 分块索引
                    "total_chunks": len(chunks),  # 总分块数
                }
                if payload.url is not None:  # 如果有URL
                    meta["url"] = payload.url  # 添加URL到元数据
                metadatas.append(meta)  # 添加元数据
            collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)  # 批量插入
        else:  # 如果不需要分块
            embedding = self._embed_texts([payload.text])[0]  # 计算嵌入
            meta = dict(payload.metadata)  # 复制元数据
            if payload.url is not None:  # 如果有URL
                meta["url"] = payload.url  # 添加URL
            collection.upsert(  # 插入单个文档
                ids=[base_id],  # ID列表
                embeddings=[embedding.tolist()],  # 嵌入列表
                documents=[payload.text],  # 文档列表
                metadatas=[meta],  # 元数据列表
            )
        return DocumentUpsertResponse(document_id=base_id, status="stored")  # 返回插入响应

    async def search(self, request: VectorSearchRequest) -> VectorSearchResponse:
        collection = self._get_collection()  # 获取集合
        query_embedding = self._embed_texts([request.query])[0]  # 计算查询文本的嵌入
        raw = collection.query(  # 执行向量查询
            query_embeddings=[query_embedding.tolist()],  # 查询嵌入
            n_results=request.top_k,  # 返回结果数量
            include=["metadatas", "distances", "documents"],  # 包含元数据、距离和文档
        )
        matches: List[VectorMatch] = []  # 初始化匹配结果列表
        ids_list = raw.get("ids", [[]])  # 获取ID列表
        distances_list = raw.get("distances", [[]])  # 获取距离列表
        metadatas_list = raw.get("metadatas", [[]])  # 获取元数据列表
        documents_list = raw.get("documents", [[]])  # 获取文档列表
        if ids_list and ids_list[0]:  # 如果有查询结果
            for idx, doc_id in enumerate(ids_list[0]):  # 遍历结果
                distance = distances_list[0][idx] if distances_list and distances_list[0] else 0.0  # 获取距离
                raw_score = 1 - float(distance)  # 计算原始分数（1-距离）
                score = round(raw_score, 4)  # 四舍五入到4位小数
                metadata = metadatas_list[0][idx] if metadatas_list and metadatas_list[0] else {}  # 获取元数据
                document_text = documents_list[0][idx] if documents_list and documents_list[0] else None  # 获取文档文本
                url = metadata.get("url")  # 获取URL
                if "url" not in metadata:  # 如果元数据中没有URL
                    metadata["url"] = url  # 添加URL到元数据
                matches.append(VectorMatch(document_id=doc_id, score=score, text=document_text, metadata=metadata))  # 添加匹配结果
        else:  # 如果没有向量查询结果，使用文本包含回退
            fallback = collection.get(  # 执行文本包含查询
                where_document={"$contains": request.query},  # 文档包含查询文本
                include=["documents", "metadatas"],  # 包含文档和元数据
            )
            f_ids = fallback.get("ids") or []  # 获取回退ID列表
            f_docs = fallback.get("documents") or []  # 获取回退文档列表
            f_metas = fallback.get("metadatas") or []  # 获取回退元数据列表
            for idx, doc_id in enumerate(f_ids[: request.top_k]):  # 遍历前top_k个结果
                meta = f_metas[idx] if idx < len(f_metas) else {}  # 获取元数据
                doc_text = f_docs[idx] if idx < len(f_docs) else None  # 获取文档文本
                matches.append(VectorMatch(document_id=doc_id, score=0.0, text=doc_text, metadata=meta))  # 添加匹配结果（分数为0）
        return VectorSearchResponse(results=matches, query=request.query, top_k=request.top_k)  # 返回搜索响应

    async def get_document_by_id(self, document_id: str) -> DocumentGetResponse:
        collection = self._get_collection()  # 获取集合
        result = collection.get(ids=[document_id], include=["documents", "metadatas"])  # 根据ID获取文档
        ids = result.get("ids") or []  # 获取ID列表
        if ids:  # 如果找到直接文档
            return DocumentGetResponse(  # 返回文档响应
                document_id=document_id,  # 文档ID
                text=(result.get("documents") or [None])[0],  # 文档文本
                metadata=(result.get("metadatas") or [{}])[0],  # 文档元数据
            )
        chunks = collection.get(where={"parent_doc": document_id}, include=["documents", "metadatas"])  # 查询分块文档
        chunk_ids = chunks.get("ids") or []  # 获取分块ID列表
        if not chunk_ids and document_id.isdigit():  # 如果没有找到分块且ID是数字
            chunks = collection.get(where={"parent_doc": int(document_id)}, include=["documents", "metadatas"])  # 按整数ID查询
            chunk_ids = chunks.get("ids") or []  # 获取分块ID列表
        if not chunk_ids:  # 如果仍然没有找到
            raise HTTPException(status_code=404, detail="document not found")  # 抛出404异常
        docs = chunks.get("documents") or []  # 获取文档列表
        metas = chunks.get("metadatas") or []  # 获取元数据列表
        items: List[tuple] = []  # 初始化项目列表
        for idx, chunk_id in enumerate(chunk_ids):  # 遍历分块ID
            meta = metas[idx] if idx < len(metas) else {}  # 获取元数据
            chunk_index = meta.get("chunk_index", idx)  # 获取分块索引
            text = docs[idx] if idx < len(docs) else ""  # 获取文本
            items.append((chunk_index, chunk_id, text, meta))  # 添加到项目列表
        items.sort(key=lambda item: item[0])  # 按分块索引排序
        out_chunks = [DocumentChunk(chunk_id=cid, text=txt, metadata=m) for _, cid, txt, m in items]  # 创建输出分块列表
        joined_content = "".join(txt for _, _, txt, _ in items if isinstance(txt, str))  # 拼接所有分块文本
        base_meta = items[0][3] if items else {}  # 获取基础元数据
        parent_meta = {k: v for k, v in base_meta.items() if k not in {"chunk_index", "total_chunks"}}  # 过滤元数据
        parent_meta["chunk_count"] = len(out_chunks)  # 添加分块数量
        return DocumentGetResponse(document_id=document_id, text=joined_content, chunks=out_chunks, metadata=parent_meta)  # 返回文档响应

    async def clear_db(self) -> ClearDbResponse:
        try:
            self._client.delete_collection("documents")  # 尝试删除集合
        except Exception:  # 忽略异常
            pass
        self._collection = None  # 重置集合对象
        self._get_collection()  # 重新创建集合
        counter_path = os.path.join(self.settings.db_path, "counter.json")  # 计数器文件路径
        try:
            if os.path.exists(counter_path):  # 如果计数器文件存在
                os.remove(counter_path)  # 删除计数器文件
        except Exception:  # 忽略异常
            pass
        return ClearDbResponse(status="cleared")  # 返回清空响应


default_service = VectorService()  # 创建默认服务实例
vector_service = default_service  # 设置全局向量服务变量
