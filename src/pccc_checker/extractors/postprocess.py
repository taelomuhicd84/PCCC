"""Hậu xử lý sau khi trích xuất toàn bộ trang (0 token):

1. Bảng cửa (door schedule): ký hiệu cửa trên mặt bằng (D03, D07...) -> điền kích thước/EI từ trang "CHI TIẾT CỬA".
2. Số liệu người thiết kế ghi sẵn (khoảng cách 2 lối thoát nạn, đường chéo công trình, sức chứa).
3. Suy ra nhóm nguy hiểm cháy theo công năng khi bản vẽ không ghi (ghi rõ là giả định).
"""
from __future__ import annotations

import re
from typing import Any

from ..models import DrawingExtraction, PageExtraction

DOOR_TYPES = ("door", "exit_door", "fire_door")

# --------------------------------------------------------------- số liệu ghi sẵn
_NUM = r"([\d]+(?:[.,]\d+)?)"
DECLARED_PATTERNS: dict[str, re.Pattern] = {
    "exit_distance_m": re.compile(rf"KHOẢNG\s*CÁCH\s*(?:GIỮA\s*)?(?:2|HAI)\s*LỐI\s*(?:RA\s*)?(?:THOÁT\s*NẠN)?[^=\d]*=?\s*{_NUM}\s*M\b", re.I),
    "plan_diagonal_m": re.compile(rf"ĐƯỜNG\s*CHÉO[^=\d]*=?\s*{_NUM}\s*M\b", re.I),
    "occupants": re.compile(r"SỨC\s*CHỨA\s*[:\-]?\s*(\d+)\s*NGƯỜI", re.I),
}
UNOCCUPIED = re.compile(r"KHÔNG\s*CÓ\s*NGƯỜI\s*(CÓ\s*MẶT\s*)?THƯỜNG\s*XUYÊN", re.I)


def parse_declared(texts: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    blob = "\n".join(texts)
    for key, pat in DECLARED_PATTERNS.items():
        m = pat.search(blob)
        if m:
            v = m.group(1).replace(",", ".")
            out[key] = int(v) if key == "occupants" else float(v)
    return out


# --------------------------------------------------------------- bảng cửa
def _norm(label: str) -> str:
    return re.sub(r"\s+", "", label or "").upper()


def apply_door_schedule(d: DrawingExtraction) -> int:
    """Trả về số cửa được bổ sung thông số từ bảng cửa."""
    schedule: dict[str, dict[str, Any]] = {}
    for p in d.pages:
        if p.category != "door_schedule":
            continue
        for e in p.elements:
            if e.type in DOOR_TYPES + ("other",) and e.label:
                e.attrs["schedule_entry"] = True          # dòng trong bảng cửa, không phải cửa thực trên mặt bằng
                schedule.setdefault(_norm(e.label), {"attrs": e.attrs, "page": p.page})
    n = 0
    for p in d.pages:
        if p.category == "door_schedule":
            continue
        for e in p.elements:
            if e.type not in DOOR_TYPES:
                continue
            src = schedule.get(_norm(e.label))
            if not src:
                continue
            filled = False
            for k in ("width_m", "height_m", "fire_rating"):
                if e.attrs.get(k) is None and src["attrs"].get(k) is not None:
                    e.attrs[k] = src["attrs"][k]
                    filled = True
            if filled:
                e.attrs["dims_from_schedule"] = f"trang {src['page']}"
                n += 1
            if e.type == "door" and e.attrs.get("fire_rating"):
                e.type = "fire_door"
    return n


# --------------------------------------------------------------- nhóm F theo công năng
# Phụ lục A QCVN 06:2022 (tham khảo nhanh, chỉ dùng khi bản vẽ KHÔNG ghi nhóm F).
USE_TO_GROUP: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r"KHÁCH\s*SẠN|NHÀ\s*NGHỈ|NHÀ\s*KHÁCH|KÝ\s*TÚC\s*XÁ", re.I), "F1.2", "khách sạn/nhà nghỉ/ký túc xá"),
    (re.compile(r"CHUNG\s*CƯ|NHÀ\s*Ở\s*TẬP\s*THỂ|CĂN\s*HỘ", re.I), "F1.3", "chung cư"),
    (re.compile(r"NHÀ\s*Ở\s*RIÊNG\s*LẺ|NHÀ\s*PHỐ|BIỆT\s*THỰ", re.I), "F1.4", "nhà ở riêng lẻ"),
    (re.compile(r"MẦM\s*NON|NHÀ\s*TRẺ|BỆNH\s*VIỆN|VIỆN\s*DƯỠNG\s*LÃO", re.I), "F1.1", "nhà trẻ/bệnh viện/dưỡng lão"),
    (re.compile(r"VĂN\s*PHÒNG|TRỤ\s*SỞ", re.I), "F4.3", "văn phòng/trụ sở"),
    (re.compile(r"TRƯỜNG\s*(HỌC|TIỂU|THCS|THPT|PHỔ)", re.I), "F4.1", "trường học"),
    (re.compile(r"SIÊU\s*THỊ|TRUNG\s*TÂM\s*THƯƠNG\s*MẠI|CỬA\s*HÀNG", re.I), "F3.1", "thương mại"),
    (re.compile(r"NHÀ\s*HÀNG|QUÁN\s*ĂN", re.I), "F3.2", "nhà hàng"),
    (re.compile(r"NHÀ\s*XƯỞNG|XƯỞNG\s*SẢN\s*XUẤT", re.I), "F5.1", "nhà xưởng"),
    (re.compile(r"NHÀ\s*KHO|KHO\s*HÀNG", re.I), "F5.2", "kho"),
]


