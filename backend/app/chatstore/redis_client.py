import os
import numpy as np
from redisvl.index import SearchIndex, AsyncSearchIndex
from redisvl.query import VectorQuery
from langchain_core.messages import HumanMessage, BaseMessage
from sentence_transformers import SentenceTransformer
import asyncio
import redisvl
from redis import Redis
from redis.asyncio import Redis as AsyncRedis

# Print redisvl version for debugging
print(f"[Debug] redisvl version: {redisvl.__version__}")

# Set environment variable to avoid tokenizers parallelism warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Cấu hình Redis và mô hình embedding
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
print(f"[Debug] REDIS_URL: {REDIS_URL}")
_model = SentenceTransformer("all-MiniLM-L6-v2")
VECTOR_DIM = 384
INDEX_NAME = "chat_index"
KEY_PREFIX = "chat_docs"

# Schema definition theo chuẩn RedisVL
schema = {
    "index": {
        "name": INDEX_NAME,
        "prefix": KEY_PREFIX,
    },
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
                "dims": VECTOR_DIM,
                "distance_metric": "cosine",
                "algorithm": "flat",
                "datatype": "float32"
            }
        }
    ]
}

# Khởi tạo client Redis (đồng bộ và bất đồng bộ)
def get_redis_client():
    """Tạo và trả về client Redis đồng bộ."""
    return Redis.from_url(REDIS_URL, decode_responses=True)

def get_async_redis_client():
    """Tạo và trả về client Redis bất đồng bộ."""
    return AsyncRedis.from_url(REDIS_URL, decode_responses=True)

# Khởi tạo SearchIndex
def get_search_index():
    """Tạo SearchIndex với Redis client đồng bộ."""
    client = get_redis_client()
    return SearchIndex.from_dict(schema, redis_client=client, validate_on_load=True)

def get_async_search_index():
    """Tạo AsyncSearchIndex với Redis client bất đồng bộ."""
    client = get_async_redis_client()
    return AsyncSearchIndex.from_dict(schema, redis_client=client, validate_on_load=True)

# Global instances
redis_client = get_redis_client()
search_index = get_search_index()
async_redis_client = get_async_redis_client()
async_search_index = get_async_search_index()

async def ensure_index_exists():
    """Đảm bảo index tồn tại sử dụng AsyncSearchIndex."""
    try:
        exists = await async_search_index.exists()
        print(f"[Debug] Index exists: {exists}")
        if not exists:
            await async_search_index.create(overwrite=True)
            print(f"[Debug] Index created: {INDEX_NAME}")
    except Exception as e:
        print(f"[Error] Failed to ensure index exists: {str(e)}")
        raise

async def add_vector_document(doc_id: str, text: str, agent: str, user_id: str, session_id: str, embedding_fn):
    """Thêm document với embedding vào Redis theo chuẩn RedisVL."""
    try:
        embedding = await embedding_fn(text)
        print(f"[Debug] Generated embedding for doc_id: {doc_id}")
        
        # Convert embedding list to bytes theo chuẩn RedisVL
        embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
        print(f"[Debug] Embedding converted to bytes for doc_id: {doc_id}")
        
        # Đảm bảo index tồn tại
        await ensure_index_exists()
        
        # Tạo custom key để tránh duplicate
        custom_key = f"{KEY_PREFIX}:{doc_id}"
        
        # Tạo data object theo schema với custom key
        data = [{
            "id": doc_id,
            "text": text,
            "agent": agent,
            "user_id": user_id,
            "session_id": session_id,
            "embedding": embedding_bytes
        }]
        
        # Sử dụng load method với custom keys để upsert
        keys = await async_search_index.load(data, keys=[custom_key])
        print(f"[Debug] Document loaded/updated with keys: {keys}")
        return keys
        
    except Exception as e:
        print(f"[Error] Failed to add document: {str(e)}")
        raise

async def search_vector_document(query_embedding: list[float], k: int = 3, filter_expr: str = None):
    """Tìm kiếm document dựa trên embedding sử dụng VectorQuery."""
    try:
        await ensure_index_exists()
        
        # Tạo VectorQuery object theo chuẩn RedisVL
        query = VectorQuery(
            vector=query_embedding,  # RedisVL sẽ tự động convert sang bytes
            vector_field_name="embedding",
            return_fields=["id", "text", "agent", "user_id", "session_id", "vector_distance"],
            num_results=k,
            return_score=True
        )
        
        # Thêm filter nếu có
        if filter_expr:
            query = query.filter(filter_expr)
        
        results = await async_search_index.query(query)
        print(f"[Debug] Search results: {results}")
        return results
        
    except Exception as e:
        print(f"[Error] Failed to search documents: {str(e)}")
        raise

