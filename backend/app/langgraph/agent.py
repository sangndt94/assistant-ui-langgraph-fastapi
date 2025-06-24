from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.errors import NodeInterrupt
from langchain_core.tools import BaseTool
from pydantic import BaseModel
from .tools import tools
from .state import AgentState
from app.chatstore.redis_client import search_chat_history, save_chat_to_vector
import os, json

# === CONFIG ===
DEFAULT_SYSTEM_PROMPT = os.getenv(
    "CORE_AGENT_SYSTEM_PROMPT",
    "Bạn là trợ lý AI chính xác, ngắn gọn, lịch sự, không bịa đặt."
)
model = ChatOpenAI()

# === DYNAMIC TOOL WRAPPER ===
class AnyArgsSchema(BaseModel):
    class Config:
        env_file = ".env"
        extra = "allow"

class FrontendTool(BaseTool):
    def __init__(self, name: str):
        super().__init__(name=name, description="", args_schema=AnyArgsSchema)

    def _run(self, *args, **kwargs):
        raise NodeInterrupt("This is a frontend tool call")

    async def _arun(self, *args, **kwargs) -> str:
        raise NodeInterrupt("This is a frontend tool call")

def get_tool_defs(config):
    frontend_tools = [
        {"type": "function", "function": tool}
        for tool in config["configurable"].get("frontend_tools", [])
    ]
    return tools + frontend_tools

def get_tools(config):
    frontend_tools = [
        FrontendTool(tool.name) for tool in config["configurable"].get("frontend_tools", [])
    ]
    return tools + frontend_tools

# === NODES ===
async def retrieve_context(state, config):
    messages = state["messages"]
    query = messages[-1].content if messages else ""

    docs = await search_chat_history(
        query,
        agent=config["configurable"].get("agent"),
        user_id=config["configurable"].get("user_id"),
        session_id=config["configurable"].get("session_id")
    )
    context = "\n".join([d["text"] for d in docs]) if docs else ""

    print("[RAG] Injected context:", context[:200])

    return {
        "messages": [SystemMessage(content=f"Ngữ cảnh: {context}")] + messages
    }

async def call_model(state, config):
    def sanitize_prompt(fe_prompt: str, fallback: str) -> str:
        if fe_prompt and len(fe_prompt.strip()) < 300:
            return f"{fallback}\n{fe_prompt}".strip()
        return fallback

    system = sanitize_prompt(config["configurable"].get("system", ""), DEFAULT_SYSTEM_PROMPT)
    messages = [SystemMessage(content=system)] + state["messages"]
    model_with_tools = model.bind_tools(get_tool_defs(config))
    response = await model_with_tools.ainvoke(messages)
    return {"messages": response}

async def run_tools(input, config, **kwargs):
    tool_node = ToolNode(get_tools(config))
    return await tool_node.ainvoke(input, config, **kwargs)

async def save_history(state, config):
    try:
        await save_chat_to_vector(
            agent=config["configurable"].get("agent"),
            user_id=config["configurable"].get("user_id"),
            session_id=config["configurable"].get("session_id"),
            messages=state["messages"]
        )
    except Exception as e:
        print(f"[SAVE] Failed: {e}")
    return state

def should_continue(state):
    last = state["messages"][-1]
    if not getattr(last, "tool_calls", None):
        return "save"
    else:
        return "tools"

async def classify_query(state, config):
    user_messages = [m for m in reversed(state["messages"]) if isinstance(m, HumanMessage)]
    if not user_messages:
        return {"next": "agent"}

    last_user_message = user_messages[0]
    query_text = last_user_message.content

    if isinstance(query_text, list):
        text_parts = [p.get("text", "") for p in query_text if isinstance(p, dict) and p.get("type") == "text"]
        query = " ".join(text_parts).lower()
    else:
        query = str(query_text).lower()

    if any(keyword in query for keyword in ["trạng thái", "mã đơn", "sản phẩm"]):
        return {"next": "agent"}
    elif any(keyword in query for keyword in ["chính sách", "quy trình", "hướng dẫn"]):
        return {"next": "retrieval"}
    else:
        return {"next": "agent"}

def route_from_classifier(state):
    return state["next"]

# === BUILD GRAPH ===
workflow = StateGraph(AgentState)
workflow.add_node("classifier", classify_query)
workflow.add_node("retrieval", retrieve_context)
workflow.add_node("agent", call_model)
workflow.add_node("tools", run_tools)
workflow.add_node("save", save_history)

workflow.set_entry_point("classifier")
workflow.add_conditional_edges("classifier", route_from_classifier, ["retrieval", "agent"])
workflow.add_edge("retrieval", "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", "save"])
workflow.add_edge("tools", "agent")
workflow.add_edge("save", END)

assistant_ui_graph = workflow.compile()
