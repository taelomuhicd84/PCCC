"""Bước 2–3 — project_facts.json: thông tin tổng thể dạng "ô dữ liệu" + kiểm tra logic trước Cổng 1.

Ô dữ liệu = [giá trị, trang, [x0,y0,x1,y1] (0–1) | None, độ tin cậy]. Không đọc được -> [None, None, None, "L"].
Độ tin cậy:
  H : người dùng xác nhận (project.yaml) | đọc từ lớp chữ vector | hai nguồn độc lập khớp (Gemini + Claude đọc ảnh)
  M : Gemini đọc khớp nhau ở >= 2 trang khác nhau | Claude đọc ảnh lệch Gemini (lấy giá trị Claude)
  L : chỉ Gemini đọc ở 1 trang (ký hiệu * trong project_info.md)
Nhóm nhà / bậc chịu lửa / hạng nổ có hai giá trị: ban_ve (chữ trên bản vẽ) và tinh (suy từ công năng theo Bảng 6
QCVN 06:2022). Lệch nhau tự nó là một phát hiện.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

FIELDS = {          # project_info -> project_facts
    "cong_nang": "cong_nang", "so_tang_noi": "so_tang_noi", "so_tang_ham": "so_tang_ham", "so_tang_nha": "so_tang_nha",
    "chieu_cao_cong_trinh": "cao_cong_trinh_m", "chieu_cao_pccc": "cao_pccc_m", "dien_tich_xay_dung": "dt_xay_dung_m2",
    "tong_dien_tich_san": "dt_san_tong_m2", "khoi_tich": "khoi_tich_m3", "cap_nguy_hiem_chay_ket_cau": "cap_s",
}
DUAL = {"nhom_nha": "nhom_nha", "bac_chiu_lua": "bac_chiu_lua", "hang_chay_no": "hang_no"}
QUYET_DINH = ("cong_nang", "so_tang_noi", "cao_pccc_m", "dt_xay_dung_m2", "nhom_nha", "hang_no", "bac_chiu_lua")

# Công năng -> nhóm nhà, theo Bảng 6 QCVN 06:2022 (nguyên văn ở rules/qcvn06/00-dinh-nghia.md). So khớp không dấu,
# thứ tự quan trọng (cụ thể trước chung). Chỉ là gợi ý "tinh" — người dùng/Cổng 1 chốt.
NHOM_THEO_CONG_NANG = [
    (r"NHA TRE|MAU GIAO|MAM NON|BENH VIEN|NHA HO SINH|DUONG LAO", "F1.1"),
    (r"KHACH SAN|NHA KHACH|NHA NGHI|NHA TRO|KY TUC XA|NHA O TAP THE", "F1.2"),
    (r"CHUNG CU", "F1.3"),
    (r"NHA O RIENG LE|NHA PHO|BIET THU", "F1.4"),
    (r"KARAOKE|RAP CHIEU|NHA HAT|VU TRUONG|HOP DEM|QUAN BAR|PHONG HAT|NHA THI DAU|THU VIEN", "F2.1"),
    (r"BAO TANG|TRIEN LAM|THUY CUNG", "F2.2"),
    (r"NHA HANG|AN UONG|GIAI KHAT", "F3.2"),
    (r"SIEU THI|TRUNG TAM THUONG MAI|CUA HANG|SHOWROOM|PHONG TRUNG BAY", "F3.1"),
    (r"NHA GA|BEN XE", "F3.3"),
    (r"PHONG KHAM|THAM MY VIEN|MASSAGE|XOA BOP", "F3.4"),
    (r"TRUONG (TIEU HOC|TRUNG HOC|THPT|THCS|DAY NGHE)", "F4.1"),
    (r"TRUONG DAI HOC|CAO DANG|HOC VIEN", "F4.2"),
    (r"VAN PHONG|TRU SO|NGAN HANG|NHA LAM VIEC", "F4.3"),
    (r"NHA XUONG|XUONG|SAN XUAT|PHONG THI NGHIEM", "F5.1"),
    (r"NHA KHO|\bKHO\b|NHA XE|GA RA|GARA|LUU TRU", "F5.2"),
]


def _plain(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").upper().replace("Đ", "D"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def nhom_tinh(*texts: str) -> str | None:
    blob = " ".join(_plain(t) for t in texts if t)
    return next((g for pat, g in NHOM_THEO_CONG_NANG if re.search(pat, blob)), None)


def _num_eq(a, b) -> bool:
    try:
        return abs(float(a) - float(b)) <= max(0.01, 0.002 * abs(float(b)))
    except (TypeError, ValueError):
        return str(a).strip().upper() == str(b).strip().upper()


def _bbox_of(quote: str, page: int | None, pdf: Path | None, cache: dict) -> list[float] | None:
    """Vị trí 0–1 của dòng chữ vector chứa câu căn cứ (chỉ có với nguồn vector)."""
    if not (pdf and page and quote):
        return None
    if page not in cache:
        import pymupdf
        from ..pdf.render import vector_text
        with pymupdf.open(pdf) as doc:
            r = doc[page - 1].rect
        cache[page] = (r.width, r.height, vector_text(pdf, page))
    W, H, lines = cache[page]
    head = quote.split(" / ")[0].split(" | ")[0].strip()[:40]
    for ln in lines:
        if head and head in ln["text"]:
            x0, y0, x1, y1 = ln["bbox"]
            return [round(x0 / W, 4), round(y0 / H, 4), round(x1 / W, 4), round(y1 / H, 4)]
    return None


def cell(fv: dict, claude: dict | None = None, pdf: Path | None = None, cache: dict | None = None) -> tuple[list, str]:
    """fv: 1 trường của project_info (value/page/text/method/status/candidates). claude: {gia_tri, trang} Claude đọc ảnh.
    -> (ô dữ liệu, nguyên văn căn cứ)."""
    cache = {} if cache is None else cache
    st, val, page, method = fv.get("status"), fv.get("value"), fv.get("page"), fv.get("method")
    if isinstance(val, list):           # project.yaml cho phép danh sách (vd nhom_nha: [F5.2])
        val = "; ".join(map(str, val)) if val else None
    if claude is not None:
        cv, cp = claude["gia_tri"], claude.get("trang")
        if val is not None and _num_eq(val, cv) or any(_num_eq(c["value"], cv) for c in fv.get("candidates", [])):
            return [cv, cp, None, "H"], f"Claude đọc ảnh tr.{cp} khớp Gemini"
        return [cv, cp, None, "M"], f"Claude đọc ảnh tr.{cp}; Gemini đọc {val}"
    if st == "confirmed":
        return [val, page, None, "H"], fv.get("text", "")
    if st == "conflict" or val is None:
        return [None, None, None, "L"], ""
    if method == "vector" or any(c.get("method") == "vector" and _num_eq(c["value"], val) for c in fv.get("candidates", [])):
        q = fv.get("text", "")
        return [val, page, _bbox_of(q, page, pdf, cache), "H"], q
    if method == "tinh_toan":
        return [val, page, None, "M"], fv.get("text", "")
    pages = {c["page"] for c in fv.get("candidates", []) if _num_eq(c["value"], val) and c.get("page")}
    return [val, page, None, "M" if len(pages) >= 2 else "L"], fv.get("text", "")


def _claude_reads(out_dir: Path) -> dict:
    """claude_doc_anh.json: [{hm, truong (khoá project_info), gia_tri, trang, bang}] — giá trị Claude đọc trên ảnh cắt."""
    f = out_dir / "claude_doc_anh.json"
    if not f.exists():
        return {}
    return {(r["hm"], r["truong"]): r for r in json.loads(f.read_text(encoding="utf-8"))}


def build_facts(info: dict, out_dir: Path | None = None, pdf: Path | None = None) -> dict:
    reads = _claude_reads(out_dir) if out_dir else {}
    cache: dict = {}
    hms = []
    for i, (ten, fields) in enumerate(info.get("hang_muc", {}).items(), 1):
        h = {"id": f"HM{i:02d}", "ten": [ten, None, None, "H"], "evid": {}}
        for src, dst in FIELDS.items():
            c, q = cell(fields.get(src, {}), reads.get((ten, src)), pdf, cache)
            h[dst] = c
            if q:
                h["evid"][dst] = q
        cn = h["cong_nang"][0] or ""
        for src, dst in DUAL.items():
            c, q = cell(fields.get(src, {}), reads.get((ten, src)), pdf, cache)
            tinh = nhom_tinh(ten, cn) if dst == "nhom_nha" else None
            h[dst] = {"ban_ve": c, "tinh": tinh}
            if q:
                h["evid"][dst] = q
        hms.append(h)
    kd = info.get("khu_dat", {})
    return {
        "schema": "project_facts/1",
        "pdf": (info.get("meta") or {}).get("pdf"),
        "ten_cong_trinh": cell(kd.get("ten_cong_trinh", {}))[0],
        "dt_khu_dat_m2": cell(kd.get("dien_tich_khu_dat", {}))[0],
        "hang_muc_chinh": info.get("hang_muc_chinh"),
        "hang_muc": hms,
        "kiem_tra": logic_checks(hms),
    }


def _v(c):
    return (c.get("ban_ve") if isinstance(c, dict) else c)[0]


def _f(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def logic_checks(hms: list[dict]) -> list[dict]:
    """Kiểm tra logic tự động trước Cổng 1. muc: loi (chắc chắn sai) | canh_bao (bất thường, cần xem)."""
    out = []

    def add(h, muc, truong, msg):
        out.append({"hm": h["id"], "ten": h["ten"][0], "muc": muc, "truong": truong, "noi_dung": msg})

    for h in hms:
        noi, nha = _f(_v(h["so_tang_noi"])), _f(_v(h["so_tang_nha"]))
        cao, pccc = _f(_v(h["cao_cong_trinh_m"])), _f(_v(h["cao_pccc_m"]))
        dxd, dsan, kt = _f(_v(h["dt_xay_dung_m2"])), _f(_v(h["dt_san_tong_m2"])), _f(_v(h["khoi_tich_m3"]))
        nb, nt = _v(h["nhom_nha"]), h["nhom_nha"]["tinh"]
        if pccc and cao and pccc > cao + 0.01:
            add(h, "loi", "cao_pccc_m", f"chiều cao PCCC {pccc:g} m > chiều cao công trình {cao:g} m")
        if dxd and dsan and dsan + 0.01 < dxd:
            add(h, "loi", "dt_san_tong_m2", f"tổng diện tích sàn {dsan:g} m² < diện tích xây dựng {dxd:g} m²")
        if noi == 1 and dxd and dsan and dsan > dxd * 1.3:
            add(h, "canh_bao", "so_tang_noi", f"1 tầng nhưng tổng sàn {dsan:g} m² > 1,3 × diện tích xây dựng {dxd:g} m²")
        if noi and nha and nha < noi:
            add(h, "loi", "so_tang_nha", f"số tầng nhà {nha:g} < số tầng nổi {noi:g} (1.4.50 tính cả tầng nổi)")
        if kt and dxd and cao and kt > dxd * cao * 1.15:
            add(h, "canh_bao", "khoi_tich_m3", f"khối tích {kt:g} m³ > diện tích XD × chiều cao ({dxd * cao:.0f} m³)")
        if nb and nt and str(nb).split(";")[0].strip() != nt:
            add(h, "canh_bao", "nhom_nha", f"bản vẽ ghi {nb}, công năng gợi ý {nt} (Bảng 6)")
        grp = nb or nt
        if grp and str(grp).startswith("F5") and not _v(h["hang_no"]):
            add(h, "loi" if nb else "canh_bao", "hang_no", f"nhóm {grp}{'' if nb else ' (theo công năng)'} bắt buộc có hạng nguy hiểm cháy nổ")
    return out


def gate1_md(facts: dict) -> str:
    """Báo cáo ngắn cho Cổng 1: trường quyết định chưa H, mâu thuẫn, kiểm tra logic. Claude đọc file này + ảnh cắt."""
    lines = [f"# Cổng 1 — {facts.get('ten_cong_trinh', [None])[0] or ''}", "",
             "Độ tin cậy: H rõ · M hai nguồn/lấy theo Claude · L chỉ Gemini 1 trang · — không đọc được", "",
             "| HM | Tên | " + " | ".join(QUYET_DINH) + " |", "|---|---|" + "---|" * len(QUYET_DINH)]
    for h in facts["hang_muc"]:
        row = []
        for k in QUYET_DINH:
            c = h[k]["ban_ve"] if isinstance(h[k], dict) else h[k]
            s = "—" if c[0] is None else f"{c[0]} ({c[3]}{', tr.' + str(c[1]) if c[1] else ''})"
            if isinstance(h[k], dict) and h[k].get("tinh"):
                s += f" · tính {h[k]['tinh']}"
            row.append(s)
        lines.append(f"| {h['id']} | {h['ten'][0]} | " + " | ".join(row) + " |")
    ks = facts.get("kiem_tra", [])
    lines += ["", f"## Kiểm tra logic ({len(ks)})"] + [f"- [{k['muc']}] {k['hm']} {k['ten']} — {k['noi_dung']}" for k in ks]
    lines += ["", "Kết luận từng trường vào `verdict.json` (skill `cong-claude`): Đúng / Sửa / Đọc lại."]
    return "\n".join(lines) + "\n"
