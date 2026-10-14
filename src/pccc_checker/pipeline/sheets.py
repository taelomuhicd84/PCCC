"""Danh mục bản vẽ: trang -> tên bản vẽ (khung tên), ký hiệu bản vẽ, hạng mục, chuyên đề (0 token).

Đọc khung tên bằng lớp chữ: nhãn "TÊN BẢN VẼ" / "DRAWING TITLE" -> dòng chữ gần nhãn nhất (không phải nhãn khác).
Không có nhãn -> dòng tiêu đề lớn trên trang (MẶT BẰNG…, CHI TIẾT…, BẢNG…). Trang scan -> trống (Gemini/Claude bổ sung).
Chuyên đề theo từ khoá của tên bản vẽ -> skill chuyên đề chỉ gọi đúng các trang của mình
(`python -m pccc_checker trang <thư mục> --cd thoat-nan`).
"""
from __future__ import annotations

import re
import unicodedata

from .chuyen_de import cd_of_sheet

LABEL_TEN = re.compile(r"^\W*(TÊN\s*BẢN\s*VẼ|TÊN\s*BV|DRAWING\s*(TITLE|NAME)|SHEET\s*TITLE|TITLE)\b\W*", re.I)
LABEL_SO = re.compile(r"^\W*((KÍ|KÝ)\s*HIỆU(\s*(BẢN\s*VẼ|BV))?|SỐ\s*HIỆU(\s*BẢN\s*VẼ)?|BẢN\s*VẼ\s*SỐ|SỐ\s*BẢN\s*VẼ|"
                      r"DRAWING\s*(NO|NUMBER)|SHEET\s*(NO|NUMBER)|DWG\s*NO)\b\W*", re.I)
LABEL_HM = re.compile(r"^\W*(HẠNG\s*MỤC|ITEM)\b\s*:?\s*", re.I)
# nhãn khác trong khung tên — không lấy làm giá trị
OTHER = re.compile(r"^\W*(TÊN\s*DỰ\s*ÁN|DỰ\s*ÁN|CÔNG\s*TRÌNH|CHỦ\s*ĐẦU\s*TƯ|CLIENT|PROJECT|ĐỊA\s*(ĐIỂM|CHỈ)|ĐƠN\s*VỊ|"
                   r"CHỦ\s*TRÌ|THIẾT\s*KẾ|THỂ\s*HIỆN|KIỂM\s*TRA|GIÁM\s*ĐỐC|NGÀY|DATE|TỶ\s*LỆ|TỈ\s*LỆ|SCALE|"
                   r"GHI\s*CHÚ|NOTE|BỘ\s*MÔN|HẠNG\s*MỤC|ITEM|(KÍ|KÝ)\s*HIỆU|SỐ\s*HIỆU|BẢN\s*VẼ\s*SỐ|DRAWING|SHEET|"
                   r"TITLE|REV|LẦN|SỬA\s*ĐỔI|KTS|KS\.|CÔNG\s*TY|TEL|E-?MAIL|WEBSITE|PHÁT\s*HÀNH|GIAI\s*ĐOẠN|"
                   r"ĐIỀU\s*CHỈNH|FOR\s|THỰC\s*HIỆN|QUẢN\s*LÝ)\b", re.I)
SO_VALUE = re.compile(r"^(?!(RE|REV|R)[\s.]*\d)(?=.*\d)[A-ZĐ]{1,6}([\s._-]*[A-Z0-9]{1,4}){1,4}$")  # KT-01, A-CX9-01-01; không lấy RE.00
HM_WORDS = re.compile(r"^\W*(NHÀ|XƯỞNG|KHO|KHÁCH\s*SẠN|TRẠM|BỂ|KHU|KHỐI|TÒA|TOÀ|CÔNG\s*TRÌNH|CHUNG\s*CƯ|VĂN\s*PHÒNG|"
                      r"FACTORY|WAREHOUSE|BLOCK|BUILDING|MASTER|TỔNG\s*THỂ)", re.I)
