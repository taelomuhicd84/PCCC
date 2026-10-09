"""Giao diện chung cho các extractor (Gemini, vector-text, ... thêm sau)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..models import BuildingInfo, DrawingExtraction, PageExtraction
from ..pdf.classify import RELEVANT, classify_page
from ..pdf.render import page_count, vector_text
from .postprocess import postprocess


class Extractor(ABC):
    name = "base"

    @abstractmethod
    def extract_page(self, pdf: Path, page_no: int) -> tuple[PageExtraction, dict[str, Any]]:
        """Trả về (PageExtraction, building_info_dict đọc được trên trang)."""

    def extract(self, pdf: Path, pages: list[int] | str | None = None,
                building_override: dict[str, Any] | None = None, log=print) -> DrawingExtraction:
        """pages: list số trang | "auto" (chỉ trang liên quan thoát nạn, theo pdf/classify.py) | None (tất cả)."""
        n_pages = page_count(pdf)
        categories = {p: classify_page(pdf, p)[0] for p in range(1, n_pages + 1)}
        if pages == "auto":
            pages = [p for p, c in categories.items() if c in RELEVANT]
            skipped = n_pages - len(pages)
            log(f"[auto] xử lý {len(pages)}/{n_pages} trang liên quan, bỏ qua {skipped} trang (kết cấu/bìa/MEP...)")
        pages = pages or list(range(1, n_pages + 1))
        building: dict[str, Any] = {}
        results = []
        page_texts: dict[int, list[str]] = {}
        for p in sorted(set(pages) | set(range(1, min(3, n_pages) + 1))):   # trang bìa: chỉ đọc text (0 token)
            page_texts[p] = [t["text"] for t in vector_text(pdf, p)]
        workers = getattr(self, "workers", 1)
        log(f"[{self.name}] {len(pages)} trang, {workers} luồng song song")

        def run(p: int):
            out = self.extract_page(pdf, p)
            log(f"[{self.name}] xong trang {p} ({categories[p]})")
            return out

        if workers > 1:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(workers) as ex:
                outputs = list(ex.map(run, pages))
        else:
            outputs = [run(p) for p in pages]
        for p, (page, binfo) in zip(pages, outputs):
            page.category = categories[p]
            for e in page.elements:      # chuẩn hoá: thang trên bản vẽ PCCC mặc định là thang thoát nạn
                if e.type == "stair":
                    e.attrs.setdefault("is_evacuation", True)
            results.append(page)
            for k, v in (binfo or {}).items():
                if v is not None and building.get(k) is None:
                    building[k] = v
        building.update({k: v for k, v in (building_override or {}).items() if v is not None})
        d = DrawingExtraction(str(pdf), BuildingInfo.from_dict(building), results, self.name)
        postprocess(d, page_texts)
        return d
