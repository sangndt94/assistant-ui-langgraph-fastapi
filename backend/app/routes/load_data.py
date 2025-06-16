from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import pandas as pd
import numpy as np
import asyncio
import redis
import io
import json
from redisvl.schema import IndexSchema, Field, TextField, VectorField
from redisvl.index import AsyncSearchIndex
from sentence_transformers import SentenceTransformer

app = FastAPI()

# Redis config
REDIS_URL = "redis://localhost:6379"
KEY_PREFIX = "warehouse_pallet"
INDEX_NAME = "pallet_index"

# Embedding model
_model = SentenceTransformer("all-MiniLM-L6-v2")
embedding_fn_sync = lambda text: _model.encode(text).tolist()

async def embedding_fn(text):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, embedding_fn_sync, text)

# Async Redis client and index
async_redis_client = redis.asyncio.Redis.from_url(REDIS_URL)
async_search_index = AsyncSearchIndex.from_dict({
    "index": {"name": INDEX_NAME},
    "fields": [
        TextField(name="id"),
        TextField(name="name"),
        TextField(name="type"),
        TextField(name="status"),
        TextField(name="location"),
        TextField(name="unit"),
        TextField(name="tags"),
        TextField(name="metadata"),
        TextField(name="text"),
        VectorField(name="embedding", dims=384, algorithm="FLAT", distance_metric="cosine")
    ]
}, redis_url=REDIS_URL)

async def ensure_index_exists():
    if not await async_search_index.exists():
        await async_search_index.create(overwrite=True)

@app.post("/upload-pallet-excel")
async def upload_excel(file: UploadFile = File(...)):
    try:
        df = pd.read_excel(io.BytesIO(await file.read()))
        await ensure_index_exists()
        results = []

        for _, row in df.iterrows():
            doc_id = f"{KEY_PREFIX}:{row['id']}"
            full_text = json.dumps(row.to_dict(), ensure_ascii=False)
            embedding = await embedding_fn(full_text)
            embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()

            data = [{
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
                "status": row["status"],
                "location": row["location"],
                "unit": row["unit"],
                "tags": row.get("tags", ""),
                "metadata": row.get("metadata", ""),
                "text": full_text,
                "embedding": embedding_bytes
            }]
            await async_search_index.load(data, keys=[doc_id])
            results.append({"id": row["id"], "status": "saved"})

        return {"message": "Upload and save successful", "results": results}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
