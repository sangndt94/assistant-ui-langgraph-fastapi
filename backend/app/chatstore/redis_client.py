import os
import json
import numpy as np
import asyncio
from redis import Redis
from redis.asyncio import Redis as AsyncRedis
from redisvl.index import SearchIndex, AsyncSearchIndex
from redisvl.query import VectorQuery
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from sentence_transformers import SentenceTransformer
import redisvl

# Debug version
print(f"[Debug] redisvl version: {redisvl.__version__}")

# Environment config
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Redis + Embedding config
AGENT_NAME = os.getenv("AGENT_NAME", "core_agent")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))
INDEX_NAME = os.getenv("INDEX_NAME", f"{AGENT_NAME}_index")
KEY_PREFIX = os.getenv("KEY_PREFIX", f"{AGENT_NAME}_docs")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
_model = SentenceTransformer(EMBEDDING_MODEL)

# RedisVL schema definition
schema = {
    "index": {"name": INDEX_NAME, "prefix": KEY_PREFIX},
    "fields": [
        {"name": "id", "type": "text"},
        {"name": "text", "type": "text"},
        {"name": "agent", "type": "tag"},
        {"name": "user_id", "type": "tag"},
        {"name": "session_id", "type": "tag"},
        {
            "name": "embedding",
            "type": "vector",
            "attrs": {
                "dims": EMBEDDING_DIM,
                "distance_metric": "cosine",
                "algorithm": "flat",
                "datatype": "float32"
            }
        }
    ]
}

# Redis clients
get_redis_client = lambda: Redis.from_url(REDIS_URL, decode_responses=True)
get_async_redis_client = lambda: AsyncRedis.from_url(REDIS_URL, decode_responses=True)
redis_client = get_redis_client()
async_redis_client = get_async_redis_client()
search_index = SearchIndex.from_dict(schema, redis_client=redis_client)
async_search_index = AsyncSearchIndex.from_dict(schema, redis_client=async_redis_client)

async def ensure_index_exists():
    if not await async_search_index.exists():
        await async_search_index.create(overwrite=True)

# Embedding
embedding_fn_sync = lambda text: _model.encode(text).tolist()
async def embedding_fn(text):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, embedding_fn_sync, text)

# Save chat
async def save_chat_to_vector(agent, user_id, session_id, messages, embedding_fn=embedding_fn):
    await ensure_index_exists()

    doc_id = f"{agent}:{user_id}:{session_id}"
    custom_key = f"{KEY_PREFIX}:{doc_id}"

    # 1️⃣ Không đọc lại Redis, chỉ ghi đè bằng messages hiện tại
    new_message_texts = []
    for m in messages:
        if isinstance(m, HumanMessage):
            new_message_texts.append({"role": "user", "type": "text", "text": m.content})
        elif isinstance(m, AIMessage):
            new_message_texts.append({"role": "assistant", "type": "text", "text": [{"type": "text", "text": m.content}]})

    full_text = json.dumps(new_message_texts, ensure_ascii=False)

    # 2️⃣ Ghi đè Redis (full đoạn hội thoại hiện tại)
    embedding = await embedding_fn(full_text)
    embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()

    data = [{
        "id": doc_id,
        "text": full_text,
        "agent": agent,
        "user_id": user_id,
        "session_id": session_id,
        "embedding": embedding_bytes
    }]

    await async_search_index.load(data, keys=[custom_key])
    await async_redis_client.hset(custom_key, mapping={"text": full_text})
    return {"status": "ok", "session_id": session_id}

# Search
async def search_chat_history(query_text, agent=None, user_id=None, session_id=None, k=3):
    embedding = await embedding_fn(query_text)
    filters = []
    if agent: filters.append(f"@agent:{{{agent}}}")
    if user_id: filters.append(f"@user_id:{{{user_id}}}")
    if session_id: filters.append(f"@session_id:{{{session_id}}}")
    query = VectorQuery(
        vector=embedding,
        vector_field_name="embedding",
        return_fields=["id", "text", "agent", "user_id", "session_id", "vector_distance"],
        num_results=k,
        return_score=True
    )
    if filters:
        query = query.filter(" ".join(filters))
    await ensure_index_exists()
    return await async_search_index.query(query)

# Delete
async def delete_chat_document(agent, user_id, session_id):
    results = await search_chat_history("", agent, user_id, session_id, k=10)
    deleted = 0
    for r in results:
        redis_key = r.get("id")
        if redis_key:
            await async_redis_client.delete(redis_key)
            deleted += 1
    return deleted

# Clear all
async def clear_chat_data():
    await ensure_index_exists()
    return await async_search_index.clear()

# Delete index
async def delete_chat_index():
    if await async_search_index.exists():
        await async_search_index.delete()

# Stats
async def get_index_stats():
    await ensure_index_exists()
    return {"exists": await async_search_index.exists(), "name": INDEX_NAME, "prefix": KEY_PREFIX}


async def load_chat_history_vecter(agent: str, user_id: str, session_id: str) -> str:
    filters = [
        f"@agent:{{{agent}}}",
        f"@user_id:{{{user_id}}}",
        f"@session_id:{{{session_id}}}"
    ]
    query = VectorQuery(
        vector=[0.0] * 384,
        vector_field_name="embedding",
        return_fields=["text"],
        num_results=1,
        return_score=False
    )
    query.filter.expression = " ".join(filters)

    results = await async_search_index.query(query)
    if results and "text" in results[0]:
        return results[0]["text"]
    return "[]"

async def load_chat_history(agent: str, user_id: str, session_id: str) -> str:
    redis_key = f"{KEY_PREFIX}:{agent}:{user_id}:{session_id}"
    try:
        value = await async_redis_client.hget(redis_key, "text")
        if value:
            print(f"[Redis] ✅ Loaded history from key: {redis_key}")
        else:
            print(f"[Redis] ⚠️ No history found for key: {redis_key}")
        return value or "[]"
    except Exception as e:
        print(f"[Redis] ❌ Failed to load chat history: {e}")
        return "[]"