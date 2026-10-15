"""Điền kết quả đối chiếu vào file Word mẫu (`datamau/B*.docx`) → "bảng đối chiếu hoàn chỉnh" của từng hạng mục.

Không tốn token: lấy findings.jsonl (D/KD/XM/NA — do Gemini lượt đầu + script kiểm chứng, Claude chỉ xét phần còn nghi),
ghép vào đúng hàng Word qua `rules/checklists/**/src_map.json` (ID → số hàng R### của bảng gốc; R### đánh số theo thứ tự hàng
của mọi bảng trong file, bỏ bảng tiêu đề 1 hàng 2 ô — cùng quy tắc `scripts/checklists/docx_to_md.py`).

Cột điền:  [2] Nội dung thiết kế = số liệu/chữ thể hiện trên bản vẽ (kèm trang);  [5] Kết luận = Đạt | Không đạt (tr.X) |
Cần xác minh (tr.X) | Không áp dụng | Chưa đánh giá. Không đạt tô đỏ, cần xác minh nghiêng cam.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor
from docx.table import Table

from ..config import PROJECT_ROOT

RED, ORANGE, GREEN = RGBColor(0xC0, 0, 0), RGBColor(0xE0, 0x6C, 0), RGBColor(0x2E, 0x7D, 0x4F)
FONT = "Times New Roman"
DATAMAU = PROJECT_ROOT / "datamau"
CHECKLISTS = PROJECT_ROOT / "rules" / "checklists"


def _trang(r: dict) -> str:
    return f"tr.{r['trang']}" if r.get("trang") else ""


VIET: dict[str, dict] = {}        # rule -> {tk, gc, nguon}; nạp từ goi/tk_bang.json (viet_tk)


def thiet_ke(r: dict) -> str:
    """Nội dung thiết kế: bản viết lại đã kiểm (Gemini) nếu có; không thì nguyên văn trên bản vẽ / quan sát đã ghi."""
    v = VIET.get(r.get("rule") or "")
    if v and v.get("tk"):
        return _sach(v["tk"])
    tr = _trang(r)
    if r["tt"] == "XM" and "BV_KT không có" in (r.get("ly_do") or ""):
        return "Chưa thể hiện trên bản vẽ; bản vẽ kiến trúc chỉ thể hiện phòng bơm 15 m2 tại tầng hầm (tr.8)"
    if r["tt"] == "NA":
        return f"Không áp dụng — {r.get('ly_do') or 'không có đối tượng'}"
    ev = (r.get("evid") or "").strip()
    nd = (r.get("ly_do") or "").strip()
    if ev and nd and ev.lower() not in nd.lower():
        return f"{tr}: «{ev}». {nd}".strip(": ")
    return f"{tr}: {ev or nd}".strip(": ")


def _sach(s: str) -> str:
    """Bỏ từ ngữ nội bộ của quy trình khỏi chữ đưa vào bảng đối chiếu (gói, mã dòng KS1-…)."""
    s = re.sub(r"(?:KS1|HT\d+|[A-Z]{2,4}\d?)-[A-Z]+-\d+", "dòng đối chiếu liên quan", s or "")
    for a, b in (("trong gói quy định", "trong bảng quy định"), ("trong gói", "trong bảng"), ("kèm theo gói", "kèm theo bảng"),
                 ("gói quy định", "bảng quy định")):
        s = s.replace(a, b)
    return s


def ket_luan(r: dict) -> tuple[str, RGBColor | None, bool]:
    tr = f" ({_trang(r)})" if r.get("trang") else ""
    gc = _sach((VIET.get(r.get("rule") or "") or {}).get("gc") or "")
    gc = f": {gc}" if gc else ""
    if r["tt"] == "D":
        return "Đạt", GREEN, False
    if r["tt"] == "KD":
        return f"Không đạt{tr}{gc}", RED, False
    if r["tt"] == "XM":
        return f"Cần xác minh{tr}{gc}", ORANGE, True
    return "Không áp dụng", None, False


def _ghi(cell, text: str, color=None, italic=False, bold=False, size=9) -> None:
    cell.text = ""
    run = cell.paragraphs[0].add_run(text)
    run.font.name = FONT                                  # không đặt font -> kế thừa font cũ của mẫu, tiếng Việt bị đổi dấu (à->ỏ)
    rf = run._element.get_or_add_rPr().get_or_add_rFonts()
    for k in ("ascii", "hAnsi", "eastAsia", "cs"):
        rf.set(qn(f"w:{k}"), FONT)
    run.font.size = Pt(size)
    run.italic, run.bold = italic, bold
    if color is not None:
        run.font.color.rgb = color


def hang_theo_R(doc: Document) -> dict[str, list]:
    """R### -> cells của hàng (đúng cách đánh số của docx_to_md.py: bỏ bảng tiêu đề)."""
    out, n = {}, 0
    for t in doc.tables:
        distinct = [c for c in _uniq_cells(t.rows[0])] if t.rows else []
        if len(t.rows) == 1 and len(distinct) == 2:
            continue
        for r in t.rows:
            n += 1
            out[f"R{n:03d}"] = r.cells
    return out


