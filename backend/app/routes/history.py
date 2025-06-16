import os
import re
import uuid
import logging
from typing import Optional, List, Dict, Any

import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from redisvl.index import AsyncSearchIndex
from redisvl.query import VectorQuery, FilterQuery
from sentence_transformers import SentenceTransformer
from chatstore.redis_client import REDIS_URL, AGENT_NAME, INDEX_NAME, KEY_PREFIX, EMBEDDING_DIM, _model as model, schema


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def escape_tag_value(val: str) -> str:
    return re.sub(r'([{}\\()\[\]\s:;@\-])', r'\\\\\\1', val)

class ChatRequest(BaseModel):
    agent: str
    user_id: str
    session_id: str

class ChatResponse(BaseModel):
    id: str
    text: str
    agent: str
    user_id: str
    session_id: str
    timestamp: Optional[float] = 0.0
    score: float = 0.0

class ChatListResponse(BaseModel):
    results: List[ChatResponse]
    total: int
    debug_info: Optional[Dict[str, Any]] = None

class SearchRequest(ChatRequest):
    query_text: str

class RedisManager:
    def __init__(self):
        self._client = None
        self._index = None

    async def get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis.from_url(REDIS_URL, decode_responses=False)
            await self._client.ping()
        return self._client

    async def get_index(self) -> AsyncSearchIndex:
        if self._index is None:
            self._index = AsyncSearchIndex.from_dict(schema, redis_client=await self.get_client())
        return self._index

    async def ensure_index_exists(self):
        index = await self.get_index()
        if not await index.exists():
            await index.create(overwrite=True)

redis_manager = RedisManager()

def safe_parse_result(result: Dict[str, Any]) -> Optional[ChatResponse]:
    try:
        return ChatResponse(
            id=str(result.get("id", "")),
            text=str(result.get("text", "")),
            agent=str(result.get("agent", "")),
            user_id=str(result.get("user_id", "")),
            session_id=str(result.get("session_id", "")),
            timestamp=float(result.get("timestamp", 0.0)),
            score=float(result.get("vector_distance", 0.0))
        )
    except Exception as e:
        logger.warning(f"Parse failed: {e}")
        return None

async def query_with_filter_only(index: AsyncSearchIndex, agent: str, user_id: str, session_id: str) -> List[Dict[str, Any]]:
    filter_expr = (
        f"@agent:{{{escape_tag_value(agent)}}} "
        f"@user_id:{{{escape_tag_value(user_id)}}} "
        f"@session_id:{{{escape_tag_value(session_id)}}}"
    )
    query = FilterQuery(
        return_fields=["id", "text", "agent", "user_id", "session_id", "timestamp"],
        filter_expression=filter_expr,
        num_results=1000
    )
    return await index.query(query)

async def query_by_redis_scan(client: redis.Redis, agent: str, user_id: str, session_id: str) -> List[Dict[str, Any]]:
    pattern = f"{KEY_PREFIX}:*"
    results = []
    async for key in client.scan_iter(match=pattern, count=100):
        try:
            doc = await client.hgetall(key)
            if doc:
                doc_decoded = {}
                for k, v in doc.items():
                    if k == b"embedding":
                        continue
                    try:
                        doc_decoded[k.decode()] = v.decode()
                    except Exception:
                        continue
                if (doc_decoded.get("agent") == agent and
                    doc_decoded.get("user_id") == user_id and
                    doc_decoded.get("session_id") == session_id):
                    doc_decoded["__redis_key__"] = key.decode()
                    results.append(doc_decoded)
        except Exception as e:
            logger.warning(f"Scan failed for {key}: {e}")
    return results

def build_history_router(prefix="/api") -> APIRouter:
    router = APIRouter(prefix=prefix)

    @router.post("/chat/get", response_model=ChatListResponse)
    async def get_chat_by_session(request: ChatRequest):
        await redis_manager.ensure_index_exists()
        index = await redis_manager.get_index()
        client = await redis_manager.get_client()
        debug_info = {"methods_tried": [], "successful_method": None}

        try:
            debug_info["methods_tried"].append("FilterQuery")
            results = await query_with_filter_only(index, request.agent, request.user_id, request.session_id)
            if not results:
                debug_info["methods_tried"].append("Redis_SCAN")
                results = await query_by_redis_scan(client, request.agent, request.user_id, request.session_id)
                debug_info["successful_method"] = "Redis_SCAN"
            else:
                debug_info["successful_method"] = "FilterQuery"

            chats = [safe_parse_result(r) for r in results if safe_parse_result(r)]
            chats.sort(key=lambda x: x.timestamp, reverse=True)
            return ChatListResponse(results=chats, total=len(chats), debug_info=debug_info)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Get failed: {e}")

    @router.post("/chat/search", response_model=ChatListResponse)
    async def search_chat(req: SearchRequest):
        await redis_manager.ensure_index_exists()
        index = await redis_manager.get_index()
        query_vector = model.encode(req.query_text).tolist()
        filter_expr = (
            f"@agent:{{{escape_tag_value(req.agent)}}} "
            f"@user_id:{{{escape_tag_value(req.user_id)}}} "
            f"@session_id:{{{escape_tag_value(req.session_id)}}}"
        )
        query = VectorQuery(
            vector=query_vector,
            vector_field_name="embedding",
            filter_expression=filter_expr,
            return_fields=["id", "text", "agent", "user_id", "session_id", "timestamp", "vector_distance"],
            num_results=10,
            return_score=True
        )
        try:
            results = await index.query(query)
            chats = [safe_parse_result(r) for r in results if safe_parse_result(r)]
            chats.sort(key=lambda x: x.score)
            return ChatListResponse(results=chats, total=len(chats))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    @router.delete("/chat/delete")
    async def delete_chat_session(request: ChatRequest):
        await redis_manager.ensure_index_exists()
        client = await redis_manager.get_client()
        results = await query_by_redis_scan(client, request.agent, request.user_id, request.session_id)
        deleted_keys = []

        for doc in results:
            redis_key = doc.get("__redis_key__")
            if redis_key:
                await client.delete(redis_key)
                deleted_keys.append(redis_key)

        return {"success": True, "deleted_count": len(deleted_keys), "deleted_keys": deleted_keys}

    return router