BO_MON = re.compile(r"^\W*(KIẾN\s*TRÚC|KẾT\s*CẤU|ARCHITECTURE|STRUCTURE|BÁO\s*CHÁY|CHỮA\s*CHÁY|HÚT\s*KHÓI|THÔNG\s*GIÓ.*|"
                    r"THIẾT\s*BỊ\s*PCCC|ĐIỆN|CẤP\s*THOÁT\s*NƯỚC|PCCC|CHÁY|TỔNG\s*THỂ|M&E|MEP)\W*$", re.I)
TITLE_LINE = re.compile(r"^(MẶT\s*BẰNG|MẶT\s*ĐỨNG|MẶT\s*CẮT|CHI\s*TIẾT|BẢNG|THỐNG\s*KÊ|TỔNG\s*MẶT|BỐ\s*TRÍ|SƠ\s*ĐỒ|"
                        r"THUYẾT\s*MINH|GHI\s*CHÚ\s*PCCC|DANH\s*MỤC|PHỐI\s*CẢNH|KẾT\s*CẤU|BÌA)", re.I)

def _plain(s: str) -> str:
    s = unicodedata.normalize("NFD", s.upper().replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _center(b):
    return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)


TITLE_WORDS = re.compile(r"^\W*(MẶT\s*BẰNG|MẶT\s*ĐỨNG|MẶT\s*CẮT|CHI\s*TIẾT|BẢNG|THỐNG\s*KÊ|TỔNG\s*MẶT|BỐ\s*TRÍ|SƠ\s*ĐỒ|"
                         r"THUYẾT\s*MINH|GHI\s*CHÚ|DANH\s*MỤC|PHỐI\s*CẢNH|KẾT\s*CẤU|BÌA|HỆ\s*THỐNG|BẢN\s*VẼ|TRIỂN\s*KHAI|"
                         r"CẤU\s*TẠO|PLAN|ELEVATION|SECTION|DETAIL|SCHEDULE|LAYOUT)", re.I)
ADDRESS = re.compile(r"\b(P\.|TP\.|TỈNH|THÀNH\s*PHỐ|HUYỆN|QUẬN|XÃ|PHƯỜNG|ĐƯỜNG|KHU\s*CÔNG\s*NGHIỆP|KCN|THỬA\s*ĐẤT|"
                     r"TỜ\s*BẢN\s*ĐỒ|ĐỊA\s*CHỈ|Đ/C|LÔ\s)", re.I)


def _axis(b) -> int:
    """Chiều xếp các dòng trong khung tên: chữ ngang -> các dòng chồng theo y (1); chữ dọc (trang xoay) -> theo x (0)."""
    return 0 if (b[2] - b[0]) < (b[3] - b[1]) else 1


def _cell_lines(label: dict, lines: list[dict], reach: float = 170, band: float = 280) -> list[tuple[float, dict]]:
    """Dòng trong vùng quanh nhãn: cách nhãn <= reach theo chiều xếp dòng, cùng cột khung tên (lệch <= band)."""
    b = label["bbox"]
    ax = _axis(b)
    pa, pp = b[ax], b[1 - ax]                         # vị trí nhãn theo chiều xếp dòng / chiều dọc dòng chữ
    out = []
    for t in lines:
        if t is label:
            continue
        tb = t["bbox"]
        if _axis(tb) != ax and len(t["text"]) > 3:
            continue
        d = abs(_center(tb)[ax] - _center(b)[ax])
        if d <= reach and pp - 15 <= tb[1 - ax] <= pp + band:
            out.append((d, t))
    return sorted(out, key=lambda z: z[0])


def _is_label(s: str) -> bool:
    return bool(LABEL_TEN.match(s) or LABEL_SO.match(s) or LABEL_HM.match(s) or OTHER.match(s))


