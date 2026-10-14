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


class GeminiQuotaError(RuntimeError):
    """Hết quota theo ngày (free tier ~20 request/ngày/model) — thử lại vô ích, cần chờ hoặc nâng gói."""


def _is_daily_quota(err: Exception) -> bool:
    s = str(err)
    return "RESOURCE_EXHAUSTED" in s and ("PerDay" in s or "free_tier" in s)


def _file_hash(path: Path) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def backend_kwargs(g: dict[str, Any]) -> dict[str, Any]:
    """model / model dự phòng / cấu hình web theo gemini.backend trong settings.yaml (api | web)."""
    if g.get("backend") != "web":
        return {"model": g["model"], "fallback_models": g.get("fallback_models")}
    w = dict(g.get("web") or {})
    for k in ("upload", "chunk_pages", "tabs"):         # (thinking: GeminiWeb nhận thẳng)  # cách gửi trang — người gọi (info_gemini) đọc thẳng từ settings
        w.pop(k, None)
    return {"model": w.pop("model", "Argon"), "fallback_models": w.pop("fallback_models", []), "web": w}


def cached(exact: Path, any_model: str) -> Path | None:
    """File cache đúng model; không có thì dùng kết quả của model khác cùng trang/prompt (đổi API <-> web không đọc lại)."""
    if exact.exists():
        return exact
    return next(iter(sorted(exact.parent.glob(any_model))), None)


def _parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0) if m else text)


