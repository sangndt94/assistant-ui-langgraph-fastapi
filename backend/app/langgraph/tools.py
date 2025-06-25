

from datetime import datetime, timedelta, timezone
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
# Mock Data (injected separately to reduce clutter)
# -----------------------------
# universal_mock_data = {
#     "OBJ-001": {
#         "id": "OBJ-001",
#         "name": "Khăn giấy lốc 10 gói",
#         "type": "pallet",
#         "status": "stored",
#         "location": "Zone B2 - Shelf 6",
#         "quantity": 600,
#         "unit": "pack",
#         "weight": 250,
#         "dimensions": {"length": 100, "width": 80, "height": 130},
#         "created_at": fmt(now - timedelta(days=7)),
#         "updated_at": fmt(now),
#         "tags": ["fragile", "dry"],
#         "metadata": {"supplier": "Vinacell", "batch_no": "B202406"},
#         "images": [
#             "https://picsum.photos/id/237/200/300",
#             "https://picsum.photos/id/100/200/300",
#             "https://picsum.photos/id/101/200/300"
#         ]
#     },
#     "OBJ-002": {
#         "id": "OBJ-002",
#         "name": "Hộp cáp sạc USB-C",
#         "type": "box",
#         "status": "stored",
#         "location": "Shelf A1",
#         "quantity": 120,
#         "unit": "piece",
#         "weight": 45,
#         "dimensions": {"length": 30, "width": 20, "height": 15},
#         "created_at": fmt(now - timedelta(days=3)),
#         "updated_at": fmt(now),
#         "tags": ["electronics"],
#         "metadata": {"brand": "Anker", "model": "A8813"},
#         "images": [
#             "https://picsum.photos/id/237/200/300",
#             "https://picsum.photos/id/100/200/300",
#             "https://picsum.photos/id/101/200/300"
#         ]
#     },
#     "OBJ-003": {
#         "id": "OBJ-003",
#         "name": "Đơn hàng #12345",
#         "type": "order",
#         "status": "shipped",
#         "location": "VNPost - Q1",
#         "quantity": 3,
#         "unit": "package",
#         "weight": 5.2,
#         "dimensions": {"length": 50, "width": 40, "height": 30},
#         "created_at": fmt(now - timedelta(days=2)),
#         "updated_at": fmt(now - timedelta(days=1)),
#         "tags": ["urgent", "COD"],
#         "metadata": {"customer": "Nguyễn Văn A", "phone": "0901234567"},
#         "images": [
#             "https://picsum.photos/id/237/200/300",
#             "https://picsum.photos/id/100/200/300",
#             "https://picsum.photos/id/101/200/300"
#         ]
#     },
#     "OBJ-004": {
#         "id": "OBJ-004",
#         "name": "Laptop Dell XPS 15",
#         "type": "asset",
#         "status": "in_use",
#         "location": "VP Hà Nội - Phòng IT",
#         "quantity": 1,
#         "unit": "unit",
#         "weight": 1.8,
#         "dimensions": {"length": 35, "width": 24, "height": 2},
#         "created_at": fmt(now - timedelta(days=180)),
#         "updated_at": fmt(now - timedelta(days=3)),
#         "tags": ["it", "equipment"],
#         "metadata": {"serial_no": "DXPS1588VN", "assigned_to": "trungnt"},
#         "images": [
#             "https://picsum.photos/id/237/200/300",
#             "https://picsum.photos/id/100/200/300",
#             "https://picsum.photos/id/101/200/300"
#         ]
#     },
#     "OBJ-005": {
#         "id": "OBJ-005",
#         "name": "Báo cáo tài chính Q1",
#         "type": "document",
#         "status": "archived",
#         "location": "Drive/Finance/2024",
#         "quantity": 1,
#         "unit": "file",
#         "weight": 0,
#         "dimensions": {"length": 0, "width": 0, "height": 0},
#         "created_at": fmt(now - timedelta(days=90)),
#         "updated_at": fmt(now - timedelta(days=60)),
#         "tags": ["finance", "confidential"],
#         "metadata": {"format": "PDF", "author": "ketoan01"},
#         "images": [
#             "https://picsum.photos/id/237/200/300",
#             "https://picsum.photos/id/100/200/300",
#             "https://picsum.photos/id/101/200/300"
#         ]
#     },
#     "OBJ-006": {
#         "id": "OBJ-006",
#         "name": "Thùng nước Lavie 500ml",
#         "type": "box",
#         "status": "pending",
#         "location": "Dock 3",
#         "quantity": 240,
#         "unit": "bottle",
#         "weight": 120,
#         "dimensions": {"length": 100, "width": 80, "height": 110},
#         "created_at": fmt(now - timedelta(hours=5)),
#         "updated_at": fmt(now - timedelta(hours=1)),
#         "tags": ["fragile", "liquid"],
#         "metadata": {"batch": "LV0624", "expiry": "2025-06-01"},
#         "images": [
#             "https://picsum.photos/id/237/200/300",
#             "https://picsum.photos/id/100/200/300",
#             "https://picsum.photos/id/101/200/300"
#         ]
#     },
#     "OBJ-0019": {
#         "id": "OBJ-006",
#         "name": "cục cứt",
#         "type": "box",
#         "status": "pending",
#         "location": "Dock 3",
#         "quantity": 240,
#         "unit": "bottle",
#         "weight": 120,
#         "dimensions": {"length": 100, "width": 80, "height": 110},
#         "created_at": fmt(now - timedelta(hours=5)),
#         "updated_at": fmt(now - timedelta(hours=1)),
#         "tags": ["fragile", "liquid"],
#         "metadata": {"batch": "LV0624", "expiry": "2025-06-01"},
#         "images": [
#             "https://picsum.photos/id/237/200/300",
#             "https://picsum.photos/id/100/200/300",
#             "https://picsum.photos/id/101/200/300"
#         ]
#     },
#     "OBJ-007": {
#         "id": "OBJ-007",
#         "name": "Shipment DHL #789",
#         "type": "shipment",
#         "status": "in_transit",
#         "location": "DHL HUB - Singapore",
#         "quantity": 5,
#         "unit": "box",
#         "weight": 42,
#         "dimensions": {"length": 150, "width": 80, "height": 60},
#         "created_at": fmt(now - timedelta(days=1)),
#         "updated_at": fmt(now),
#         "tags": ["international"],
#         "metadata": {"tracking": "DHL789SG", "receiver": "LEGO Vietnam"},
#         "images": [
#             "https://picsum.photos/id/237/200/300",
#             "https://picsum.photos/id/100/200/300",
#             "https://picsum.photos/id/101/200/300"
#         ]
#     },
#     "OBJ-008": {
#         "id": "OBJ-008",
#         "name": "Ổ cứng SSD 2TB",
#         "type": "hardware",
#         "status": "stored",
#         "location": "Tủ an toàn số 2",
#         "quantity": 10,
#         "unit": "unit",
#         "weight": 0.2,
#         "dimensions": {"length": 10, "width": 7, "height": 1},
#         "created_at": fmt(now - timedelta(days=10)),
#         "updated_at": fmt(now - timedelta(days=2)),
#         "tags": ["storage", "it"],
#         "metadata": {"brand": "Samsung", "model": "980 Pro"},
#         "images": [
#             "https://picsum.photos/id/237/200/300",
#             "https://picsum.photos/id/100/200/300",
#             "https://picsum.photos/id/101/200/300"
#         ]
#     },
#     "OBJ-009": {
#         "id": "OBJ-009",
#         "name": "Thùng bánh Oreo",
#         "type": "pallet",
#         "status": "stored",
#         "location": "Kho D - Line 4",
#         "quantity": 360,
#         "unit": "box",
#         "weight": 400,
#         "dimensions": {"length": 120, "width": 100, "height": 140},
#         "created_at": fmt(now - timedelta(days=5)),
#         "updated_at": fmt(now),
#         "tags": ["food"],
#         "metadata": {"supplier": "Mondelez", "expiry": "2025-01-15"},
#         "images": [
#             "https://picsum.photos/id/237/200/300",
#             "https://picsum.photos/id/100/200/300",
#             "https://picsum.photos/id/101/200/300"
#         ]
#     },
#     "OBJ-010": {
#         "id": "OBJ-010",
#         "name": "Biên bản kiểm kê 6/2024",
#         "type": "document",
#         "status": "in_review",
#         "location": "Tủ hồ sơ P.Kế toán",
#         "quantity": 1,
#         "unit": "file",
#         "weight": 0,
#         "dimensions": {"length": 0, "width": 0, "height": 0},
#         "created_at": fmt(now - timedelta(days=3)),
#         "updated_at": fmt(now - timedelta(days=1)),
#         "tags": ["inventory", "internal"],
#         "metadata": {"approved_by": None, "version": 2},
#         "images": [
#             "https://picsum.photos/id/237/200/300",
#             "https://picsum.photos/id/100/200/300",
#             "https://picsum.photos/id/101/200/300"
#         ]
#     }
# }