def _title_near(label: dict, lines: list[dict]) -> str:
    cell = _cell_lines(label, lines)
    good = [(d, t) for d, t in cell if TITLE_WORDS.match(t["text"].strip()) and not _is_label(t["text"].strip())
            and not ADDRESS.search(t["text"])]
    if not good:
        return ""
    first = good[0][1]
    ax = _axis(first["bbox"])
    h = max(3.0, first["bbox"][ax + 2] - first["bbox"][ax])          # bề dày 1 dòng chữ theo chiều xếp dòng
    parts, last = [first], first
    for _ in range(2):                                 # tên 2–3 dòng (VN + EN): dòng sát kế tiếp, không phải nhãn / địa chỉ
        lc = _center(last["bbox"])[ax]
        nxt = [t for _, t in cell if t not in parts and 0.3 * h < abs(_center(t["bbox"])[ax] - lc) <= 2.2 * h
               and not _is_label(t["text"].strip()) and not ADDRESS.search(t["text"]) and len(t["text"].strip()) >= 3
               and not HM_WORDS.match(t["text"].strip())          # dòng tên hạng mục (NHÀ XƯỞNG 01…) không ghép vào tên
               and not re.fullmatch(r"[\d\s.,:/+-]+", t["text"].strip())
               and abs(_center(t["bbox"])[ax] - _center(label["bbox"])[ax]) > abs(lc - _center(label["bbox"])[ax]) - 0.5 * h]
        if not nxt:
            break
        last = min(nxt, key=lambda t: abs(_center(t["bbox"])[ax] - lc))
        parts.append(last)
    return " ".join(p["text"].strip() for p in parts)[:140]


def _value_after(label_re: re.Pattern, text: str) -> str:
    m = label_re.match(text)
    rest = text[m.end():].strip(" :-/") if m else ""
    return rest if len(rest) >= 3 and not OTHER.match(rest) else ""


def _hm_near(label: dict, lines: list[dict], ten: str = "") -> str:
    for _, t in _cell_lines(label, lines, reach=90):
        s = t["text"].strip()
        if (len(s) >= 3 and not _is_label(s) and not ADDRESS.search(s) and not TITLE_WORDS.match(s)
                and not BO_MON.match(s) and s not in ten and not re.fullmatch(r"[\d\s.,:/+-]+", s)
                and HM_WORDS.search(s)):
            return s[:80]
    return ""


MAX_CONTENT = 8_000_000       # byte nét vẽ của trang; nặng hơn -> không dò ô kẻ (tổng mặt bằng 79 MB mất ~11 s)
LABEL_EN = re.compile(r"^\W*(SHEET\s*TITLE|DRAWING\s*(TITLE|NAME|NO\.?|NUMBER)|SHEET\s*NO\.?|ITEM|TITLE)\W*$", re.I)


def segments(page) -> tuple[list, list] | None:
    """Nét ngang / dọc của trang (toạ độ trang ĐANG HIỂN THỊ). None nếu trang quá nặng."""
    if len(page.read_contents()) > MAX_CONTENT:
        return None
    import pymupdf
    m = page.rotation_matrix
    hs, vs = [], []
    for d in page.get_cdrawings():
        for it in d["items"]:
            if it[0] == "l":
                pts = [pymupdf.Point(it[1]) * m, pymupdf.Point(it[2]) * m]
                segs = [pts]
            elif it[0] == "re":
                r = pymupdf.Rect(it[1]) * m
                segs = [[r.tl, r.tr], [r.bl, r.br], [r.tl, r.bl], [r.tr, r.br]]
            else:
                continue
            for a, b in segs:
                if abs(a.y - b.y) < 0.8 and abs(a.x - b.x) >= 15:
                    hs.append((min(a.x, b.x), max(a.x, b.x), (a.y + b.y) / 2))
                elif abs(a.x - b.x) < 0.8 and abs(a.y - b.y) >= 8:
                    vs.append((min(a.y, b.y), max(a.y, b.y), (a.x + b.x) / 2))
    return hs, vs


