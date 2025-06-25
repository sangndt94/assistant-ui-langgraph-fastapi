import os
from functools import lru_cache
from sentence_transformers import SentenceTransformer

# Env Configs
AGENT_NAME = os.getenv("AGENT_NAME", "core_agent")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "384"))
INDEX_NAME = os.getenv("INDEX_NAME", f"{AGENT_NAME}_index")
KEY_PREFIX = os.getenv("KEY_PREFIX", f"{AGENT_NAME}_docs")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
TOOL_KEY_PREFIX = os.getenv("TOOL_KEY_PREFIX", "core_agent:data:tool:")

# Cached model
@lru_cache()
def get_model():
    return SentenceTransformer(EMBEDDING_MODEL)
