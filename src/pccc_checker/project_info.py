"""Bước ⓪ `info`: đọc thông tin công trình + thông tin đầu vào PCCC từ bìa, bảng quy mô, thuyết minh PCCC.

Nguyên tắc:
- Ưu tiên text vector (offline, 0 token): regex cặp nhãn - giá trị; ô bảng cùng hàng được ghép lại trước khi dò.
- Chỉ gọi Gemini cho trang không có text vector hoặc bảng mà regex không tách được (extractors/info_gemini.py).
- KHÔNG suy đoán: chỉ lấy giá trị ghi trên bản vẽ. Nhiều trang ghi khác nhau -> `conflict`, giữ mọi ứng viên.
- Một hồ sơ = một KHU ĐẤT (`khu_dat`: tên công trình, diện tích khu đất) gồm nhiều HẠNG MỤC (karaoke, nhà ở, nhà xe...).
  Mỗi bảng quy mô có "CÔNG NĂNG" là một hạng mục; giá trị khác nhau giữa các hạng mục KHÔNG phải conflict.
  Mọi hạng mục giữ trong `ProjectInfo.hang_muc`; `project_info`/`fire_inputs` = hạng mục chính (khớp tên công trình,
  hoặc khối tích/diện tích lớn nhất, hoặc `hang_muc_chinh` trong project.yaml) — rule engine kiểm tra theo hạng mục này.
- Giá trị ngoài danh sách hợp lệ (config/fire_inputs.yaml) -> loại, ghi cảnh báo.
- project.yaml của người dùng luôn được ưu tiên (status `confirmed`).
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from .config import CONFIG_DIR

SCHEMA_VERSION = 1
FOUND, MISSING, CONFLICT, CONFIRMED = "found", "missing", "conflict", "confirmed"
SECTIONS = ("khu_dat", "project_info", "fire_inputs")
PROJECT_KEYS = {"ten_cong_trinh", "dien_tich_khu_dat"}     # thuộc khu đất, không gán hạng mục
HM_SECTIONS = ("project_info", "fire_inputs")            # trường của từng hạng mục


# ------------------------------------------------------------------ cấu hình
def load_spec(path: Optional[Path] = None) -> Dict[str, Any]:
    spec = yaml.safe_load((path or CONFIG_DIR / "fire_inputs.yaml").read_text(encoding="utf-8"))
    spec.setdefault("khu_dat", {})
    return spec


def section_of(key: str, spec: Dict[str, Any]) -> Optional[str]:
    return next((sec for sec in SECTIONS if key in spec[sec]), None)


def _keys(spec: Dict[str, Any], sections=SECTIONS) -> List[str]:
    return [k for sec in sections for k in spec[sec]]


# ------------------------------------------------------------------ dữ liệu
@dataclass
class FieldValue:
    value: Any = None
    unit: Optional[str] = None
    page: Optional[int] = None
    text: str = ""
    method: Optional[str] = None             # vector | gemini | user
    status: str = MISSING                    # found | missing | conflict | confirmed
    candidates: List[Dict[str, Any]] = field(default_factory=list)   # [{value, page, text, method}]

    @property
    def usable(self) -> bool:
        return self.status in (FOUND, CONFIRMED) and self.value is not None


@dataclass
class ProjectInfo:
    project_info: Dict[str, FieldValue] = field(default_factory=dict)
    fire_inputs: Dict[str, FieldValue] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    hang_muc: Dict[str, Dict[str, FieldValue]] = field(default_factory=dict)   # tên hạng mục -> {key: FieldValue}
    hang_muc_chinh: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)   # schema_version, pdf, pdf_hash, pages, prompt, model
    khu_dat: Dict[str, FieldValue] = field(default_factory=dict)

    def get(self, key: str) -> FieldValue:
        return self.fire_inputs.get(key) or self.project_info.get(key) or self.khu_dat.get(key) or FieldValue()

    def items(self):
        yield from self.khu_dat.items()
        yield from self.project_info.items()
        yield from self.fire_inputs.items()

    def to_dict(self) -> Dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, **asdict(self)}

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ProjectInfo":
        def fields(sec):
            return {k: FieldValue(**v) for k, v in (d.get(sec) or {}).items()}
        hm = {name: {k: FieldValue(**v) for k, v in fs.items()} for name, fs in (d.get("hang_muc") or {}).items()}
        return cls(fields("project_info"), fields("fire_inputs"), list(d.get("warnings") or []), hm,
                   d.get("hang_muc_chinh"), d.get("meta") or {}, fields("khu_dat"))

    # -------------------------------------------------------------- ràng buộc
    def required_keys(self, spec: Dict[str, Any]) -> List[str]:
        out = []
        nhom = self.get("nhom_nha").value
        nhoms = nhom if isinstance(nhom, list) else [nhom] if nhom else []
        for k, s in spec["fire_inputs"].items():
            if s.get("required"):
                out.append(k)
            prefix = (s.get("required_when") or {}).get("nhom_nha_prefix")
            if prefix and any(str(n).startswith(prefix) for n in nhoms):
                out.append(k)
        return out

    def problems(self, spec: Dict[str, Any]) -> Dict[str, str]:
        """Trường bắt buộc đang missing/conflict -> lý do (dùng để đánh dấu luật `cannot_check`)."""
        out = {}
        for k in self.required_keys(spec):
            fv = self.get(k)
            if fv.status == MISSING:
                out[k] = f"thiếu {spec['fire_inputs'][k]['label'].lower()}"
            elif fv.status == CONFLICT:
                out[k] = f"{spec['fire_inputs'][k]['label'].lower()} mâu thuẫn giữa các trang: {fmt_candidates(fv)}"
        nhom = self.get("nhom_nha")
        if nhom.usable and isinstance(nhom.value, list) and len(nhom.value) > 1:
            out["nhom_nha"] = f"nhà nhiều nhóm ({', '.join(nhom.value)}) — cần xác nhận nhóm áp dụng trong project.yaml"
        return out

    def to_building(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Ánh xạ sang khoá BuildingInfo cũ. Trường không dùng được -> None (luật phụ thuộc sẽ `cannot_check`)."""
        out: Dict[str, Any] = {}
        for key, bkey in spec["building_map"].items():
            fv = self.get(key)
            v = fv.value if fv.usable else None
            if isinstance(v, list):
                v = v[0] if len(v) == 1 else None
            out[bkey] = v
        return out


# ------------------------------------------------------------------ chuẩn hoá
def parse_number(s: str, thousands_dot: bool = False) -> Optional[float]:
    """'12,5' -> 12.5 ; '1.234,5' -> 1234.5 ; '1,234.5' -> 1234.5 ; '4.811,83' -> 4811.83.
    thousands_dot=True (diện tích, khối tích): '1.433' -> 1433 (dấu chấm + đúng 3 chữ số = phân cách nghìn)."""
    s = s.strip().replace(" ", "")
    if not s:
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3}){2,}", s) else s.replace(",", ".")
    elif thousands_dot and re.fullmatch(r"\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def _clean(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip(" :;,.-–=\"'“”")
    return s


def _roman(s: str) -> str:
    return s.upper().replace(" ", "")


def _int(s: str) -> Optional[int]:
    if re.fullmatch(r"(?i)KHÔNG|KHÔNG\s*CÓ", s.strip()):
        return 0
    n = parse_number(s)
    return int(n) if n is not None and n == int(n) else None


NUM = r"(\d[\d.,]*\d|\d)(?![\d:/])"
UNIT_HDR = r"(?:\s*\(\s*(?:M|M2|M²|M3|M³|m|m2|m²|m3|m³)\s*\))?"   # "CHIỀU CAO PCCC (M)", "KHỐI TÍCH ( M3 )"
SEP = r"\s*(?:[:=|\-–]|LÀ|ĐẠT)?\s*"
BULLET = r"^\W{0,4}(?:\d{1,2}[.)]\s*|[a-zđ][.)]\s*)?"                 # "- ", "+ ", "1. ", "a) ", "***"


def _pat(label: str, value: str, anchored: bool = True) -> re.Pattern:
    return re.compile((BULLET if anchored else r"") + label + UNIT_HDR + SEP + value, re.I)


# key -> [(pattern, converter(match) -> (value, unit))]. Nhãn có neo đầu dòng để tránh dính câu văn khác;
# các trường có giá trị đặc trưng (F2.1, II, S0, "6m") được phép đứng giữa câu.
Conv = Callable[[re.Match], Tuple[Any, Optional[str]]]


def _area(m: re.Match) -> Tuple[Any, Optional[str]]:
    return parse_number(m.group(1), thousands_dot=True), "m²"


def _vol(m: re.Match) -> Tuple[Any, Optional[str]]:
    return parse_number(m.group(1), thousands_dot=True), "m³"


def _len(m: re.Match) -> Tuple[Any, Optional[str]]:
    return parse_number(m.group(1)), "m"


AREA_UNIT = r"\s*(?:m2|m²|m\s*2)?"
VOL_UNIT = r"\s*(?:m3|m³|m\s*3)?"
LEN_UNIT = r"\s*m\b"