def _uniq_cells(row) -> list:
    out, prev = [], None
    for c in row.cells:
        if c._tc is prev:
            continue
        prev = c._tc
        out.append(c)
    return out


def dien(doc: Document, src_map: dict, findings: list[dict], tien_to: str) -> dict:
    """Điền vào doc. findings: các dòng của 1 hạng mục. Trả thống kê."""
    rows = hang_theo_R(doc)
    by_rule = {f["rule"]: f for f in findings}
    st = {"dien": 0, "chua_danh_gia": 0, "khong_hang": 0}
    for rid, m in src_map.items():
        if not rid.startswith(tien_to):
            continue
        cells = rows.get(m["row"])
        if cells is None or len(cells) < 6:
            st["khong_hang"] += 1
            continue
        if cells[2]._tc is cells[1]._tc or cells[5]._tc is cells[4]._tc:    # hàng tiêu đề mục gộp ô
            continue
        f = by_rule.get(rid)
        if not f:
            if (cells[3].text or "").strip():                                  # hàng có quy định mà chưa đánh giá
                _ghi(cells[5], "Chưa đánh giá", italic=True)
                st["chua_danh_gia"] += 1
            continue
        kl, color, nghieng = ket_luan(f)
        _ghi(cells[2], thiet_ke(f))
        _ghi(cells[5], kl, color=color, italic=nghieng, bold=f["tt"] in ("D", "KD"))
        st["dien"] += 1
    return st


def dien_dau_bang(doc: Document, tt: dict) -> None:
    """Các dòng '1. Tên công trình', '2. Địa điểm'… ở đầu file."""
    khoa = (("1. Tên công trình", "ten"), ("2. Địa điểm xây dựng", "dia_diem"), ("3. Chủ đầu tư", "chu_dau_tu"),
            ("4. Cơ quan thiết kế", "co_quan_thiet_ke"))
    for p in doc.paragraphs[:20]:
        for nhan, k in khoa:
            if p.text.strip().startswith(nhan) and tt.get(k):
                _viet_doan(p, f"{nhan}: {tt[k]}")


