"""Render trang PDF thành ảnh (PNG) và lấy text vector kèm toạ độ."""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from .vn_encoding import fix_identity_fonts, fix_span


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


def _table_images(page) -> list:
    """Ảnh raster dán vào trang (bảng Word/Excel...: ≥ 2% khổ giấy, rộng ≥ 600 px) — chữ trong đó không có ở lớp text."""
    area = page.rect.width * page.rect.height
    return [im for im in page.get_image_info()
            if (im["bbox"][2] - im["bbox"][0]) * (im["bbox"][3] - im["bbox"][1]) >= 0.02 * area and im.get("width", 0) >= 600]


def image_table_pages(pdf_path: Path, pages) -> set[int]:
    with pymupdf.open(pdf_path) as doc:
        return {p for p in pages if _table_images(doc[p - 1])}


def export_image_tables(pdf_path: Path, pages, out_dir: Path) -> list[Path]:
    """Cắt từng bảng dạng ảnh ra PNG (cạnh dài ~1800 px) để Claude kiểm giá trị * — đọc ảnh cắt chính xác hơn Gemini
    (thử BW Đồng An 14/10/2026). -> danh sách file."""
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    with pymupdf.open(pdf_path) as doc:
        for p in pages:
            page = doc[p - 1]
            for k, im in enumerate(_table_images(page), 1):
                r = pymupdf.Rect(im["bbox"]) & page.rect
                zoom = min(3.0, 1800 / max(1.0, r.width, r.height))
                f = out_dir / f"p{p:02d}_bang{k}.png"
                page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=r).save(f)
                files.append(f)
    return files


def vector_text(pdf_path: Path, page_no: int) -> list[dict]:
    """Trả về các dòng text vector: [{'text', 'bbox'}] (đã chuyển font VNI -> Unicode). Rỗng nếu PDF là ảnh scan."""
    out = []
    with pymupdf.open(pdf_path) as doc:
        page = doc[page_no - 1]
        fix_identity_fonts(doc, page)
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(fix_span(s["text"], s.get("font", "")) for s in line["spans"])
                text = unicodedata.normalize("NFC", text.replace("\xa0", " ")).strip()
                if text:
                    out.append({"text": text, "bbox": [round(v, 1) for v in line["bbox"]]})
    return out
