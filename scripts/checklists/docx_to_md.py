#!/usr/bin/env python3
"""Chuyen bang doi chieu .docx -> .md giu nguyen thu tu, xu ly o gop.
Dung: python3 -I docx_to_md.py <in.docx> <out.md>
Moi hang bang duoc danh so R### de lam ID tam (build_rules.py se doi thanh ID ben vung)."""
import sys, re
import docx
from docx.table import Table
from docx.text.paragraph import Paragraph

def cell_text(c):
    parts = [p.text.strip() for p in c.paragraphs]
    t = "<br>".join(x for x in parts if x)
    return t.replace("|", "\\|")

def table_rows(t):
    rows, above = [], {}
    for r in t.rows:
        out, prev = [], None
        for ci, c in enumerate(r.cells):
            tc = c._tc
            if tc is prev:            # gop ngang
                continue
            prev = tc
            if above.get(ci) is tc:   # gop doc: o tiep noi
                out.append("")
            else:
                out.append(cell_text(c))
            above[ci] = tc
        rows.append(out)
    return rows

def main(src, dst):
    d = docx.Document(src)
    body = d.element.body
    lines, n = [], 0
    for el in body.iterchildren():
        tag = el.tag.split('}')[1]
        if tag == 'p':
            t = Paragraph(el, d).text.strip()
            if t:
                lines.append(t)
                lines.append("")
        elif tag == 'tbl':
            tbl_rows = table_rows(Table(el, d))
            for row in tbl_rows:
                # chuan hoa ve 6 cot: TT | Noi dung | Thiet ke | Quy dinh | Dieu | Ket luan
                if len(row) == 2 and len(tbl_rows) == 1:   # bang tieu de dau file
                    lines.append("> " + " / ".join(x for x in row if x))
                    continue
                row = (row + [""] * 6)[:6]                  # hang gop ngang -> dem du 6 cot
                n += 1
                lines.append(f"| R{n:03d} | " + " | ".join(row[:5]) + " |")
            lines.append("")
    open(dst, "w", encoding="utf-8").write("\n".join(lines))
    print(dst, "rows:", n, "chars:", sum(len(x) for x in lines))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