PATTERNS: Dict[str, List[Tuple[re.Pattern, Conv]]] = {
    "dien_tich_khu_dat": [
        # "***Tổng diện tích khu đất hạng mục thẩm duyệt PCCC: 1433.4m2"
        (_pat(r"(?:TỔNG\s*)?DIỆN\s*TÍCH\s*KHU\s*ĐẤT[^:|\d]{0,50}", NUM + AREA_UNIT), _area),
        # "TỔNG DIỆN TÍCH ĐẤT : 6075 M2" (không nhận "diện tích đất (không) xây dựng")
        (_pat(r"(?:TỔNG\s*)?DIỆN\s*TÍCH\s*ĐẤT(?!\s*(?:KHÔNG\s*)?XÂY)", NUM + AREA_UNIT), _area),
    ],
    "ten_cong_trinh": [
        # bắt buộc "CÔNG TRÌNH:" (có dấu hai chấm) để không dính câu "Công trình có cấp nguy hiểm..."
        (re.compile(BULLET + r"(?:TÊN\s*(?:CÔNG\s*TRÌNH|DỰ\s*ÁN)\s*[:|]|(?:CÔNG\s*TRÌNH|DỰ\s*ÁN)\s*:)\s*([^|]{3,120})", re.I),
         lambda m: (_clean(m.group(1)), None)),
    ],
    "cong_nang": [
        (_pat(r"CÔNG\s*NĂNG(?:\s*(?:SỬ\s*DỤNG|CHÍNH|CÔNG\s*TRÌNH))?", r"([^|]{3,80})"), lambda m: (_clean(m.group(1)), None)),
    ],
    "dien_tich_xay_dung": [
        (_pat(r"DIỆN\s*TÍCH\s*(?:ĐẤT\s*)?XÂY\s*DỰNG", NUM + AREA_UNIT), _area),
    ],
    "tong_dien_tich_san": [
        (_pat(r"TỔNG\s*DIỆN\s*TÍCH\s*SÀN(?:\s*XÂY\s*DỰNG)?", NUM + AREA_UNIT), _area),
    ],
    "chieu_cao_cong_trinh": [
        (_pat(r"CHIỀU\s*CAO\s*(?:CÔNG\s*TRÌNH|KIẾN\s*TRÚC|XÂY\s*DỰNG|NHÀ|MÁI)", NUM + r"\s*m?\b"), _len),
    ],
    "so_tang_nha": [
        (_pat(r"(?:TỔNG\s*SỐ\s*TẦNG|SỐ\s*TẦNG\s*NHÀ)", r"(\d{1,3})\b(?!\s*[.,]\d)"), lambda m: (_int(m.group(1)), None)),
    ],
    "so_tang_noi": [
        (_pat(r"SỐ\s*TẦNG(?:\s*(?:NỔI|CAO|TRÊN\s*MẶT\s*ĐẤT))?(?!\s*(?:HẦM|NHÀ|BÁN))", r"(\d{1,3})\b(?!\s*[.,]\d)"), lambda m: (_int(m.group(1)), None)),
        (re.compile(r"\b(\d{1,3})\s*TẦNG\s*NỔI\b", re.I), lambda m: (_int(m.group(1)), None)),
    ],
    "so_tang_ham": [
        (_pat(r"SỐ\s*TẦNG\s*HẦM", r"(\d{1,2}|KHÔNG(?:\s*CÓ)?)\b"), lambda m: (_int(m.group(1)), None)),
        (re.compile(r"\b(\d{1,2})\s*TẦNG\s*HẦM\b", re.I), lambda m: (_int(m.group(1)), None)),
        (re.compile(r"KHÔNG\s*CÓ\s*TẦNG\s*HẦM", re.I), lambda m: (0, None)),
    ],
    "tang_tum_ky_thuat": [
        (_pat(r"TẦNG\s*(?:TUM|KỸ\s*THUẬT|MÁI\s*TUM)", r"([^|]{1,60})"), lambda m: (_clean(m.group(1)), None)),
    ],
    "khoi_tich": [
        (_pat(r"(?:TỔNG\s*)?KHỐI\s*TÍCH(?:\s*(?:CÔNG\s*TRÌNH|NHÀ|XÂY\s*DỰNG))?", NUM + VOL_UNIT), _vol),
    ],
    "bac_chiu_lua": [
        (_pat(r"BẬC\s*CHỊU\s*LỬA(?:\s*(?:CỦA\s*)?(?:CÔNG\s*TRÌNH|NHÀ))?", r"(?:BẬC\s*)?[\"“']?(IV|V|I{1,3})\b", anchored=False),
         lambda m: (_roman(m.group(1)), None)),
    ],
    "nhom_nha": [
        (_pat(r"NHÓM\s*(?:NHÀ|NGUY\s*HIỂM\s*CHÁY(?:\s*THEO\s*CÔNG\s*NĂNG)?)",
              r"(?:LÀ\s*|NHÓM\s*)?\(?(F\s*\d\s*[.,]\s*\d(?:\s*(?:;|,|/|VÀ|\+)\s*F\s*\d\s*[.,]\s*\d)*)", anchored=False),
         lambda m: (re.findall(r"F\d\.\d", re.sub(r"\s", "", m.group(1)).replace(",", ".").upper()), None)),
    ],
    "hang_chay_no": [
        (_pat(r"HẠNG\s*(?:NGUY\s*HIỂM\s*)?CHÁY(?:\s*(?:VÀ\s*)?(?:CHÁY\s*)?NỔ)?(?:\s*(?:CỦA\s*)?(?:NHÀ|CÔNG\s*TRÌNH))?",
              r"(?:HẠNG\s*)?[\"“']?([ABCDE][1-4]?)\b(?![.\d])", anchored=False),
         lambda m: (m.group(1).upper(), None)),
    ],
    "chieu_cao_pccc": [
        (_pat(r"CHIỀU\s*CAO\s*(?:PCCC|PHÒNG\s*CHÁY(?:\s*(?:VÀ\s*)?CHỮA\s*CHÁY)?)(?:\s*(?:CỦA\s*)?(?:CÔNG\s*TRÌNH|NHÀ))?",
              NUM + r"\s*(?:m\b|M\b)?", anchored=False), _len),
    ],
    "cap_nguy_hiem_chay_ket_cau": [
        (_pat(r"CẤP\s*NGUY\s*HIỂM\s*CHÁY(?:\s*(?:CỦA\s*)?KẾT\s*CẤU)?(?:\s*(?:CỦA\s*)?(?:NHÀ|CÔNG\s*TRÌNH))?",
              r"(?:CẤP\s*)?[\"“']?(S\s*[0-3O])\b", anchored=False),
         lambda m: (m.group(1).upper().replace(" ", "").replace("O", "0"), None)),
    ],
}
SECTION = {k: "fire_inputs" for k in ("bac_chiu_lua", "nhom_nha", "hang_chay_no", "chieu_cao_pccc",
                                      "cap_nguy_hiem_chay_ket_cau")}


# Tên bộ môn / phần hồ sơ (trang bìa từng phần) -> không phải tên công trình, không phải công năng
DISCIPLINE = re.compile(r"^\W*(?:HẠNG\s*MỤC\s*:?\s*)?(KIẾN\s*TRÚC|KẾT\s*CẤU|HỆ\s*THỐNG\b.*|BÌNH\s*CHỮA\s*CHÁY.*|"
                        r"EXIT.*|ĐIỆN\b.*|CẤP\s*(THOÁT\s*)?NƯỚC.*|THÔNG\s*GIÓ.*|CHỐNG\s*SÉT.*|BÁO\s*CHÁY.*|"
                        r"CHỮA\s*CHÁY.*|TIẾP\s*ĐỊA.*)\W*$", re.I)
# Chữ của khung tên bản vẽ hay nằm cùng hàng với nhãn -> không phải giá trị
TITLE_BLOCK = re.compile(r"CHẤP\s*THUẬN|FOR\s*APPROVAL|PHÁT\s*HÀNH|ISSUED|THỂ\s*HIỆN|CHỦ\s*ĐẦU\s*TƯ|TÊN\s*DỰ\s*ÁN|"
                         r"ĐIỀU\s*CHỈNH|RESUBMISSION|HOÀN\s*CÔNG|ĐƠN\s*VỊ\s*TƯ\s*VẤN|GHI\s*CHÚ|KÝ\s*HIỆU", re.I)


def match_text(text: str) -> List[Tuple[str, Any, Optional[str]]]:
    """Dò mọi trường trong một chuỗi -> [(key, value, unit)]. Dùng cho test và cho từng dòng/hàng bảng."""
    out = []
    for key, pats in PATTERNS.items():
        for pat, conv in pats:
            m = pat.search(text)
            if m:
                try:
                    v, unit = conv(m)
                except (ValueError, TypeError):
                    continue
                if v in (None, "", []) or key in ("cong_nang", "tang_tum_ky_thuat", "ten_cong_trinh") \
                        and TITLE_BLOCK.search(str(v)):
                    continue
                out.append((key, v, unit))
                break
    return out


# ------------------------------------------------------------------ dò trên trang
def row_strings(texts: List[Dict[str, Any]], max_dx: float = 400.0) -> List[str]:
    """Mỗi dòng text + các ô cùng hàng nằm bên phải (bảng 'NHÓM NHÀ | F2.1'): ghép thành 'NHÓM NHÀ | F2.1'."""
    out = []
    for t in texts:
        x0, y0, x1, y1 = t["bbox"]
        cy, h = (y0 + y1) / 2, max(1.0, y1 - y0)
        right = []
        for o in texts:
            if o is t:
                continue
            ox0, oy0, ox1, oy1 = o["bbox"]
            oh = max(1.0, oy1 - oy0)
            if abs((oy0 + oy1) / 2 - cy) <= 0.6 * max(h, oh) and x1 - 2 <= ox0 <= x1 + max_dx and oh < 2.5 * h \
                    and len(o["text"]) <= 40:
                right.append(o)
        right.sort(key=lambda o: o["bbox"][0])
        out.append(" | ".join([t["text"], *(o["text"] for o in right)]) if right else t["text"])
    return out


# Chủ ngữ của câu ghi chú: "Nhà hàng 1 & 2 thuộc nhóm nhà F3.2 ...", "Nhà xe 01 & 02 có bậc chịu lửa bậc IV"
SUBJECT = re.compile(r"^\W{0,4}((?:NHÀ|PHÒNG|TRẠM|KHỐI|KHU|BỂ|TÒA|BLOCK|XƯỞNG|KHO|KARAOKE|MÁI\s*CHE)\b[^,:;.<>=]{0,40}?)"
                     r"\s+(?:CÓ|THUỘC|ĐƯỢC|LÀ)\b", re.I)
PAIR = re.compile(r"^(.*?)\s*0*(\d{1,2})\s*(?:&|VÀ|,|\+)\s*0*(\d{1,2})$", re.I)


