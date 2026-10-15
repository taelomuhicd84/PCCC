"""Trích MỌI bảng có tiêu đề "Bảng …" của file Word QCVN 06 hợp nhất -> mỗi bảng một module trong knowledge/quy-chuan/.

    python scripts/knowled_import_qcvn.py "<file.docx>" [--chi 4,6,e1] [--ghi-de]

- Mỗi bảng = 1 file `qcvn06-bang-<số>.md` (vd bang-4, bang-a1, bang-e4a) — sửa tay từng file, không đụng file khác.
- Mặc định KHÔNG ghi đè file đã có (giữ chỉnh sửa tay); `--ghi-de` nạp lại từ Word.
- Bảng chia nhiều trang (cùng tiêu đề) được ghép; ô gộp dọc ghi 〃 (giống ô trên); hàng bị ngắt trang (ô đầu trống) nối vào hàng trước.
- Bảng có ô gộp ngang/dọc hoặc ghép nhiều khối -> trang_thai `cho_duyet` (kiểm bố cục với Word rồi `knowled duyet <id>`);
  bảng đơn giản -> `verified` (chép nguyên văn từ Word người dùng cung cấp).
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import docx
import yaml
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[1]
CAP = re.compile(r"^Bảng\s+([A-Z]?\.?\d+[a-z]?)\b\s*[-–—:.]?\s*(.*)$", re.I)
NOTE = re.compile(r"^(CHÚ THÍCH|Chú thích|Ghi chú|\d+\)|\*|-\s|[a-z]\))", re.U)


def cid(n: str) -> str:
    return n.replace(".", "").lower()


LOOK = str.maketrans("ЕЗКСАВМНОРТХ", "E3KCABMHOPTX")      # chữ Kirin giống chữ Latin lẫn trong ký hiệu (RЕI, SЗ) của file Word
CODE = re.compile(r"^[\sA-Za-z0-9ЕЗКСАВМНОРТХ,.\-–/()≤≥<>+%]+$")


def cell_text(c) -> str:
    s = re.sub(r"\s+", " ", " ".join(p.text for p in c.paragraphs)).replace("|", "/").strip()
    return s.translate(LOOK) if CODE.match(s) else s       # chỉ ô toàn ký hiệu (REI 60, S3); ô tiếng Việt giữ nguyên


def doc_items(d):
    for ch in d.element.body.iterchildren():
        if ch.tag.endswith("}p"):
            yield "p", Paragraph(ch, d)
        elif ch.tag.endswith("}tbl"):
            yield "t", Table(ch, d)


def rows_of(t: Table) -> tuple[list[list[str]], bool]:
    """-> (các hàng, có_ô_gộp). Ô gộp ngang bị bỏ trùng; ô gộp dọc ghi 〃."""
    out, prev, span = [], [], False
    for r in t.rows:
        cs, cur, last = [], [], None
        for c in r.cells:
            if c._tc is last:
                span = True
                continue
            last = c._tc
            cur.append(c._tc)
            cs.append("〃" if c._tc in prev else cell_text(c))
        if any(x == "〃" for x in cs):
            span = True
        prev = cur
        out.append(cs)
    return out, span


def build(docx_path: Path) -> dict[str, dict]:
    items = list(doc_items(docx.Document(docx_path)))
    bang: dict[str, dict] = {}
    cap, cap_i = None, -99
    for i, (k, v) in enumerate(items):
        if k == "p":
            m = CAP.match(v.text.strip())
            if m and len(v.text) < 300:
                cap, cap_i = (cid(m.group(1)), m.group(1), v.text.strip()), i
        elif cap and i - cap_i <= 8:
            rows, span = rows_of(v)
            b = bang.setdefault(cap[0], dict(num=cap[1], title=cap[2], rows=[], span=False, blocks=0, notes=[]))
            if b["blocks"] and rows and rows[0] == b["rows"][0]:
                rows = rows[1:]                                       # tiêu đề cột lặp ở trang sau
            elif b["blocks"] and rows and not rows[0][0] and b["rows"]:   # hàng bị ngắt trang: nối vào hàng trước
                for j, x in enumerate(rows[0]):
                    if x and j < len(b["rows"][-1]):
                        b["rows"][-1][j] = (b["rows"][-1][j] + " " + x).strip()
                rows = rows[1:]
            b["rows"] += rows
            b["span"] |= span
            b["blocks"] += 1
            b["last_i"] = i
            cap_i = i                                                  # bảng nối tiếp cùng tiêu đề
    for b in bang.values():                                            # chú thích ngay dưới bảng
        j, n = b["last_i"] + 1, 0
        while j < len(items) and n < 14:
            k, v = items[j]
            t = v.text.strip() if k == "p" else None
            if k == "t" or (t and CAP.match(t)):
                break
            if t:
                if not NOTE.match(t):
                    break
                b["notes"].append(t)
                n += 1
            j += 1
    return bang


def md_table(rows: list[list[str]]) -> str:
    w = max(len(r) for r in rows)
    rows = [r + [""] * (w - len(r)) for r in rows]
    return "\n".join(["| " + " | ".join(rows[0]) + " |", "|" + "---|" * w] + ["| " + " | ".join(r) + " |" for r in rows[1:]])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("--chi", help="chỉ các bảng này, vd 4,6,e1")
    ap.add_argument("--ghi-de", action="store_true")
    a = ap.parse_args()
    bang = build(Path(a.docx))
    want = {x.strip().lower() for x in a.chi.split(",")} if a.chi else None
    kho = ROOT / "knowledge" / "quy-chuan"
    kho.mkdir(parents=True, exist_ok=True)
    n = skip = 0
    for k, b in bang.items():
        if (want and k not in want) or (k == "6" and not want):    # Bảng 6 đã nạp riêng: bang-6-phan-nhom-nha
            continue
        f = kho / f"qcvn06-bang-{k}.md"
        if f.exists() and not a.ghi_de:
            skip += 1
            continue
        ok = not b["span"] and b["blocks"] == 1
        ten = re.sub(r"^Bảng\s+\S+\s*[-–—:.]?\s*", "", b["title"])
        fm = dict(id=f"qcvn06-bang-{k}", tieu_de=b["title"], nhom="quy-chuan",
                  tu_khoa=f"bảng {b['num']}, bảng {k}, {ten}",
                  trang_thai="verified" if ok else "cho_duyet",
                  nguon=f"{Path(a.docx).name} (QCVN 06:2022 hợp nhất SĐ1:2023), Bảng {b['num']}", cap_nhat=str(date.today()))
        body = md_table(b["rows"]) + "\n"
        if b["notes"]:
            body += "\n" + "\n".join(b["notes"]) + "\n"
        if not ok:
            body += (f"\n> Nạp tự động từ Word: {b['blocks']} khối, {'có ô gộp (〃 = giống ô trên) ' if b['span'] else ''}"
                     "— kiểm bố cục với file Word rồi `knowled duyet`.\n")
        f.write_text("---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, width=200) + "---\n" + body, encoding="utf-8")
        n += 1
    print(f"đã nạp {n} bảng, bỏ qua {skip} (đã có; --ghi-de để nạp lại) — tổng {len(bang)} bảng có tiêu đề trong Word")


if __name__ == "__main__":
    main()