def xuat(out: Path, hm_id: str | None = None) -> list[Path]:
    """Xuất mọi hạng mục + mẫu hệ thống đã áp dụng -> out/bang_doi_chieu/<HM>_<mẫu>.docx."""
    keys = json.loads((out / "rule_keys.json").read_text(encoding="utf-8"))
    F = [json.loads(x) for x in (out / "findings.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    tt = json.loads((out / "thong_tin_chung.json").read_text(encoding="utf-8")) if (out / "thong_tin_chung.json").exists() else {}
    dest = out / "bang_doi_chieu"
    dest.mkdir(exist_ok=True)
    VIET.clear()
    vf = out / "goi" / "tk_bang.json"
    if vf.exists():
        VIET.update(json.loads(vf.read_text(encoding="utf-8")))
    ra = []
    for h in keys["hang_muc"]:
        if hm_id and h["hm"] != hm_id:
            continue
        mau = h.get("mau")
        if not mau:
            continue
        fh = [f for f in F if f.get("hm") == h["hm"]]
        # bảng chính của loại hình (ID dạng KS1-…)
        mf = _mau_file(mau)
        if mf:
            sm = json.loads((CHECKLISTS / h["loai_hinh"] / "src_map.json").read_text(encoding="utf-8"))
            pre = next(iter(sm)).split("-")[0] + "-"
            doc = Document(mf)
            dien_dau_bang(doc, tt)
            st = dien(doc, sm, fh, pre)
            p = dest / f"{h['hm']}_{mau}.docx"
            p = _luu(doc, p)
            ra.append((p, st))
        # mẫu hệ thống (B36…)
        hsm = CHECKLISTS / "he-thong" / "src_map.json"
        if hsm.exists():
            sm = json.loads(hsm.read_text(encoding="utf-8"))
            for b in sorted({f["rule"].split("-")[0] for f in fh if f["rule"].startswith("HT")}):
                mb = {k: v for k, v in sm.items() if k.startswith(b + "-")}
                if not mb:
                    continue
                code = mb[next(iter(mb))]["mau"]
                mf2 = _mau_file(code)
                if not mf2:
                    continue
                doc = Document(mf2)
                dien_dau_bang(doc, tt)
                st = dien(doc, mb, fh, b + "-")
                p = dest / f"{h['hm']}_{code}.docx"
                p = _luu(doc, p)
                ra.append((p, st))
    return ra


def _mau_file(mau: str) -> Path | None:
    for f in sorted(DATAMAU.glob("*.docx")):
        if re.match(rf"^{re.escape(mau)}[\s.]", f.name):
            return f
    return None


def thu_dong(out: Path, hm_id: str | None = None) -> list[tuple[str, str, str, dict]]:
    """Các dòng bảng chính (không phải mẫu hệ thống) có kết quả -> [(rule, nội dung đối chiếu, quy định, finding)]."""
    keys = json.loads((out / "rule_keys.json").read_text(encoding="utf-8"))
    F = [json.loads(x) for x in (out / "findings.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    ds = []
    for h in keys["hang_muc"]:
        if hm_id and h["hm"] != hm_id or not h.get("mau") or not _mau_file(h["mau"]):
            continue
        sm = json.loads((CHECKLISTS / h["loai_hinh"] / "src_map.json").read_text(encoding="utf-8"))
        rows = hang_theo_R(Document(_mau_file(h["mau"])))
        for f in F:
            if f.get("hm") == h["hm"] and f["rule"] in sm and f["tt"] in ("D", "KD", "XM", "NA"):
                c = rows[sm[f["rule"]]["row"]]
                ds.append((f["rule"], " ".join(c[1].text.split()), " ".join(c[3].text.split()), f))
    return ds


def _luu(doc: Document, p: Path) -> Path:
    """File đang mở trong Word (khoá ghi) -> lưu thành <tên>_moi.docx thay vì lỗi."""
    chuan_font(doc)
    assert font_loi(doc) == 0, "còn run thiếu font tường minh -> tiếng Việt méo dấu"
    try:
        doc.save(p)
        return p
    except PermissionError:
        for n in range(1, 20):
            q = p.with_name(f"{p.stem}_moi{n if n > 1 else ''}.docx")
            try:
                doc.save(q)
                return q
            except PermissionError:
                continue
        raise


def _viet_doan(p, text: str) -> None:
    """Thay chữ cả đoạn nhưng đặt font tường minh (p.text = … tạo run không font -> tiếng Việt méo dấu); giữ cỡ chữ cũ."""
    size = next((r.font.size for r in p.runs if r.font.size), None)
    for r in list(p.runs):
        r._element.getparent().remove(r._element)
    run = p.add_run(text)
    run.font.name = FONT
    rf = run._element.get_or_add_rPr().get_or_add_rFonts()
    for k in ("ascii", "hAnsi", "eastAsia", "cs"):
        rf.set(qn(f"w:{k}"), FONT)
    if size:
        run.font.size = size


def _moi_run(doc: Document):
    """Mọi run có chữ: thân văn bản, bảng (kể cả bảng lồng), đầu/cuối trang."""
    def doan(ps):
        for p in ps:
            yield from p.runs

    def bang(ts):
        for tb in ts:
            for row in tb.rows:
                for c in row.cells:
                    yield from doan(c.paragraphs)
                    yield from bang(c.tables)

    yield from doan(doc.paragraphs)
    yield from bang(doc.tables)
    for s in doc.sections:
        for part in (s.header, s.footer):
            yield from doan(part.paragraphs)
            yield from bang(part.tables)


def _co_font(run) -> bool:
    rpr = run._element.rPr
    return rpr is not None and rpr.rFonts is not None and rpr.rFonts.get(qn("w:ascii")) is not None


def chuan_font(doc: Document) -> int:
    """GỐC LỖI MÉO DẤU: style Normal của mẫu dùng '.VnTime' (font VN cũ, không phải Unicode) — run nào không ghi font tường minh
    sẽ bị đổi dấu (á->ỏ, â->õ…). Run của mẫu đều có Times New Roman; run do tool tạo mà thiếu font thì gán Times New Roman.
    Trả về số run đã vá; luôn chạy trước khi lưu, nên không thể sót dù thêm chỗ ghi chữ mới."""
    n = 0
    for r in _moi_run(doc):
        if r.text and not _co_font(r):
            r.font.name = FONT
            rf = r._element.get_or_add_rPr().get_or_add_rFonts()
            for k in ("ascii", "hAnsi", "eastAsia", "cs"):
                rf.set(qn(f"w:{k}"), FONT)
            n += 1
    return n


def font_loi(doc: Document) -> int:
    """Số run có chữ mà thiếu font tường minh (phải = 0 sau chuan_font)."""
    return sum(1 for r in _moi_run(doc) if r.text and not _co_font(r))