def embedding_fn_sync(text: str) -> list[float]:
    """Tạo embedding đồng bộ."""
    return _model.encode(text).tolist()

async def embedding_fn(text: str) -> list[float]:
    """Tạo embedding bất đồng bộ."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, embedding_fn_sync, text)

async def save_chat_to_vector(agent: str, user_id: str, session_id: str, messages: list[BaseMessage], embedding_fn=embedding_fn):
    """Lưu chat vào vector database với cấu trúc mới - tránh duplicate bằng cách upsert."""
    print(f"[Debug] Agent: {agent}")
    print(f"[Debug] User ID: {user_id}")
    print(f"[Debug] Session ID: {session_id}")
    print(f"[Debug] Messages: {messages}")

    # Tạo full text từ các HumanMessage
    full_text = "\n".join(
        m.content if isinstance(m.content, str) else str(m.content)
        for m in messages if isinstance(m, HumanMessage)
    )
    print(f"[Debug] Full text: {full_text}")

    # Tạo doc_id từ agent, user_id và session_id
    doc_id = f"{agent}:{user_id}:{session_id}"
    
    # Kiểm tra xem document đã tồn tại chưa
    try:
        existing_results = await search_chat_history("", agent=agent, user_id=user_id, session_id=session_id, k=1)
        if existing_results:
            print(f"[Debug] Found existing document for {doc_id}, will update")
            # Xóa document cũ trước khi thêm mới
            await delete_chat_document(agent, user_id, session_id)
    except Exception as e:
        print(f"[Debug] No existing document found for {doc_id}: {str(e)}")

    try:
        keys = await add_vector_document(
            doc_id=doc_id, 
            text=full_text, 
            agent=agent,
            user_id=user_id,
            session_id=session_id,
            embedding_fn=embedding_fn
        )
        print(f"[Debug] Chat saved with keys: {keys}")
        return keys
    except Exception as e:
        print(f"[Error] Failed to save chat: {str(e)}")
        raise Exception(f"[RedisVL] Failed to save chat: {str(e)}")

async def search_chat_history(query_text: str, agent: str = None, user_id: str = None, session_id: str = None, k: int = 3):
    """Tìm kiếm chat history với các filter tùy chọn."""
    try:
        # Tạo embedding cho query
        query_embedding = await embedding_fn(query_text)
        
        # Tạo filter expression nếu có
        filters = []
        if agent:
            filters.append(f"@agent:{{{agent}}}")
        if user_id:
            filters.append(f"@user_id:{{{user_id}}}")
        if session_id:
            filters.append(f"@session_id:{{{session_id}}}")
        
        filter_expr = " ".join(filters) if filters else None
        
        # Thực hiện search
        results = await search_vector_document(query_embedding, k=k, filter_expr=filter_expr)
        return results
        
    except Exception as e:
        print(f"[Error] Failed to search chat history: {str(e)}")
        raise

async def delete_chat_document(agent: str, user_id: str, session_id: str):
    """Xóa một document cụ thể dựa trên agent, user_id, session_id."""
    try:
        # Tìm document cần xóa
        results = await search_chat_history("", agent=agent, user_id=user_id, session_id=session_id, k=10)
        
        if not results:
            print(f"[Debug] No document found to delete for {agent}:{user_id}:{session_id}")
            return 0
        
        # Xóa tất cả documents matching criteria
        deleted_count = 0
        for result in results:
            try:
                # Lấy Redis key từ result
                redis_key = result.get('id', '')  # Hoặc có thể là key khác tùy theo cách RedisVL trả về
                if redis_key:
                    # Sử dụng Redis client để xóa trực tiếp
                    await async_redis_client.delete(redis_key)
                    deleted_count += 1
                    print(f"[Debug] Deleted document with key: {redis_key}")
            except Exception as e:
                print(f"[Error] Failed to delete document: {str(e)}")
                continue
        
        return deleted_count
        
    except Exception as e:
        print(f"[Error] Failed to delete chat document: {str(e)}")
        raise

async def clear_chat_data():
    """Xóa tất cả data của index."""
    try:
        await ensure_index_exists()
        count = await async_search_index.clear()
        print(f"[Debug] Cleared {count} documents from index")
        return count
    except Exception as e:
        print(f"[Error] Failed to clear chat data: {str(e)}")
        raise

async def delete_chat_index():
    """Xóa hoàn toàn index và data."""
    try:
        if await async_search_index.exists():
            await async_search_index.delete()
            print(f"[Debug] Index {INDEX_NAME} deleted completely")
        else:
            print(f"[Debug] Index {INDEX_NAME} does not exist")
    except Exception as e:
        print(f"[Error] Failed to delete chat index: {str(e)}")
        raise

# Utility functions
async def get_index_stats():
    """Lấy thống kê của index."""
    try:
        await ensure_index_exists()
        # Note: stats method cần được implement nếu có trong AsyncSearchIndex
        # Tạm thời return basic info
        exists = await async_search_index.exists()
        return {"exists": exists, "name": INDEX_NAME, "prefix": KEY_PREFIX}
    except Exception as e:
        print(f"[Error] Failed to get index stats: {str(e)}")
        raise

async def save_chat_to_vector_v2(agent: str, user_id: str, session_id: str, messages: list[BaseMessage], embedding_fn=embedding_fn):
    """
    Phiên bản cải tiến để lưu chat - sử dụng timestamp để tránh duplicate.
    Mỗi lần chat sẽ tạo một document mới với timestamp.
    """
    import time
    
    print(f"[Debug] Agent: {agent}")
    print(f"[Debug] User ID: {user_id}")
    print(f"[Debug] Session ID: {session_id}")
    print(f"[Debug] Messages: {messages}")

    # Tạo full text từ các HumanMessage
    full_text = "\n".join(
        m.content if isinstance(m.content, str) else str(m.content)
        for m in messages if isinstance(m, HumanMessage)
    )
    print(f"[Debug] Full text: {full_text}")

    # Tạo doc_id với timestamp để đảm bảo unique
    timestamp = int(time.time() * 1000)  # milliseconds
    doc_id = f"{agent}:{user_id}:{session_id}:{timestamp}"
    
    # Tạo custom key để control việc tạo key
    custom_key = f"{KEY_PREFIX}:{doc_id}"

    try:
        embedding = await embedding_fn(full_text)
        print(f"[Debug] Generated embedding for doc_id: {doc_id}")
        
        # Convert embedding list to bytes theo chuẩn RedisVL
        embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
        print(f"[Debug] Embedding converted to bytes for doc_id: {doc_id}")
        
        # Đảm bảo index tồn tại
        await ensure_index_exists()
        
        # Tạo data object theo schema với custom key
        data = [{
            "id": doc_id,
            "text": full_text,
            "agent": agent,
            "user_id": user_id,
            "session_id": session_id,
            "embedding": embedding_bytes
        }]
        
        # Sử dụng load method với custom key
        keys = await async_search_index.load(data, keys=[custom_key])
        print(f"[Debug] Chat saved with keys: {keys}")
        return keys
        
    except Exception as e:
        print(f"[Error] Failed to save chat: {str(e)}")
        raise Exception(f"[RedisVL] Failed to save chat: {str(e)}")
    
    

# # Example usage function
# async def example_usage():
#     """Ví dụ sử dụng các function."""
#     try:
#         # Test messages
#         messages = [
#             HumanMessage(content="Hello, how are you today?"),
#             HumanMessage(content="I need help with Python programming")
#         ]
        
#         # Save chat - sử dụng version 2 để tránh duplicate
#         keys = await save_chat_to_vector_v2("assistant", "user123", "session456", messages)
#         print(f"Saved chat with keys: {keys}")
        
#         # Save chat lần 2 - sẽ tạo document mới thay vì duplicate
#         messages2 = [
#             HumanMessage(content="Can you help me with machine learning?"),
#         ]
#         keys2 = await save_chat_to_vector_v2("assistant", "user123", "session456", messages2)
#         print(f"Saved second chat with keys: {keys2}")
        
#         # Search chat
#         results = await search_chat_history("Python programming", user_id="user123")
#         print(f"Search results: {results}")
        
#         # Get stats
#         stats = await get_index_stats()
#         print(f"Index stats: {stats}")
        
#     except Exception as e:
#         print(f"[Error] Example usage failed: {str(e)}")

# # Main execution
# if __name__ == "__main__":
#     asyncio.run(example_usage())