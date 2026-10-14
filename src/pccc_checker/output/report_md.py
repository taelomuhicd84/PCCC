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
        if k != "assumptions":
            lines.append(f"- {k}: {v if v is not None else '—'}")
    for a in b.assumptions:
        lines.append(f"- ⚠ Giả định: {a}")
    for p in d.pages:
        lines += ["", f"## Trang {p.page} [{p.category or '?'}] — {p.sheet_title or '(không tên)'}  (tỉ lệ: {p.scale or '?'})", ""]
        if p.declared:
            lines += [f"Số liệu thiết kế ghi trên bản vẽ: {p.declared}", ""]
        if p.elements:
            lines += ["| id | loại | ký hiệu | thuộc tính | conf |", "|---|---|---|---|---|"]
            for e in p.elements:
                attrs = ", ".join(f"{k}={v}" for k, v in e.attrs.items() if v is not None)
                lines.append(f"| {e.id} | {e.type} | {e.label} | {attrs} | {e.confidence:.1f} |")
        for n in p.notes:
            lines.append(f"- Ghi chú: {n}")
    return "\n".join(lines) + "\n"


def project_info_md(info, findings: list[Finding]) -> list[str]:
    """Mục 'Thông tin công trình': mỗi trường + trang nguồn + trạng thái; trường thiếu/mâu thuẫn + số luật ảnh hưởng."""
    from ..project_info import hang_muc_table, load_spec, table_rows
    spec = load_spec()
    head, hm = hang_muc_table(info, spec)
    hm_md = ["### Các hạng mục trong khu đất", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head),
             *("| " + " | ".join(x.replace("|", "/") for x in row) + " |" for row in hm), "",
             f"Mọi hạng mục đều là hạng mục chính; luật YAML tạm chạy theo: **{info.hang_muc_chinh}**.", ""] if hm else []
    lines = ["## Thông tin công trình", "", *hm_md, "| Trường | Giá trị | Trang | Trạng thái |", "|---|---|---|---|"]
    for _, label, val, pages, st in table_rows(info, spec):
        lines.append(f"| {label} | {val.replace('|', '/')} | {pages} | {st.replace('|', '/')} |")
    problems = info.problems(spec)
    if problems:
        cannot = [f for f in findings if f.status == "cannot_check"]
        lines += ["", "**Trường bắt buộc thiếu hoặc mâu thuẫn:**", ""]
        for k, why in problems.items():
            label = spec["fire_inputs"][k]["label"]
            n = sum(why in f.message for f in cannot)
            lines.append(f"- {label}: {why} → {n} luật không kiểm tra được / không xác định được ngưỡng")
    for w in info.warnings:
        lines.append(f"- ⚠ {w}")
    return lines + [""]


def findings_md(d: DrawingExtraction, findings: list[Finding], pdf_out: str = "", info=None) -> str:
    cannot = [f for f in findings if f.status == "cannot_check" and not f.dismissed]
    findings_ok = [f for f in findings if f.status != "cannot_check"]
    c = Counter(f.severity for f in findings_ok if not f.dismissed)
    n_dismissed = sum(f.dismissed for f in findings)
    lines = [
        "# Báo cáo kiểm tra PCCC theo QCVN 06:2022/BXD & Sửa đổi 1:2023", "",
        f"- Bản vẽ: `{d.source_pdf}`",
        f"- Thời gian: {datetime.now():%Y-%m-%d %H:%M}",
        f"- PDF đã ghi chú: `{pdf_out}`" if pdf_out else "",
        *(f"- ⚠ Giả định: {x}" for x in d.building.assumptions),
        f"- Tổng: {ICON['error']} {c['error']} lỗi · {ICON['warning']} {c['warning']} cảnh báo · {ICON['info']} {c['info']} thông tin",
        f"- Đã bác bỏ sau review: {n_dismissed}" if n_dismissed else "",
        f"- Luật không kiểm tra được do thiếu/mâu thuẫn thông tin công trình: {len(cannot)}" if cannot else "",
        "", *(project_info_md(info, findings) if info else []),
        "## Kết quả kiểm tra", "",
        "> (*) = luật chưa được kỹ sư đối chiếu nguyên văn văn bản (`verified: false` trong rules/*.yaml).",
        "> Kết quả do máy đọc bản vẽ — kỹ sư PCCC phải xác nhận trước khi sử dụng chính thức.", "",
    ]
    hm = any(f.hang_muc for f in findings)
    lines += (["| # | Hạng mục | Mức | Trang | Luật | Điều khoản | Nội dung |", "|---|---|---|---|---|---|---|"] if hm else
              ["| # | Mức | Trang | Luật | Điều khoản | Nội dung |", "|---|---|---|---|---|---|"])
    for i, f in enumerate(findings, 1):  # giữ số thứ tự gốc để khớp nhãn #i trên PDF
        if f.dismissed or f.status == "cannot_check":
            continue
        star = "" if f.verified_rule else " (*)"
        msg = f.message.replace("|", "\\|")
        if f.reviewer_note:
            msg += f"<br>_Review: {f.reviewer_note}_"
        lines.append(f"| {i} |{f' {f.hang_muc} |' if hm else ''} {ICON.get(f.severity, '')} {f.severity} | {f.page or '-'} | "
                     f"{f.rule_id} | {f.clause}{star} | {msg} |")
    return "\n".join(l for l in lines if l is not None) + "\n"
