"""Extractor dùng Gemini (vision) — phần "mắt" của hệ thống, rẻ hơn nhiều so với để Claude đọc ảnh.

Kết quả từng trang được cache theo hash(PDF)+trang+model để không gọi lại API khi chạy lại.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from ..config import PROMPTS_DIR, gemini_api_key
from ..models import ELEMENT_TYPES, Element, PageExtraction
from ..pdf.render import page_size, render_tiles, vector_text
from .base import Extractor


def _file_hash(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0) if m else text)


class GeminiExtractor(Extractor):
    name = "gemini"

    def __init__(self, model: str = "gemini-2.5-flash", dpi: int = 150, grid: tuple[int, int] = (1, 1),
                 max_px: int = 3000, temperature: float = 0.1, cache_dir: Path | None = None,
                 fallback_models: list[str] | None = None, retries: int = 4):
        key = gemini_api_key()
        if not key:
            raise RuntimeError("Thiếu GEMINI_API_KEY (đặt trong .env hoặc biến môi trường).")
        from google import genai  # import muộn để chạy được offline khi không dùng Gemini
        self._genai = genai
        self.client = genai.Client(api_key=key)
        self.model, self.dpi, self.grid, self.max_px, self.temperature = model, dpi, grid, max_px, temperature
        self.prompt = (PROMPTS_DIR / "gemini_extract.md").read_text(encoding="utf-8")
        self.cache_dir = cache_dir
        self.fallback_models = fallback_models or []
        self.retries = retries

    # ------------------------------------------------------------------ API
    def _call(self, png: bytes, texts: list[dict]) -> dict[str, Any]:
        from google.genai import types
        ctx = json.dumps(texts[:400], ensure_ascii=False)
        contents = [
            types.Part.from_bytes(data=png, mime_type="image/png"),
            f"{self.prompt}\n\nTEXT VECTOR TRONG VÙNG NÀY (toạ độ đã chuẩn hoá 0-1000 theo ảnh, dạng [x0,y0,x1,y1]):\n{ctx}",
        ]
        cfg = types.GenerateContentConfig(temperature=self.temperature, response_mime_type="application/json")
        last_err: Exception | None = None
        for model in [self.model, *self.fallback_models]:
            for attempt in range(self.retries):
                try:
                    resp = self.client.models.generate_content(model=model, contents=contents, config=cfg)
                    return _parse_json(resp.text or "{}")
                except Exception as e:  # 503 quá tải / 429 quota / mạng / JSON lỗi -> chờ rồi thử lại
                    last_err = e
                    if "API key" in str(e) or "PERMISSION_DENIED" in str(e):
                        raise
                    time.sleep(min(60, 5 * 2 ** attempt))
        raise RuntimeError(f"Gemini lỗi sau khi thử lại và đổi model dự phòng: {last_err}")

    # -------------------------------------------------------------- per page
    def extract_page(self, pdf: Path, page_no: int):
        cache = None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            g = f"{self.grid[0]}x{self.grid[1]}"
            cache = self.cache_dir / f"{_file_hash(pdf)}_p{page_no}_{self.model}_{g}.json"
            if cache.exists():
                raw_tiles = json.loads(cache.read_text(encoding="utf-8"))
                return self._to_page(pdf, page_no, raw_tiles)

        all_text = vector_text(pdf, page_no)
        raw_tiles = []
        for tile in render_tiles(pdf, page_no, self.dpi, self.grid, max_px=self.max_px):
            x0, y0, x1, y1 = tile.clip
            tw, th = x1 - x0, y1 - y0
            local = []
            for t in all_text:
                bx = t["bbox"]
                if bx[0] >= x0 and bx[2] <= x1 and bx[1] >= y0 and bx[3] <= y1:
                    local.append({"text": t["text"], "bbox": [
                        round((bx[0] - x0) / tw * 1000), round((bx[1] - y0) / th * 1000),
                        round((bx[2] - x0) / tw * 1000), round((bx[3] - y0) / th * 1000)]})
            raw_tiles.append({"clip": tile.clip, "data": self._call(tile.png, local)})
        if cache:
            cache.write_text(json.dumps(raw_tiles, ensure_ascii=False, indent=1), encoding="utf-8")
        return self._to_page(pdf, page_no, raw_tiles)

    def _to_page(self, pdf: Path, page_no: int, raw_tiles: list[dict]):
        W, H = page_size(pdf, page_no)
        page = PageExtraction(page_no, W, H)
        building: dict[str, Any] = {}
        n = 0
        for rt in raw_tiles:
            x0, y0, x1, y1 = rt["clip"]
            tw, th = x1 - x0, y1 - y0
            data = rt["data"] or {}
            page.sheet_title = page.sheet_title or data.get("sheet_title", "")
            page.scale = page.scale or data.get("scale", "")
            page.notes.extend(data.get("notes") or [])
            pb = data.get("plan_box_2d")
            if isinstance(pb, list) and len(pb) == 4:
                ymin, xmin, ymax, xmax = pb
                b = [x0 + xmin / 1000 * tw, y0 + ymin / 1000 * th, x0 + xmax / 1000 * tw, y0 + ymax / 1000 * th]
                page.plan_bbox = b if not page.plan_bbox else [min(page.plan_bbox[0], b[0]), min(page.plan_bbox[1], b[1]),
                                                                max(page.plan_bbox[2], b[2]), max(page.plan_bbox[3], b[3])]
            for k, v in (data.get("building") or {}).items():
                if v is not None and building.get(k) is None:
                    building[k] = v
            for el in data.get("elements") or []:
                box = el.get("box_2d") or [0, 0, 0, 0]
                if len(box) != 4:
                    continue
                ymin, xmin, ymax, xmax = box
                bbox = [x0 + xmin / 1000 * tw, y0 + ymin / 1000 * th, x0 + xmax / 1000 * tw, y0 + ymax / 1000 * th]
                typ = el.get("type", "other")
                n += 1
                page.elements.append(Element(
                    id=f"p{page_no}-g{n}", type=typ if typ in ELEMENT_TYPES else "other", page=page_no,
                    bbox=[round(v, 1) for v in bbox], label=str(el.get("label") or ""),
                    attrs=el.get("attrs") or {}, confidence=float(el.get("confidence") or 0.5), source="gemini"))
        page.elements = _dedupe(page.elements)
        return page, building


def _iou(a: list[float], b: list[float]) -> float:
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _same(a: Element, b: Element) -> bool:
    if a.type != b.type:
        return False
    if _iou(a.bbox, b.bbox) > 0.5:
        return True
    # cùng ký hiệu (vd "D2") và hai khung chạm/gần nhau -> cùng một đối tượng bị cắt ở 2 tile
    la, lb = a.label.strip().upper(), b.label.strip().upper()
    if la and la == lb:
        pad = 20
        return not (b.bbox[0] > a.bbox[2] + pad or b.bbox[2] < a.bbox[0] - pad
                    or b.bbox[1] > a.bbox[3] + pad or b.bbox[3] < a.bbox[1] - pad)
    return False


def _dedupe(els: list[Element]) -> list[Element]:
    """Bỏ trùng do các tile chồng lấn: giữ phần tử confidence cao, bổ sung thuộc tính còn thiếu từ bản trùng."""
    kept: list[Element] = []
    for e in sorted(els, key=lambda x: -x.confidence):
        dup = next((k for k in kept if _same(k, e)), None)
        if dup is None:
            kept.append(e)
        else:
            for key, v in e.attrs.items():
                dup.attrs.setdefault(key, v)
    return kept
