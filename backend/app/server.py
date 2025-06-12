import os
from dotenv import load_dotenv
from routes.history import register_history_routes

load_dotenv()

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from .langgraph.agent import assistant_ui_graph
from .routes.add_langgraph_route import add_langgraph_route

app = FastAPI()
# cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký route chat
add_langgraph_route(app, assistant_ui_graph, "/api/chat")

# Đăng ký route history
register_history_routes(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