def cell_of(r, segs) -> tuple[float, float, float, float] | None:
    """Ô kẻ chứa nhãn r (Rect hiển thị): nét gần nhất bên trái / phải / trên và nét ngang dưới (bỏ gạch chân sát nhãn)."""
    hs, vs = segs
    cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
    top = max((y for x0, x1, y in hs if x0 - 1 <= cx <= x1 + 1 and y <= r.y0 + 1), default=None)
    bots = sorted(y for x0, x1, y in hs if x0 - 1 <= cx <= x1 + 1 and y >= r.y1 - 1)
    left = max((x for y0, y1, x in vs if y0 - 1 <= cy <= y1 + 1 and x <= r.x0 + 1), default=None)
    right = min((x for y0, y1, x in vs if y0 - 1 <= cy <= y1 + 1 and x >= r.x1 - 1), default=None)
    if None in (top, left, right) or not bots:
        return None
    h = r.y1 - r.y0
    bot = next((y for y in bots if y - r.y1 > 0.6 * h), bots[-1])
    if bot - top > 25 * h or right - left > 80 * h:      # không phải ô khung tên
        return None
    return left, top, right, bot


def _in_cell(lines_vis: list[tuple], cell, skip) -> list[str]:
    x0, y0, x1, y1 = cell
    got = [(r.y0, r.x0, t["text"].strip()) for t, r in lines_vis
           if t is not skip and x0 - 1 <= (r.x0 + r.x1) / 2 <= x1 + 1 and y0 - 1 <= (r.y0 + r.y1) / 2 <= y1 + 1]
    return [s for _, _, s in sorted(got) if s and not LABEL_EN.match(s) and not LABEL_TEN.match(s)
            and not LABEL_SO.match(s) and not LABEL_HM.match(s)]


def sheet_info(lines: list[dict], page=None, segs=None) -> dict:
    """lines = vector_text(pdf, p) [{'text','bbox'}]; page (pymupdf) để dò ô kẻ khung tên.
    Tên bản vẽ = chữ TRONG Ô "TÊN BẢN VẼ" (yêu cầu người dùng 14/10/2026). Ô trống / không tìm được -> để trống."""
    import pymupdf
    vis = [(t, pymupdf.Rect(t["bbox"]) * page.rotation_matrix) for t in lines] if page is not None else []
    if page is not None and segs is None:
        segs = segments(page)
    out = {"ten_ban_ve": "", "ky_hieu": "", "hang_muc": "", "nguon_ten": ""}
    for k, (t, r) in enumerate(vis or [(t, None) for t in lines]):
        s = t["text"].strip()
        for key, rx in (("ten_ban_ve", LABEL_TEN), ("ky_hieu", LABEL_SO), ("hang_muc", LABEL_HM)):
            if out[key] or not rx.match(s):
                continue
            val = _value_after(rx, s)
            cell = cell_of(r, segs) if (not val and segs and r is not None) else None
            if cell:
                inside = _in_cell(vis, cell, t)
                if key == "ky_hieu":
                    inside = [x for x in inside if SO_VALUE.match(x)] or inside[:1]
                    val = inside[0] if inside else ""
                else:
                    val = " ".join(inside)[:140]
                if key == "ten_ban_ve":
                    out["nguon_ten"] = "o_khung_ten" if val else "o_trong"
            elif not val:                                   # không dò được ô (trang nặng / không có nét) -> quanh nhãn
                if key == "ten_ban_ve":
                    val = _title_near(t, lines)
                    out["nguon_ten"] = "gan_nhan" if val else ""
                elif key == "ky_hieu":
                    near = [x for _, x in _cell_lines(t, lines, reach=120) if SO_VALUE.match(x["text"].strip())]
                    val = near[0]["text"].strip() if near else ""
                else:
                    val = _hm_near(t, lines, out["ten_ban_ve"])
            elif key == "ten_ban_ve":
                out["nguon_ten"] = "o_khung_ten"
            out[key] = val
    return out


def chuyen_de(ten: str, loai: str = "") -> list[str]:
    p = _plain(ten)
    out = cd_of_sheet(p)
    if not out and loai in ("cover", "thuyet_minh_pccc", "bang_quy_mo"):
        out = ["quy-mo"]
    return out


def danh_muc(pdf, pages: list[int] | None = None, loai: dict[int, str] | None = None) -> list[dict]:
    from ..pdf.render import page_count, vector_text
    pages = pages or list(range(1, page_count(pdf) + 1))
    loai = loai or {}
    out = []
    import pymupdf
    doc = pymupdf.open(pdf)
    for p in pages:
        info = sheet_info(vector_text(pdf, p), doc[p - 1])
        out.append({"trang": p, **info, "chuyen_de": chuyen_de(info["ten_ban_ve"], loai.get(p, ""))})
    return out