data = load_uploaded_tools_from_redis()


# -----------------------------
# Utility Find Functions
# -----------------------------
def find_by_id(query: str) -> Optional[dict]:
    return data.get(query.strip().upper())

def find_by_name(query: str) -> Optional[dict]:
    q = query.lower()
    return next((item for item in data.values() if q in item.get("name", "").lower()), None)

def find_all_by_name(query: str) -> list[dict]:
    q = query.lower()
    return [item for item in data.values() if q in item.get("name", "").lower()]

def find_by_type(type_query: str) -> list[dict]:
    t = type_query.lower()
    return [item for item in data.values() if item.get("type", "").lower() == t]

def find_by_general_fields(query: str) -> list[dict]:
    q = query.lower()
    matched = []
    for item in data.values():
        if (
            q in item["id"].lower()
            or q in item["name"].lower()
            or q in item.get("location", "").lower()
            or q in item.get("type", "").lower()
            or any(q in tag.lower() for tag in item.get("tags", []))
            or any(q in str(v).lower() for v in item.get("metadata", {}).values())
        ):
            matched.append(item)
    return matched

# -----------------------------
# Format Output Functions
# -----------------------------
def format_description(item: dict) -> str:
    desc = (
        f"Pallet có mã ID {item['id']} chứa {item['name']} đang được lưu trữ tại {item['location']}.\n"
        f"Số lượng: {item['quantity']} {item['unit']}, trọng lượng: {item['weight']} kg.\n"
        f"Kích thước: {item['dimensions']['length']}x{item['dimensions']['width']}x{item['dimensions']['height']}cm."
    )
    if item.get("metadata"):
        metadata = ", ".join(f"{k.capitalize()}: {v}" for k, v in item["metadata"].items())
        desc += f"\nThông tin thêm: {metadata}."
    if item.get("updated_at"):
        updated = parse_iso(item["updated_at"])
        if updated:
            desc += f"\nCập nhật lần cuối vào ngày {updated.strftime('%d/%m/%Y')}."
    return desc

