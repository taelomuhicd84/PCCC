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
    w = g.get("web") or {}
    return InfoGeminiReader(gem, w.get("upload", "pdf"), w.get("chunk_pages", 8), w.get("tabs", 10))


PNG_DPI = 300           # 1/4 trang A3 ~ 2400 px: chữ bảng nhỏ vẫn nét (Gemini web hạ độ phân giải file PDF -> đọc sai)
PNG_PER_MSG = 8         # Gemini web nhận tối đa 10 file/tin nhắn -> 2 trang x 4 phần


class InfoGeminiReader:
    def __init__(self, gem: GeminiExtractor, upload: str = "pdf", chunk_pages: int = 8, tabs: int = 9):
        self.gem = gem
        self.upload, self.chunk_pages, self.tabs = upload, chunk_pages, tabs
        self.khu_vuc: List[Dict[str, Any]] = []         # khu vực bên trong hạng mục: ghi nhớ, không thống kê
        self.prompt_hash = hashlib.sha1(gem.prompt.encode("utf-8")).hexdigest()[:8]
        self.models_used: set = set()

    def _cache(self, pdf: Path, page_no: int) -> Optional[Path]:
        if not self.gem.cache_dir:
            return None
        self.gem.cache_dir.mkdir(parents=True, exist_ok=True)
        mode = "_png" if self.upload == "png" else ""      # 2 cách gửi cho kết quả khác nhau -> cache riêng
        return self.gem.cache_dir / f"{_file_hash(pdf)}_p{page_no}_info_{self.gem.model}{mode}_{self.prompt_hash}.json"

    def prefetch(self, pdf: Path, pages: List[int], log=print) -> bool:
        """Quy trình chuẩn (backend web): gộp mọi trang chưa có cache thành 1 PDF (lớp chữ đã sửa font), tải lên Gemini
        1 lần với model trong settings (Pro), nhận JSON từng trang rồi ghi cache. -> False nếu lỗi (người gọi quyết định
        có đọc từng trang không). Chưa đăng nhập -> PermissionError (dừng hẳn, đọc từng trang cũng lỗi)."""
        from .gemini_extractor import _subset_pdf
        if not getattr(self.gem, "web", None):
            return True
        todo = [p for p in pages if not ((c := self._cache(pdf, p)) and c.exists())]
        if not todo:
            return True
        if self.upload == "png":
            return self._prefetch_png(pdf, todo, log)
        if len(todo) > self.chunk_pages:
            return self._prefetch_chunks(pdf, todo, log)
        log(f"[info] Gemini web: tải 1 PDF gồm {len(todo)} trang {todo}, model {self.gem.model}...")
        try:
            data = self.gem._call(_subset_pdf(pdf, todo), [], self._pdf_prompt(todo), "ban_ve.pdf", "application/pdf")
        except PermissionError:
            raise
        except Exception as e:
            log(f"[info] ⚠ Gemini đọc PDF lỗi ({str(e)[:120]})")
            return False
        self._store(pdf, todo, data, log)
        return True

    def _pdf_prompt(self, todo: List[int]) -> str:
        return (f"File PDF đính kèm gồm {len(todo)} trang bản vẽ, lần lượt là các trang số {todo} của hồ sơ gốc. "
                "Áp dụng hướng dẫn dưới đây cho TỪNG trang (chỉ ghi giá trị có chữ trên chính trang đó). Lớp chữ của PDF "
                'là text vector để đối chiếu. Trả về {"pages": [{"page": <số trang gốc>, "fields": {...}}, ...]} '
                "đủ mọi trang.\n\n" + self.gem.prompt)

    def _prefetch_chunks(self, pdf: Path, todo: List[int], log) -> bool:
        """Quá nhiều trang cho 1 tin nhắn: chia chunk `chunk_pages` trang, mỗi chunk 1 file PDF trong 1 tab (cuộc trò
        chuyện riêng), tối đa `tabs` tab song song, rồi gộp kết quả (người dùng cho phép nhiều phiên trong trường hợp này)."""
        from .gemini_extractor import _parse_json, _subset_pdf
        raw_dir = (self.gem.cache_dir or Path("data/cache")) / "raw"   # bảng lưu tạm câu trả lời gốc của từng phiên
        raw_dir.mkdir(parents=True, exist_ok=True)
        size = self.chunk_pages
        for attempt in range(2):                    # chunk lỗi (JSON hỏng / rỗng / treo) -> gửi lại 1 lần, chunk nhỏ bằng nửa
            chunks = [todo[i:i + size] for i in range(0, len(todo), size)]
            log(f"[info] Gemini web: {len(chunks)} chunk PDF, tối đa {min(self.tabs, 10)} tab cùng lúc (hàng đợi), "
                f"model {self.gem.model}{' (gửi lại)' if attempt else ''}...")
            jobs = [(_subset_pdf(pdf, c), self._pdf_prompt(c) + "\n\nCHỈ trả về một khối JSON, không giải thích.",
                     "ban_ve.pdf", "application/pdf") for c in chunks]

            def keep(i, text, chunks=chunks):
                c = chunks[i]
                (raw_dir / f"{_file_hash(pdf)}_p{c[0]}-{c[-1]}_{self.prompt_hash}.txt").write_text(text, encoding="utf-8")
                try:                                # ghi cache trang ngay khi có kết quả (dừng giữa chừng không mất)
                    self.gem.last_model = self.gem.model
                    self._store(pdf, c, _parse_json(text), log)
                except Exception as e:
                    log(f"[info] ⚠ chunk trang {c[0]}-{c[-1]} lỗi ({str(e)[:120]})")

            for c, res in zip(chunks, self.gem.web.generate_many(self.gem.model, jobs, on_result=keep, log=log)):
                if isinstance(res, PermissionError):
                    raise res
                if isinstance(res, Exception):
                    log(f"[info] ⚠ chunk trang {c[0]}-{c[-1]} lỗi ({str(res)[:120]})")
            todo = [p for p in todo if not ((c := self._cache(pdf, p)) and c.exists())]
            if not todo:
                return True
            size = max(1, size // 2)
        return False

    def _store(self, pdf: Path, todo: List[int], data: Dict[str, Any], log) -> None:
        got = data.get("pages") or []
        for k, pd in enumerate(got):
            p = pd.get("page") if pd.get("page") in todo else (todo[k] if k < len(todo) else None)
            c = self._cache(pdf, p) if p is not None else None
            if c:
                c.write_text(json.dumps({"model": self.gem.last_model, "data": pd}, ensure_ascii=False, indent=1),
                             encoding="utf-8")
        log(f"[info] Gemini web: nhận {len(got)}/{len(todo)} trang")

    def _prefetch_png(self, pdf: Path, todo: List[int], log) -> bool:
        """Mỗi trang cắt 2x2 ảnh PNG nét; mỗi tin nhắn gửi 2 trang (8 ảnh), mọi tin nhắn trong CÙNG 1 cuộc trò chuyện."""
        per = PNG_PER_MSG // 4
        ok = True
        for i in range(0, len(todo), per):
            part = todo[i:i + per]
            files = [(f"trang{p}_phan{k + 1}.png", "image/png", t.png) for p in part
                     for k, t in enumerate(render_tiles(pdf, p, PNG_DPI, (2, 2), max_px=self.gem.max_px))]
            log(f"[info] Gemini web: gửi {len(files)} ảnh của trang {part}, model {self.gem.model}...")
            text = (f"Đính kèm {len(files)} ảnh: mỗi trang bản vẽ ({part}) được cắt thành 4 phần (phan1 trên-trái, "
                    "phan2 trên-phải, phan3 dưới-trái, phan4 dưới-phải, chồng lấn nhẹ); tên ảnh trangN_phanK là trang "
                    "số N của hồ sơ gốc. CHỈ đọc các ảnh đính kèm trong tin nhắn này. Gộp 4 phần thành 1 trang rồi áp dụng "
                    "hướng dẫn dưới đây cho TỪNG trang (chỉ ghi giá trị có chữ trên chính trang đó, chép đúng từng chữ số). "
                    'Trả về {"pages": [{"page": <số trang gốc>, "fields": {...}}, ...]} đủ mọi trang.\n\n' + self.gem.prompt)
            try:
                self._store(pdf, part, self.gem._call(files, [], text), log)
            except PermissionError:
                raise
            except Exception as e:
                log(f"[info] ⚠ Gemini đọc ảnh trang {part} lỗi ({str(e)[:120]})")
                ok = False
        return ok

    def read_page(self, pdf: Path, page_no: int) -> List[Dict[str, Any]]:
        """-> danh sách hit {key, value, unit, page, text, method='gemini', hang_muc}.
        Chỉ dùng cache đúng model đang chọn (Pro) — không lấy kết quả Flash cũ."""
        data = None
        cache = self._cache(pdf, page_no)
        if cache and cache.exists():
            c = json.loads(cache.read_text(encoding="utf-8"))
            data, model = c.get("data"), c.get("model", self.gem.model)
        if data is None and getattr(self.gem, "web", None):
            # người dùng: Gemini web CHỈ nhận file PDF, KHÔNG gửi ảnh -> trang chưa đọc được qua PDF thì bỏ qua
            raise RuntimeError(f"trang {page_no} chưa đọc được qua file PDF — không gửi ảnh, bỏ qua")
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
        self.khu_vuc += khu_vuc(data, page_no)
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
            unit = it.get("unit") if str(it.get("unit")).lower() not in ("null", "none", "") else None
            hits.append({"key": key, "value": v, "unit": unit, "page": page_no,
                         "text": str(it.get("text") or "")[:200], "method": "gemini",
                         "hang_muc": _hang_muc(it.get("hang_muc"))})
    for row in (data or {}).get("bang_thong_ke") or []:     # bảng thống kê hạng mục = danh sách hạng mục chuẩn
        name = _hang_muc(row.get("hang_muc")) if isinstance(row, dict) else None
        if not name or FLOOR.search(name) or re.match(r"\W*(SÀN\s*LỬNG|LỬNG|TRỆT)\b", name, re.I):
            # bảng diện tích theo tầng (TẦNG TRỆT, LẦU 1, SÀN LỬNG) không phải bảng hạng mục
            continue
        text = str(row.get("text") or "")[:200]
        hits.append({"key": "_bang_thong_ke", "value": name, "unit": None, "page": page_no, "text": text,
                     "method": "gemini", "hang_muc": name})
        # MỌI cột của bảng (bảng quy mô hay có cả cột PCCC): tên trường chuẩn hoặc tên cột hay gặp -> trường
        for col, raw in row.items():
            key = col if col in PATTERNS else TABLE_COLS.get(col)
            if not key or raw in (None, "", "-", "—") or key == "ten_cong_trinh":
                continue
            v = _norm(key, raw, parse_number)
            if v is not None:
                hits.append({"key": key, "value": v, "unit": None, "page": page_no, "text": text,
                             "method": "gemini", "hang_muc": name, "from_table": col})   # nhãn = tên cột
    if floor_groups:          # nhóm F theo tầng -> nhóm nhà của cả tòa nhà (nhà hỗn hợp)
        hits.append({"key": "nhom_nha", "value": sorted({f for _, f in floor_groups}), "unit": None, "page": page_no,
                     "method": "gemini", "hang_muc": None,
                     "text": ("theo tầng: " + "; ".join(f"{fl} {f}" for fl, f in floor_groups))[:200]})
    return hits


TABLE_COLS = {"dien_tich": "dien_tich_xay_dung", "chieu_cao": "chieu_cao_cong_trinh",
              "chieu_cao_mai": "chieu_cao_cong_trinh", "so_tang": "so_tang_noi",
              "hang_nguy_hiem_chay": "hang_chay_no", "hang_nguy_hiem_chay_no": "hang_chay_no"}


def khu_vuc(data: Dict[str, Any], page_no: int) -> List[Dict[str, Any]]:
    """Khu vực bên trong 1 hạng mục (phòng, khu phụ trợ...) — ghi nhớ kèm hạng mục chứa nó, không thành cột hạng mục."""
    out = []
    for k in (data or {}).get("khu_vuc") or []:
        if isinstance(k, dict) and k.get("ten"):
            out.append({"ten": str(k["ten"])[:120], "thuoc": k.get("thuoc"), "dien_tich": k.get("dien_tich"),
                        "page": page_no, "text": str(k.get("text") or "")[:200]})
    return out


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
