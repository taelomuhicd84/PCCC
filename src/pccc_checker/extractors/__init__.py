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
        self.workers = getattr(gemini, "workers", 1)

    def extract_page(self, pdf: Path, page_no: int):
        from .gemini_extractor import GeminiQuotaError
        vp, vb = self.vector.extract_page(pdf, page_no)
        try:
            gp, gb = self.gemini.extract_page(pdf, page_no)
        except GeminiQuotaError as e:
            vp.notes.append(f"⚠ Gemini không đọc được trang này ({str(e)[:80]}...) — chỉ dùng text vector, cần chạy lại")
            vp.sheet_title = vp.sheet_title or ""
            return vp, vb
        gemini_empty = not gp.elements
        for ve in vp.elements:
            match = next((ge for ge in gp.elements if _match(ge, ve)), None)
            if match:
                for k, v in ve.attrs.items():
                    match.attrs.setdefault(k, v)
                # ghi chú trên bản vẽ (vector) là căn cứ chắc chắn hơn phỏng đoán của Gemini
                if ve.attrs.get("_evac_note"):
                    match.attrs.update(is_evacuation=False, _evac_note=True)
                if ve.attrs.get("_type_note"):
                    match.attrs.update(stair_type=ve.attrs["stair_type"], _type_note=True)
            elif gemini_empty:      # Gemini không đọc được gì -> dùng tạm kết quả vector
                gp.elements.append(ve)
        gp.plan_bbox = gp.plan_bbox or vp.plan_bbox
        gp.scale = gp.scale or vp.scale
        for k, v in vb.items():
            gb.setdefault(k, v)
        return gp, gb


def _match(ge, ve) -> bool:
    """Cùng đối tượng: cùng nhóm loại và (cùng ký hiệu hoặc vị trí gần nhau)."""
    group = lambda t: "door" if t in ("door", "exit_door", "fire_door") else t
    if group(ge.type) != group(ve.type):
        return False
    same_label = ge.label and ve.label and ge.label.replace(" ", "").upper() == ve.label.replace(" ", "").upper()
    if same_label and ge.type == "stair":      # ký hiệu thang (BTB1, TB3) là duy nhất trên 1 trang
        return True
    return _near(ge.bbox, ve.bbox, 60 if same_label else 20)


def make_extractor(kind: str, settings: dict[str, Any], cache_dir: Path | None = None,
                   grid: tuple[int, int] = (1, 1)) -> Extractor:
    if kind == "vector":
        return VectorTextExtractor()
    from .gemini_extractor import GeminiExtractor
    g = settings["gemini"]
    gem = GeminiExtractor(model=g["model"], dpi=g["dpi"], grid=grid, max_px=g["max_tile_px"],
                          temperature=g["temperature"], cache_dir=cache_dir,
                          fallback_models=g.get("fallback_models"), retries=g.get("retries", 4),
                          thinking_budget=g.get("thinking_budget"), workers=g.get("workers", 1))
    if kind == "gemini":
        return gem
    if kind == "hybrid":
        return HybridExtractor(gem, VectorTextExtractor())
    raise ValueError(f"extractor không hợp lệ: {kind}")