def subject_names(line: str) -> List[str]:
    """Hạng mục là chủ ngữ của câu ghi chú. 'Nhà hàng 1 & 2' -> ['Nhà hàng 1', 'Nhà hàng 2']."""
    m = SUBJECT.match(line)
    if not m:
        return []
    name = _clean(m.group(1))
    if _norm_text(name) in ("NHÀ", "CÔNG TRÌNH", "KHU", "KHỐI"):
        return []
    pm = PAIR.match(name)
    return [f"{pm.group(1)} {pm.group(2)}", f"{pm.group(1)} {pm.group(3)}"] if pm else [name]


# Bảng thống kê hạng mục DẠNG CỘT: hàng tiêu đề (HẠNG MỤC | DIỆN TÍCH | CHIỀU CAO PCCC (m) | ...), mỗi hàng 1 hạng mục.
TABLE_ANCHOR = re.compile(r"^\W*(?:TÊN\s*)?HẠNG\s*MỤC\W*$", re.I)
FLOOR_ANCHOR = re.compile(r"^\W*TẦNG\W*$", re.I)          # bảng theo tầng: hàng = tầng, KHÔNG phải hạng mục
# (tiêu đề cột, key, nhãn chuẩn để chạy lại PATTERNS). Cột "DIỆN TÍCH (m2)" trơn KHÔNG gán cho diện tích xây dựng
# (có thể là diện tích sàn/điển hình) -> bỏ qua.
COLUMN_KEYS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(r"CHIỀU\s*CAO.*PCCC", re.I), "chieu_cao_pccc", "CHIỀU CAO PCCC"),
    (re.compile(r"CHIỀU\s*CAO.*(MÁI|CÔNG\s*TRÌNH|KIẾN\s*TRÚC)", re.I), "chieu_cao_cong_trinh", "CHIỀU CAO CÔNG TRÌNH"),
    (re.compile(r"DIỆN\s*TÍCH\s*XÂY\s*DỰNG", re.I), "dien_tich_xay_dung", "DIỆN TÍCH XÂY DỰNG"),
    (re.compile(r"TỔNG\s*DIỆN\s*TÍCH\s*SÀN", re.I), "tong_dien_tich_san", "TỔNG DIỆN TÍCH SÀN"),
    (re.compile(r"SỐ\s*TẦNG(?!\s*HẦM)", re.I), "so_tang_noi", "SỐ TẦNG"),
    (re.compile(r"TẦNG\s*HẦM", re.I), "so_tang_ham", "SỐ TẦNG HẦM"),
    (re.compile(r"KHỐI\s*TÍCH", re.I), "khoi_tich", "KHỐI TÍCH"),
    (re.compile(r"BẬC\s*CHỊU\s*LỬA", re.I), "bac_chiu_lua", "BẬC CHỊU LỬA"),
    (re.compile(r"NHÓM", re.I), "nhom_nha", "NHÓM NHÀ"),
    (re.compile(r"HẠNG\s*NGUY\s*HIỂM|CHÁY\s*,?\s*NỔ", re.I), "hang_chay_no", "HẠNG NGUY HIỂM CHÁY NỔ"),
    (re.compile(r"CẤP\s*NGUY\s*HIỂM", re.I), "cap_nguy_hiem_chay_ket_cau", "CẤP NGUY HIỂM CHÁY KẾT CẤU"),
    (re.compile(r"CÔNG\s*NĂNG", re.I), "cong_nang", "CÔNG NĂNG"),
    (re.compile(r"^\W*DIỆN\s*TÍCH(?!\s*(XÂY|SÀN|KHU|ĐẤT))", re.I), "dien_tich_tang", "DIỆN TÍCH"),   # chỉ bảng theo tầng
]


def _cx(t: Dict[str, Any]) -> float:
    return (t["bbox"][0] + t["bbox"][2]) / 2


def _cy(t: Dict[str, Any]) -> float:
    return (t["bbox"][1] + t["bbox"][3]) / 2


def _table_columns(texts: List[Dict[str, Any]], anchor: Dict[str, Any], h: float) -> List[Dict[str, Any]]:
    """Tiêu đề cột: mảnh chữ trong dải ±2h quanh ô 'HẠNG MỤC', bên phải, gom theo cột (chồng lấn theo x)."""
    ax1, ay0, ay1 = anchor["bbox"][2], anchor["bbox"][1], anchor["bbox"][3]
    # tiêu đề cột nằm từ trên ô 'HẠNG MỤC' tới ngay dưới nó (không lấn xuống hàng dữ liệu đầu tiên)
    band = [t for t in texts if t is not anchor and ay0 - 2.0 * h <= _cy(t) <= ay1 + 0.5 * h
            and ax1 - 2 <= t["bbox"][0] <= ax1 + 800 and len(t["text"]) <= 30
            and not re.match(r"^\W*BẢNG", t["text"], re.I)]          # tên bảng trùm nhiều cột -> không phải tiêu đề cột
    cols: List[Dict[str, Any]] = []
    for t in sorted(band, key=_cx):
        c = next((c for c in cols if t["bbox"][0] <= c["x1"] + 2 and t["bbox"][2] >= c["x0"] - 2), None)
        if c is None:
            cols.append({"x0": t["bbox"][0], "x1": t["bbox"][2], "parts": [t]})
        else:
            c["x0"], c["x1"] = min(c["x0"], t["bbox"][0]), max(c["x1"], t["bbox"][2])
            c["parts"].append(t)
    mapped = []
    for c in cols:
        head = " ".join(t["text"] for t in sorted(c["parts"], key=_cy))
        found = next(((k, lab) for pat, k, lab in COLUMN_KEYS if pat.search(head)), None)
        if found:
            mapped.append(dict(c, key=found[0], label=found[1], head=head))
    return mapped


FLOOR_KIND: List[Tuple[str, re.Pattern]] = [
    ("ap_mai", re.compile(r"ÁP\s*MÁI", re.I)),
    ("ban_ham", re.compile(r"BÁN\s*HẦM|NỬA\s*HẦM", re.I)),
    ("ham", re.compile(r"\bHẦM\b", re.I)),
    ("lung", re.compile(r"\bLỬNG\b", re.I)),
    ("tum", re.compile(r"\bTUM\b|SÂN\s*THƯỢNG", re.I)),
    ("mai", re.compile(r"^\W*MÁI\b", re.I)),
]


def floor_kind(name: str) -> str:
    """ap_mai | ban_ham | ham | lung | tum | mai | thuong (trệt, lầu n, tầng n, tầng kỹ thuật...)."""
    return next((k for k, pat in FLOOR_KIND if pat.search(name)), "thuong")


def count_floors(floors: List[Tuple[str, Optional[float]]], rules: Dict[str, Any]) -> Dict[str, Any]:
    """Tính số tầng theo QCVN 06 1.4.50 từ danh sách (tên tầng, diện tích sàn) theo thứ tự dưới -> trên.
    -> {so_tang_nha, so_tang_noi, so_tang_ham, so_tang_ban_ham, tum: str, assumptions: [..], detail: [..]}"""
    nha = noi = ham = ban_ham = 0
    lung_exempted = False
    detail, assumptions, tum = [], [], ""
    prev_area: Optional[float] = None
    last_real = max((i for i, (n, _) in enumerate(floors) if floor_kind(n) not in ("mai", "ap_mai")), default=-1)
    for i, (name, area) in enumerate(floors):
        kind = floor_kind(name)
        if kind == "tum" and i != last_real and re.search(r"SÂN\s*THƯỢNG", name, re.I):
            kind = "thuong"                      # sân thượng còn tầng bên trên -> tầng thường
        a = f"{area:g} m²" if area else "? m²"
        if kind in ("mai", "ap_mai"):
            detail.append(f"{name}: {'áp mái' if kind == 'ap_mai' else 'mái'} — không tính")
        elif kind == "ham":
            ham += 1
            detail.append(f"{name}: tầng hầm — không tính vào số tầng nhà")
        elif kind == "ban_ham":
            ban_ham += 1
            nha += 1
            detail.append(f"{name}: bán hầm — tính số tầng nhà, không phải tầng nổi")
        elif kind == "lung":
            ratio = area / prev_area if area and prev_area else None
            small = ratio is not None and ratio <= rules["lung_max_ratio"] and area <= rules["lung_max_m2"]
            if small and not lung_exempted:
                lung_exempted = True
                detail.append(f"{name}: lửng {a} = {ratio:.0%} sàn dưới ≤ {rules['lung_max_ratio']:.0%} — không tính")
                assumptions.append(f"{name} không tính vào số tầng nhà với giả định chỉ làm khu kỹ thuật — cần xác nhận")
            else:
                nha += 1
                noi += 1
                why = f"{ratio:.0%} sàn dưới > {rules['lung_max_ratio']:.0%}" if ratio is not None else "thiếu diện tích"
                detail.append(f"{name}: lửng {a} ({why}) — tính")
        elif kind == "tum":
            ratio = area / prev_area if area and prev_area else None
            if ratio is not None and ratio <= rules["tum_max_ratio"]:
                tum = f"{name} {a} = {ratio:.1%} sàn mái ≤ {rules['tum_max_ratio']:.0%} — không tính vào số tầng nhà"
                detail.append(f"{name}: tum {a} = {ratio:.1%} sàn mái — không tính")
                assumptions.append(f"{name} không tính vào số tầng nhà với giả định chỉ bao che thang/thiết bị kỹ thuật — "
                                   f"cần xác nhận")
            else:
                nha += 1
                noi += 1
                why = f"{ratio:.1%} sàn mái > {rules['tum_max_ratio']:.0%}" if ratio is not None else "thiếu diện tích"
                tum = f"{name} {a} ({why}) — tính là 1 tầng"
                detail.append(f"{name}: tum ({why}) — tính")
        else:
            nha += 1
            noi += 1
            detail.append(f"{name}: tính")
        if area:
            prev_area = area
    return {"so_tang_nha": nha, "so_tang_noi": noi, "so_tang_ham": ham, "so_tang_ban_ham": ban_ham,
            "tum": tum, "assumptions": assumptions, "detail": detail}


