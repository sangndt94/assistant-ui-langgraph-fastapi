from fastapi import FastAPI, Query
from langchain.vectorstores.redis import Redis
from langchain.embeddings import OpenAIEmbeddings
import os

# Khởi tạo kết nối RedisVectorStore
# NOTE: Đảm bảo bạn có các biến môi trường phù hợp
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

embedding = OpenAIEmbeddings()
vectorstore = Redis(
    redis_url=REDIS_URL,
    index_name="chat_history",  # tùy theo bạn dùng tên index gì
    embedding=embedding,
)

def register_history_routes(app: FastAPI):
    @app.get("/api/chat/history")
    async def get_chat_history(session_id: str = Query(..., description="Session ID của người dùng")):
        try:
            # Truy vấn các message có metadata với session_id
            results = vectorstore.similarity_search(
                query="history",  # Dummy query để lấy all
                k=20,
                filter={"session_id": session_id}  # Giả sử bạn lưu metadata kiểu này
            )

            # Trả về các nội dung chat
            history = [{"content": doc.page_content, "metadata": doc.metadata} for doc in results]
            return {"history": history}
        except Exception as e:
            return {"error": str(e)}