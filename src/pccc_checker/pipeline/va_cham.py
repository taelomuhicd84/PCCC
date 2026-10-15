"""Va chạm — chỗ bản vẽ tự mâu thuẫn (cùng một thông số, các trang/bảng ghi khác nhau) -> `va_cham.json` + PDF ghi chú.

Nguồn (gộp, trùng (hạng mục, trường) thì nguồn trước thắng):
  1. nghi_ngo.json `mau_thuan_tren_ban_ve`  — Claude đã xác nhận (Cổng 1)                    loai = ban_ve
  2. project_info.json trường `conflict`      — script thấy các trang ghi khác nhau
     (>= 2 giá trị có nguồn không phải Gemini -> ban_ve; còn Gemini -> doc_lech, Claude xem ảnh rồi bỏ/giữ)
  3. project_facts.json `kiem_tra` giữa 2 trường (chiều cao PCCC > chiều cao nhà, sàn < xây dựng…)  loai = logic
Mỗi giá trị có 1 vị trí {trang, bbox 0–1 theo trang đang hiển thị, cach}:
  vector   : tìm thấy câu/số trong lớp chữ (chắc chắn)
  vector?  : số xuất hiện nhiều chỗ trên trang -> lấy chỗ đầu, Claude kiểm
  vung_anh : số nằm trong bảng dán ảnh -> khung = cả ảnh (`anh` = số thứ tự ảnh, khớp crops/pNN_bangK.png)
  claude   : Claude chỉ vị trí (va_cham_claude.json)
  trang    : không định vị được -> không vẽ, chỉ liệt kê trong Note phản hồi.docx
Khung trên PDF = comment → rectangle, chỉ vẽ khi vị trí chính xác (bbox ≤ 15 % trang); nội dung ghi thẳng số liệu va chạm.
nghi_ngo.json `gia_tri` = {"tr.7,11": giá trị, ...} (KHÓA = nơi ghi, GIÁ TRỊ = số liệu).
Claude sửa/bổ sung bằng `va_cham_claude.json`:
  [{"vt": "VC-002.1", "bbox": [x0,y0,x1,y1]}                        bbox 0–1 của trang
   {"vt": "VC-002.1", "anh": 2, "bbox_trong_anh": [x0,y0,x1,y1]}    bbox 0–1 trong ảnh cắt pNN_bang2.png
   {"id": "VC-004", "bo": true, "ly_do": "Gemini đọc lệch, ảnh bảng ghi 600"}]
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pymupdf

LABEL = {
    "so_tang": "số tầng", "so_tang_noi": "số tầng nổi", "so_tang_nha": "số tầng nhà", "dien_tich": "diện tích",
    "dien_tich_xay_dung": "diện tích xây dựng", "dt_xay_dung_m2": "diện tích xây dựng",
    "tong_dien_tich_san": "tổng diện tích sàn", "dt_san_tong_m2": "tổng diện tích sàn",
    "chieu_cao_cong_trinh": "chiều cao công trình", "cao_cong_trinh_m": "chiều cao công trình",
    "chieu_cao_pccc": "chiều cao PCCC", "cao_pccc_m": "chiều cao PCCC", "khoi_tich": "khối tích",
    "khoi_tich_m3": "khối tích", "bac_chiu_lua": "bậc chịu lửa", "nhom_nha": "nhóm nhà",
    "hang_chay_no": "hạng nguy hiểm cháy nổ", "cap_nguy_hiem_chay_ket_cau": "cấp nguy hiểm cháy kết cấu",
}
# kiểm tra logic giữa 2 trường -> 2 vị trí cần ghi chú
PAIRS = {"cao_pccc_m": ["cao_pccc_m", "cao_cong_trinh_m"], "dt_san_tong_m2": ["dt_san_tong_m2", "dt_xay_dung_m2"],
         "so_tang_nha": ["so_tang_nha", "so_tang_noi"], "khoi_tich_m3": ["khoi_tich_m3", "dt_xay_dung_m2", "cao_cong_trinh_m"],
         "so_tang_noi": ["so_tang_noi", "dt_san_tong_m2", "dt_xay_dung_m2"]}
COLOR = (1.0, 0.45, 0.0)
MAX_HIT = 5
MIN_TOK = 3                    # số/chữ ngắn hơn -> không dò trong lớp chữ (vd số tầng '2')
LAM_TRON = 0.005               # các số lệch <= 0,5% -> làm tròn, không phải va chạm


def _load(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _same(a, b) -> bool:
    try:
        return abs(float(a) - float(b)) < 1e-6
    except (TypeError, ValueError):
        return str(a).strip().upper() == str(b).strip().upper()


def _pages_in(label: str) -> list[int]:
    m = re.search(r"tr\.?\s*([\d,\s\-–]+)", label)
    if not m:
        return []
    out = []
    for part in re.split(r"[,\s]+", m.group(1).strip()):
        a = re.split(r"[-–]", part)
        if a[0].isdigit():
            out += list(range(int(a[0]), int(a[-1]) + 1)) if len(a) > 1 and a[-1].isdigit() else [int(a[0])]
    return out


# ------------------------------------------------------------------ thu thập
def from_nghi_ngo(nn: dict) -> list[dict]:
    out = []
    for m in nn.get("mau_thuan_tren_ban_ve", []):
        gv = m.get("gia_tri")
        if not isinstance(gv, dict):
            continue
        trang = m.get("trang") or []
        vals = []
        for src, v in gv.items():
            pages = _pages_in(src) or trang[:1]
            vals.append({"gia_tri": v, "nguon": src, "trang": pages[0] if pages else None, "text": None})
        out.append({"hm": m.get("hang_muc"), "truong": m.get("truong"), "loai": "ban_ve", "nguon": "nghi_ngo.json",
                    "ghi_chu": m.get("ghi_chu") or m.get("nguyen_van") or "", "gia_tri": vals})
    return out


def from_project_info(info: dict) -> list[dict]:
    out = []
    secs = [(hm, fs) for hm, fs in (info.get("hang_muc") or {}).items()] + [(None, info.get("khu_dat") or {})]
    for hm, fs in secs:
        for k, fv in fs.items():
            if fv.get("status") != "conflict":
                continue
            groups: list[dict] = []
            for c in fv.get("candidates") or []:
                g = next((g for g in groups if _same(g["gia_tri"], c["value"])), None)
                if g is None:
                    groups.append(g := {"gia_tri": c["value"], "cands": []})
                g["cands"].append(c)
            if len(groups) < 2:
                continue
            vals = []
            for g in groups:
                c = next((c for c in g["cands"] if c.get("method") != "gemini"), g["cands"][0])
                vals.append({"gia_tri": g["gia_tri"], "nguon": c.get("method"), "trang": c.get("page"),
                             "text": c.get("text"), "trang_khac": sorted({x["page"] for x in g["cands"]} - {c.get("page")})})
            ban_ve = sum(any(c.get("method") != "gemini" for c in g["cands"]) for g in groups) >= 2
            out.append({"hm": hm, "truong": k, "loai": "ban_ve" if ban_ve else "doc_lech", "nguon": "project_info.json",
                        "ghi_chu": "" if ban_ve else "có giá trị chỉ Gemini đọc — xem ảnh, Gemini đọc lệch thì bỏ",
                        "gia_tri": vals})
    return out


def from_facts(facts: dict) -> list[dict]:
    hms = {h["id"]: h for h in facts.get("hang_muc", [])}
    out = []
    for k in facts.get("kiem_tra", []):
        h = hms.get(k["hm"])
        if not h or k["truong"] not in PAIRS:
            continue
        vals = []
        for f in PAIRS[k["truong"]]:
            c = h.get(f)
            c = c.get("ban_ve") if isinstance(c, dict) else c
            if c and c[0] is not None:
                vals.append({"gia_tri": c[0], "nguon": LABEL.get(f, f), "trang": c[1], "text": (h.get("evid") or {}).get(f),
                             "bbox": c[2]})
        if len(vals) >= 2:
            out.append({"hm": k["ten"], "truong": k["truong"], "loai": "logic", "nguon": "project_facts.json",
                        "ghi_chu": k["noi_dung"], "gia_tri": vals})
    return out


def _lam_tron(vals: list) -> bool:
    try:
        f = [float(v) for v in vals]
    except (TypeError, ValueError):
        return False
    return len(f) >= 2 and max(f) - min(f) <= LAM_TRON * max(abs(x) for x in f)


def _key(hm, truong) -> tuple:
    from ..project_info import _hm_key
    t = {"so_tang": "so_tang_noi", "dien_tich": "dien_tich_xay_dung"}.get(truong, truong)
    return (_hm_key(hm or ""), t)


def collect(out: Path) -> list[dict]:
    items, seen = [], set()
    for part in (from_nghi_ngo(_load(out / "nghi_ngo.json", {})),
                 from_project_info(_load(out / "project_info.json", {})),
                 from_facts(_load(out / "project_facts.json", {}))):
        for it in part:
            k = _key(it["hm"], it["truong"]) + ((it["loai"],) if it["loai"] == "logic" else ())
            if k in seen:
                continue
            seen.add(k)
            items.append(it)
    for it in items:
        if _lam_tron([v["gia_tri"] for v in it["gia_tri"]]) and it["loai"] != "logic":
            it["bo"] = "làm tròn (lệch ≤ 0,5%)"
    for i, it in enumerate(items, 1):
        it["id"] = f"VC-{i:03d}"
        for j, v in enumerate(it["gia_tri"], 1):
            v["vt"] = f"{it['id']}.{j}"
    return items


# ------------------------------------------------------------------ định vị
def _tokens(v) -> list[str]:
    """Các cách viết của 1 giá trị trên bản vẽ: 2000 -> 2000, 2.000, 2 000; 11.425 -> 11,425 / 11.425."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        f = float(v)
        if f.is_integer():
            n = int(f)
            s = {str(n), f"{n:,}".replace(",", "."), f"{n:,}".replace(",", " ")}
        else:
            t = f"{f:g}"
            s = {t, t.replace(".", ",")}
            ip, dp = t.split(".")
            if int(ip) >= 1000:
                s |= {f"{int(ip):,}".replace(",", ".") + "," + dp, f"{int(ip):,}".replace(",", " ") + "," + dp}
        return sorted(s, key=len, reverse=True)
    s = str(v).strip()
    out = [s] if len(s) >= MIN_TOK else []
    for m in re.findall(r"\d[\d.,]*\d|\d", s):          # '3000 m², 13,7 m, 36.510 m³' -> từng số (viết kiểu VN)
        x = m.replace(".", "").replace(",", ".") if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", m) else m.replace(",", ".")
        try:
            out += [t for t in _tokens(float(x)) if t not in out]
        except ValueError:
            pass
    return out


