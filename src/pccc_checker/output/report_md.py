"""Xuất Markdown: (1) bản trích xuất bản vẽ dạng MD, (2) báo cáo lỗi."""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from ..models import DrawingExtraction, Finding

ICON = {"error": "🔴", "warning": "🟠", "info": "🔵"}


def extraction_md(d: DrawingExtraction) -> str:
    """Bản tóm tắt gọn của bản vẽ — đầu vào rẻ token cho agent Claude review."""
    b = d.building
    lines = [f"# Trích xuất bản vẽ: {d.source_pdf}", f"Extractor: `{d.extractor}`", "",
             "## Thông tin công trình", ""]
    for k, v in vars(b).items():
        lines.append(f"- {k}: {v if v is not None else '—'}")
    for p in d.pages:
        lines += ["", f"## Trang {p.page} — {p.sheet_title or '(không tên)'}  (tỉ lệ: {p.scale or '?'})", ""]
        if p.elements:
            lines += ["| id | loại | ký hiệu | thuộc tính | conf |", "|---|---|---|---|---|"]
            for e in p.elements:
                attrs = ", ".join(f"{k}={v}" for k, v in e.attrs.items() if v is not None)
                lines.append(f"| {e.id} | {e.type} | {e.label} | {attrs} | {e.confidence:.1f} |")
        for n in p.notes:
            lines.append(f"- Ghi chú: {n}")
    return "\n".join(lines) + "\n"


def findings_md(d: DrawingExtraction, findings: list[Finding], pdf_out: str = "") -> str:
    c = Counter(f.severity for f in findings if not f.dismissed)
    n_dismissed = sum(f.dismissed for f in findings)
    lines = [
        "# Báo cáo kiểm tra PCCC theo QCVN 06:2022/BXD & Sửa đổi 1:2023", "",
        f"- Bản vẽ: `{d.source_pdf}`",
        f"- Thời gian: {datetime.now():%Y-%m-%d %H:%M}",
        f"- PDF đã ghi chú: `{pdf_out}`" if pdf_out else "",
        f"- Tổng: {ICON['error']} {c['error']} lỗi · {ICON['warning']} {c['warning']} cảnh báo · {ICON['info']} {c['info']} thông tin",
        f"- Đã bác bỏ sau review: {n_dismissed}" if n_dismissed else "",
        "", "> (*) = luật chưa được kỹ sư đối chiếu nguyên văn văn bản (`verified: false` trong rules/*.yaml).",
        "> Kết quả do máy đọc bản vẽ — kỹ sư PCCC phải xác nhận trước khi sử dụng chính thức.", "",
        "| # | Mức | Trang | Luật | Điều khoản | Nội dung |", "|---|---|---|---|---|---|",
    ]
    for i, f in enumerate(findings, 1):  # giữ số thứ tự gốc để khớp nhãn #i trên PDF
        if f.dismissed:
            continue
        star = "" if f.verified_rule else " (*)"
        msg = f.message.replace("|", "\\|")
        if f.reviewer_note:
            msg += f"<br>_Review: {f.reviewer_note}_"
        lines.append(f"| {i} | {ICON.get(f.severity, '')} {f.severity} | {f.page or '-'} | {f.rule_id} | {f.clause}{star} | {msg} |")
    return "\n".join(l for l in lines if l is not None) + "\n"
