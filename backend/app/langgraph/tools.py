from datetime import datetime, timezone
from typing import Optional
from langchain_core.tools import tool
from app.chatstore.redis_client import load_uploaded_tools_from_redis

# -----------------------------
# Helpers
# -----------------------------
now = datetime.now(timezone.utc)
fmt = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")

def parse_iso(iso_str):
    try:
        return datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    except:
        return None

# -----------------------------
# Load Q&A Claims Data from RedisVL
# -----------------------------
data = load_uploaded_tools_from_redis()

# -----------------------------
# Utility Functions
# -----------------------------
def find_by_id(query: str) -> Optional[dict]:
    return data.get(query.strip().upper())

def find_by_question(query: str) -> Optional[dict]:
    q = query.lower()
    return next((item for item in data.values() if q in item.get("question", "").lower()), None)

def find_all_by_keywords(query: str) -> list[dict]:
    q = query.lower()
    return [item for item in data.values() if any(q in str(v).lower() for v in item.values())]

# -----------------------------
# Tool: get_claim_answer
# Output: dict { result: str, content: list[{type, text}] }
# -----------------------------
@tool
def get_claim_answer(query: str) -> dict:
    """Tìm câu trả lời cho câu hỏi khiếu nại, tư vấn, hỗ trợ khách hàng."""
    item = find_by_id(query) or find_by_question(query)
    if not item:
        return {
            "result": "Không tìm thấy thông tin phù hợp với: " + query,
            "content": [{"type": "text", "text": f"❌ Không tìm thấy câu trả lời cho: {query}"}]
        }

    contents = [{"type": "text", "text": f"❓ Câu hỏi: {item['question']}\n💬 Trả lời: {item['answer']}"}]

    if item.get("product"):
        contents.append({"type": "text", "text": f"📦 Sản phẩm liên quan: {item['product']}"})
    if item.get("issue"):
        contents.append({"type": "text", "text": f"🚨 Vấn đề: {item['issue']}"})
    if item.get("resolution"):
        contents.append({"type": "text", "text": f"🛠️ Hướng xử lý: {item['resolution']}"})

    return {"result": "OK", "content": contents}

# -----------------------------
# Tool: search_claims_by_keyword
# Output: string mô tả danh sách Q&A liên quan
# -----------------------------
@tool(return_direct=True)
def search_claims_by_keyword(query: str) -> str:
    """Tìm tất cả câu hỏi khiếu nại, tư vấn có chứa từ khóa liên quan."""
    matched = find_all_by_keywords(query)
    if not matched:
        return f"Không tìm thấy câu hỏi hoặc phản hồi nào liên quan đến: '{query}'"

    lines = [f"Tìm thấy {len(matched)} kết quả cho từ khóa '{query}':\n"]
    for item in matched[:10]:
        lines.append(f"- ❓ {item['question']}\n  💬 {item['answer']}")

    return "\n".join(lines)

# -----------------------------
# Register tools
# -----------------------------
tools = [get_claim_answer, search_claims_by_keyword]