def _num_in(tok: str, line: str) -> bool:
    return bool(re.search(rf"(?<![\d.,]){re.escape(tok)}(?![\d]|[.,]\d)", line, re.I))


def _norm_rect(r: pymupdf.Rect, page) -> list[float]:
    W, H = page.rect.width, page.rect.height
    return [round(max(0, r.x0 / W), 4), round(max(0, r.y0 / H), 4), round(min(1, r.x1 / W), 4), round(min(1, r.y1 / H), 4)]


def locate(items: list[dict], pdf: Path, page_index: list[dict] | None = None) -> None:
    from ..pdf.render import _table_images, image_rect, vector_text
    idx = {p["trang"]: p for p in page_index or []}
    cache: dict[int, list] = {}
    with pymupdf.open(pdf) as doc:
        for it in items:
            for v in it["gia_tri"]:
                p = v.get("trang")
                if not p or p > doc.page_count:
                    v["vi_tri"] = {"trang": p, "bbox": None, "cach": "trang"}
                    continue
                page = doc[p - 1]
                if p not in cache:
                    cache[p] = vector_text(pdf, p)
                lines = cache[p]
                hit = []
                quote = re.sub(r"\s+", " ", str(v.get("text") or "")).strip()
                if len(quote) >= 8:
                    hit = [t for t in lines if quote[:40].upper() in re.sub(r"\s+", " ", t["text"]).upper()]
                if not hit:
                    for tok in [t for t in _tokens(v["gia_tri"]) if len(t) >= MIN_TOK]:   # '2', 'IV' trùng khắp trang
                        hit = [t for t in lines if (_num_in(tok, t["text"]) if tok[0].isdigit() else tok.upper() in t["text"].upper())]
                        if hit:
                            break
                    if len(hit) > MAX_HIT:                  # số ngắn ('2', 'IV') trùng khắp trang -> không định vị
                        hit = []
                if hit:
                    r = pymupdf.Rect(hit[0]["bbox"]) * page.rotation_matrix      # chữ theo trang chưa xoay -> trang hiển thị
                    v["vi_tri"] = {"trang": p, "bbox": _norm_rect(r, page), "cach": "vector" if len(hit) == 1 else "vector?",
                                   **({"so_cho": len(hit)} if len(hit) > 1 else {})}
                    continue
                if v.get("bbox"):
                    v["vi_tri"] = {"trang": p, "bbox": v["bbox"], "cach": "facts"}
                    continue
                imgs = _table_images(page)
                if imgs:
                    boxes = [_norm_rect(image_rect(page, im), page) for im in imgs]
                    v["vi_tri"] = {"trang": p, "bbox": boxes[0] if len(boxes) == 1 else None, "cach": "vung_anh",
                                   "anh": 1 if len(boxes) == 1 else None, "so_anh": len(boxes),
                                   "crops": [f"crops/p{p:02d}_bang{k}.png" for k in range(1, len(boxes) + 1)]}
                    continue
                v["vi_tri"] = {"trang": p, "bbox": None, "cach": "trang",
                               **({"luong": idx[p]["luong"]} if p in idx else {})}


