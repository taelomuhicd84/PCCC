"""Phân loại trang bản vẽ theo text (0 token) để chỉ gửi Gemini các trang liên quan thoát nạn/PCCC.

Hồ sơ thực tế thường gộp kiến trúc + kết cấu + điện nước: gửi cả bộ cho Gemini rất lãng phí.
Trang không có text (PDF scan) -> 'unknown' và vẫn được xử lý.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Tuple

from .render import page_count, vector_text

# Thứ tự quan trọng: loại kết cấu được xét trước vì "MẶT BẰNG DẦM TẦNG 1" cũng chứa "MẶT BẰNG TẦNG".
CATEGORIES: list[tuple[str, re.Pattern]] = [
    ("structure", re.compile(r"MÓNG|DẦM|ĐÀ KIỀNG|ĐÀ GIẰNG|THÉP SÀN|CỐT THÉP|UỐN THÉP|KẾT CẤU|CỌC BTCT|SÀN BTCT", re.I)),
    ("mep", re.compile(r"CẤP NƯỚC|THOÁT NƯỚC|ĐIỆN CHIẾU SÁNG|ĐIỀU HÒA|CHỐNG SÉT", re.I)),
    ("door_schedule", re.compile(r"(CHI TIẾT|THỐNG KÊ|BẢNG)\s*(CỬA|CỬA ĐI)", re.I)),
    ("site", re.compile(r"(TỔNG\s*MẶT\s*BẰNG|MẶT\s*BẰNG\s*TỔNG\s*THỂ|GIAO THÔNG PCCC|CHI TIẾT BÃI)", re.I)),
    ("pump", re.compile(r"PHÒNG\s*BƠM", re.I)),
    ("plan", re.compile(r"MẶT\s*BẰNG\s*(TẦNG|TRỆT|HẦM|BÁN HẦM|MÁI|THOÁT NẠN|BỐ TRÍ|PCCC|ĐIỂN HÌNH|LẦU|SÂN\s*THƯỢNG)", re.I)),
    ("stair", re.compile(r"CHI TIẾT\s*(B?TB\d|THANG|CẦU THANG)|(MẶT\s*BẰNG|MẶT\s*CẮT)\s*(BUỒNG|CẦU)\s*THANG", re.I)),
    ("section", re.compile(r"MẶT\s*CẮT", re.I)),
    ("elevation", re.compile(r"MẶT\s*ĐỨNG", re.I)),
]
# Trang chứa thông tin công trình (bước `info`). Nhận diện theo nhãn đầu dòng, không chỉ tiêu đề, và xét trước
# 'structure'/'elevation' vì bảng quy mô hay có chữ "KẾT CẤU" (cấp nguy hiểm cháy kết cấu).
INFO_LABEL = re.compile(r"^\W*(BẬC\s*CHỊU\s*LỬA|NHÓM\s*(NHÀ|NGUY\s*HIỂM)|CHIỀU\s*CAO\s*(PCCC|CÔNG\s*TRÌNH)|KHỐI\s*TÍCH|"
                        r"SỐ\s*TẦNG|DIỆN\s*TÍCH\s*XÂY\s*DỰNG|TỔNG\s*DIỆN\s*TÍCH\s*SÀN|CẤP\s*NGUY\s*HIỂM\s*CHÁY|"
                        r"HẠNG\s*NGUY\s*HIỂM\s*CHÁY|CÔNG\s*NĂNG)", re.I)
KHU_DAT = re.compile(r"DIỆN\s*TÍCH\s*KHU\s*ĐẤT|TỔNG\s*DIỆN\s*TÍCH\s*ĐẤT\b(?!\s*(KHÔNG\s*)?XÂY)", re.I)
BANG_HANG_MUC = re.compile(r"BẢNG\s*(THỐNG\s*KÊ\s*)?(CÁC\s*)?HẠNG\s*MỤC\s*CÔNG\s*TRÌNH|BẢNG\s*QUY\s*MÔ", re.I)       # mặt bằng định vị / tổng mặt bằng
TM_PCCC = re.compile(r"THUYẾT\s*MINH.*(PCCC|PHÒNG\s*CHÁY|AN\s*TOÀN\s*CHÁY|CÔNG\s*TRÌNH|THIẾT\s*KẾ)", re.I)
INFO_CATEGORIES = {"cover", "bang_quy_mo", "thuyet_minh_pccc", "khu_dat", "ghi_chu_pccc"}
FIRE_INPUT_KEYS = {"bac_chiu_lua", "nhom_nha", "hang_chay_no", "chieu_cao_pccc", "cap_nguy_hiem_chay_ket_cau"}
DRAWING_CATEGORIES = {"plan", "stair", "door_schedule", "section", "site"}
RELEVANT = {"plan", "stair", "door_schedule", "section", "site", "unknown"}
TITLE_LINE = re.compile(r"^(MẶT|CHI TIẾT|BẢNG|THỐNG KÊ|TỔNG|BỐ TRÍ|SƠ ĐỒ|KẾT CẤU)", re.I)


def info_kind(texts: List[str]) -> str:
    """'bang_quy_mo' | 'thuyet_minh_pccc' | 'khu_dat' | '' — trang có thông tin công trình cho bước `info`."""
    labels = {INFO_LABEL.match(t).group(1).split()[0].upper() for t in texts if INFO_LABEL.match(t)}
    if len(labels) >= 3:                     # >= 3 loại nhãn quy mô khác nhau (bậc, nhóm, chiều cao...) ở đầu dòng
        return "bang_quy_mo"
    if any(BANG_HANG_MUC.search(t) and len(t) <= 80 for t in texts):
        return "bang_quy_mo"
    if any(TM_PCCC.search(t) and len(t) <= 80 for t in texts):
        return "thuyet_minh_pccc"
    if any(KHU_DAT.search(t) for t in texts):
        return "khu_dat"
    return ""


def classify_page(pdf: Path, page_no: int) -> tuple[str, str]:
    """Trả về (loại, tiêu đề nhận diện được).
    Trang bản vẽ (mặt bằng, thang...) có kèm bảng quy mô vẫn giữ loại bản vẽ để `extract` không bỏ sót;
    `info_pages()` nhận diện riêng các trang đó."""
    texts = [t["text"] for t in vector_text(pdf, page_no)]
    if sum(len(t) for t in texts) < 50:
        return "unknown", ""
    titles = [t for t in texts if TITLE_LINE.match(t) and len(t) <= 80]
    title = titles[0] if titles else ""
    # Ưu tiên tiêu đề có chữ to nhất là khó; dùng toàn bộ dòng tiêu đề, xét loại theo thứ tự ưu tiên.
    blob = " | ".join(titles)
    base = next((name for name, pat in CATEGORIES if pat.search(blob)), "")
    if base in DRAWING_CATEGORIES:
        return base, title
    kind = info_kind(texts)
    if kind:
        return kind, next((t for t in texts if TM_PCCC.search(t) and len(t) <= 80), title)
    return base or ("cover" if len(texts) < 40 else "other"), title


def classify(pdf: Path) -> list[dict]:
    return [dict(zip(("page", "category", "title"), (p, *classify_page(pdf, p))))
            for p in range(1, page_count(pdf) + 1)]


def relevant_pages(pdf: Path) -> list[int]:
    return [c["page"] for c in classify(pdf) if c["category"] in RELEVANT]


def _fire_note(texts: List[str]) -> str:
    """Trang bản vẽ có câu ghi chú nêu thông tin PCCC ("Nhà hàng có bậc chịu lửa bậc IV...") -> 'ghi_chu_pccc'."""
    from ..project_info import match_text     # import muộn: tránh vòng import
    return "ghi_chu_pccc" if any(k in FIRE_INPUT_KEYS for t in texts for k, _, _ in match_text(t)) else ""


def info_pages(pdf: Path) -> List[Tuple[int, str]]:
    """Trang cho bước `info`: bìa, bảng quy mô, thuyết minh PCCC — kể cả trang mặt bằng có kèm bảng quy mô
    và trang mà `extract` bỏ qua. Trả về [(trang, loại)]."""
    out = []
    for p in range(1, page_count(pdf) + 1):
        texts = [t["text"] for t in vector_text(pdf, p)]
        if sum(len(t) for t in texts) < 50:
            out.append((p, "unknown"))           # trang scan: không có text -> để Gemini đọc
            continue
        kind = info_kind(texts) or ("cover" if classify_page(pdf, p)[0] == "cover" else "") or _fire_note(texts)
        if kind:
            out.append((p, kind))
    return out