def _floor_table(texts, cols, rows, top, pitch, page) -> List[Dict[str, Any]]:
    """Bảng THEO TẦNG (hàng = tầng của 1 tòa nhà, không phải hạng mục):
    - mã F ở cột CÔNG NĂNG của từng tầng -> nhom_nha (danh sách nhóm) cho cả tòa nhà;
    - tên tầng + diện tích -> số tầng nhà / tầng nổi / hầm / bán hầm theo QCVN 06 1.4.50 (method 'tinh_toan')."""
    def cells(col):
        out = {}
        for t in texts:
            if not (col["x0"] - 3 <= _cx(t) <= col["x1"] + 3) or t["bbox"][1] < top - 1:
                continue
            r = min(range(len(rows)), key=lambda i: abs(_cy(t) - _cy(rows[i])))
            if abs(_cy(t) - _cy(rows[r])) <= 0.6 * pitch:
                out.setdefault(r, []).append(t["text"])
        return out

    hits: List[Dict[str, Any]] = []
    col = next((c for c in cols if c["key"] == "cong_nang"), None)
    if col is not None:
        per_floor = [(_clean(rows[r]["text"]), f"F{a}.{b}") for r, ts in sorted(cells(col).items())
                     for t in ts for a, b in re.findall(r"F\s*(\d)\s*[.,]\s*(\d)", t, re.I)]
        if per_floor:
            hits.append({"key": "nhom_nha", "value": sorted({f for _, f in per_floor}), "unit": None, "page": page,
                         "method": "vector",
                         "text": ("bảng theo tầng: " + "; ".join(f"{fl} {f}" for fl, f in per_floor))[:200]})
    area_col = next((c for c in cols if c["key"] == "dien_tich_tang"), None)
    areas = {r: parse_number(ts[0], thousands_dot=True) for r, ts in cells(area_col).items()} if area_col else {}
    floors = [(_clean(r["text"]), areas.get(i)) for i, r in enumerate(rows)]
    if len(floors) >= 2:
        res = count_floors(floors, load_spec()["so_tang"])
        ev = "tính từ bảng theo tầng (QCVN 06 1.4.50): " + "; ".join(res["detail"])
        for key in ("so_tang_nha", "so_tang_noi", "so_tang_ham", "so_tang_ban_ham"):
            hits.append({"key": key, "value": res[key], "unit": None, "page": page, "method": "tinh_toan",
                         "text": ev[:400], "assumptions": res["assumptions"]})
        if res["tum"]:
            hits.append({"key": "tang_tum_ky_thuat", "value": res["tum"], "unit": None, "page": page,
                         "method": "tinh_toan", "text": ev[:400]})
    return hits


def column_tables(texts: List[Dict[str, Any]], page: int) -> List[Dict[str, Any]]:
    """Đọc bảng thống kê hạng mục dạng cột -> hit gắn `hang_muc` = tên ở cột HẠNG MỤC.
    Ô gộp nằm giữa 2 hàng (vd 'HẠNG C' chung cho 2 hạng mục) -> gán cho cả 2."""
    hits: List[Dict[str, Any]] = []
    for a in texts:
        floor_table = bool(FLOOR_ANCHOR.match(a["text"]))
        if not (TABLE_ANCHOR.match(a["text"]) or floor_table):
            continue
        ax0, ay0, ax1, ay1 = a["bbox"]
        h = max(4.0, ay1 - ay0)
        cols = _table_columns(texts, a, h)
        if len(cols) < 2:                 # không phải bảng (vd "HẠNG MỤC" trong khung tên)
            continue
        top = max(t["bbox"][3] for c in cols for t in c["parts"])
        first_col = min(c["x0"] for c in cols)
        names = sorted([t for t in texts if t["bbox"][1] >= top - 1 and ax0 - 25 <= t["bbox"][0] <= ax1
                        and _cx(t) < first_col and re.search(r"[A-ZÀ-Ỹa-zà-ỹ]{2}", t["text"])], key=_cy)
        rows: List[Dict[str, Any]] = []
        for t in names:
            if rows and _cy(t) - _cy(rows[-1]) > 5 * h:      # hết bảng
                break
            if re.match(r"^\W*(TỔNG|GHI\s*CHÚ|THỂ\s*HIỆN)", t["text"], re.I):
                break
            rows.append(t)
        if not rows:
            continue
        pitch = min([_cy(b) - _cy(r) for r, b in zip(rows, rows[1:])] or [3 * h])
        if floor_table:
            hits.extend(_floor_table(texts, cols, rows, top, pitch, page))
            continue
        for c in cols:
            for t in texts:
                if not (c["x0"] - 3 <= _cx(t) <= c["x1"] + 3) or t["bbox"][1] < top - 1:
                    continue
                d = sorted(((abs(_cy(t) - _cy(r)), i) for i, r in enumerate(rows)))
                if d[0][0] > 0.6 * pitch:
                    continue
                owners = [rows[d[0][1]]]
                if len(d) > 1 and d[1][0] - d[0][0] < 0.3 * pitch:   # ô gộp giữa 2 hàng -> cả 2 hạng mục
                    owners.append(rows[d[1][1]])
                for key, v, unit in match_text(f"{c['label']}: {t['text']}"):
                    if key != c["key"]:
                        continue
                    for r in owners:
                        name = _clean(r["text"])
                        hits.append({"key": key, "value": v, "unit": unit, "page": page, "method": "vector",
                                     "hang_muc": name, "text": f"{name} | {c['head']} | {t['text']}"[:200]})
    return hits


def scan_page(texts: List[Dict[str, Any]], page: int) -> List[Dict[str, Any]]:
    """Trả về các 'hit' {key, value, unit, page, text, method[, hang_muc]} đọc được trên trang (text vector):
    cặp nhãn - giá trị trên 1 dòng/hàng bảng, câu ghi chú có chủ ngữ là hạng mục, bảng hạng mục dạng cột."""
    hits: List[Dict[str, Any]] = []
    seen = set()
    for h in column_tables(texts, page):
        sig = (h["key"], str(h["value"]), h.get("hang_muc"))
        if sig not in seen:
            seen.add(sig)
            hits.append(h)
    for t, s in zip(texts, row_strings(texts)):
        subjects = subject_names(t["text"])
        for key, v, unit in match_text(s):
            for hm in subjects or [None]:
                hm = hm if key not in PROJECT_KEYS else None
                sig = (key, str(v), hm)
                if sig in seen:
                    continue
                seen.add(sig)
                h = {"key": key, "value": v, "unit": unit, "page": page, "text": s[:200], "method": "vector"}
                if hm:
                    h["hang_muc"] = hm
                hits.append(h)
    return hits


# ------------------------------------------------------------------ hợp nhất
def _validate(key: str, value: Any, spec: Dict[str, Any]) -> Tuple[Any, Optional[str]]:
    """-> (giá trị hợp lệ hoặc None, cảnh báo)."""
    if key in ("ten_cong_trinh", "cong_nang") and isinstance(value, str) and DISCIPLINE.match(value):
        return None, f"{key}='{value}' là tên bộ môn/phần hồ sơ, không phải {'tên công trình' if key == 'ten_cong_trinh' else 'công năng'}"
    s = spec["fire_inputs"].get(key) or {}
    allowed = s.get("values")
    if not allowed:
        if key == "chieu_cao_pccc" and not (isinstance(value, (int, float)) and 0 < value < 600):
            return None, f"chieu_cao_pccc={value}: ngoài khoảng hợp lý"
        return value, None
    allowed_u = {str(a).upper() for a in allowed}
    vals = value if isinstance(value, list) else [value]
    bad = [v for v in vals if str(v).upper() not in allowed_u]
    if bad:
        return None, f"{key}={value}: giá trị {bad} không nằm trong danh sách hợp lệ {allowed} -> bỏ"
    return value, None


TEXT_KEYS = {"ten_cong_trinh", "cong_nang", "tang_tum_ky_thuat"}


def _norm_text(v: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\s*-\s*", " ", str(v).upper().replace("&", " VÀ "))).strip(" .")


def _same(a: Any, b: Any, text: bool = False) -> bool:
    """So sánh 2 giá trị. Trường chữ: không phân biệt hoa/thường, '&' = 'VÀ', chuỗi này chứa chuỗi kia = cùng giá trị
    ('KARAOKE HOÀNG ANH 2' ~ 'KARAOKE HOÀNG ANH 2 VÀ CÁC CÔNG TRÌNH PHỤ TRỢ')."""
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) < 1e-6
        except (TypeError, ValueError):
            return False
    if isinstance(a, list) and isinstance(b, list):
        # nhóm nhà: 1 tầng ghi F4.3, cả nhà hỗn hợp ghi F1.4; F4.3 -> không mâu thuẫn (tập con)
        return set(a) <= set(b) or set(b) <= set(a)
    na, nb = _norm_text(a), _norm_text(b)
    return na == nb or (text and (na in nb or nb in na))


def distinct_values(cands: List[Dict[str, Any]], text: bool = False) -> List[Dict[str, Any]]:
    """Gộp ứng viên trùng giá trị -> [{value, pages, methods, hang_muc}] (giá trị đại diện = chuỗi dài nhất)."""
    groups: List[Dict[str, Any]] = []
    for c in cands:
        g = next((g for g in groups if _same(g["value"], c["value"], text)), None)
        if g is None:
            g = {"value": c["value"], "pages": [], "methods": [], "hang_muc": []}
            groups.append(g)
        elif text and len(str(c["value"])) > len(str(g["value"])):
            g["value"] = c["value"]
        elif isinstance(c["value"], list) and len(c["value"]) > len(g["value"]):   # giữ danh sách nhóm đầy đủ
            g["value"] = c["value"]
        for k, v in (("pages", c.get("page")), ("methods", c.get("method")), ("hang_muc", c.get("hang_muc"))):
            if v and v not in g[k]:
                g[k].append(v)
    return groups