def infer_function_group(d: DrawingExtraction, texts: list[str]) -> None:
    if d.building.function_group:
        return
    blob = " ".join(texts)
    m = re.search(r"CÔNG\s*TRÌNH\s*[:\-]?\s*([^|\n]{3,60})", blob, re.I)
    candidates = [m.group(1)] if m else []
    candidates.append(blob)
    for text in candidates:
        for pat, group, name in USE_TO_GROUP:
            if pat.search(text):
                d.building.function_group = group
                d.building.assumptions.append(
                    f"function_group={group}: suy ra từ công năng '{name}' (bản vẽ không ghi nhóm F) — cần xác nhận")
                return


def postprocess(d: DrawingExtraction, page_texts: dict[int, list[str]]) -> None:
    for p in d.pages:
        found = parse_declared(page_texts.get(p.page, []) + p.notes)
        for k, v in found.items():
            p.declared.setdefault(k, v)
        if UNOCCUPIED.search(" ".join(page_texts.get(p.page, []) + p.notes)):
            p.declared["unoccupied"] = True
        if "exit_distance_m" in p.declared:      # vị trí dòng ghi chú -> nơi đặt ghi chú lỗi 3.2.8
            p.declared["exit_distance_bbox"] = _locate(d.source_pdf, p.page, DECLARED_PATTERNS["exit_distance_m"])
        if "plan_diagonal_m" in p.declared or "exit_distance_m" in p.declared:
            p.notes.append(f"Số liệu thiết kế ghi trên bản vẽ: {p.declared}")
    n = apply_door_schedule(d)
    if n:
        d.building.assumptions.append(f"{n} cửa lấy kích thước từ bảng cửa (kích thước bảng cửa có thể là phủ bì, "
                                      "không phải thông thuỷ)")
    first_texts = [t for pno in sorted(page_texts)[:3] for t in page_texts[pno]]
    infer_function_group(d, first_texts + [p.sheet_title for p in d.pages])
    finalize(d, page_texts)


def _locate(pdf: str, page_no: int, pat: re.Pattern) -> list[float] | None:
    from pathlib import Path

    from ..pdf.render import vector_text
    try:
        return next((t["bbox"] for t in vector_text(Path(pdf), page_no) if pat.search(t["text"])), None)
    except Exception:
        return None


def _page(d: DrawingExtraction, no: int) -> PageExtraction | None:
    return next((p for p in d.pages if p.page == no), None)


