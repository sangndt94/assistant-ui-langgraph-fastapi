import numpy as np
import asyncio
from .config import get_model

def embedding_fn_sync(text: str) -> list[float]:
    return get_model().encode(text).tolist()

def embedding_to_bytes(vec: list[float]) -> bytes:
    return np.array(vec, dtype=np.float32).tobytes()

async def embedding_fn(text: str) -> list[float]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, embedding_fn_sync, text)
