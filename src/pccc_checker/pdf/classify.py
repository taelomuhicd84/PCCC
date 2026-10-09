"""Phân loại trang bản vẽ theo text (0 token) để chỉ gửi Gemini các trang liên quan thoát nạn/PCCC.

Hồ sơ thực tế thường gộp kiến trúc + kết cấu + điện nước: gửi cả bộ cho Gemini rất lãng phí.
Trang không có text (PDF scan) -> 'unknown' và vẫn được xử lý.
"""
from __future__ import annotations

import re
from pathlib import Path

from .render import page_count, vector_text

# Thứ tự quan trọng: loại kết cấu được xét trước vì "MẶT BẰNG DẦM TẦNG 1" cũng chứa "MẶT BẰNG TẦNG".
CATEGORIES: list[tuple[str, re.Pattern]] = [
    ("structure", re.compile(r"MÓNG|DẦM|ĐÀ KIỀNG|ĐÀ GIẰNG|THÉP SÀN|CỐT THÉP|UỐN THÉP|KẾT CẤU|CỌC BTCT|SÀN BTCT", re.I)),
    ("mep", re.compile(r"CẤP NƯỚC|THOÁT NƯỚC|ĐIỆN CHIẾU SÁNG|ĐIỀU HÒA|CHỐNG SÉT", re.I)),
    ("door_schedule", re.compile(r"(CHI TIẾT|THỐNG KÊ|BẢNG)\s*(CỬA|CỬA ĐI)", re.I)),
    ("site", re.compile(r"(TỔNG\s*MẶT\s*BẰNG|MẶT\s*BẰNG\s*TỔNG\s*THỂ|GIAO THÔNG PCCC|CHI TIẾT BÃI)", re.I)),
    ("pump", re.compile(r"PHÒNG\s*BƠM", re.I)),
    ("plan", re.compile(r"MẶT\s*BẰNG\s*(TẦNG|TRỆT|HẦM|BÁN HẦM|MÁI|THOÁT NẠN|BỐ TRÍ|PCCC|ĐIỂN HÌNH)", re.I)),
    ("stair", re.compile(r"CHI TIẾT\s*(B?TB\d|THANG|CẦU THANG)|(MẶT\s*BẰNG|MẶT\s*CẮT)\s*(BUỒNG|CẦU)\s*THANG", re.I)),
    ("section", re.compile(r"MẶT\s*CẮT", re.I)),
    ("elevation", re.compile(r"MẶT\s*ĐỨNG", re.I)),
]
RELEVANT = {"plan", "stair", "door_schedule", "section", "site", "unknown"}
TITLE_LINE = re.compile(r"^(MẶT|CHI TIẾT|BẢNG|THỐNG KÊ|TỔNG|BỐ TRÍ|SƠ ĐỒ|KẾT CẤU)", re.I)


def classify_page(pdf: Path, page_no: int) -> tuple[str, str]:
    """Trả về (loại, tiêu đề nhận diện được)."""
    texts = [t["text"] for t in vector_text(pdf, page_no)]
    if sum(len(t) for t in texts) < 50:
        return "unknown", ""
    titles = [t for t in texts if TITLE_LINE.match(t) and len(t) <= 80]
    # Ưu tiên tiêu đề có chữ to nhất là khó; dùng toàn bộ dòng tiêu đề, xét loại theo thứ tự ưu tiên.
    blob = " | ".join(titles)
    for name, pat in CATEGORIES:
        if pat.search(blob):
            return name, (titles[0] if titles else "")
    return ("cover" if len(texts) < 40 else "other"), (titles[0] if titles else "")


def classify(pdf: Path) -> list[dict]:
    return [dict(zip(("page", "category", "title"), (p, *classify_page(pdf, p))))
            for p in range(1, page_count(pdf) + 1)]


def relevant_pages(pdf: Path) -> list[int]:
    return [c["page"] for c in classify(pdf) if c["category"] in RELEVANT]