# --------------------------------------------------------------- kiểm chứng & hợp nhất (rút ra từ hồ sơ thật)
# Khoảng giá trị hợp lý (m). Ngoài khoảng -> Gemini đọc nhầm (vd chi tiết bậc thang 132 mm bị coi là bề rộng thang).
PLAUSIBLE = {
    "flight_width_m": (0.5, 6.0), "landing_width_m": (0.5, 10.0), "tread_m": (0.1, 0.6), "riser_m": (0.03, 0.35),
    "width_m": (0.4, 12.0), "height_m": (1.2, 6.0), "length_m": (0.5, 500.0),
}
NUMERIC_ATTRS = ("width_m", "height_m", "flight_width_m", "tread_m", "riser_m", "landing_width_m")
EVIDENCE = {
    "has_auto_sprinkler": re.compile(r"SPRINKLER|CHỮA\s*CHÁY\s*TỰ\s*ĐỘNG|ĐẦU\s*PHUN", re.I),
    "has_auto_fire_alarm": re.compile(r"BÁO\s*CHÁY\s*TỰ\s*ĐỘNG|ĐẦU\s*BÁO|TỦ\s*TRUNG\s*TÂM\s*BÁO\s*CHÁY", re.I),
}
REF_ONLY_PAGES = {"section", "elevation", "site", "door_schedule", "pump"}


def _numbers(texts: list[str]) -> set[int]:
    out: set[int] = set()
    for t in texts:
        for m in re.finditer(r"\d+(?:[.,]\d+)?", t):
            v = float(m.group(0).replace(",", "."))
            out.add(round(v * 1000) if v < 20 else round(v))     # 0.9 (m) hoặc 900 (mm) -> 900
    return out


def check_plausible(d: DrawingExtraction) -> int:
    n = 0
    for e in d.elements():
        for k, (lo, hi) in PLAUSIBLE.items():
            v = e.attrs.get(k)
            if isinstance(v, (int, float)) and not lo <= v <= hi:
                e.attrs.setdefault("_rejected", {})[k] = v
                del e.attrs[k]
                n += 1
    return n


def verify_numbers(d: DrawingExtraction, page_texts: dict[int, list[str]]) -> None:
    """Số đo Gemini đọc phải xuất hiện trong text vector của trang (hoặc trang bảng cửa). Không thấy -> '_unverified'.
    Bỏ qua trang không có text (bản scan) vì không có gì để đối chiếu."""
    sched_pages = [p.page for p in d.pages if p.category == "door_schedule"]
    for p in d.pages:
        texts = page_texts.get(p.page, [])
        if sum(len(t) for t in texts) < 50:
            continue
        nums = _numbers(texts + [t for sp in sched_pages for t in page_texts.get(sp, [])])
        for e in p.elements:
            if e.source != "gemini":
                continue
            bad = [k for k in NUMERIC_ATTRS
                   if isinstance(e.attrs.get(k), (int, float)) and round(e.attrs[k] * 1000) not in nums]
            if bad:
                e.attrs["_unverified"] = bad


def require_evidence(d: DrawingExtraction, page_texts: dict[int, list[str]]) -> None:
    """Gemini hay tự suy 'có sprinkler/báo cháy'. Chỉ giữ True khi bản vẽ có chữ làm căn cứ."""
    blob = " ".join(t for ts in page_texts.values() for t in ts) + " ".join(n for p in d.pages for n in p.notes)
    h = d.building.height_pccc_m
    if isinstance(h, (int, float)) and round(h * 1000) not in _numbers(list(page_texts.get(0, [])) + blob.split()):
        levels = sorted(set(re.findall(r"\+\s?\d{1,3}[.,]\d{3}", blob)), key=lambda x: float(x[1:].replace(",", ".")))
        d.building.assumptions.append(
            f"height_pccc_m={h}: Gemini ước lượng, không có số này trên bản vẽ"
            + (f" (cao độ ghi trên bản vẽ: {', '.join(levels[-6:])})" if levels else "")
            + " — xác nhận bằng --set height_pccc_m=…")
    for key, pat in EVIDENCE.items():
        if getattr(d.building, key) is True and not pat.search(blob):
            setattr(d.building, key, None)
            d.building.assumptions.append(
                f"{key}: Gemini đánh dấu có nhưng không thấy căn cứ trên bản vẽ -> coi là CHƯA RÕ (dùng --set {key}=true nếu có)")


def fix_types(d: DrawingExtraction) -> None:
    for p in d.pages:
        for e in p.elements:
            lab = e.label.upper()
            if e.type == "stair" and "THANG MÁY" in lab:
                e.type = "elevator"
            elif e.type == "stair" and re.search(r"CHI\s*TIẾT|BẬC\s*THANG|^\W*\d+'?\W*$|^EI\s*\d", lab):
                e.type = "other"                 # chi tiết bậc, số trục, nhãn EI... không phải 1 cầu thang
                e.attrs["ref_only"] = True
            elif e.type == "stair" and not lab.strip() and p.category == "stair":
                e.attrs["ref_only"] = True


