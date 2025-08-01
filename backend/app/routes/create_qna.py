from fastapi import APIRouter, Form
from redis import Redis
from redisvl.index import SearchIndex
from sentence_transformers import SentenceTransformer
import datetime, uuid, numpy as np, json, os

# ─── Config ─────────────────────────────────────────────
VECTOR_DIM = 384
INDEX_NAME = "core_agent_claims_index"
REDIS_URL = "redis://localhost:6379"
KEY_PREFIX = "core_agent:data:claims:"

# ─── Redis & Model Setup ────────────────────────────────
redis_client = Redis.from_url(REDIS_URL, decode_responses=False)
model = SentenceTransformer("all-MiniLM-L6-v2")

def get_embedding(text: str) -> bytes:
    vector = model.encode(text)
    return np.array(vector, dtype=np.float32).tobytes()

# ─── Redis Schema ───────────────────────────────────────
schema = {
    "index": {"name": INDEX_NAME, "prefix": KEY_PREFIX},
    "fields": [
        {"name": "id", "type": "tag"},
        {"name": "question", "type": "text"},
        {"name": "answer", "type": "text"},
        {"name": "product", "type": "tag"},
        {"name": "issue", "type": "tag"},
        {"name": "customer_reply", "type": "text"},
        {"name": "official_reply", "type": "text"},
        {"name": "resolution", "type": "text"},
        {"name": "remedy", "type": "text"},
        {"name": "discipline", "type": "text"},
        {"name": "tags", "type": "tag"},
        {"name": "embedding", "type": "vector", "attrs": {
            "dims": VECTOR_DIM, "distance_metric": "cosine", "algorithm": "hnsw", "datatype": "float32"
        }}
    ]
}

index = SearchIndex.from_dict(schema, redis_client=redis_client)
if not index.exists():
    index.create(overwrite=False)

# ─── Router ─────────────────────────────────────────────
def build_claims_router(prefix: str = "/api") -> APIRouter:
    router = APIRouter(prefix=prefix)

    @router.post("/upload_claim_qna", summary="📄 Upload 1 QA khiếu nại từ FE")
    async def upload_claim_qna(
        id: str = Form(default=None),
        question: str = Form(...),
        answer: str = Form(...),
        product: str = Form(...),
        issue: str = Form(...),
        customer_reply: str = Form(""),
        official_reply: str = Form(""),
        resolution: str = Form(""),
        remedy: str = Form(""),
        discipline: str = Form(""),
        tags: str = Form("")  # comma-separated
    ):
        try:
            now = datetime.datetime.utcnow().isoformat()
            obj_id = id or f"CLAIM-{uuid.uuid4().hex[:8].upper()}"

            embedding_text = f"{question} {answer} {product} {issue}"
            embedding = get_embedding(embedding_text)

            redis_key = f"{KEY_PREFIX}{obj_id}"

            doc = {
                "id": obj_id,
                "question": question,
                "answer": answer,
                "product": product,
                "issue": issue,
                "customer_reply": customer_reply,
                "official_reply": official_reply,
                "resolution": resolution,
                "remedy": remedy,
                "discipline": discipline,
                "tags": tags,
                "embedding": embedding
            }

            index.load([doc], keys=[redis_key])

            return {"success": True, "message": f"✅ QA đã được ghi vào RedisVL dưới key {obj_id}"}

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"❌ Lỗi khi ghi RedisVL: {e}")

    return router
