"""Gemini đọc thông tin công trình (bước `info`) — chỉ cho trang không có text vector hoặc bảng regex không tách được.

Dùng lại GeminiExtractor._call (retry, model dự phòng, quota) với prompt riêng prompts/gemini_project_info.md.
Cache theo hash(PDF)+trang+model+hash(prompt) trong data/cache/ -> chạy lại không tốn API.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..pdf.render import render_tiles, vector_text
from .gemini_extractor import GeminiExtractor, _file_hash, backend_kwargs, cached

PROMPT_FILE = "gemini_project_info.md"


def make_info_reader(settings: Dict[str, Any], cache_dir: Optional[Path]) -> "InfoGeminiReader":
    g = settings["gemini"]
    gem = GeminiExtractor(**backend_kwargs(g), dpi=g["dpi"], max_px=g["max_tile_px"], temperature=g["temperature"],
                          cache_dir=cache_dir, retries=g.get("retries", 4),
                          thinking_budget=g.get("thinking_budget"), prompt_file=PROMPT_FILE)
    return InfoGeminiReader(gem)


class InfoGeminiReader:
    def __init__(self, gem: GeminiExtractor):
        self.gem = gem
        self.prompt_hash = hashlib.sha1(gem.prompt.encode("utf-8")).hexdigest()[:8]
        self.models_used: set = set()

    def _cache(self, pdf: Path, page_no: int) -> Optional[Path]:
        if not self.gem.cache_dir:
            return None
        self.gem.cache_dir.mkdir(parents=True, exist_ok=True)
        return self.gem.cache_dir / f"{_file_hash(pdf)}_p{page_no}_info_{self.gem.model}_{self.prompt_hash}.json"

    def prefetch(self, pdf: Path, pages: List[int], log=print) -> None:
        """Quy trình chuẩn (backend web): gộp mọi trang chưa có cache thành 1 PDF (lớp chữ đã sửa font), tải lên Gemini
        1 lần với model trong settings (Pro), nhận JSON từng trang rồi ghi cache. Lỗi -> read_page đọc từng trang."""
        from .gemini_extractor import _subset_pdf
        if not getattr(self.gem, "web", None):
            return
        todo = [p for p in pages if not ((c := self._cache(pdf, p)) and c.exists())]
        if not todo:
            return
        log(f"[info] Gemini web: tải 1 PDF gồm {len(todo)} trang {todo}, model {self.gem.model}...")
        text = (f"File PDF đính kèm gồm {len(todo)} trang bản vẽ, lần lượt là các trang số {todo} của hồ sơ gốc. "
                "Áp dụng hướng dẫn dưới đây cho TỪNG trang (chỉ ghi giá trị có chữ trên chính trang đó). Lớp chữ của PDF "
                'là text vector để đối chiếu. Trả về {"pages": [{"page": <số trang gốc>, "fields": {...}}, ...]} '
                "đủ mọi trang.\n\n" + self.gem.prompt)
        try:
            data = self.gem._call(_subset_pdf(pdf, todo), [], text, "ban_ve.pdf", "application/pdf")
        except Exception as e:
            log(f"[info] ⚠ Gemini đọc PDF lỗi ({str(e)[:120]}) -> đọc từng trang")
            return
        got = data.get("pages") or []
        for k, pd in enumerate(got):
            p = pd.get("page") if pd.get("page") in todo else (todo[k] if k < len(todo) else None)
            c = self._cache(pdf, p) if p is not None else None
            if c:
                c.write_text(json.dumps({"model": self.gem.last_model, "data": pd}, ensure_ascii=False, indent=1),
                             encoding="utf-8")
        log(f"[info] Gemini web: nhận {len(got)}/{len(todo)} trang")

    def read_page(self, pdf: Path, page_no: int) -> List[Dict[str, Any]]:
        """-> danh sách hit {key, value, unit, page, text, method='gemini', hang_muc}.
        Chỉ dùng cache đúng model đang chọn (Pro) — không lấy kết quả Flash cũ."""
        data = None
        cache = self._cache(pdf, page_no)
        if cache and cache.exists():
            c = json.loads(cache.read_text(encoding="utf-8"))
            data, model = c.get("data"), c.get("model", self.gem.model)
        if data is None:
            tile = render_tiles(pdf, page_no, self.gem.dpi, (1, 1), max_px=self.gem.max_px)[0]
            W = tile.clip[2] - tile.clip[0]
            H = tile.clip[3] - tile.clip[1]
            texts = [{"text": t["text"], "bbox": [round(t["bbox"][0] / W * 1000), round(t["bbox"][1] / H * 1000),
                                                  round(t["bbox"][2] / W * 1000), round(t["bbox"][3] / H * 1000)]}
                     for t in vector_text(pdf, page_no)]
            data = self.gem._call(tile.png, texts)
            model = self.gem.last_model
            if cache:
                cache.write_text(json.dumps({"model": model, "data": data}, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
        self.models_used.add(model)
        return to_hits(data, page_no)


# Tầng của MỘT tòa nhà (không phải hạng mục): số liệu riêng từng tầng bị bỏ, chỉ giữ thông tin PCCC chung của nhà
FLOOR = re.compile(r"^\W*(TẦNG\b|LẦU\b|SÂN\s*THƯỢNG|MÁI\b|TUM\b|BÁN\s*HẦM|HẦM\b|THÔNG\s*GIÓ)|\bTẦNG\s*CÓ\b", re.I)
FLOOR_KEEP = {"bac_chiu_lua", "cap_nguy_hiem_chay_ket_cau", "chieu_cao_pccc"}


def to_hits(data: Dict[str, Any], page_no: int) -> List[Dict[str, Any]]:
    """Chuẩn hoá JSON Gemini -> hit cùng dạng với regex (giá trị chạy lại qua bộ chuẩn hoá của project_info)."""
    from ..project_info import PATTERNS, parse_number
    hits = []
    floor_groups: List[Tuple[str, str]] = []
    for field_key, items in ((data or {}).get("fields") or {}).items():
        if field_key not in PATTERNS:
            continue
        for it in items if isinstance(items, list) else [items]:
            if not isinstance(it, dict) or it.get("value") in (None, "", []):
                continue
            key = field_key
            v = _norm(key, it["value"], parse_number)
            if v is None:
                continue
            if key == "so_tang_noi" and re.search(r"TỔNG\s*SỐ\s*TẦNG|SỐ\s*TẦNG\s*NHÀ", str(it.get("text") or ""), re.I):
                key = "so_tang_nha"              # QCVN 06 1.4.50: tổng số tầng gồm cả bán hầm -> không phải tầng nổi
            floor = str(it.get("hang_muc") or "")
            per_floor = re.search(r"\bTẦNG\b[^|]{0,30}\bCÓ\s*CÔNG\s*NĂNG", str(it.get("text") or ""), re.I)
            if FLOOR.search(floor) or per_floor or key == "cong_nang" and FLOOR.search(str(v)):
                if key == "nhom_nha":
                    floor_groups += [(floor, f) for f in (v if isinstance(v, list) else [v])]
                if key not in FLOOR_KEEP:
                    continue
                it = dict(it, hang_muc=None)
            hits.append({"key": key, "value": v, "unit": it.get("unit"), "page": page_no,
                         "text": str(it.get("text") or "")[:200], "method": "gemini",
                         "hang_muc": _hang_muc(it.get("hang_muc"))})
    if floor_groups:          # nhóm F theo tầng -> nhóm nhà của cả tòa nhà (nhà hỗn hợp)
        hits.append({"key": "nhom_nha", "value": sorted({f for _, f in floor_groups}), "unit": None, "page": page_no,
                     "method": "gemini", "hang_muc": None,
                     "text": ("theo tầng: " + "; ".join(f"{fl} {f}" for fl, f in floor_groups))[:200]})
    return hits


def _hang_muc(name: Any) -> Any:
    """Tên hạng mục Gemini trả về: bỏ câu văn dài / có dấu phẩy ('Vật liệu trang trí, vật liệu ốp lát...')."""
    s = str(name or "").strip()
    return s if s and len(s) <= 40 and "," not in s and s.lower() not in ("null", "none") else None


def _norm(key: str, v: Any, parse_number) -> Any:
    import re
    s = str(v).strip()
    if key in ("dien_tich_khu_dat", "dien_tich_xay_dung", "tong_dien_tich_san", "khoi_tich"):
        return parse_number(re.sub(r"(?i)\s*m\s*[23²³]?$", "", s), thousands_dot=True)
    if key in ("chieu_cao_cong_trinh", "chieu_cao_pccc"):
        return parse_number(re.sub(r"(?i)\s*m$", "", s))
    if key in ("so_tang_noi", "so_tang_ham"):
        n = parse_number(s)
        return int(n) if n is not None and n == int(n) else None
    if key == "nhom_nha":
        return re.findall(r"F\d\.\d", re.sub(r"\s", "", s).replace(",", ".").upper()) or [s]
    if key in ("bac_chiu_lua", "hang_chay_no"):
        return s.upper().replace("BẬC", "").replace("HẠNG", "").strip()
    if key == "cap_nguy_hiem_chay_ket_cau":
        return s.upper().replace(" ", "").replace("O", "0")
    return s
