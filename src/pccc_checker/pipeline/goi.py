"""Gói đối chiếu — script lọc bảng tra TRƯỚC khi Claude đọc, để Claude chỉ xét dòng thật sự cần phán đoán.

Vì sao: bảng tra chuyên đề rất dài (một loại hình ~100k token) nhưng phần lớn dòng không cần phán đoán:
  - dòng tiêu đề (không có quy định)                      -> bỏ, không ghi finding
  - dòng không có đối tượng (nhà 1 tầng mà hỏi thang…)    -> NA tự động (rules/dieu_kien.yaml)
  - dòng chỉ dẫn tới bảng số chưa chép vào bảng tra        -> XM tự động (không lấy số từ trí nhớ)
  - còn lại ("cần xét")                                    -> Claude đọc, kèm tóm tắt chữ bản vẽ đúng trang
Hạng mục giống hệt nhau (cùng khoá tra + cùng số liệu) gộp 1 gói; findings vẫn ghi riêng từng hạng mục.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from ..config import PROJECT_ROOT
from .chuyen_de import MUC

CHECKLISTS = PROJECT_ROOT / "rules" / "checklists"
DIEU_KIEN = PROJECT_ROOT / "rules" / "dieu_kien.yaml"
ROW = re.compile(r"^\|\s*([A-Z]{2,3}\d{0,2}-[A-Z]+-\d{3})\s*\|")
CAT_QD = 900            # cắt cột "Quy định" dài hơn ngần này; xem đủ bằng `dong <ID>`
SLUG = {nn: s for nn, s, *_ in MUC} | {s: s for _, s, *_ in MUC}
REF_ONLY = re.compile(r"^(theo\s+)?(bảng|phụ lục|điều|đ)\s*[\w.\-]+(\s*(,|và)?\s*(bảng|phụ lục)\s*[\w.\-]+)*"
                      r"(\s+(qcvn|tcvn|nđ|tt)[\w:/.\-]*)*(\s+(và\s+)?(sửa đổi|sđ)[\w :./\-]*)?\.?$", re.I)


KHO_BANG = PROJECT_ROOT / "knowledge" / "quy-chuan"
BANG_REF = re.compile(r"[Bb]ảng\s+([A-Z]\.?\d+[a-z]?|\d+[a-z]?)(?![\d.]*\d)([^|]{0,28})")


def cid(n: str) -> str:
    return n.replace(".", "").lower()


# quy chuẩn có bảng trong kho: mẫu nhận dạng ở chữ ngay sau "Bảng N" -> tiền tố id (file knowledge/quy-chuan/<tiền tố>-bang-<số>.md)
CHUAN_KHO = (("qcvn13", r"QCVN\s*13"), ("qcvn10", r"QCVN\s*10"), ("tcvn7568-14", r"TCVN\s*7568"))


def bang_refs(r: dict) -> list[str]:
    """Các bảng số mà dòng dẫn tới: '4', 'e3' (QCVN 06); 'qcvn13-3', 'tcvn7568-14-1' (chuẩn khác ĐÃ có trong kho knowled);
    'x5' (bảng của quy chuẩn khác chưa có trong kho)."""
    out = []
    for m in BANG_REF.finditer(" || ".join((r["qd"], r["dk"], r["luu_y"]))):
        n, sau = cid(m.group(1)), m.group(2)
        pre = next((p for p, rx in CHUAN_KHO if re.search(rx, sau)), None)
        if pre:
            out.append(f"{pre}-{n}")
        elif re.search(r"QCVN\s*(?!06)\d|TCVN|QCXDVN", sau):
            out.append("x" + n)
        else:
            out.append(n)
    out = list(dict.fromkeys(out))
    # "Bảng 3" (cột Quy định) + "Bảng 3 / QCVN 13" (cột Điều khoản) = cùng bảng: bỏ bản không nêu chuẩn
    return [i for i in out if not any(o != i and (o == "x" + i or o.endswith("-" + i)) for o in out)]


def bang_file(i: str) -> Path:
    for p, _ in CHUAN_KHO:
        if i.startswith(p + "-"):
            return KHO_BANG / f"{p}-bang-{i[len(p) + 1:]}.md"
    return KHO_BANG / f"qcvn06-bang-{i}.md"


def bang_co(i: str) -> bool:
    return not i.startswith("x") and bang_file(i).exists()


def bang_thieu(ids: list[str]) -> bool:
    """Có bảng chưa nạp / của quy chuẩn khác / chưa duyệt -> không được kết luận D/KD dựa vào dòng này."""
    return any(not bang_co(i) or "trang_thai: verified" not in bang_file(i).read_text(encoding="utf-8-sig")[:600] for i in ids)


def bang_text(ids: list[str], toi_da: int = 5200) -> str:
    L = []
    for i in dict.fromkeys(ids):
        if not bang_co(i):
            continue
        s = bang_file(i).read_text(encoding="utf-8-sig")
        ok = "trang_thai: verified" in s[:600]
        tit = next((ln[9:].strip() for ln in s.splitlines() if ln.startswith("tieu_de:")), i)
        body = s.split("\n---\n", 1)[-1].strip()
        body = body if len(body) <= toi_da else body[:toi_da] + f" …[cắt — đọc đủ: knowled doc {bang_file(i).stem}]"
        L.append(f"### {tit} [{'verified' if ok else 'CHỜ DUYỆT: chỉ để tham khảo, không kết luận D/KD'}]\n{body}")
    return "\n\n".join(L)


def tok(s: str) -> int:
    return int(len(s) / 3.2)


def _clean(s: str) -> str:
    s = re.sub(r"<br\s*/?>", " / ", s or "")
    return re.sub(r"\s+", " ", s).strip(" /")


def parse_rows(path: Path) -> list[dict]:
    """Bảng .md -> [{id, tt, nd, luu_y, qd, dk, chain}]; ô nhiều dòng được ghép lại."""
    lines, cur = [], None
    for ln in path.read_text(encoding="utf-8-sig").splitlines():
        if ROW.match(ln):
            cur = [ln]
            lines.append(cur)
        elif cur is not None and ln.strip() and not ln.startswith("---"):
            cur.append(ln)
    rows, chain = [], []
    for blk in lines:
        txt = " ".join(blk).strip()
        txt = txt[1:] if txt.startswith("|") else txt
        txt = txt[:-1] if txt.endswith("|") else txt
        c = [x.strip() for x in re.split(r"\s\|\s", txt)]
        c = c[:5] + [" | ".join(c[5:])] if len(c) > 6 else c + [""] * (6 - len(c))
        r = dict(id=c[0], tt=c[1], nd=_clean(c[2]), luu_y=_clean(c[3]), qd=_clean(c[4]), dk=_clean(c[5]))
        rows.append(r)
    return rows


def files_for(bang: str, cd: str) -> list[Path]:
    """rules/checklists/<bang>/NN-slug[.p].md của chuyên đề (nhiều phần -> nhiều file)."""
    slug = SLUG.get(cd, cd)
    nn = next(n for n, s, *_ in MUC if s == slug)
    return sorted((CHECKLISTS / bang).glob(f"{nn}-{slug}*.md"))


def tom_tat_hm(h: dict) -> dict:
    """project_facts hạng mục -> số liệu đủ để lọc điều kiện + khoá nhóm."""
    def v(k):
        c = h.get(k)
        c = c.get("ban_ve") if isinstance(c, dict) else c
        return c[0] if isinstance(c, list) and c else None
    noi, ham, nha = v("so_tang_noi"), v("so_tang_ham"), v("so_tang_nha")
    co_ham = None
    if ham is not None:
        co_ham = ham > 0
    elif noi is not None and nha is not None:
        co_ham = nha > noi
    return dict(hm=h["id"], ten=h["ten"][0], tang_noi=noi, co_ham=co_ham, cao=v("cao_pccc_m") or v("cao_cong_trinh_m"),
                nhom=v("nhom_nha"), bac=v("bac_chiu_lua"), s=v("cap_s"), hang=v("hang_no"), dt=v("dt_xay_dung_m2"))


def khoa_nhom(t: dict) -> tuple:
    return tuple(t[k] for k in ("tang_noi", "co_ham", "cao", "nhom", "bac", "s", "hang"))


def _khi(khi: dict, t: dict) -> bool:
    """Điều kiện đúng CHẮC CHẮN (số liệu thiếu -> không cắt)."""
    for k, want in khi.items():
        if k == "co_ham" and t["co_ham"] is not want:
            return False
        if k == "tang_noi_max" and not (t["tang_noi"] is not None and t["tang_noi"] <= want):
            return False
        if k == "tang_noi_min" and not (t["tang_noi"] is not None and t["tang_noi"] >= want):
            return False
    return True


def luat_dieu_kien() -> list[dict]:
    return yaml.safe_load(DIEU_KIEN.read_text(encoding="utf-8")) if DIEU_KIEN.exists() else []


def phan_loai(r: dict, t: dict, dk: list[dict], lines: dict[int, list[str]] | None = None) -> tuple[str, str]:
    """-> (TD tiêu đề | NA | XM | XET, lý do). `lines`: chữ vector cả hồ sơ (cho mục dieu_kien có tu_khoa)."""
    if not r["qd"] and not r["luu_y"] and not r["dk"]:
        return "TD", "tiêu đề"
    for d in dk:
        if not re.search(d["nd"], r["nd"], re.I) or (d.get("khong_nd") and re.search(d["khong_nd"], r["nd"], re.I)):
            continue
        if "khi" in d and _khi(d["khi"], t):
            return "NA", f"{d['id']}: {d['ly_do']}"
        if "tu_khoa" in d and lines and not thieu_chu(lines) and not co_tu_khoa(lines, d["tu_khoa"]):
            return "NA", f"{d['id']}: không thấy chữ «{d['tu_khoa'][:40]}» ở {len(lines)} trang vector — {d['ly_do']}"
    refs = bang_refs(r)
    co_bang = any(bang_co(i) for i in refs)
    if not r["qd"] and not r["luu_y"]:
        if co_bang:
            return "XET", ""
        return "XM", f"dòng chỉ có điều khoản dẫn ({r['dk'][:60]}), bảng tra không chép nội dung/số liệu; bảng {', '.join(refs) or '?'} chưa có trong kho knowled"
    if r["qd"] and (REF_ONLY.match(r["qd"]) or (r["qd"].endswith(":") and len(r["qd"]) < 200)):
        if co_bang:
            return "XET", ""
        return "XM", f"quy định chỉ dẫn tới «{r['qd'][:70]}» — bảng số liệu {', '.join(refs) or '?'} chưa có trong kho knowled"
    return "XET", ""


def _cat(s: str, n: int, id_: str) -> str:
    return s if len(s) <= n else s[:n].rstrip() + f" …[cắt {len(s) - n} ký tự — xem đủ: dong {id_}]"


def dong_day_du(id_: str) -> str | None:
    for f in CHECKLISTS.rglob("*.md"):
        for r in parse_rows(f):
            if r["id"] == id_:
                return (f"{r['id']} · {r['nd']}\nLƯU Ý: {r['luu_y']}\nQUY ĐỊNH: {r['qd']}\nĐIỀU KHOẢN: {r['dk']}\n[{f.relative_to(PROJECT_ROOT)}]")
    return None


# ---- chữ vector của bản vẽ -------------------------------------------------------------------------------------------
_BIEN = re.compile(r"^(?:\d+|[A-Za-z]'?|[\d.,+\-]+\s*(?:m|mm|M2|m2|M3|m3)?)$")


def doc_lines(pdf: Path) -> dict[int, list[str]]:
    """{trang: các dòng chữ vector} của cả hồ sơ (0 token)."""
    import fitz
    d = fitz.open(pdf)
    return {i + 1: [re.sub(r"\s+", " ", x).strip() for x in pg.get_text("text").splitlines()] for i, pg in enumerate(d)}


def chu_trang(lines: dict[int, list[str]], pages: list[int], toi_da: int = 1400) -> dict[int, str]:
    """Chữ của các trang cần đọc, bỏ khung tên (dòng lặp ở ≥ 30 % trang cả hồ sơ) và dòng chỉ là số/kích thước."""
    dem: dict[str, int] = {}
    for ls in lines.values():
        for x in set(ls):
            dem[x] = dem.get(x, 0) + 1
    lap = max(3, len(lines) * 0.3)
    out = {}
    for p in pages:
        keep, seen = [], set()
        for x in lines.get(p, []):
            if len(x) < 3 or _BIEN.match(x) or x in seen or dem.get(x, 0) >= lap:
                continue
            seen.add(x)
            keep.append(x)
        s = " | ".join(keep)
        out[p] = s[:toi_da] + ("…" if len(s) > toi_da else "")
    return out


def thieu_chu(lines: dict[int, list[str]]) -> bool:
    """Hồ sơ scan/ảnh nhiều (> 20 % trang không có chữ) -> không dám kết luận 'không thấy từ khoá'."""
    return bool(lines) and sum(1 for ls in lines.values() if not any(len(x) > 2 for x in ls)) > 0.2 * len(lines)


def co_tu_khoa(lines: dict[int, list[str]], rx: str) -> list[int]:
    return [p for p, ls in lines.items() if any(re.search(rx, x, re.I) for x in ls)]


# ---- kết quả gọn Claude ghi + bộ nhớ đệm ------------------------------------------------------------------------------
def khoa_cache(r: dict, t: dict, chu: str) -> str:
    import hashlib
    h = json.dumps([r["id"], r["nd"], r["luu_y"], r["qd"], r["dk"], khoa_nhom(t), chu, bang_text(bang_refs(r))], ensure_ascii=False)
    return hashlib.sha1(h.encode("utf-8")).hexdigest()[:14]


def doc_cache(gd: Path) -> dict:
    f = gd / "cache.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def doc_ket_qua(f: Path) -> list[dict]:
    """Dòng gọn: `ID | TT | trang | lý do | evid | x0,y0,x1,y1`  (evid, bbox chỉ cần cho KD)."""
    rows = []
    for ln in f.read_text(encoding="utf-8-sig").splitlines():
        if not ln.strip() or ln.lstrip().startswith("#"):
            continue
        c = [x.strip() for x in ln.split("|")] + [""] * 6
        if c[1] not in ("D", "KD", "XM", "NA"):
            raise ValueError(f"{f.name}: dòng «{ln[:60]}» — cột 2 phải là D | KD | XM | NA")
        tr = [int(x) for x in re.findall(r"\d+", c[2])]
        bb = [float(x) for x in re.findall(r"[\d.]+", c[5])][:4]
        rows.append(dict(rule=c[0], tt=c[1], trang=(tr[0] if len(tr) == 1 else tr) or None, ly_do=c[3], evid=c[4], bbox=bb or None))
    return rows




# ---- Gemini làm lượt đầu, script kiểm chứng, Claude chỉ xét phần còn nghi -----------------------------------------------
def pdf_trang(pdf: Path, pages: list[int]) -> bytes:
    """Gộp các trang cần đọc thành 1 PDF nhỏ (Gemini web chỉ nhận file PDF, không nhận ảnh)."""
    import fitz
    src, out = fitz.open(pdf), fitz.open()
    for p in pages:
        out.insert_pdf(src, from_page=p - 1, to_page=p - 1)
    return out.tobytes(deflate=True, garbage=3)


def doc_dong_xet(md: Path) -> list[str]:
    """Các dòng '- ID · ...' trong mục 'Cần Claude xét' của gói."""
    ls, on = [], False
    for ln in md.read_text(encoding="utf-8-sig").splitlines():
        if ln.startswith("## Cần Claude xét"):
            on = True
        elif on and ln.startswith("- "):
            ls.append(ln[2:])
    return ls


def doc_bang(f: Path) -> str:
    """File `<gói>.bang.md` (bảng số tham chiếu của gói) — chỉ gửi cho Gemini / đưa vào can-claude đúng bảng cần."""
    return f.read_text(encoding="utf-8-sig").strip() if f.exists() else ""


def prompt_gemini(so_lieu: str, pages: list[int], dong: list[str], bang: str = "") -> str:
    ban_do = ", ".join(f"trang {i + 1} của file = trang {p} hồ sơ gốc" for i, p in enumerate(pages))
    return (
        "Bạn là kỹ sư thẩm duyệt PCCC. File PDF đính kèm gồm các trang bản vẽ cần đối chiếu (" + ban_do + ").\n"
        f"Số liệu hạng mục (đã đọc trước): {so_lieu}\n\n"
        "Với MỖI dòng quy định bên dưới, đối chiếu CHỈ với chữ, ký hiệu và kích thước thấy trên bản vẽ đính kèm. "
        "KHÔNG dùng kiến thức ngoài dòng quy định; KHÔNG suy đoán số không có trên bản vẽ.\n"
        "Mỗi dòng trả lời ĐÚNG MỘT dòng, định dạng:\n"
        "ID | TT | trang gốc | lý do (≤ 25 từ) | trích NGUYÊN VĂN chữ trên bản vẽ làm căn cứ\n"
        "TT chỉ là một trong: D (bản vẽ ghi giá trị và ĐẠT), KD (bản vẽ ghi giá trị và VI PHẠM), "
        "XM (bản vẽ không ghi / không đọc rõ / không chắc), NA (hạng mục không có đối tượng của dòng này). "
        "D và KD bắt buộc có trích nguyên văn và trang gốc. Không markdown, không đánh số, không giải thích thêm.\n\n"
        "CÁC DÒNG QUY ĐỊNH:\n" + "\n".join(dong)
        + (("\n\nBẢNG SỐ THAM CHIẾU (nguyên văn quy chuẩn; dòng nào dẫn tới bảng này thì so với số trong bảng, không dùng số khác):\n" + bang) if bang else ""))


def _chuan(s: str) -> str:
    return re.sub(r"[\W_]+", "", (s or "").lower())


def phan_tich_gemini(text: str, ids: list[str], lines: dict[int, list[str]], can_bang: set[str] | None = None) -> dict[str, dict]:
    """Câu trả lời Gemini -> {ID: {tt, ly_do, trang, evid, nguon_tt}}.
    D chỉ giữ khi trích nguyên văn CÓ trong chữ vector của trang đã nêu (chống bịa); KD của Gemini luôn hạ XM để Claude xét."""
    van = {p: _chuan(" ".join(ls)) for p, ls in lines.items()}
    kq: dict[str, dict] = {}
    for ln in text.splitlines():
        c = [x.strip() for x in ln.strip().strip("`").split("|")]
        if len(c) < 3 or c[0] not in ids or c[0] in kq:
            continue
        tt = c[1].upper().replace("*", "").strip()
        tr = [int(x) for x in re.findall(r"\d+", c[2])]
        ly, ev = (c[3] if len(c) > 3 else ""), (c[4] if len(c) > 4 else "")
        kq[c[0]] = dict(tt=tt if tt in ("D", "KD", "XM", "NA") else "XM", ly_do=ly, trang=(tr[0] if tr else None), evid=ev, g=tt)
    for i in ids:
        k = kq.setdefault(i, dict(tt="XM", ly_do="Gemini không trả lời dòng này", trang=None, evid="", g=""))
        e = _chuan(k["evid"])
        if k["tt"] == "D" and i in (can_bang or ()):
            k["tt"], k["ly_do"] = "XM", f"[Gemini D nhưng dòng cần so với Bảng số chưa chép vào bảng tra] {k['ly_do']}"
        elif k["tt"] == "D":
            ok = bool(e) and len(e) >= 6 and k["trang"] in van and e in van[k["trang"]]
            if not ok:
                k["tt"], k["ly_do"] = "XM", f"[Gemini D nhưng trích dẫn không có trong chữ vector tr.{k['trang']}] {k['ly_do']}"
        elif k["tt"] == "KD":
            k["tt"], k["ly_do"] = "XM", f"[Gemini nghi KD — Claude xét] {k['ly_do']}"
        elif k["tt"] == "XM":
            k["ly_do"] = f"[Gemini XM] {k['ly_do']}"
    return kq
