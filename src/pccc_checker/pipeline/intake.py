"""Bước 1 — intake: lập chỉ mục trang (0 token).

Mỗi trang đi theo một luồng, quyết định ai đọc vùng nào:
  LAYER   : chữ vector đọc được, không có bảng ảnh lớn -> script lấy chữ + toạ độ, không tốn token thị giác
  HON-HOP : nền vector kèm bảng dán dạng ảnh (bảng quy mô, bảng tính thoát nạn...) -> chỉ vùng ảnh cần đọc bằng mắt
  SCAN    : không có lớp chữ dùng được -> cả trang là ảnh
Mã băm từng trang để bản vẽ sửa đổi chỉ đọc lại trang đổi.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf

from ..pdf.classify import _readable, classify_page
from ..pdf.render import _table_images, image_rect, vector_text

LUONG = ("LAYER", "HON-HOP", "SCAN")


def page_hash(doc, page) -> str:
    """sha1 nội dung vẽ của trang + luồng ảnh nhúng (đổi chữ, nét hay ảnh dán đều đổi băm)."""
    h = hashlib.sha1(page.read_contents())
    for xref, *_ in page.get_images(full=True):
        h.update(hashlib.sha1(doc.xref_stream_raw(xref) or b"").digest())
    return h.hexdigest()[:16]


def _norm(r: pymupdf.Rect, page) -> list[float]:
    """bbox theo tỉ lệ 0–1 của trang đã xoay (gốc trên-trái) — dùng chung cho cả LAYER và SCAN."""
    W, H = page.rect.width, page.rect.height
    return [round(r.x0 / W, 4), round(r.y0 / H, 4), round(r.x1 / W, 4), round(r.y1 / H, 4)]


def luong_of(text: str, n_table_images: int) -> str:
    if not _readable(text):
        return "SCAN"
    return "HON-HOP" if n_table_images else "LAYER"


def page_index(pdf: Path) -> list[dict]:
    out = []
    with pymupdf.open(pdf) as doc:
        for i, page in enumerate(doc, 1):
            texts = vector_text(pdf, i)
            blob = " | ".join(t["text"] for t in texts)
            imgs = _table_images(page)
            loai, title = classify_page(pdf, i)
            out.append({
                "trang": i, "loai": loai, "tieu_de": title, "luong": luong_of(blob, len(imgs)),
                "so_ky_tu": len(blob), "xoay": page.rotation,
                "vung_anh": [_norm(image_rect(page, im), page) for im in imgs],
                "hash": page_hash(doc, page),
            })
    return out


def diff_hashes(old: list[dict], new: list[dict]) -> list[int]:
    """Trang có băm khác (hoặc mới thêm) so với page_index.json lần trước -> chỉ đọc lại các trang này."""
    prev = {p["trang"]: p["hash"] for p in old}
    return [p["trang"] for p in new if prev.get(p["trang"]) != p["hash"]]


def summary(idx: list[dict]) -> str:
    cnt = {k: sum(p["luong"] == k for p in idx) for k in LUONG}
    return f"{len(idx)} trang: " + ", ".join(f"{k} {v}" for k, v in cnt.items())