# -----------------------------
# Tool: get_pallet_info
# Output: dict { result: str, content: list[{type, text/data}] }
# -----------------------------
@tool
def get_pallet_info(query: str) -> dict:
    """Tìm và mô tả thông tin một pallet hoặc vật phẩm trong kho."""
    item = find_by_id(query) or find_by_name(query)
    if not item:
        return {
            "result": "Không tìm thấy thông tin nào khớp với: " + query,
            "content": [{"type": "text", "text": f"❌ Không tìm thấy thông tin với: {query}"}]
        }

    content = [{"type": "text", "text": format_description(item)}]

    if item.get("images"):
        content.append({"type": "text", "text": f"Hình ảnh của pallet {item['id']}:"})
        content.extend({"type": "image", "data": url} for url in item["images"])

    return {"result": "OK", "content": content}

# -----------------------------
# Tool: get_inventory_info
# Output: string mô tả danh sách item
# -----------------------------
@tool(return_direct=True)
def get_inventory_info(query: str) -> str:
    """Tìm kiếm thông tin kho theo ID, tên, vị trí, loại, tag hoặc metadata."""
    matched = find_by_general_fields(query)
    if not matched:
        return f"Không tìm thấy vật phẩm nào liên quan đến: '{query}'"

    lines = [f"Tìm thấy {len(matched)} vật phẩm liên quan đến '{query}':\n"]
    for item in matched:
        updated_str = ""
        updated_dt = parse_iso(item.get("updated_at"))
        if updated_dt:
            updated_str = f", cập nhật: {updated_dt.strftime('%d/%m/%Y')}"

        lines.append(
            f"- {item['name']} (Mã: {item['id']}, Vị trí: {item['location']}, SL: {item['quantity']} {item['unit']}{updated_str})"
        )
    return "\n".join(lines)

# -----------------------------
# Tool: get_all_pallets
# Output: dict content với mô tả + ảnh của tất cả pallet
# -----------------------------
@tool
def get_all_pallets() -> dict:
    """Trả về toàn bộ các pallet trong kho cùng hình ảnh."""
    pallets = find_by_type("pallet")
    if not pallets:
        return {
            "result": "Không tìm thấy pallet nào.",
            "content": [{"type": "text", "text": "❌ Không có pallet nào trong kho."}]
        }

    contents = []
    for pallet in pallets:
        contents.append({"type": "text", "text": format_description(pallet)})
        if pallet.get("images"):
            contents.append({"type": "text", "text": f"Hình ảnh của pallet {pallet['id']}:"})
            contents.extend({"type": "image", "data": url} for url in pallet["images"])

    return {"result": f"Tìm thấy {len(pallets)} pallet.", "content": contents}

# -----------------------------
# Register tools
# -----------------------------
tools = [get_pallet_info, get_inventory_info, get_all_pallets]
