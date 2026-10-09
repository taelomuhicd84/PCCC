"""Tạo bản vẽ PDF mẫu (vector) có cài sẵn lỗi để test pipeline offline.

python scripts/make_sample_pdf.py data/input/sample_mat_bang.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

FONT_CANDIDATES = [r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "/Library/Fonts/Arial Unicode.ttf"]


def make(out: Path) -> Path:
    doc = pymupdf.open()
    page = doc.new_page(width=1191, height=842)  # A3 ngang
    font = next((f for f in FONT_CANDIDATES if Path(f).exists()), None)
    kw = {"fontfile": font, "fontname": "vn"} if font else {}

    def text(x, y, s, size=9):
        page.insert_text((x, y), s, fontsize=size, **kw)

    # tường bao + hành lang
    page.draw_rect(pymupdf.Rect(100, 100, 900, 600), width=2)
    page.draw_rect(pymupdf.Rect(100, 330, 900, 370), width=1)
    text(450, 352, "HÀNH LANG B=900")
    # thang bộ (vế thang hẹp, bậc cao) — lỗi cố ý
    page.draw_rect(pymupdf.Rect(120, 380, 220, 580), width=1)
    text(125, 470, "THANG BỘ TB1")
    text(125, 482, "B=850")
    text(125, 494, "BẬC 180x240")
    # 2 lối ra thoát nạn đặt sát nhau (< 7 m ở tỉ lệ 1:100)
    page.draw_rect(pymupdf.Rect(880, 335, 900, 365), width=1)
    text(905, 345, "D1 700x2100")
    text(905, 357, "LỐI THOÁT NẠN")
    page.draw_rect(pymupdf.Rect(880, 400, 900, 430), width=1)
    text(905, 410, "D2 1200x2200")
    text(905, 422, "LỐI THOÁT NẠN")
    # cửa ngăn cháy thiếu EI
    text(240, 470, "CN1 1000x2100 CỬA NGĂN CHÁY")
    # khung tên
    page.draw_rect(pymupdf.Rect(950, 650, 1180, 830), width=1)
    text(960, 670, "MẶT BẰNG THOÁT NẠN TẦNG 3", 10)
    text(960, 690, "TỈ LỆ 1:100")
    text(960, 710, "CÔNG NĂNG: CHUNG CƯ F1.3")
    text(960, 730, "CHIỀU CAO PCCC: 24.5 m")
    text(960, 750, "BẬC CHỊU LỬA II")
    text(960, 770, "9 TẦNG NỔI, 1 TẦNG HẦM")
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    return out


if __name__ == "__main__":
    print(make(Path(sys.argv[1] if len(sys.argv) > 1 else "data/input/sample_mat_bang.pdf")))
