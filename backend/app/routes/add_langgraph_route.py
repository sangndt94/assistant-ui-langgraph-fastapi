from assistant_stream import create_run, RunController
from assistant_stream.serialization import DataStreamResponse
from langchain_core.messages import (
    HumanMessage,
    AIMessageChunk,
    AIMessage,
    ToolMessage,
    SystemMessage,
    BaseMessage,
)
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Literal, Union, Optional, Any
from app.chatstore.redis_client import save_chat_to_vector, async_search_index, load_chat_history
from redisvl.query import VectorQuery
import json, re

class LanguageModelTextPart(BaseModel):
    type: Literal["text"]
    text: str
    providerMetadata: Optional[Any] = None

class LanguageModelImagePart(BaseModel):
    type: Literal["image"]
    image: str
    mimeType: Optional[str] = None
    providerMetadata: Optional[Any] = None

class LanguageModelFilePart(BaseModel):
    type: Literal["file"]
    data: str
    mimeType: str
    providerMetadata: Optional[Any] = None

class LanguageModelToolCallPart(BaseModel):
    type: Literal["tool-call"]
    toolCallId: str
    toolName: str
    args: Any
    providerMetadata: Optional[Any] = None

class LanguageModelToolResultContentPart(BaseModel):
    type: Literal["text", "image"]
    text: Optional[str] = None
    data: Optional[str] = None
    mimeType: Optional[str] = None

class LanguageModelToolResultPart(BaseModel):
    type: Literal["tool-result"]
    toolCallId: str
    toolName: str
    result: Any
    isError: Optional[bool] = None
    content: Optional[List[LanguageModelToolResultContentPart]] = None
    providerMetadata: Optional[Any] = None

class LanguageModelSystemMessage(BaseModel):
    role: Literal["system"]
    content: str

class LanguageModelUserMessage(BaseModel):
    role: Literal["user"]
    content: List[
        Union[LanguageModelTextPart, LanguageModelImagePart, LanguageModelFilePart]
    ]

class LanguageModelAssistantMessage(BaseModel):
    role: Literal["assistant"]
    content: List[Union[LanguageModelTextPart, LanguageModelToolCallPart]]

class LanguageModelToolMessage(BaseModel):
    role: Literal["tool"]
    content: List[LanguageModelToolResultPart]

LanguageModelV1Message = Union[
    LanguageModelSystemMessage,
    LanguageModelUserMessage,
    LanguageModelAssistantMessage,
    LanguageModelToolMessage,
]

def convert_to_langchain_messages(
    messages: List[LanguageModelV1Message],
) -> List[BaseMessage]:
    result = []

    for msg in messages:
        if msg.role == "system":
            result.append(SystemMessage(content=msg.content))

        elif msg.role == "user":
            content = []
            for p in msg.content:
                if isinstance(p, LanguageModelTextPart):
                    content.append({"type": "text", "text": p.text})
                elif isinstance(p, LanguageModelImagePart):
                    content.append({"type": "image_url", "image_url": p.image})
            result.append(HumanMessage(content=content))

        elif msg.role == "assistant":
            text_parts = [
                p for p in msg.content if isinstance(p, LanguageModelTextPart)
            ]
            text_content = "".join(p.text for p in text_parts)  # gộp không có dấu cách
            tool_calls = [
                {
                    "id": p.toolCallId,
                    "name": p.toolName,
                    "args": p.args,
                }
                for p in msg.content
                if isinstance(p, LanguageModelToolCallPart)
            ]
            result.append(AIMessage(content=text_content, tool_calls=tool_calls))

        elif msg.role == "tool":
            for tool_result in msg.content:
                result.append(
                    ToolMessage(
                        content=str(tool_result.result),
                        tool_call_id=tool_result.toolCallId,
                    )
                )

    return result

class FrontendToolCall(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: dict[str, Any]

class ChatRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    agent: Optional[str] = None
    system: Optional[str] = ""
    tools: Optional[List[FrontendToolCall]] = []
    messages: List[LanguageModelV1Message]

def try_unescape(text: str) -> str:
    """Giải mã các ký tự escape như \\n, \\" nếu tồn tại."""
    try:
        return json.loads(f'"{text}"')
    except Exception:
        return text


def add_langgraph_route(app: FastAPI, graph, path: str):
    async def chat_completions(request: ChatRequest):
        history_json = await load_chat_history(request.agent, request.user_id, request.session_id)

        history_messages: List[BaseMessage] = []
        if history_json:
            try:
                history_raw = json.loads(history_json)
                for item in history_raw:
                    if item["role"] == "user":
                        history_messages.append(HumanMessage(content=item["text"]))
                    elif item["role"] == "assistant":
                        text = item["text"]
                        if isinstance(text, list):
                            text = "".join(part.get("text", "") for part in text if part.get("type") == "text")
                        history_messages.append(AIMessage(content=text))
            except Exception as e:
                print(f"[Redis] Failed to load history: {e}")

        new_inputs = convert_to_langchain_messages(request.messages)
        inputs = history_messages + new_inputs

        async def run(controller: RunController):
            tool_calls = {}
            tool_calls_by_idx = {}
            full_messages: List[BaseMessage] = inputs.copy()
            ai_response_buffer = ""

            async for msg, metadata in graph.astream(
                {"messages": inputs},
                {
                    "configurable": {
                        "system": request.system,
                        "frontend_tools": request.tools,
                    }
                },
                stream_mode="messages",
            ):
                # ✅ Nhận kết quả từ tool, KHÔNG stream về FE
                if isinstance(msg, ToolMessage):
                    cleaned_tool_content = try_unescape(msg.content)
                    tool_controller = tool_calls.get(msg.tool_call_id)
                    if tool_controller:
                        tool_controller.set_result(cleaned_tool_content)
                    full_messages.append(ToolMessage(content=cleaned_tool_content, tool_call_id=msg.tool_call_id))

                # ✅ Chỉ stream phản hồi TỰ NHIÊN cuối cùng từ AI
                if isinstance(msg, AIMessageChunk):
                    if msg.content:
                        formatted_content = try_unescape(msg.content)
                        controller.append_text(formatted_content)
                        ai_response_buffer += formatted_content

            # ✅ Sau khi stream xong mới ghi lại lịch sử
            if ai_response_buffer:
                full_messages.append(AIMessage(content=ai_response_buffer))

            try:
                await save_chat_to_vector(
                    agent=request.agent,
                    user_id=request.user_id,
                    session_id=request.session_id,
                    messages=full_messages,
                )
            except Exception as e:
                print(f"[RedisVL] Failed to save chat: {e}")

        return DataStreamResponse(create_run(run))

    app.add_api_route(path, chat_completions, methods=["POST"])