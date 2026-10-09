"""Extractor offline dựa trên text vector của PDF xuất từ CAD (không tốn token).

Độ chính xác thấp hơn Gemini nhưng: miễn phí, nhanh, có toạ độ chính xác. Dùng khi:
- chưa có GEMINI_API_KEY, hoặc
- chạy chế độ `--extractor hybrid` để bổ sung kích thước mà Gemini bỏ sót.
Không áp dụng được cho PDF scan (không có text).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ..models import Element, PageExtraction
from ..pdf.render import page_size, vector_text
from .base import Extractor

DIM = re.compile(r"(\d{3,4})\s*[xX×*]\s*(\d{3,4})")
FIRE = re.compile(r"\bE\s*I\s*-?\s*(\d{2,3})\b", re.I)
DOOR_LABEL = re.compile(r"^\s*(Đ|D|C|DC|ĐC|CĐ|CN|S)\s*-?\s*\d{1,3}[A-Z]?\b", re.I)
STAIR = re.compile(r"THANG\s*(BỘ|THOÁT|N[123]|L[12])|BUỒNG\s*THANG|\bTB\s*-?\d", re.I)
CORRIDOR = re.compile(r"HÀNH\s*LANG|\bHL\b", re.I)
EXIT = re.compile(r"LỐI\s*(RA|THOÁT)|\bEXIT\b", re.I)
FIRE_DOOR = re.compile(r"NGĂN\s*CHÁY|CHỐNG\s*CHÁY|\bEI\s*\d", re.I)
WIDTH = re.compile(r"(?:B|R|W|RỘNG|VẾ\s*THANG)\s*[=:]?\s*(\d{3,4})(?:\s*mm)?", re.I)
NOTE_LINE = re.compile(r"^\s*(\d+[.)]|-|\*|GHI\s*CHÚ|KHOẢNG\s*CÁCH|ĐƯỜNG\s*CHÉO|SỨC\s*CHỨA)", re.I)
STAIR_LABEL = re.compile(r"^\s*(B?TB|CT|BT)\s*-?\d+\b", re.I)
TYPE3_NOTE = re.compile(r"THANG\s*(SẮT|THÉP)[^|]*(NGOÀI|HỞ)|CẦU\s*THANG\s*(BỘ\s*)?LOẠI\s*3", re.I)
NOT_EVAC = re.compile(r"KHÔNG\s*THOÁT\s*NẠN|DI\s*CHUYỂN\s*NỘI\s*BỘ", re.I)
SCALE = re.compile(r"(?:TỈ\s*LỆ|TỶ\s*LỆ|SCALE)\s*[:]?\s*1\s*[:/]\s*(\d+)", re.I)
SHEET = re.compile(r"^\s*(MẶT\s*BẰNG|MẶT\s*CẮT|SƠ\s*ĐỒ)", re.I)
STEP = re.compile(r"(?:BẬC|h\s*=?)\s*(\d{2,3})\s*[xX×/]\s*(\d{2,3})", re.I)

BUILDING_PATTERNS: dict[str, tuple[re.Pattern, Any]] = {
    "function_group": (re.compile(r"\b(F\s?[1-5]\.\d)\b"), lambda m: m.group(1).replace(" ", "")),
    "fire_resistance_level": (re.compile(r"BẬC\s*CHỊU\s*LỬA\s*[:\-]?\s*(IV|V|I{1,3})\b", re.I), lambda m: m.group(1).upper()),
    "structural_hazard_class": (re.compile(r"\b(S[0-3])\b"), lambda m: m.group(1)),
    "height_pccc_m": (re.compile(r"CHIỀU\s*CAO\s*PCCC\s*[:=]?\s*([\d.,]+)\s*m", re.I), lambda m: float(m.group(1).replace(",", "."))),
    "floors_above": (re.compile(r"(\d{1,3})\s*TẦNG\s*(NỔI)?\b", re.I), lambda m: int(m.group(1))),
    "basements": (re.compile(r"(\d)\s*TẦNG\s*HẦM", re.I), lambda m: int(m.group(1))),
}


def _nearest(els, bbox: list[float], max_d: float):
    def dist(e):
        ex, ey = (e.bbox[0] + e.bbox[2]) / 2, (e.bbox[1] + e.bbox[3]) / 2
        tx, ty = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        return ((ex - tx) ** 2 + (ey - ty) ** 2) ** 0.5
    cands = [e for e in els if dist(e) <= max_d]
    # Ghi chú CAD thường căn thẳng cột/hàng với ký hiệu đối tượng -> ưu tiên ứng viên chồng lấn theo X hoặc Y
    pad = 10
    aligned = [e for e in cands
               if (e.bbox[0] <= bbox[2] + pad and e.bbox[2] >= bbox[0] - pad)
               or (e.bbox[1] <= bbox[3] + pad and e.bbox[3] >= bbox[1] - pad)]
    pool = aligned or cands
    return min(pool, key=dist) if pool else None


def _near(a: list[float], b: list[float], d: float) -> bool:
    return not (b[0] > a[2] + d or b[2] < a[0] - d or b[1] > a[3] + d or b[3] < a[1] - d)


def _largest_rect(pdf: Path, page_no: int) -> list[float] | None:
    """Khung mặt bằng ~ hình chữ nhật vẽ lớn nhất (bỏ khung giấy/khung bản vẽ chiếm > 90% trang)."""
    import pymupdf
    with pymupdf.open(pdf) as doc:
        pg = doc[page_no - 1]
        area = pg.rect.width * pg.rect.height
        rects = [dr["rect"] for dr in pg.get_drawings() if dr.get("rect") is not None]
    rects = [r for r in rects if r.width * r.height < 0.9 * area]
    if not rects:
        return None
    r = max(rects, key=lambda r: r.width * r.height)
    return [round(v, 1) for v in (r.x0, r.y0, r.x1, r.y1)]


class VectorTextExtractor(Extractor):
    name = "vector"

    def __init__(self, near_pt: float = 40.0):
        self.near_pt = near_pt

    def extract_page(self, pdf: Path, page_no: int):
        W, H = page_size(pdf, page_no)
        page = PageExtraction(page_no, W, H)
        texts = vector_text(pdf, page_no)
        building: dict[str, Any] = {}
        full = "\n".join(t["text"] for t in texts)
        for key, (pat, conv) in BUILDING_PATTERNS.items():
            m = pat.search(full)
            if m:
                try:
                    building[key] = conv(m)
                except ValueError:
                    pass

        m = SCALE.search(full)
        if m:
            page.scale = f"1:{m.group(1)}"
        title = next((t["text"] for t in texts if SHEET.match(t["text"])), "")
        page.sheet_title = title

        page.plan_bbox = _largest_rect(pdf, page_no)
        n = 0
        exit_texts: list[dict] = []
        not_evac_texts: list[dict] = []
        type3_texts: list[dict] = []

        def add(typ: str, t: dict, attrs: dict, label: str = "") -> None:
            nonlocal n
            n += 1
            page.elements.append(Element(f"p{page_no}-v{n}", typ, page_no, t["bbox"], label or t["text"][:40],
                                         attrs, confidence=0.4, source="vector"))

        for t in texts:
            s = t["text"]
            neigh = " ".join(o["text"] for o in texts if o is not t and _near(t["bbox"], o["bbox"], self.near_pt))
            ctx = f"{s} {neigh}"
            if DOOR_LABEL.match(s) or (DIM.search(s) and re.search(r"CỬA|\bD\d|\bĐ\d", s, re.I)):
                attrs: dict[str, Any] = {}
                m = DIM.search(s) or DIM.search(ctx)
                if m:
                    attrs["width_m"], attrs["height_m"] = int(m.group(1)) / 1000, int(m.group(2)) / 1000
                f = FIRE.search(s) or FIRE.search(ctx)
                if f:
                    attrs["fire_rating"] = f"EI{f.group(1)}"
                if EXIT.search(ctx):
                    attrs["is_exit"] = True
                typ = "exit_door" if attrs.get("is_exit") else ("fire_door" if f or FIRE_DOOR.search(s) else "door")
                add(typ, t, attrs, DOOR_LABEL.match(s).group(0) if DOOR_LABEL.match(s) else "")
            elif STAIR_LABEL.match(s) or (STAIR.search(s) and len(s) <= 25 and not NOTE_LINE.match(s)):
                attrs = {"is_evacuation": True}
                w = WIDTH.search(s) or WIDTH.search(ctx)
                if w:
                    attrs["flight_width_m"] = int(w.group(1)) / 1000
                st = STEP.search(ctx)
                if st:
                    a, b = int(st.group(1)), int(st.group(2))
                    attrs["riser_m"], attrs["tread_m"] = min(a, b) / 1000, max(a, b) / 1000
                label = STAIR_LABEL.match(s).group(0).strip() if STAIR_LABEL.match(s) else ""
                add("stair", t, attrs, label)
            elif len(s) > 25 or NOTE_LINE.match(s):     # câu ghi chú: chỉ dùng làm căn cứ, không tạo phần tử
                if NOT_EVAC.search(s):
                    not_evac_texts.append(t)
                elif TYPE3_NOTE.search(s):
                    type3_texts.append(t)
                continue
            elif CORRIDOR.search(s):
                attrs = {}
                w = WIDTH.search(s) or WIDTH.search(ctx)
                if w:
                    attrs["width_m"] = int(w.group(1)) / 1000
                add("corridor", t, attrs)
            elif EXIT.search(s) and not SHEET.match(s):
                exit_texts.append(t)
        # Chữ "LỐI THOÁT NẠN"/"EXIT" đứng riêng: gán cho cửa gần nhất, nếu không có cửa thì tạo lối ra mới
        doors = [e for e in page.elements if e.type in ("door", "fire_door", "exit_door")]
        for t in exit_texts:
            near = [e for e in doors if _near(e.bbox, t["bbox"], self.near_pt)]
            if near:
                for e in near:
                    e.attrs["is_exit"] = True
                    if e.type == "door":
                        e.type = "exit_door"
            else:
                add("exit_door", t, {"is_exit": True})
        # Ghi chú cạnh thang là căn cứ mạnh hơn phỏng đoán của Gemini -> gán cho thang GẦN NHẤT (cờ _..._note)
        # ưu tiên thang có ký hiệu mã (BTB1, TB3); nhãn chung như "BUỒNG THANG" chỉ dùng khi không có
        coded = [e for e in page.elements if e.type == "stair" and STAIR_LABEL.match(e.label or "")]
        stairs = coded or [e for e in page.elements if e.type == "stair"]
        for texts_, apply in ((not_evac_texts, {"is_evacuation": False, "_evac_note": True}),
                              (type3_texts, {"stair_type": "loai3", "_type_note": True})):
            for t in texts_:
                e = _nearest(stairs, t["bbox"], self.near_pt * 4)
                if e is not None:
                    e.attrs.update(apply)
        return page, building
