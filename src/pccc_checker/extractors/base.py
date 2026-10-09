"""Giao diện chung cho các extractor (Gemini, vector-text, ... thêm sau)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..models import BuildingInfo, DrawingExtraction, PageExtraction
from ..pdf.render import page_count


class Extractor(ABC):
    name = "base"

    @abstractmethod
    def extract_page(self, pdf: Path, page_no: int) -> tuple[PageExtraction, dict[str, Any]]:
        """Trả về (PageExtraction, building_info_dict đọc được trên trang)."""

    def extract(self, pdf: Path, pages: list[int] | None = None,
                building_override: dict[str, Any] | None = None, log=print) -> DrawingExtraction:
        pages = pages or list(range(1, page_count(pdf) + 1))
        building: dict[str, Any] = {}
        results = []
        for p in pages:
            log(f"[{self.name}] trang {p}/{pages[-1]}")
            page, binfo = self.extract_page(pdf, p)
            for e in page.elements:      # chuẩn hoá: thang trên bản vẽ PCCC mặc định là thang thoát nạn
                if e.type == "stair":
                    e.attrs.setdefault("is_evacuation", True)
            results.append(page)
            for k, v in (binfo or {}).items():
                if v is not None and building.get(k) is None:
                    building[k] = v
        building.update({k: v for k, v in (building_override or {}).items() if v is not None})
        return DrawingExtraction(str(pdf), BuildingInfo.from_dict(building), results, self.name)