def apply_claude(items: list[dict], fixes: list[dict], pdf: Path) -> list[str]:
    """va_cham_claude.json -> sửa vị trí / bỏ va chạm. Trả về nhật ký."""
    from ..pdf.render import _table_images, image_rect
    log = []
    by_vt = {v["vt"]: (it, v) for it in items for v in it["gia_tri"]}
    by_id = {it["id"]: it for it in items}
    with pymupdf.open(pdf) as doc:
        for f in fixes:
            if f.get("bo") and f.get("id") in by_id:
                by_id[f["id"]]["bo"] = f.get("ly_do") or True
                log.append(f"{f['id']}: bỏ ({f.get('ly_do', '')})")
                continue
            if f.get("vt") not in by_vt:
                log.append(f"không có vị trí {f.get('vt')} — bỏ qua")
                continue
            _, v = by_vt[f["vt"]]
            p = f.get("trang") or v["vi_tri"]["trang"]
            page = doc[p - 1]
            if f.get("bbox_trong_anh") and f.get("anh"):
                im = _table_images(page)[f["anh"] - 1]
                r = image_rect(page, im)
                x0, y0, x1, y1 = f["bbox_trong_anh"]
                rr = pymupdf.Rect(r.x0 + x0 * r.width, r.y0 + y0 * r.height, r.x0 + x1 * r.width, r.y0 + y1 * r.height)
                bbox = _norm_rect(rr, page)
            elif f.get("anh"):
                bbox = _norm_rect(image_rect(page, _table_images(page)[f["anh"] - 1]), page)
            else:
                bbox = f.get("bbox")
            v["vi_tri"] = {"trang": p, "bbox": bbox, "cach": "claude"}
            log.append(f"{f['vt']}: tr.{p} {bbox}")
    return log


