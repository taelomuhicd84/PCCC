"""Nạp một tiêu chuẩn/quy chuẩn (PDF có lớp chữ, .docx, .doc) vào knowledge/quy-chuan/, mỗi phần một module để sửa riêng:

    python scripts/knowled_import_pdf.py "<file.pdf|.docx|.doc>" --ma qcvn13 --ten "QCVN 13:2018/BXD Gara ô-tô" [--tach 3] [--ghi-de]
    (.doc được Word chuyển sang .docx tạm; Word/docx cho bảng đúng bố cục hơn PDF — bảng không ô gộp -> verified)
    python scripts/knowled_import_pdf.py "<file.txt>"  --ma qcvn10 ...        # văn bản đã OCR (xem knowled_ocr_gemini.py): chỉ tách mục, không có bảng

- `<ma>-bang-<số>.md`  mỗi bảng có tiêu đề "Bảng N." (bảng nhiều trang được ghép; tiêu đề cột lặp bị bỏ). Mặc định `cho_duyet`
  (bố cục ô gộp có thể lệch) — so với PDF rồi `knowled duyet`.
- `<ma>-<số mục>.md`  mỗi mục đánh số tới cấp --tach (mặc định 3: 2.2.1…) kèm toàn bộ điều khoản con; chữ trong bảng được thay bằng
  dòng "[Bảng N → <ma>-bang-N]" để không lặp. `verified` vì chép nguyên văn từ lớp chữ PDF.
- Không ghi đè file đã có (giữ chỉnh sửa tay) trừ khi --ghi-de.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CAP = re.compile(r"^\s*Bảng\s+([A-Z]?\.?\d+[a-z]?)\s*[.\-–:]\s*(\S.*)$")
HEAD = re.compile(r"^((?:[A-Z]\.)?\d+(?:\.\d+){0,3})\.?\s{1,4}(\S.*)$")
PL = re.compile(r"^(?:PHỤ LỤC|Phụ lục)\s+([A-Z])\b[\s.:–\-]*(.*)$")


def bd(s: str) -> str:
    s = unicodedata.normalize("NFD", s.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def cid(n: str) -> str:
    return n.replace(".", "").lower()


def cl(c) -> str:
    return re.sub(r"\s+", " ", (c or "").replace("|", "/")).strip()


def pdf_parts(pdf: Path):
    """-> (dòng văn bản theo thứ tự đọc, chỗ bảng là marker [__BANG__:mã], {mã bảng: dict})."""
    import fitz
    d = fitz.open(pdf)
    lines: list[str] = []
    bang: dict[str, dict] = {}
    cap = None                                                  # (mã, số hiệu, tiêu đề, trang)
    for pn, pg in enumerate(d, 1):
        tabs = [(t.bbox, [[cl(c) for c in r] for r in t.extract()]) for t in pg.find_tables().tables]
        caps = []
        for ln in pg.get_text("text").splitlines():
            m = CAP.match(ln)
            if m:
                rs = pg.search_for(ln.strip()[:40])
                caps.append((rs[0].y0 if rs else 0, m))
        events = [(y, "c", m) for y, m in caps] + [(tb[1], "t", i) for i, (tb, _) in enumerate(tabs)]
        tab_cap: dict[int, str | None] = {}
        for y, kind, v in sorted(events, key=lambda e: (e[0], e[1] == "t")):
            if kind == "c":
                cap = (cid(v.group(1)), v.group(1), v.group(2).strip(), pn)
            elif cap and pn - cap[3] <= 1:
                bb = bang.setdefault(cap[0], dict(num=cap[1], title=cap[2], rows=[], blocks=0))
                rows = [r for r in tabs[v][1] if any(r)]
                if bb["blocks"] and rows and rows[0] == bb["rows"][0]:
                    rows = rows[1:]
                bb["rows"] += rows
                bb["blocks"] += 1
                tab_cap[v] = cap[0]
        placed: set[int] = set()
        for b in sorted(pg.get_text("blocks"), key=lambda b: (round(b[1]), b[0])):
            if b[6] != 0:
                continue
            inside = next((i for i, (tb, _) in enumerate(tabs) if i in tab_cap and b[1] >= tb[1] - 2 and b[3] <= tb[3] + 2 and b[0] >= tb[0] - 2 and b[2] <= tb[2] + 2), None)
            if inside is not None:
                if inside not in placed:
                    placed.add(inside)
                    mk = f"[__BANG__:{tab_cap.get(inside) or '?'}]"
                    if not lines or lines[-1] != mk:
                        lines.append(mk)
                continue
            lines += [x.strip() for x in b[4].splitlines() if x.strip()]
    return lines, bang


def doc_sang_docx(src: Path) -> Path:
    """.doc -> .docx tạm bằng Word (COM). Không ghi cạnh file nguồn."""
    import subprocess
    import tempfile
    out = Path(tempfile.mkdtemp(prefix="knowled_")) / (src.stem + ".docx")
    ps = (f"$w=New-Object -ComObject Word.Application;$w.Visible=$false;$w.DisplayAlerts=0;"
          f"$d=$w.Documents.Open('{src}',$false,$true);$d.SaveAs2('{out}',16);$d.Close($false);$w.Quit()")
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, capture_output=True, timeout=300)
    if not out.exists():
        raise SystemExit("Word không chuyển được .doc -> .docx")
    return out


CAP_D = re.compile(r"^\s*Bảng\s+([A-Z]?\.?\d+[a-z]?)\b\s*(?:[.\-–:]\s*(.*))?$", re.S)


def docx_parts(path: Path):
    """-> (dòng văn bản, marker [__BANG__:mã] ở chỗ bảng có tiêu đề, {mã: dict(num,title,rows,blocks,span)})."""
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    sys.path.insert(0, str(Path(__file__).parent))
    from knowled_import_qcvn import rows_of
    d = docx.Document(path)
    lines: list[str] = []
    bang: dict[str, dict] = {}
    cap, cap_i = None, -99
    pl, cnt = "", [0, 0, 0, 0]
    nz = lambda x: re.sub(r"\W+", "", x.lower())
    TOCRX = r"[….]{3,}\s*\d+\s*$|\s\d{1,3}$"
    titles: dict[str, str] = {}                      # tiêu đề phụ lục lấy từ mục lục (nhãn "Phụ lục A" trong thân là số tự động, không có trong chữ)
    for ch in d.element.body.iterchildren():
        if ch.tag.endswith("}p"):
            pr = Paragraph(ch, d)
            tt = re.sub(r"\s+", " ", pr.text).strip()
            mm = PL.match(tt)
            if mm and (pr.style.name.lower().startswith("toc") or re.search(TOCRX, tt)):
                titles.setdefault(mm.group(1), nz(re.sub(TOCRX, "", mm.group(2))))
    started: set[str] = set()
    for i, ch in enumerate(d.element.body.iterchildren()):
        if ch.tag.endswith("}p"):
            para = Paragraph(ch, d)
            t = re.sub(r"[ \t]*\n[ \t]*", " ", re.sub(r"[ \t]+", " ", para.text)).strip()
            if not t:
                continue
            mpl = PL.match(t)
            if mpl and (para.style.name.lower().startswith("toc") or re.search(TOCRX, t)):
                mpl = None                                           # dòng mục lục (có số trang cuối dòng), không phải tiêu đề phụ lục
            if not mpl and not para.style.name.lower().startswith("toc") and not re.search(TOCRX, t):
                for L, ti in titles.items():                         # đoạn trùng tiêu đề phụ lục trong mục lục -> mở phụ lục L
                    if L not in started and ti and nz(t).startswith(ti[:40]) and len(nz(t)) < len(ti) + 12:
                        t = f"PHỤ LỤC {L} {t}"
                        mpl = PL.match(t)
                        break
            if mpl:
                started.add(mpl.group(1))
                pl, cnt = mpl.group(1), [0, 0, 0, 0]               # vào phụ lục mới: đánh số lại từ đầu, tiền tố chữ
            hm = re.match(r"^Heading (\d)$", para.style.name)
            if hm and 1 <= int(hm.group(1)) <= 4 and not HEAD.match(t) and not mpl:
                lv = int(hm.group(1)) - 1
                cnt[lv] += 1
                cnt[lv + 1:] = [0] * (3 - lv)
                num = ".".join(str(x) for x in cnt[: lv + 1])
                t = f"\x01{pl + '.' if pl else ''}{num} {t}"          # \x01 = tiêu đề do kiểu Heading (kể cả điều khoản dài)
            m = CAP_D.match(t.replace("\n", " "))
            if m and len(t) < 300:
                cap, cap_i = (cid(m.group(1)), m.group(1), (m.group(2) or "").strip()), i
            lines.append(t)
        elif ch.tag.endswith("}tbl"):
            rows, span = rows_of(Table(ch, d))
            if cap and i - cap_i <= 8:
                b = bang.setdefault(cap[0], dict(num=cap[1], title=cap[2], rows=[], blocks=0, span=False))
                if not b["title"] and cap[2]:
                    b["title"] = cap[2]
                if b["blocks"] and rows and rows[0] == b["rows"][0]:
                    rows = rows[1:]
                elif b["blocks"] and rows and not rows[0][0] and b["rows"]:
                    for j, x in enumerate(rows[0]):
                        if x and j < len(b["rows"][-1]):
                            b["rows"][-1][j] = (b["rows"][-1][j] + " " + x).strip()
                    rows = rows[1:]
                b["rows"] += rows
                b["blocks"] += 1
                b["span"] |= span
                cap_i = i
                mk = f"[__BANG__:{cap[0]}]"
                if not lines or lines[-1] != mk:
                    lines.append(mk)
            else:                                          # bảng không có tiêu đề: giữ chữ tại chỗ
                lines += ["| " + " | ".join(r) + " |" for r in rows]
    return lines, bang


def md_table(rows: list[list[str]]) -> str:
    w = max(len(r) for r in rows)
    keep = [j for j in range(w) if any((r[j] if j < len(r) else "") for r in rows)]
    rows = [[(r[j] if j < len(r) else "") for j in keep] for r in rows]
    return "\n".join(["| " + " | ".join(rows[0]) + " |", "|" + "---|" * len(keep)] + ["| " + " | ".join(r) + " |" for r in rows[1:]])


def tach_muc(lines: list[str], ma: str, tach: int) -> list[tuple[str, str, str]]:
    """-> [(số mục, tiêu đề, nội dung)] — tách ở tiêu đề mục cấp ≤ tach; mục lục (số mục xuất hiện 2 lần) giữ bản dài nhất."""
    out, cur, buf = [], ("mo-dau", "Mở đầu"), []
    for ln in lines:
        mk = re.match(r"^\[__BANG__:(.+)\]$", ln)
        if mk:
            buf.append("[Bảng → " + (f"{ma}-bang-{mk.group(1)}" if mk.group(1) != "?" else "không rõ tiêu đề") + "]")
            continue
        forced = ln.startswith("\x01")
        ln = ln.lstrip("\x01")
        mpl = PL.match(ln)
        if mpl and len(ln) < 200:
            if "".join(buf).strip():
                out.append((cur[0], cur[1], "\n".join(buf).strip()))
            cur, buf = (f"pl-{mpl.group(1).lower()}", (mpl.group(2) or f"Phụ lục {mpl.group(1)}").strip()), [ln]
            continue
        m = HEAD.match(ln)
        dep = len(m.group(1).split(".")) if m else 0
        if m and dep <= tach + (1 if forced else 0) and (forced or len(ln) < 150) \
                and not (dep == 1 and not forced and not re.match(r"^[A-ZĐÀ-Ỹ ,.\-–]{4,}$", m.group(2))):
            if "".join(buf).strip():
                out.append((cur[0], cur[1], "\n".join(buf).strip()))
            cur, buf = (m.group(1), m.group(2).strip()[:110]), [ln]
        else:
            buf.append(ln)
    if "".join(buf).strip():
        out.append((cur[0], cur[1], "\n".join(buf).strip()))
    best: dict[str, tuple[str, str, str]] = {}
    for n, t, c in out:
        if n not in best or len(c) > len(best[n][2]):
            best[n] = (n, t, c)
    return [best[n] for n in dict.fromkeys(n for n, _, _ in out)]


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("nguon")
    ap.add_argument("--ma", required=True)
    ap.add_argument("--ten", required=True)
    ap.add_argument("--tach", type=int, default=3)
    ap.add_argument("--ghi-de", action="store_true")
    ap.add_argument("--toi-da", type=int, default=6000, dest="toi_da", help="mục dài hơn ngần này ký tự thì tách tiếp theo điều khoản con")
    a = ap.parse_args()
    src = Path(a.nguon)
    suf = src.suffix.lower()
    if suf == ".txt":
        lines, bang = [x.strip() for x in src.read_text(encoding="utf-8-sig").splitlines() if x.strip()], {}
    elif suf in (".docx", ".doc"):
        lines, bang = docx_parts(doc_sang_docx(src) if suf == ".doc" else src)
    else:
        lines, bang = pdf_parts(src)
    kho = ROOT / "knowledge" / "quy-chuan"
    kho.mkdir(parents=True, exist_ok=True)
    n_t = n_b = skip = 0

    def ghi(f: Path, fm: dict, body: str) -> bool:
        if f.exists() and not a.ghi_de:
            return False
        f.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, width=200) + "---\n" + body.strip() + "\n", encoding="utf-8")
        return True

    for k, b in bang.items():
        if not b["rows"]:
            continue
        ok = ghi(kho / f"{a.ma}-bang-{k}.md",
                 dict(id=f"{a.ma}-bang-{k}", tieu_de=f"{a.ten} — Bảng {b['num']}. {b['title']}", nhom="quy-chuan",
                      tu_khoa=f"bảng {b['num']}, {a.ma} bảng {k}, {b['title']}",
                      trang_thai="verified" if (suf in (".docx", ".doc") and not b.get("span") and b["blocks"] == 1) else "cho_duyet",
                      nguon=f"{src.name}, Bảng {b['num']}", cap_nhat=str(date.today())),
                 md_table(b["rows"]) + f"\n\n> Nạp tự động ({b['blocks']} khối{', có ô gộp' if b.get('span') else ''}) — so bố cục ô với file gốc rồi `knowled duyet {a.ma}-bang-{k}`.")
        n_b += ok
        skip += not ok
    muc = []
    for num, tit, body in tach_muc(lines, a.ma, a.tach):
        if len(body) > a.toi_da:                              # mục quá dài (vd 2.2.1 có ~30 điều) -> tách tiếp theo điều khoản con
            sub = tach_muc(body.splitlines(), a.ma, a.tach + 1)
            muc += sub if len(sub) > 1 else [(num, tit, body)]
        else:
            muc.append((num, tit, body))
    for num, tit, body in muc:
        slug = re.sub(r"[^a-z0-9]+", "-", bd(num)).strip("-")
        ok = ghi(kho / f"{a.ma}-{slug}.md",
                 dict(id=f"{a.ma}-{slug}", tieu_de=f"{a.ten} — {num} {tit}"[:150], nhom="quy-chuan",
                      tu_khoa=f"{a.ma}, mục {num}, {tit}", trang_thai="verified", nguon=f"{src.name}, mục {num}", cap_nhat=str(date.today())),
                 body)
        n_t += ok
        skip += not ok
    print(f"{a.ma}: nạp {n_t} mục + {n_b} bảng, bỏ qua {skip} (đã có; --ghi-de để nạp lại)")


if __name__ == "__main__":
    main()
