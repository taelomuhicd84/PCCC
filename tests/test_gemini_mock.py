"""Kiểm tra quy đổi toạ độ + gộp tile của GeminiExtractor mà không gọi API thật."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from make_sample_pdf import make  # noqa: E402

from pccc_checker.extractors.gemini_extractor import GeminiExtractor


def test_gemini_tiles_to_page_coords(tmp_path, monkeypatch):
    pdf = make(tmp_path / "s.pdf")
    ex = GeminiExtractor.__new__(GeminiExtractor)  # bỏ qua __init__ (không cần API key)
    ex.dpi, ex.grid, ex.max_px, ex.cache_dir = 50, (1, 2), 1000, None
    calls = []

    def fake_call(png, texts):
        calls.append(len(texts))
        return {"scale": "1:100", "building": {"function_group": "F1.3", "height_pccc_m": None},
                "elements": [{"type": "exit_door", "label": "D1", "box_2d": [0, 0, 500, 500],
                              "attrs": {"width_m": 0.7}, "confidence": 0.9}]}

    monkeypatch.setattr(ex, "_call", fake_call)
    page, building = ex.extract_page(pdf, 1)
    assert len(calls) == 2                      # lưới 1x2 -> 2 tile
    assert building["function_group"] == "F1.3"
    xs = sorted(e.bbox[0] for e in page.elements)
    assert xs[0] == 0 and xs[1] > 500           # tile thứ 2 nằm ở nửa phải trang
    assert all(e.source == "gemini" for e in page.elements)