def consolidate_stairs(d: DrawingExtraction) -> None:
    """Hợp nhất thang theo ký hiệu (BTB1, TB3...) trên toàn bộ hồ sơ:
    - Không thoát nạn CHỈ khi có ghi chú rõ ('không thoát nạn', '_evac_note'); còn lại là thang thoát nạn.
    - Loại thang (N1/L1/loai3...): ưu tiên ghi chú vector, rồi trang chi tiết thang, rồi giá trị xuất hiện nhiều nhất.
    - Số đo: lấy từ trang chi tiết thang. Kiểm tra số đo chỉ chạy 1 lần/thang (bản đại diện); các bản khác 'ref_only'."""
    by_label: dict[str, list] = {}
    for p in d.pages:
        for e in p.elements:
            if e.type == "stair" and e.label and re.match(r"^B?TB\s*\d|^CT\s*\d|^THANG", e.label.strip(), re.I):
                by_label.setdefault(_norm(e.label), []).append((p, e))
    for label, items in by_label.items():
        # ghi chú (không thoát nạn / loại thang) chỉ tin khi gắn với thang này ở >= 1/2 số trang mặt bằng có thang đó
        n_plan = sum(1 for p, _ in items if p.category == "plan") or 1
        evac_false = sum(1 for _, e in items if e.attrs.get("_evac_note")) * 2 >= n_plan
        noted = [e.attrs["stair_type"] for _, e in items if e.attrs.get("_type_note")]
        types = (noted if len(noted) * 2 >= n_plan else []) or \
                [e.attrs["stair_type"] for p, e in items if p.category == "stair" and e.attrs.get("stair_type")] or \
                [e.attrs["stair_type"] for _, e in items if e.attrs.get("stair_type")]
        stype = max(set(types), key=types.count) if types else None
        detail = [e for p, e in items if p.category == "stair"]
        rep = max(detail or [e for _, e in items], key=lambda e: sum(k in e.attrs for k in NUMERIC_ATTRS))
        for p, e in items:
            e.attrs["is_evacuation"] = not evac_false
            if stype:
                e.attrs["stair_type"] = stype
            if e is not rep:
                e.attrs["ref_only"] = True        # vẫn dùng để đếm lối ra, không kiểm số đo lặp lại
    # Thang không ký hiệu: không hợp nhất được -> chỉ tin ghi chú trên bản vẽ, không tin phỏng đoán của Gemini
    labelled = {id(e) for items in by_label.values() for _, e in items}
    for e in d.elements():
        if e.type == "stair" and id(e) not in labelled:
            e.attrs["is_evacuation"] = not e.attrs.get("_evac_note")
            if not e.attrs.get("_type_note"):
                e.attrs.pop("stair_type", None)
            e.attrs["ref_only"] = True
    # Trang mặt cắt/mặt đứng/tổng mặt bằng: chỉ tham khảo. Trang chi tiết thang: cửa đã được kiểm trên mặt bằng.
    for p in d.pages:
        for e in p.elements:
            if e.attrs.get("schedule_entry"):
                continue
            if p.category in REF_ONLY_PAGES or (p.category == "stair" and e.type != "stair"):
                e.attrs["ref_only"] = True


def schedule_authority(d: DrawingExtraction) -> None:
    """Bảng cửa là nguồn chuẩn: loại cửa trong bảng KHÔNG có EI thì cửa đó không phải cửa ngăn cháy."""
    sched = {_norm(e.label): e for p in d.pages if p.category == "door_schedule" for e in p.elements if e.label}
    for e in d.elements():
        if e.type == "fire_door" and not e.attrs.get("fire_rating") and not e.attrs.get("schedule_entry"):
            s = sched.get(_norm(e.label))
            if s is not None and not s.attrs.get("fire_rating"):
                e.type = "exit_door" if e.attrs.get("is_exit") else "door"
                e.attrs["type_from_schedule"] = True


def finalize(d: DrawingExtraction, page_texts: dict[int, list[str]]) -> None:
    n = check_plausible(d)
    if n:
        d.building.assumptions.append(f"{n} số đo ngoài khoảng hợp lý đã bị loại (đọc nhầm chi tiết/kích thước khác)")
    verify_numbers(d, page_texts)
    require_evidence(d, page_texts)
    fix_types(d)
    consolidate_stairs(d)
    schedule_authority(d)
