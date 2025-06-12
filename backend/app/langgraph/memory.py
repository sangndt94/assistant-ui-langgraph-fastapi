# app/langgraph/memory.py
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

def get_message_history(session_id: str):
    return RedisChatMessageHistory(
        session_id=session_id,
        url="redis://localhost:6379",  # tùy chỉnh theo server Redis
        ttl=None  # hoặc TTL (giây) nếu cần tự xoá
    )

def wrap_with_memory(graph):
    return RunnableWithMessageHistory(
        graph,
        get_message_history,
        input_messages_key="messages",
        history_messages_key="messages"
    )