def page_title(texts: List[Dict[str, Any]], title_line: re.Pattern) -> str:
    """Các dòng tiêu đề (MẶT BẰNG/MẶT ĐỨNG/...) kèm dòng nối tiếp ngay bên dưới, cùng cột."""
    out = []
    for t in texts:
        if not (title_line.match(t["text"]) and len(t["text"]) <= 80):
            continue
        x0, y0, x1, y1 = t["bbox"]
        h = max(1.0, y1 - y0)
        nxt = [o for o in texts if 0 < o["bbox"][1] - y1 <= 0.8 * h and o["bbox"][0] < x1 and o["bbox"][2] > x0
               and len(o["text"]) <= 60]
        out.append(" ".join([t["text"], *(o["text"] for o in sorted(nxt, key=lambda o: o["bbox"][1])[:1])]))
    return " | ".join(out)


def tag_by_title(hits: List[Dict[str, Any]], titles: Dict[int, str]) -> None:
    """Hit chưa có hạng mục trên trang mà tiêu đề nêu đúng MỘT hạng mục đã biết -> gán hạng mục đó.
    So khớp: tên đầy đủ, hoặc 2 từ đầu của tên ('NHÀ Ở' trong 'MẶT BẰNG TẦNG 1 NHÀ Ở' -> 'NHÀ Ở NHÂN VIÊN')."""
    known = {}
    for h in hits:
        for name in _split_pair(str(h.get("hang_muc") or "")) if h.get("hang_muc") else []:
            known.setdefault(_hm_key(name), name)
    for page, title in titles.items():
        t = " " + _hm_key(title) + " "
        full = [k for k in known if f" {k} " in t]
        if not full:
            short = [k for k in known if len(k.split()) > 2 and f" {' '.join(k.split()[:2])} " in t]
            full = short if len({' '.join(k.split()[:2]) for k in short}) == 1 and len(short) == 1 else []
        # 'PCCC' và 'PHÒNG TRỰC PCCC' cùng có trong tiêu đề -> giữ tên dài
        full = [k for k in full if not any(o != k and f" {k} " in f" {o} " for o in full)]
        if len(full) != 1:
            continue
        for h in hits:
            if h["page"] == page and not h.get("hang_muc") and h["key"] not in PROJECT_KEYS:
                h["hang_muc"] = known[full[0]]


def tag_hang_muc(hits: List[Dict[str, Any]]) -> None:
    """Gán `hang_muc` = công năng của trang cho các hit chưa có (trang bảng quy mô của một hạng mục).
    Trang không ghi công năng hoặc ghi nhiều công năng khác nhau -> để trống (thông tin chung)."""
    by_page: Dict[int, List[Any]] = {}
    for h in hits:
        if h["key"] == "cong_nang" and not re.search(r"\bTẦNG\b|\bLẦU\b", str(h["value"]), re.I):
            vals = by_page.setdefault(h["page"], [])
            i = next((i for i, v in enumerate(vals) if _same(v, h["value"], text=True)), None)
            if i is None:
                vals.append(h["value"])
            elif len(str(h["value"])) > len(str(vals[i])):
                vals[i] = h["value"]
    for h in hits:
        vals = by_page.get(h["page"]) or []
        if not h.get("hang_muc") and h["key"] not in PROJECT_KEYS and len(vals) == 1:
            h["hang_muc"] = vals[0]


def _merge_fields(hs_all: List[Dict[str, Any]], spec: Dict[str, Any], sections=SECTIONS) -> Dict[str, FieldValue]:
    by_key: Dict[str, List[Dict[str, Any]]] = {}
    for h in hs_all:
        by_key.setdefault(h["key"], []).append(h)
    out = {}
    for key in _keys(spec, sections):
        unit = spec[section_of(key, spec)][key].get("unit")
        hs = by_key.get(key, [])
        cands = [{"value": h["value"], "page": h["page"], "text": h["text"], "method": h["method"],
                  **({"hang_muc": h["hang_muc"]} if h.get("hang_muc") else {})} for h in hs]
        distinct = distinct_values(cands, key in TEXT_KEYS)
        if not hs:
            fv = FieldValue(unit=unit)
        elif len(distinct) == 1:
            h = next(h for h in hs if h["value"] == distinct[0]["value"])
            fv = FieldValue(h["value"], h.get("unit") or unit, h["page"], h["text"], h["method"], FOUND,
                            cands if len(cands) > 1 else [])
        else:
            fv = FieldValue(None, unit, None, "", None, CONFLICT, cands)
        out[key] = fv
    return out


GENERIC_HM = {"CÔNG TRÌNH", "NHÀ", "HẠNG MỤC", "CÔNG TRÌNH CHÍNH", "DỰ ÁN"}
FIRE_KEYS = ("nhom_nha", "chieu_cao_pccc")


def _hm_key(name: Any) -> str:
    """Chuẩn hoá tên hạng mục: bỏ hậu tố '(S1)', '(chính)'; số thứ tự '01' -> '1' ('NHÀ HÀNG 01' ~ 'Nhà hàng 1')."""
    s = _norm_text(name)
    s = re.sub(r"\s*\((?:S\d|CHÍNH|\d+)\)\s*$", "", s).strip()
    return re.sub(r"\b0+(\d)", r"\1", s)


def _split_pair(name: str) -> List[str]:
    """'NHÀ XE 01 & 02' -> ['NHÀ XE 01', 'NHÀ XE 02']."""
    m = PAIR.match(name.strip())
    return [f"{m.group(1)} {m.group(2)}", f"{m.group(1)} {m.group(3)}"] if m else [name]


TOTAL_KEYS = {"khoi_tich", "dien_tich_xay_dung", "tong_dien_tich_san"}   # số tổng cộng, không chia cho hạng mục ghép


def _numbered(base: str, other: str) -> bool:
    """other = base + số thứ tự ('NHÀ HÀNG' / 'NHÀ HÀNG 2')."""
    return bool(re.fullmatch(re.escape(base) + r"\s+\d{1,2}[A-Z]?", other))


def _group_hang_muc(hits: List[Dict[str, Any]]) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, str]]:
    """Gom hit theo hạng mục.
    - 'NHÀ XE 01 & 02' -> 2 hạng mục 'NHÀ XE 1', 'NHÀ XE 2' (hit được nhân đôi).
    - Tên trần 'Nhà hàng' khi có 'NHÀ HÀNG 1', 'NHÀ HÀNG 2' -> áp cho tất cả các hạng mục đánh số đó.
    - Tên này là phần đầu của tên kia và phần thêm là CHỮ -> cùng hạng mục: 'NHÀ Ở' ~ 'NHÀ Ở NHÂN VIÊN'
      (nhưng không gộp 'NHÀ HÀNG 1' với 'NHÀ HÀNG 2', không gộp 'KARAOKE' với 'ĐẤT ... GIỮA KARAOKE ...')."""
    expanded: List[Tuple[str, Dict[str, Any]]] = []
    raw: Dict[str, str] = {}
    for h in hits:
        if not h.get("hang_muc"):
            continue
        names = _split_pair(str(h["hang_muc"]))
        if len(names) > 1 and h["key"] in TOTAL_KEYS:
            continue
        for name in names:
            k = _hm_key(name)
            expanded.append((k, h))
            if len(name) > len(raw.get(k, "")):
                raw[k] = name
    keys = set(raw)
    targets: Dict[str, List[str]] = {}
    for k in keys:
        nums = sorted(o for o in keys if _numbered(k, o))
        targets[k] = nums or [k]
    alias: Dict[str, str] = {}
    for k in sorted(keys, key=len):
        if targets[k] != [k]:
            continue
        base = next((b for b in sorted(set(alias.values()), key=len)
                     if (k + " ").startswith(b + " ") and re.match(r"\s+\(?[A-ZÀ-Ỹ]{2}", k[len(b):])), None)
        alias[k] = base or k
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for k, h in expanded:
        for t in targets[k]:
            g = alias[t]
            if not any(x is h for x in groups.get(g, [])):
                groups.setdefault(g, []).append(h)
    names: Dict[str, str] = {}
    for k, g in alias.items():                       # tên hiển thị = tên dài nhất trong nhóm, không kèm hậu tố '(S1)'
        name = re.sub(r"\s*\((?:S\d|CHÍNH|\d+)\)\s*$", "", raw[k], flags=re.I)
        if len(name) > len(names.get(g, "")):
            names[g] = name
    return groups, names


def _pick_main(groups: Dict[str, List[Dict[str, Any]]], general: List[Dict[str, Any]], prefer: Optional[str] = None) -> Tuple[str, str]:
    """-> (khoá hạng mục chính, lý do). Chỉ xét hạng mục có số liệu PCCC (nhóm nhà / chiều cao PCCC) và tên cụ thể."""
    if prefer:
        g = next((g for g in groups if g == _hm_key(prefer)), None)
        if g:
            return g, "project.yaml"
    pool = {g: hs for g, hs in groups.items()
            if g not in GENERIC_HM and any(h["key"] in FIRE_KEYS for h in hs)} or groups
    titles = [_norm_text(h["value"]) for h in general if h["key"] == "ten_cong_trinh"]
    def bare(g: str) -> str:
        return re.sub(r"\s+\d{1,2}[A-Z]?$", "", g)
    in_title = [g for g in pool if bare(g) not in GENERIC_HM
                and any(re.search(rf"(^|\s){re.escape(bare(g))}(\s|$)", t) for t in titles)]
    if len(in_title) == 1:
        return in_title[0], "khớp tên công trình"
    if in_title:
        vol = {g: max((h["value"] for h in pool[g] if h["key"] == "khoi_tich" and isinstance(h["value"], (int, float))),
                      default=0) for g in in_title}
        return max(in_title, key=lambda g: (vol[g], len(g))), "khớp tên công trình, khối tích lớn nhất"
    for key in ("khoi_tich", "tong_dien_tich_san", "dien_tich_xay_dung"):
        size = {g: max((h["value"] for h in hs if h["key"] == key and isinstance(h["value"], (int, float))),
                       default=None) for g, hs in pool.items()}
        size = {g: v for g, v in size.items() if v is not None}
        if size:
            return max(size, key=size.get), f"{key.replace('_', ' ')} lớn nhất"
    return next(iter(pool)), "hạng mục đầu tiên"