def can_claude(items: list[dict]) -> list[str]:
    """Vị trí Claude cần chỉ: chưa có bbox, nhiều chỗ khớp, hoặc va chạm doc_lech (cần xem ảnh để bỏ/giữ)."""
    out = []
    for it in items:
        if it.get("bo"):
            continue
        if it["loai"] == "doc_lech":
            out.append(f"{it['id']}: doc_lech — xem ảnh, bỏ nếu Gemini đọc sai")
        for v in it["gia_tri"]:
            vt = v.get("vi_tri") or {}
            if vt.get("cach") in ("trang", "vector?") or (vt.get("cach") == "vung_anh"):
                out.append(f"{v['vt']}: tr.{vt.get('trang')} {vt.get('cach')}"
                           + (f" ({vt['so_anh']} ảnh: {', '.join(vt['crops'])})" if vt.get("crops") else ""))
    return out


# ------------------------------------------------------------------ xuất
def _so(x):
    try:
        return float(str(x).replace(",", "."))
    except (TypeError, ValueError):
        return None


def chenh(it: dict) -> str:
    """Các giá trị đều là số -> 'lệch X' (cao nhất - thấp nhất); không thì rỗng."""
    n = [_so(v["gia_tri"]) for v in it["gia_tri"]]
    if len(n) >= 2 and all(x is not None for x in n) and max(n) != min(n):
        return f"lệch {max(n) - min(n):g}"
    return ""


