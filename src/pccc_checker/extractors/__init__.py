"""Factory chọn extractor. Thêm extractor mới: tạo class kế thừa Extractor rồi đăng ký ở đây."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import Extractor
from .vector_extractor import VectorTextExtractor, _near


class HybridExtractor(Extractor):
    """Gemini đọc hình + vector text bổ sung số đo bị thiếu (khớp theo vị trí, cùng loại)."""
    name = "hybrid"

    def __init__(self, gemini: Extractor, vector: VectorTextExtractor):
        self.gemini, self.vector = gemini, vector

    def extract_page(self, pdf: Path, page_no: int):
        gp, gb = self.gemini.extract_page(pdf, page_no)
        vp, vb = self.vector.extract_page(pdf, page_no)
        for ve in vp.elements:
            match = next((ge for ge in gp.elements if ge.type == ve.type and _near(ge.bbox, ve.bbox, 30)), None)
            if match:
                for k, v in ve.attrs.items():
                    match.attrs.setdefault(k, v)
            else:
                gp.elements.append(ve)
        for k, v in vb.items():
            gb.setdefault(k, v)
        return gp, gb


def make_extractor(kind: str, settings: dict[str, Any], cache_dir: Path | None = None,
                   grid: tuple[int, int] = (1, 1)) -> Extractor:
    if kind == "vector":
        return VectorTextExtractor()
    from .gemini_extractor import GeminiExtractor
    g = settings["gemini"]
    gem = GeminiExtractor(model=g["model"], dpi=g["dpi"], grid=grid, max_px=g["max_tile_px"],
                          temperature=g["temperature"], cache_dir=cache_dir,
                          fallback_models=g.get("fallback_models"), retries=g.get("retries", 4))
    if kind == "gemini":
        return gem
    if kind == "hybrid":
        return HybridExtractor(gem, VectorTextExtractor())
    raise ValueError(f"extractor không hợp lệ: {kind}")
