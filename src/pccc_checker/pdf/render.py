"""Render trang PDF thành ảnh (PNG) và lấy text vector kèm toạ độ."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass
class Tile:
    page: int
    png: bytes
    clip: tuple[float, float, float, float]   # vùng trang (point) mà tile này phủ


def render_tiles(pdf_path: Path, page_no: int, dpi: int = 150, grid: tuple[int, int] = (1, 1),
                 overlap: float = 0.05, max_px: int = 3000) -> list[Tile]:
    """Cắt trang thành lưới rows x cols (có chồng lấn) để Gemini đọc chi tiết bản vẽ khổ lớn."""
    rows, cols = grid
    with pymupdf.open(pdf_path) as doc:
        page = doc[page_no - 1]
        W, H = page.rect.width, page.rect.height
        tw, th = W / cols, H / rows
        tiles: list[Tile] = []
        for r in range(rows):
            for c in range(cols):
                x0 = max(0, c * tw - overlap * tw)
                y0 = max(0, r * th - overlap * th)
                x1 = min(W, (c + 1) * tw + overlap * tw)
                y1 = min(H, (r + 1) * th + overlap * th)
                clip = pymupdf.Rect(x0, y0, x1, y1)
                zoom = dpi / 72
                longest = max(clip.width, clip.height) * zoom
                if longest > max_px:
                    zoom *= max_px / longest
                pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip, alpha=False)
                tiles.append(Tile(page_no, pix.tobytes("png"), (x0, y0, x1, y1)))
        return tiles


def page_count(pdf_path: Path) -> int:
    with pymupdf.open(pdf_path) as doc:
        return doc.page_count


def page_size(pdf_path: Path, page_no: int) -> tuple[float, float]:
    with pymupdf.open(pdf_path) as doc:
        r = doc[page_no - 1].rect
        return r.width, r.height


def vector_text(pdf_path: Path, page_no: int) -> list[dict]:
    """Trả về các dòng text vector: [{'text', 'bbox'}]. Rỗng nếu PDF là ảnh scan."""
    out = []
    with pymupdf.open(pdf_path) as doc:
        page = doc[page_no - 1]
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(s["text"] for s in line["spans"]).strip()
                if text:
                    out.append({"text": text, "bbox": [round(v, 1) for v in line["bbox"]]})
    return out