def merge(hits: List[Dict[str, Any]], spec: Dict[str, Any], hang_muc_chinh: Optional[str] = None) -> ProjectInfo:
    info = ProjectInfo()
    valid = []
    for h in hits:
        v, warn = _validate(h["key"], h["value"], spec)
        if warn:
            info.warnings.append(f"trang {h['page']} ({h['method']}): {warn} — \"{h['text'][:80]}\"")
            continue
        valid.append(dict(h, value=v))
    # hạng mục ghi trùng tên dự án ("KARAOKE HOÀNG ANH 2 & CÁC CÔNG TRÌNH PHỤ TRỢ") = thông tin chung, không phải hạng mục
    # tên công trình: text vector (bìa, khung tên) là chuẩn; Gemini hay chép tên trang/tên hạng mục vào đây
    vec_titles = [h["value"] for h in valid if h["key"] == "ten_cong_trinh" and h["method"] != "gemini"]
    if vec_titles:
        valid = [h for h in valid if h["key"] != "ten_cong_trinh" or h["method"] != "gemini"
                 or any(_same(h["value"], t, text=True) for t in vec_titles)]
    titles = [h["value"] for h in valid if h["key"] == "ten_cong_trinh"]
    for h in valid:
        if h.get("hang_muc") and any(_same(h["hang_muc"], t, text=True) and len(_norm_text(h["hang_muc"]).split()) >= 3
                                     and len(_norm_text(h["hang_muc"])) >= 0.6 * len(_norm_text(t))
                                     for t in titles):
            h["hang_muc"] = None
    # công năng ghi bằng chính tên dự án -> không phải công năng
    valid = [h for h in valid if not (h["key"] == "cong_nang" and any(
        _norm_text(h["value"]) == _norm_text(t) or len(_norm_text(h["value"])) > 0.8 * len(_norm_text(t)) and _same(h["value"], t)
        for t in titles))]
    # diện tích của hạng mục trùng đúng diện tích khu đất -> nghi đọc nhầm nhãn (thường do Gemini)
    land = {h["value"] for h in valid if h["key"] == "dien_tich_khu_dat"}
    for h in valid:
        if h["key"] in ("dien_tich_xay_dung", "tong_dien_tich_san") and h["value"] in land:
            info.warnings.append(f"trang {h['page']} ({h['method']}): {h['key']}={h['value']} trùng diện tích khu đất "
                                 f"— nghi đọc nhầm nhãn, cần kiểm tra — \"{h['text'][:80]}\"")
    general = [h for h in valid if not h.get("hang_muc")]
    groups, names = _group_hang_muc(valid)
    main: List[Dict[str, Any]] = []
    if groups:
        g, why = _pick_main(groups, general, hang_muc_chinh)
        main = groups[g]
        info.hang_muc = {names[k]: _merge_fields(hs, spec, HM_SECTIONS) for k, hs in groups.items()}
        info.hang_muc_chinh = names[g]
        if len(groups) > 1:
            info.warnings.append(f"công trình nhiều hạng mục ({', '.join(names.values())}): thông tin chung lấy theo "
                                 f"hạng mục chính {names[g]} ({why}) — đổi bằng `hang_muc_chinh` trong project.yaml")
        if hang_muc_chinh and why != "project.yaml":
            info.warnings.append(f"project.yaml: hang_muc_chinh '{hang_muc_chinh}' không có trong hồ sơ "
                                 f"(có: {', '.join(names.values())})")
    # giá trị không gắn hạng mục trên trang có >= 2 hạng mục (bảng thống kê, mặt bằng chung) -> không rõ của ai,
    # không gán cho hạng mục chính (thông tin khu đất vẫn giữ)
    hm_on_page: Dict[int, set] = {}
    for g, hs in groups.items():
        for h in hs:
            hm_on_page.setdefault(h["page"], set()).add(g)
    general = [h for h in general if h["key"] in PROJECT_KEYS or len(hm_on_page.get(h["page"], ())) < 2]
    for key, fv in _merge_fields(general + main, spec).items():
        getattr(info, section_of(key, spec))[key] = fv
    return info


def _flat(d: Dict[str, Any]) -> Dict[str, Any]:
    """{key: v} phẳng hoặc chia mục khu_dat/project_info/fire_inputs -> phẳng."""
    out: Dict[str, Any] = {}
    for k, v in (d or {}).items():
        if k in SECTIONS and isinstance(v, dict):
            out.update(v)
        else:
            out[k] = v
    return out


def _apply_fields(info: ProjectInfo, target: Optional[Dict[str, FieldValue]], values: Dict[str, Any],
                  spec: Dict[str, Any], where: str, sections=SECTIONS) -> None:
    """Ghi giá trị người dùng (status `confirmed`). target=None -> ghi vào mục tương ứng của info (khu_dat/...)."""
    for key, v in values.items():
        if v is None or v == "":
            continue
        sec = section_of(key, spec)
        if sec not in sections:
            info.warnings.append(f"{where}: khoá '{key}' không dùng ở đây -> bỏ qua")
            continue
        if key == "nhom_nha" and isinstance(v, str):
            v = re.findall(r"F\d\.\d", v.upper())
        elif key in ("bac_chiu_lua", "hang_chay_no", "cap_nguy_hiem_chay_ket_cau"):
            v = str(v).upper()
        val, warn = _validate(key, v, spec)
        if warn:
            info.warnings.append(f"{where}: {warn}")
            continue
        dst = target if target is not None else getattr(info, sec)
        old = dst.get(key) or FieldValue()
        cands = old.candidates or ([{"value": old.value, "page": old.page, "text": old.text, "method": old.method}]
                                   if old.value is not None else [])
        dst[key] = FieldValue(val, old.unit or spec[sec][key].get("unit"), None, where, "user", CONFIRMED, cands)


def _find_hang_muc(info: ProjectInfo, name: Any) -> Optional[str]:
    n = _hm_key(name)
    return next((k for k in info.hang_muc if _hm_key(k) == n), None) or         next((k for k in info.hang_muc if (_hm_key(k) + " ").startswith(n + " ")), None)


def apply_user(info: ProjectInfo, user: Dict[str, Any], spec: Dict[str, Any]) -> None:
    """project.yaml — luôn thắng, status `confirmed`:
        khu_dat: {ten_cong_trinh, dien_tich_khu_dat}
        hang_muc_chinh: KARAOKE
        hang_muc: {KARAOKE: {project_info: {...}, fire_inputs: {...}}, NHÀ Ở: {...}}
    Dạng cũ (project_info/fire_inputs ở gốc, hoặc phẳng) vẫn dùng được = ghi cho hạng mục chính."""
    user = dict(user or {})
    khu_dat, hms = user.pop("khu_dat", None) or {}, user.pop("hang_muc", None) or {}
    want = user.pop("hang_muc_chinh", None)
    _apply_fields(info, None, _flat(khu_dat), spec, "project.yaml · khu_dat", ("khu_dat",))
    for name, d in (hms.items() if isinstance(hms, dict) else []):
        key = _find_hang_muc(info, name) or str(name)
        _apply_fields(info, info.hang_muc.setdefault(key, {}), _flat(d if isinstance(d, dict) else {}), spec,
                      f"project.yaml · {key}", HM_SECTIONS)
    main = _find_hang_muc(info, want) if want else info.hang_muc_chinh
    if main is None and len(info.hang_muc) == 1:
        main = next(iter(info.hang_muc))
    if main and main != info.hang_muc_chinh:          # đổi hạng mục chính -> thông tin chung lấy lại theo hạng mục mới
        for key in _keys(spec, HM_SECTIONS):
            sec = section_of(key, spec)
            getattr(info, sec)[key] = info.hang_muc[main].get(key) or FieldValue(unit=spec[sec][key].get("unit"))
        info.hang_muc_chinh = main
    elif main:
        for key, fv in info.hang_muc[main].items():
            if fv.status == CONFIRMED:
                getattr(info, section_of(key, spec))[key] = fv
    _apply_fields(info, None, _flat(user), spec, "project.yaml")
    if main and user:                                 # dạng cũ: đồng bộ vào hạng mục chính
        for key in _keys(spec, HM_SECTIONS):
            fv = info.get(key)
            if fv.status == CONFIRMED:
                info.hang_muc[main][key] = fv


# ------------------------------------------------------------------ hiển thị
def fmt_candidates(fv: FieldValue, text: bool = False) -> str:
    """'6 (tr.5) / 5.1 (tr.43,44 · NHÀ Ở) / 3.2 (tr.56 · PHÒNG TRỰC PCCC)'"""
    out = []
    for g in distinct_values(fv.candidates, text):
        extra = ",".join(map(str, sorted(g["pages"])))
        if g["hang_muc"]:
            extra += " · " + ", ".join(g["hang_muc"])
        out.append(f"{_v(g['value'])} (tr.{extra})")
    return " / ".join(out)


def fmt_value(fv: FieldValue) -> str:
    if fv.status == CONFLICT:
        return "mâu thuẫn"
    if fv.value is None:
        return "—"
    return _v(fv.value) + (f" {fv.unit}" if fv.unit and not isinstance(fv.value, str) else "")


def _v(v: Any) -> str:
    if isinstance(v, list):
        return "; ".join(map(str, v))
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def fmt_pages(fv: FieldValue) -> str:
    if fv.status == CONFIRMED:
        return "project.yaml"
    pages = sorted({c["page"] for c in fv.candidates if c.get("page")} | ({fv.page} if fv.page else set()))
    return ",".join(map(str, pages)) or "—"


HM_COLUMNS = ("cong_nang", "nhom_nha", "bac_chiu_lua", "cap_nguy_hiem_chay_ket_cau", "so_tang_noi",
              "chieu_cao_pccc", "khoi_tich")