class GeminiExtractor(Extractor):
    name = "gemini"

    def __init__(self, model: str = "gemini-2.5-flash", dpi: int = 150, grid: tuple[int, int] = (1, 1),
                 max_px: int = 3000, temperature: float = 0.1, cache_dir: Path | None = None,
                 fallback_models: list[str] | None = None, retries: int = 4,
                 thinking_budget: int | None = None, workers: int = 1, prompt_file: str = "gemini_extract.md",
                 web: dict | None = None):
        self.web = None
        if web is not None:                     # backend web: gemini.google.com qua Chrome, không cần API key
            from .gemini_web import GeminiWeb
            self.web = GeminiWeb(**web)
            workers = 1                         # Playwright sync chỉ chạy trên 1 luồng
        else:
            key = gemini_api_key()
            if not key:
                raise RuntimeError("Thiếu GEMINI_API_KEY (đặt trong .env hoặc biến môi trường).")
            from google import genai  # import muộn để chạy được offline khi không dùng Gemini
            self.client = genai.Client(api_key=key)
        self.model, self.dpi, self.grid, self.max_px, self.temperature = model, dpi, grid, max_px, temperature
        self.prompt = (PROMPTS_DIR / prompt_file).read_text(encoding="utf-8")
        self.last_model = model                 # model thực sự trả lời (có thể là model dự phòng)
        self.cache_dir = cache_dir
        self.fallback_models = fallback_models or []
        self.retries = retries
        self.thinking_budget = thinking_budget
        self.quota_exhausted = False
        self.workers = max(1, workers)

    # ------------------------------------------------------------------ API
    def _call(self, png: bytes, texts: list[dict], text: str | None = None, name: str = "tile.png",
              mime: str = "image/png") -> dict[str, Any]:
        """Gửi 1 file (ảnh tile, hoặc PDF khi `text` đã soạn sẵn) + prompt; thử lại / đổi model dự phòng."""
        if text is None:
            ctx = json.dumps(texts[:400], ensure_ascii=False)
            text = f"{self.prompt}\n\nTEXT VECTOR TRONG VÙNG NÀY (toạ độ đã chuẩn hoá 0-1000 theo ảnh, dạng [x0,y0,x1,y1]):\n{ctx}"
        if self.web:
            generate = lambda model: self.web.generate(model, png, text + "\n\nCHỈ trả về một khối JSON, không giải thích.",
                                                       name, mime)
        else:
            from google.genai import types
            contents = [types.Part.from_bytes(data=png, mime_type=mime), text]
            cfg = types.GenerateContentConfig(
                temperature=self.temperature, response_mime_type="application/json",
                thinking_config=(types.ThinkingConfig(thinking_budget=self.thinking_budget)
                                 if self.thinking_budget is not None else None))
            generate = lambda model: self.client.models.generate_content(model=model, contents=contents,
                                                                         config=cfg).text
        if self.quota_exhausted:
            raise GeminiQuotaError("Gemini đã hết quota trong lượt chạy này")
        last_err: Exception | None = None
        quota_models = 0
        for model in [self.model, *self.fallback_models]:
            for attempt in range(self.retries):
                try:
                    data = _parse_json(generate(model) or "{}")
                    self.last_model = model
                    return data
                except Exception as e:  # 503 quá tải / 429 quota / mạng / JSON lỗi -> chờ rồi thử lại
                    last_err = e
                    if "API key" in str(e) or "PERMISSION_DENIED" in str(e) or isinstance(e, PermissionError):
                        raise
                    if _is_daily_quota(e):      # hết quota ngày của model này -> sang model dự phòng ngay
                        quota_models += 1
                        break
                    time.sleep(min(60, 5 * 2 ** attempt))
        if quota_models == 1 + len(self.fallback_models):
            self.quota_exhausted = True
            raise GeminiQuotaError(f"Gemini hết quota theo ngày cho mọi model ({last_err})")
        raise RuntimeError(f"Gemini lỗi sau khi thử lại và đổi model dự phòng: {last_err}")

    # -------------------------------------------------------------- per page
    def _cache(self, pdf: Path, page_no: int) -> tuple[Path, Path | None]:
        """-> (file cache của model này, file cache có sẵn của model bất kỳ hoặc None)."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        g = f"{self.grid[0]}x{self.grid[1]}"
        ph = hashlib.sha1(self.prompt.encode("utf-8")).hexdigest()[:8]   # đổi prompt -> cache mới
        cache = self.cache_dir / f"{_file_hash(pdf)}_p{page_no}_{self.model}_{g}_{ph}.json"
        return cache, cached(cache, f"{_file_hash(pdf)}_p{page_no}_*_{g}_{ph}.json")

    def prefetch(self, pdf: Path, pages: list[int], log=print, batch: int = 10) -> None:
        """Backend web: hỏi từng ô ảnh rất chậm (~2 phút/ô) -> gộp các trang chưa có cache thành 1 PDF nhỏ (lớp chữ
        đã sửa font), tải lên 1 lần, nhận JSON từng trang rồi ghi cache. Lỗi thì để extract_page đọc theo ô như cũ."""
        if not getattr(self, "web", None) or not self.cache_dir:
            return
        todo = [p for p in pages if not self._cache(pdf, p)[1]]
        for i in range(0, len(todo), batch):
            part = todo[i:i + batch]
            log(f"[gemini-web] tải {len(part)} trang {part} dạng PDF, model {self.model}...")
            text = (f"File PDF đính kèm gồm {len(part)} trang bản vẽ, lần lượt là các trang số {part} của hồ sơ gốc. "
                    "Mỗi trang là MỘT ẢNH TOÀN TRANG: áp dụng hướng dẫn dưới đây cho từng trang, toạ độ box_2d / "
                    "plan_box_2d chuẩn hoá 0-1000 theo toàn trang đó. Lớp chữ của PDF là text vector để đối chiếu. "
                    'Trả về {"pages": [{"page": <số trang gốc>, ...JSON theo schema...}, ...]} đủ mọi trang.\n\n'
                    + self.prompt)
            try:
                data = self._call(_subset_pdf(pdf, part), [], text, "ban_ve.pdf", "application/pdf")
            except PermissionError:          # chưa đăng nhập: đọc từng ô ảnh cũng lỗi -> dừng ngay
                raise
            except Exception as e:
                log(f"[gemini-web] lỗi đọc PDF ({str(e)[:120]}) — bỏ qua các trang này (không gửi ảnh)")
                continue
            got = data.get("pages") or []
            for k, pd in enumerate(got):
                p = pd.get("page") if pd.get("page") in part else (part[k] if k < len(part) else None)
                if p is None:
                    continue
                W, H = page_size(pdf, p)
                self._cache(pdf, p)[0].write_text(json.dumps([{"clip": [0, 0, W, H], "data": pd}], ensure_ascii=False,
                                                             indent=1), encoding="utf-8")
            log(f"[gemini-web] nhận {len(got)}/{len(part)} trang")

    def extract_page(self, pdf: Path, page_no: int):
        cache = None
        if self.cache_dir:
            cache, hit = self._cache(pdf, page_no)
            if hit:
                raw_tiles = json.loads(hit.read_text(encoding="utf-8"))
                return self._to_page(pdf, page_no, raw_tiles)

        all_text = vector_text(pdf, page_no)
        if getattr(self, "web", None):            # người dùng: Gemini web CHỈ nhận file PDF (prefetch), KHÔNG gửi ảnh -> chỉ text vector
            from ..models import PageExtraction
            return PageExtraction(page=page_no, width=page_size(pdf, page_no)[0], height=page_size(pdf, page_no)[1],
                                  notes=["Gemini chưa đọc được trang này qua file PDF (không gửi ảnh)"])
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


def _subset_pdf(pdf: Path, pages: list[int]) -> bytes:
    """PDF chỉ gồm các trang cần đọc, đã gắn ToUnicode cho font lỗi để Gemini đọc được chữ Việt."""
    import pymupdf
    from ..pdf.vn_encoding import fix_identity_fonts
    with pymupdf.open(pdf) as doc:
        for p in pages:
            fix_identity_fonts(doc, doc[p - 1])
        doc.select([p - 1 for p in pages])
        return doc.tobytes(garbage=3, deflate=True)


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