def mo_ta(it: dict, v: dict | None = None) -> str:
    """Nội dung 1 va chạm kèm SỐ LIỆU. Có `v`: nêu giá trị tại vị trí này rồi các giá trị còn lại."""
    ten = LABEL.get(it["truong"], it["truong"])
    ch = chenh(it)
    if v is None:
        s = f"{ten}: " + " ≠ ".join(f"{x['gia_tri']} [tr.{x.get('trang')}]" for x in it["gia_tri"])
    else:
        khac = "; ".join(f"{o['gia_tri']} (tr.{o.get('trang')})" for o in it["gia_tri"] if o is not v)
        s = f"{ten}: ghi {v['gia_tri']} tại đây ≠ {khac}"
    return s + (f" — {ch}" if ch else "")


def chinh_xac(bbox) -> bool:
    """bbox chỉ 1 chỗ (không phải cả trang / cả bảng ảnh)."""
    if not bbox:
        return False
    x0, y0, x1, y1 = bbox
    return (x1 - x0) * (y1 - y0) <= 0.15


def annotate(pdf: Path, items: list[dict], pdf_out: Path) -> int:
    """Mỗi vị trí va chạm chính xác = 1 ghi chú dạng comment → rectangle (khung chữ nhật, nội dung ở popup).
    Không ghi biểu tượng Note phụ, không ghi trùng: cùng khung gộp nội dung, cùng nội dung chỉ ghi 1 lần.
    Vị trí chưa chỉ được chính xác (cả bảng ảnh / chỉ có trang) KHÔNG vẽ — liệt kê trong Note phản hồi.docx
    (Claude chỉ vị trí bằng va_cham_claude.json rồi chạy lại)."""
    doc = pymupdf.open(pdf)
    groups: dict[tuple, dict] = {}
    for it in items:
        if it.get("bo"):
            continue
        for v in it["gia_tri"]:
            vt = v.get("vi_tri") or {}
            p = vt.get("trang")
            if not p or p > doc.page_count or not chinh_xac(vt.get("bbox")):
                continue
            g = groups.setdefault((p, tuple(round(x, 3) for x in vt["bbox"])), {"ma": [], "nd": []})
            nd = mo_ta(it, v)
            if nd not in g["nd"]:
                g["nd"].append(nd)
            g["ma"].append(v["vt"])
    n = 0
    for (p, bb), g in groups.items():
        page = doc[p - 1]
        W, H = page.rect.width, page.rect.height
        vis = pymupdf.Rect(bb[0] * W, bb[1] * H, bb[2] * W, bb[3] * H) + (-3, -3, 3, 3)
        r = (vis * page.derotation_matrix) & page.mediabox      # annot dùng toạ độ trang chưa xoay
        box = page.add_rect_annot(r)
        box.set_colors(stroke=COLOR)
        box.set_border(width=2)
        box.set_info(title="Va chạm " + ", ".join(g["ma"]), content="\n".join(g["nd"]))
        box.update(opacity=0.9)
        n += 1
    pdf_out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(pdf_out, garbage=3, deflate=True)
    doc.close()
    return n


def to_md(items: list[dict]) -> str:
    lines = ["# Va chạm trên bản vẽ", "",
             "Cùng một thông số, các trang/bảng ghi khác nhau. `cach`: vector (chắc) · vector? (nhiều chỗ, cần kiểm) · "
             "vung_anh (khung cả bảng ảnh) · claude (Claude chỉ) · trang (chưa định vị — ghi ở góc trang).", "",
             "| ID | Hạng mục | Thông số | Loại | Giá trị · nơi ghi · vị trí |", "|---|---|---|---|---|"]
    for it in items:
        vals = "<br>".join(f"{v['vt']}: **{v['gia_tri']}** — {v['nguon']} · tr.{v.get('trang')} · {(v.get('vi_tri') or {}).get('cach', '')}"
                           for v in it["gia_tri"])
        bo = f" ~~bỏ: {it['bo']}~~" if it.get("bo") else ""
        lines.append(f"| {it['id']} | {it['hm'] or 'khu đất'} | {LABEL.get(it['truong'], it['truong'])} | {it['loai']}{bo} | {vals} |")
    return "\n".join(lines) + "\n"