def hang_muc_table(info: ProjectInfo, spec: Dict[str, Any]) -> Tuple[List[str], List[List[str]]]:
    """Bảng so sánh các hạng mục trong khu đất (rỗng nếu chỉ có <= 1 hạng mục)."""
    if len(info.hang_muc) < 2:
        return [], []
    head = ["Hạng mục", *(spec[section_of(k, spec)][k]["label"] for k in HM_COLUMNS), "Trang"]
    rows = []
    for name, fs in info.hang_muc.items():
        pages = sorted({p for fv in fs.values() for p in [fv.page, *(c.get("page") for c in fv.candidates)] if p})
        rows.append([name + (" (chính)" if name == info.hang_muc_chinh else ""),
                     *(fmt_value(fs.get(k) or FieldValue()) for k in HM_COLUMNS),
                     ",".join(map(str, pages)) or "project.yaml"])
    return head, rows


def table_rows(info: ProjectInfo, spec: Dict[str, Any]) -> List[Tuple[str, str, str, str, str]]:
    """[(key, nhãn, giá trị, trang, trạng thái)] theo thứ tự trong fire_inputs.yaml."""
    rows = []
    req = set(info.required_keys(spec))
    for sec in SECTIONS:
        for key, s in spec[sec].items():
            fv = getattr(info, sec).get(key) or FieldValue()
            st = fv.status + (" ⚠" if key in req and fv.status in (MISSING, CONFLICT) else "")
            if fv.status == CONFLICT:
                st += ": " + fmt_candidates(fv, key in TEXT_KEYS)
            rows.append((key, s["label"], fmt_value(fv), fmt_pages(fv), st))
    return rows


# ------------------------------------------------------------------ file để người dùng kiểm tra
STATUS_VI = {FOUND: "✅ đọc được", CONFIRMED: "✔️ đã xác nhận (project.yaml)", CONFLICT: "⚠️ mâu thuẫn",
             MISSING: "— không thấy"}


def _evidence(fv: FieldValue) -> List[Dict[str, Any]]:
    """Mọi căn cứ của 1 trường: ứng viên (nếu có) hoặc chính giá trị."""
    if fv.candidates:
        return fv.candidates
    return [{"value": fv.value, "page": fv.page, "text": fv.text, "method": fv.method}] if fv.value is not None else []


def _md(s: Any) -> str:
    return str(s).replace("|", "/").replace("\n", " ").strip()


def _field_block(label: str, fv: FieldValue, text_key: bool, unit: Optional[str]) -> List[str]:
    val = fmt_candidates(fv, text_key) if fv.status == CONFLICT else fmt_value(fv)
    if fv.status != CONFLICT and fv.value is not None and unit and isinstance(fv.value, str) is False and not fv.unit:
        val += f" {unit}"
    lines = [f"| **{label}** | {_md(val)} | {STATUS_VI.get(fv.status, fv.status)} | |"]
    seen = set()
    for c in _evidence(fv):
        sig = (str(c.get("value")), c.get("page"), c.get("method"))
        if sig in seen:
            continue
        seen.add(sig)
        src = f"tr.{c['page']}" if c.get("page") else "project.yaml"
        hm = f" · {c['hang_muc']}" if c.get("hang_muc") else ""
        lines.append(f"| ↳ | {_md(_v(c.get('value')))} | {src} · {c.get('method') or ''}{hm} | “{_md(c.get('text') or '')[:110]}” |")
    return lines