def pages_for(dm: list[dict], cd: str) -> list[int]:
    return [d["trang"] for d in dm if cd in d.get("chuyen_de", [])]


def to_md(dm: list[dict]) -> str:
    lines = ["# Danh mục bản vẽ (trang → tên bản vẽ)", "",
             "Nguồn tên: o_khung_ten = chữ trong ô TÊN BẢN VẼ (dò theo nét kẻ) · gan_nhan = trang nặng, lấy chữ gần nhãn · o_trong = ô trống · — = không có khung tên / lớp chữ.",
             "", "| Trang | Ký hiệu | Tên bản vẽ | Hạng mục | Chuyên đề |", "|---|---|---|---|---|"]
    for d in dm:
        lines.append(f"| {d['trang']} | {d['ky_hieu'] or ''} | {(d['ten_ban_ve'] or '—').replace('|', '/')} "
                     f"| {d['hang_muc'] or ''} | {', '.join(d['chuyen_de'])} |")
    return "\n".join(lines) + "\n"


def to_html(dm: list[dict]) -> str:
    """Mục 'Danh mục bản vẽ' cho thong_tin_cong_trinh.html (dùng class sẵn có của trang: .tw, table, small.n)."""
    import html
    rows = "\n".join(
        f"      <tr><th>{d['trang']}</th><td>{html.escape(d['ky_hieu'] or '')}</td>"
        f"<td style=\"white-space:normal\">{html.escape(d['ten_ban_ve'] or '—')}</td>"
        f"<td style=\"white-space:normal\">{html.escape(d['hang_muc'] or '')}</td>"
        f"<td style=\"white-space:normal\"><small class=\"n\">{', '.join(d['chuyen_de'])}</small></td></tr>" for d in dm)
    n_ok = sum(bool(d["ten_ban_ve"]) for d in dm)
    if not n_ok:                                        # lỗi font / scan: không liệt kê 1 bảng toàn "—"
        return ('  <!-- danh-muc-ban-ve -->\n  <h2>Danh mục bản vẽ</h2>\n  <p class="legend">Không đọc được tên bản vẽ ở trang nào '
                f'({len(dm)} trang): lớp chữ PDF lỗi font hoặc bản scan — cần Gemini / Claude đọc khung tên.</p>\n'
                '  <!-- /danh-muc-ban-ve -->\n')
    return (f'  <!-- danh-muc-ban-ve -->\n  <h2>Danh mục bản vẽ ({n_ok}/{len(dm)} trang đọc được tên)</h2>\n'
            '  <p class="legend">Tên lấy từ ô TÊN BẢN VẼ trong khung tên (hoặc dòng tiêu đề trên trang). Cột chuyên đề: '
            'skill chuyên đề sau này chỉ gọi đúng các trang này (<code>python -m pccc_checker trang &lt;thư mục&gt; --cd &lt;chuyên đề&gt;</code>). '
            '— = trang không có lớp chữ (scan / lỗi font).</p>\n'
            '  <div class="tw"><table>\n    <thead><tr><th>Trang</th><th>Ký hiệu</th><th>Tên bản vẽ</th><th>Hạng mục</th>'
            f'<th>Chuyên đề</th></tr></thead>\n    <tbody>\n{rows}\n    </tbody>\n  </table></div>\n  <!-- /danh-muc-ban-ve -->\n')


def insert_html(page: str, dm: list[dict]) -> str:
    """Chèn / thay mục danh mục vào cuối thẻ .card của HTML thông tin công trình."""
    sec = to_html(dm)
    if "<!-- danh-muc-ban-ve -->" in page:
        a, rest = page.split("<!-- danh-muc-ban-ve -->", 1)
        b = rest.split("<!-- /danh-muc-ban-ve -->", 1)[1]
        return a[:a.rfind("\n") + 1] + sec + b.lstrip("\n")
    i = page.rfind("</div>")
    return page[:i] + sec + page[i:] if i >= 0 else page + sec
