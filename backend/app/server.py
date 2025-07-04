import os
from dotenv import load_dotenv

load_dotenv()

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from .langgraph.agent import assistant_ui_graph
from .routes.add_langgraph_route import add_langgraph_route
from .routes.history import build_history_router
from .routes.load_data import build_upload_router

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
app.include_router(build_history_router("/api")) 
app.include_router(build_upload_router("/api")) 
# Đăng ký route history
# register_history_routes(app)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
