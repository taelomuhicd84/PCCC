"""Ghi chú lỗi trực tiếp lên PDF: khung màu + nhãn số lỗi + sticky note (comment) chứa nội dung."""
from __future__ import annotations

from collections import OrderedDict
from pathlib import Path

import pymupdf

from ..models import Finding

COLORS = {"error": (0.9, 0.1, 0.1), "warning": (1.0, 0.55, 0.0), "info": (0.1, 0.45, 0.9)}
RANK = {"error": 0, "warning": 1, "info": 2}


def annotate(pdf_in: Path, findings: list[Finding], pdf_out: Path, min_severity: str = "info") -> int:
    """Trả về số ghi chú đã thêm. Lỗi không có vị trí -> ghi ở góc trên-trái trang (hoặc trang 1).
    Nhiều lỗi trên cùng một vị trí được gộp thành 1 khung, nhãn dạng "#3,#4"."""
    doc = pymupdf.open(pdf_in)
    groups: "OrderedDict[tuple, list[tuple[int, Finding]]]" = OrderedDict()
    for idx, f in enumerate(findings, 1):
        if f.dismissed or RANK.get(f.severity, 3) > RANK[min_severity]:
            continue
        pno = (f.page or 1) - 1
        if pno >= doc.page_count:
            continue
        key = (pno, tuple(round(v) for v in f.bbox) if f.bbox else None)
        groups.setdefault(key, []).append((idx, f))

    count = 0
    corner_y: dict[int, float] = {}
    for (pno, bbox), items in groups.items():
        page = doc[pno]
        worst = min(items, key=lambda it: RANK.get(it[1].severity, 3))[1]
        color = COLORS.get(worst.severity, (0.5, 0.5, 0.5))
        if bbox:
            r = (pymupdf.Rect(bbox) + (-4, -4, 4, 4)) & page.rect
            box = page.add_rect_annot(r)
            box.set_colors(stroke=color)
            box.set_border(width=1.5)
            box.set_info(title="PCCC", content="; ".join(f"#{i} {f.message}" for i, f in items))
            box.update(opacity=0.9)
            label = ",".join(f"#{i}" for i, _ in items)
            tag = page.add_freetext_annot(pymupdf.Rect(r.x0, max(0, r.y0 - 12), r.x0 + 12 + 14 * len(items), r.y0),
                                          label, fontsize=8, text_color=color, fill_color=(1, 1, 1))
            tag.update()
            x, y = r.x1 + 2, r.y0
        else:
            x, y = 20, corner_y.get(pno, 20.0)
            corner_y[pno] = y + 18 * len(items)
        for k, (idx, f) in enumerate(items):
            mark = "" if f.verified_rule else " (*luật chưa xác minh)"
            title = f"#{idx} [{f.severity.upper()}] {f.rule_id}"
            body = f"{f.message}\nĐiều khoản: {f.clause}{mark}"
            if f.reviewer_note:
                body += f"\nReview: {f.reviewer_note}"
            note = page.add_text_annot(pymupdf.Point(x + 18 * k if bbox else x, y if bbox else y + 18 * k),
                                       body, icon="Comment")
            note.set_info(title=title, content=body)
            note.set_colors(stroke=COLORS.get(f.severity, color))
            note.update()
            count += 1
    pdf_out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(pdf_out, garbage=3, deflate=True)
    doc.close()
    return count
