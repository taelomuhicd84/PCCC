"""Xuất kết quả trích xuất (+ lỗi) ra DXF để mở trong AutoCAD.

Mỗi trang -> 1 vùng đặt cạnh nhau theo trục X. Toạ độ: point PDF, lật trục Y (CAD gốc dưới-trái).
Nếu biết tỉ lệ bản vẽ thì nhân hệ số để ra mm thực tế.
"""
from __future__ import annotations

import re
from pathlib import Path

import ezdxf

from ..models import DrawingExtraction, Finding

LAYER_COLORS = {"exit_door": 3, "door": 8, "fire_door": 1, "stair": 5, "corridor": 4, "room": 9,
                "lobby": 6, "fire_wall": 1, "evac_route": 3, "equipment": 2, "other": 8}
SEV_COLORS = {"error": 1, "warning": 30, "info": 5}


def _scale_mm(scale: str) -> float:
    m = re.search(r"1\s*[:/]\s*(\d+)", scale or "")
    return (25.4 / 72) * (int(m.group(1)) if m else 1)


def export_dxf(d: DrawingExtraction, findings: list[Finding], out: Path) -> Path:
    doc = ezdxf.new("R2010", setup=True)
    msp = doc.modelspace()
    for name, col in LAYER_COLORS.items():
        doc.layers.add(f"PCCC_{name.upper()}", color=col)
    for sev, col in SEV_COLORS.items():
        doc.layers.add(f"LOI_{sev.upper()}", color=col)

    offset_x = 0.0
    for p in d.pages:
        k = _scale_mm(p.scale)
        H = p.height

        def tr(x: float, y: float) -> tuple[float, float]:
            return offset_x + x * k, (H - y) * k

        msp.add_lwpolyline([tr(0, 0), tr(p.width, 0), tr(p.width, p.height), tr(0, p.height)], close=True,
                           dxfattribs={"layer": "0"})
        msp.add_text(f"TRANG {p.page} {p.sheet_title}", height=10 * k,
                     dxfattribs={"layer": "0"}).set_placement(tr(5, -10))
        for e in p.elements:
            x0, y0, x1, y1 = e.bbox
            layer = f"PCCC_{e.type.upper()}" if e.type in LAYER_COLORS else "PCCC_OTHER"
            msp.add_lwpolyline([tr(x0, y0), tr(x1, y0), tr(x1, y1), tr(x0, y1)], close=True, dxfattribs={"layer": layer})
            attrs = " ".join(f"{a}={v}" for a, v in e.attrs.items() if v is not None)
            msp.add_text(f"{e.label} {attrs}".strip()[:120], height=3 * k,
                         dxfattribs={"layer": layer}).set_placement(tr(x0, y0 - 1))
        for i, f in enumerate(findings, 1):
            if f.page != p.page or not f.bbox:
                continue
            x0, y0, x1, y1 = f.bbox
            layer = f"LOI_{f.severity.upper()}"
            msp.add_circle(tr((x0 + x1) / 2, (y0 + y1) / 2), radius=max(x1 - x0, y1 - y0, 10) * k * 0.75,
                           dxfattribs={"layer": layer})
            msp.add_mtext(f"#{i} {f.rule_id}: {f.message}", dxfattribs={"layer": layer, "char_height": 3 * k}
                          ).set_location(tr(x1 + 4, y0))
        offset_x += (p.width + 50) * k
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(out)
    return out