def info_markdown(info: ProjectInfo, spec: Dict[str, Any]) -> str:
    """Bản thông tin công trình để kỹ sư đối chiếu: giá trị + trang + câu nguyên văn trên bản vẽ."""
    m = info.meta or {}
    pdf = m.get("pdf", "")
    out = [f"# Thông tin công trình — {fmt_value(info.khu_dat.get('ten_cong_trinh') or FieldValue())}", "",
           f"- File: `{pdf}`  (hash `{m.get('pdf_hash', '')}`)",
           f"- Trang đã đọc: {', '.join(map(str, m.get('pages') or []))}",
           f"- Gemini: {m.get('gemini_mode', '')}" + (f" — trang {', '.join(map(str, m.get('gemini_pages') or []))}, "
                                                    f"model {', '.join(m.get('model') or [])}" if m.get("gemini_pages") else ""),
           f"- Hạng mục chính (dùng để kiểm tra luật): **{info.hang_muc_chinh or '—'}**", "",
           "> Mỗi trường: dòng **đậm** = giá trị tool dùng; các dòng ↳ = căn cứ (giá trị · trang · nguồn · câu nguyên văn).",
           "> `vector` = chữ trong PDF (chính xác); `gemini` = AI đọc ảnh (đã loại giá trị không có chữ trên trang).",
           "> Sai/thiếu -> sửa trong `project.yaml` (mẫu `config/project.example.yaml`) rồi chạy lại `info --project`.", ""]
    problems = info.problems(spec)
    if problems:
        out += ["## ⚠️ Cần xác nhận trước khi kiểm tra", ""]
        out += [f"- **{spec['fire_inputs'][k]['label']}**: {why}" for k, why in problems.items()]
        out.append("")

    out += ["## 1. Khu đất", "", "| Trường | Giá trị | Trạng thái / nguồn | Nguyên văn |", "|---|---|---|---|"]
    for key, s in spec["khu_dat"].items():
        out += _field_block(s["label"], info.khu_dat.get(key) or FieldValue(), key in TEXT_KEYS, s.get("unit"))
    out.append("")

    head, rows = hang_muc_table(info, spec)
    if rows:
        out += ["## 2. Tổng hợp các hạng mục", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        out += ["| " + " | ".join(_md(c) for c in r) + " |" for r in rows]
        out.append("")

    def section(title: str, fields: Dict[str, FieldValue]) -> None:
        out.extend([title, "", "| Trường | Giá trị | Trạng thái / nguồn | Nguyên văn |", "|---|---|---|---|"])
        for sec in HM_SECTIONS:
            for key, s in spec[sec].items():
                out.extend(_field_block(s["label"], fields.get(key) or FieldValue(), key in TEXT_KEYS, s.get("unit")))
        out.append("")

    main = {**info.project_info, **info.fire_inputs}
    section(f"## 3. Hạng mục chính: {info.hang_muc_chinh or '(chung)'}", main)
    others = [(n, fs) for n, fs in info.hang_muc.items() if n != info.hang_muc_chinh]
    for i, (name, fs) in enumerate(others, 1):
        section(f"## 4.{i} Hạng mục: {name}", fs)

    if info.warnings:
        out += ["## Cảnh báo khi đọc", ""] + [f"- {_md(w)}" for w in info.warnings] + [""]
    return "\n".join(out) + "\n"


def _cell(fv: FieldValue, unit: Optional[str]) -> Tuple[str, str]:
    """-> (ô kết quả gọn, loại cần lưu ý: '' | 'conflict' | 'gemini')."""
    if fv.status == CONFLICT:
        vals = " / ".join(_v(g["value"]) for g in distinct_values(fv.candidates))
        return f"⚠ {vals}", "conflict"
    if fv.value is None:
        return "—", ""
    v = _v(fv.value) + (f" {unit}" if unit and not isinstance(fv.value, str) else "")
    if fv.status == CONFIRMED:
        return f"{v} ✔", ""
    methods = {c.get("method") for c in _evidence(fv)}
    if methods == {"gemini"}:
        return f"{v} *", "gemini"
    return v, ""


def info_summary(info: ProjectInfo, spec: Dict[str, Any]) -> str:
    """Bản GỌN: mỗi hạng mục 1 kết quả cho mỗi trường (sau khi đã đối chiếu mọi trang) + danh sách cần xác nhận."""
    m = info.meta or {}
    ten = fmt_value(info.khu_dat.get("ten_cong_trinh") or FieldValue())
    names = [info.hang_muc_chinh] + [n for n in info.hang_muc if n != info.hang_muc_chinh] if info.hang_muc else []
    # hạng mục không có số liệu nào ngoài công năng -> không chiếm cột, liệt kê riêng
    empty = [n for n in names if n != info.hang_muc_chinh and not any(
        fv.value is not None or fv.status == CONFLICT for k, fv in info.hang_muc.get(n, {}).items() if k != "cong_nang")]
    names = [n for n in names if n not in empty]
    cols = names or ["(công trình)"]
    fields_of = {n: info.hang_muc.get(n, {}) for n in names} or {"(công trình)": {**info.project_info, **info.fire_inputs}}
    land = info.khu_dat.get("dien_tich_khu_dat") or FieldValue()
    out = [f"# {ten}", "",
           f"- Diện tích khu đất: **{fmt_value(land)}**" + (f" (tr.{fmt_pages(land)})" if land.value is not None else ""),
           f"- Số hạng mục: {len(info.hang_muc) or 1} — hạng mục chính (dùng kiểm tra luật QCVN 06): **{info.hang_muc_chinh or '—'}**",
           f"- File: `{m.get('pdf', '')}` · đọc {len(m.get('pages') or [])} trang · chi tiết căn cứ: `project_info_chi_tiet.md`",
           "", "Ký hiệu: ⚠ = các trang ghi khác nhau (cần chọn) · * = chỉ Gemini đọc được (cần kiểm) · "
           "✔ = đã xác nhận trong project.yaml · — = bản vẽ không ghi", ""]
    head = ["Trường"] + [f"**{n}**" + (" (chính)" if n == info.hang_muc_chinh and len(cols) > 1 else "") for n in cols]
    out += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    notes: List[str] = []
    gem_by: Dict[str, List[str]] = {}
    for sec in ("fire_inputs", "project_info"):
        for key, s in spec[sec].items():
            row = [s["label"]]
            for n in cols:
                fv = fields_of[n].get(key) or FieldValue()
                cell, kind = _cell(fv, s.get("unit"))
                if key == "cong_nang":            # công năng ghi khác chữ không quan trọng: lấy cách ghi dài nhất
                    vals = [g["value"] for g in distinct_values(_evidence(fv), True)]
                    cell, kind = (max(map(str, vals), key=len) if vals else "—"), ""
                row.append(cell)
                if kind == "conflict":
                    notes.append(f"**{n} — {s['label']}**: " + "; ".join(
                        f"{_v(g['value'])} (tr.{','.join(map(str, sorted(g['pages'])))})" for g in distinct_values(fv.candidates)))
                elif kind == "gemini" and key != "cong_nang":       # công năng ~ tên hạng mục: không cần kiểm
                    gem_by.setdefault(s["label"], []).append(f"{n} {_v(fv.value)}")
            if any(c != "—" for c in row[1:]):
                out.append("| " + " | ".join(_md(c) for c in row) + " |")
        if sec == "fire_inputs":
            out.append("| | " + " | ".join("" for _ in cols) + " |")
    out.append("")
    if empty:
        out += [f"Hạng mục khác (bản vẽ chỉ nêu tên, không có số liệu): {', '.join(empty)}", ""]
    main = info.hang_muc_chinh or "(công trình)"
    for k, why in info.problems(spec).items():           # vd nhà nhiều nhóm F, thiếu trường bắt buộc
        if not any(spec["fire_inputs"][k]["label"] in x and main in x for x in notes):
            notes.append(f"**{main} — {spec['fire_inputs'][k]['label']}**: {why}")
    conflicts = notes
    gem = [f"{label}: {', '.join(v)} — chỉ Gemini đọc, text vector không xác nhận" for label, v in gem_by.items()]
    if conflicts:
        out += ["## ⚠ Cần anh/chị chọn giá trị", ""] + [f"- {x}" for x in conflicts] + [""]
    if gem:
        out += ["## * Cần kiểm lại (chỉ Gemini đọc)", ""] + [f"- {x}" for x in gem] + [""]
    assumed = [w[len("số tầng: "):] for w in info.warnings if w.startswith("số tầng: ")]
    if assumed:
        out += ["## Giả định khi tính số tầng (QCVN 06 1.4.50)", ""] + [f"- {x}" for x in assumed] + [""]
    dropped = sum("Gemini tự suy" in w for w in info.warnings)
    if dropped:
        out += [f"_Đã loại {dropped} giá trị Gemini tự suy (không có chữ trên bản vẽ) — xem `project_info_chi_tiet.md`._", ""]
    out += ["Sửa/xác nhận: điền vào `project.yaml` (mẫu `config/project.example.yaml`) rồi chạy lại "
            "`python -m pccc_checker info <pdf> --project project.yaml`."]
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ điều phối
def _value_tokens(key: str, value: Any) -> List[List[str]]:
    """Các cách viết của giá trị để tìm trong text trang. [] = không kiểm (trường chữ)."""
    if key in TEXT_KEYS or key in PROJECT_KEYS and isinstance(value, str):
        return []
    vals = value if isinstance(value, list) else [value]
    out = []
    for v in vals:
        if isinstance(v, (int, float)):
            f = float(v)
            txt = f"{f:.6f}".rstrip("0").rstrip(".")
            forms = {txt, txt.replace(".", ",")}
            if f == int(f):
                forms |= {str(int(f)), f"{int(f):02d}"}
            out.append(sorted(forms))
        else:
            out.append([str(v)])
    return out


def _on_page(token: str, blob: str) -> bool:
    """token có trong text trang như một từ/số riêng; số cho phép 0 thừa phía sau ('3.5' ~ '3.50') và dính 'm' ('6m')."""
    tail = r"(?:[.,]?0+)?" if re.fullmatch(r"[\d.,]+", token) else ""
    pat = r"(?<![\w.,])" + re.escape(token) + tail + r"(?:(?![\w]|[.,]\d)|(?=\s*[mM](?:[23²³]|\b)))"
    return re.search(pat, blob, re.I) is not None


# Nhãn bắt buộc có trong câu căn cứ Gemini trả về (chặn gán nhầm: "DIỆN TÍCH MỖI TẦNG" -> tổng diện tích sàn,
# "LẦU 2" -> số tầng 2, "CHIỀU CAO PCCC" -> chiều cao kiến trúc...)
GEMINI_LABEL: Dict[str, re.Pattern] = {
    "tong_dien_tich_san": re.compile(r"DIỆN\s*TÍCH\s*SÀN", re.I),
    "dien_tich_xay_dung": re.compile(r"XÂY\s*DỰNG", re.I),
    "dien_tich_khu_dat": re.compile(r"ĐẤT", re.I),
    "so_tang_noi": re.compile(r"SỐ\s*TẦNG|TẦNG\s*NỔI|\d+\s*TẦNG\b", re.I),
    "so_tang_ham": re.compile(r"HẦM", re.I),
    "chieu_cao_cong_trinh": re.compile(r"CHIỀU\s*CAO(?!\s*(PCCC|PHÒNG|THÔNG\s*THỦY|TẦNG))", re.I),
    "chieu_cao_pccc": re.compile(r"PCCC|PHÒNG\s*CHÁY", re.I),
    "khoi_tich": re.compile(r"KHỐI\s*TÍCH", re.I),
    "bac_chiu_lua": re.compile(r"BẬC", re.I),
    "hang_chay_no": re.compile(r"HẠNG", re.I),
}


def verify_gemini(hits: List[Dict[str, Any]], page_texts: Dict[int, str]) -> List[str]:
    """Bỏ hit Gemini có giá trị không xuất hiện trong text vector của trang (trang có text). -> cảnh báo."""
    warns = []
    keep = []
    for h in hits:
        blob = page_texts.get(h["page"], "")
        if h["method"] != "gemini" or len(blob) < 50:
            keep.append(h)
            continue
        toks = _value_tokens(h["key"], h["value"])
        ok = all(any(_on_page(t, blob) for t in forms) for forms in toks)
        lab = GEMINI_LABEL.get(h["key"])
        if ok and lab and not lab.search(h.get("text") or ""):
            warns.append(f"trang {h['page']} (gemini): {h['key']}={_v(h['value'])} — câu căn cứ không có nhãn của trường "
                         f"(\"{(h.get('text') or '')[:50]}\"), đã bỏ")
            continue
        if ok:
            keep.append(h)
        else:
            warns.append(f"trang {h['page']} (gemini): {h['key']}={_v(h['value'])} KHÔNG có trên bản vẽ (text vector) "
                         f"— Gemini tự suy, đã bỏ")
    hits[:] = keep
    return list(dict.fromkeys(warns))


def read_project_info(pdf: Path, settings: Dict[str, Any], gemini: str = "auto", project_yaml: Optional[Path] = None,
                      cache_dir: Optional[Path] = None, pages: Optional[List[int]] = None, log=print) -> ProjectInfo:
    """gemini: 'auto' (chỉ trang không có text / bảng regex không tách được) | 'always' | 'never'."""
    from .extractors.gemini_extractor import _file_hash
    from .pdf.classify import info_pages
    from .pdf.render import vector_text
    spec = load_spec()
    targets = info_pages(pdf) if not pages else [(p, "chỉ định") for p in pages]
    log(f"[info] đọc {len(targets)} trang: {', '.join(f'{p}({k})' for p, k in targets)}")
    from .pdf.classify import TITLE_LINE
    hits: List[Dict[str, Any]] = []
    titles: Dict[int, str] = {}
    page_texts: Dict[int, str] = {}
    need_gemini: List[int] = []
    for p, kind in targets:
        texts = vector_text(pdf, p)
        titles[p] = page_title(texts, TITLE_LINE)
        page_texts[p] = "\n".join(t["text"] for t in texts)
        ph = scan_page(texts, p)
        if kind == "khu_dat":                 # trang định vị khu đất: chỉ lấy thông tin chung của khu đất
            ph = [h for h in ph if h["key"] in PROJECT_KEYS or h.get("hang_muc")]
        hits.extend(ph)
        no_text = sum(len(t["text"]) for t in texts) < 50
        # trang ghi chú PCCC (mặt bằng/mặt đứng) không tính là bảng yếu: text vector là đủ
        weak_table = kind in ("bang_quy_mo", "thuyet_minh_pccc") and len({h["key"] for h in ph}) < 3
        if no_text or (gemini == "always" and kind != "cover") or (gemini == "auto" and weak_table):
            need_gemini.append(p)
    meta: Dict[str, Any] = {"schema_version": SCHEMA_VERSION, "pdf": str(pdf), "pdf_hash": _file_hash(pdf),
                            "pages": [p for p, _ in targets], "gemini_mode": gemini, "gemini_pages": []}
    warnings: List[str] = []
    if need_gemini and gemini != "never":
        try:
            from .extractors.info_gemini import PROMPT_FILE, make_info_reader
            reader = make_info_reader(settings, cache_dir)
            for p in need_gemini:
                try:
                    gh = reader.read_page(pdf, p)
                    hits.extend(gh)
                    meta["gemini_pages"].append(p)
                    log(f"[info] Gemini trang {p}: {len(gh)} giá trị")
                except Exception as e:      # quota / mạng: vẫn giữ kết quả vector
                    warnings.append(f"Gemini không đọc được trang {p}: {str(e)[:120]}")
                    log(f"[info] ⚠ Gemini trang {p}: {str(e)[:120]}")
            meta.update(prompt=PROMPT_FILE, prompt_hash=reader.prompt_hash, model=sorted(reader.models_used))
        except RuntimeError as e:          # thiếu API key
            warnings.append(f"Không gọi Gemini: {e}")
            log(f"[info] ⚠ {e}")
    user = yaml.safe_load(Path(project_yaml).read_text(encoding="utf-8")) or {} \
        if project_yaml and Path(project_yaml).exists() else None
    warnings += verify_gemini(hits, page_texts)
    tag_by_title(hits, titles)
    tag_hang_muc(hits)
    info = merge(hits, spec, (user or {}).get("hang_muc_chinh"))
    for a in dict.fromkeys(x for h in hits for x in h.get("assumptions") or []):
        info.warnings.append(f"số tầng: {a}")
    info.warnings = warnings + info.warnings
    info.meta = meta
    if user is not None:
        apply_user(info, user, spec)
        info.meta["project_yaml"] = str(project_yaml)
    return info
