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


def test_hybrid_falls_back_to_vector_on_daily_quota(tmp_path, monkeypatch):
    from pccc_checker.extractors import HybridExtractor
    from pccc_checker.extractors.gemini_extractor import GeminiQuotaError
    from pccc_checker.extractors.vector_extractor import VectorTextExtractor

    pdf = make(tmp_path / "s.pdf")
    gem = GeminiExtractor.__new__(GeminiExtractor)

    def boom(*a, **k):
        raise GeminiQuotaError("429 RESOURCE_EXHAUSTED PerDay")

    monkeypatch.setattr(gem, "extract_page", boom)
    d = HybridExtractor(gem, VectorTextExtractor()).extract(pdf, log=lambda *_: None)
    assert d.elements()                                         # vẫn có kết quả từ text vector
    assert any("Gemini không đọc được" in n for n in d.pages[0].notes)


def test_backend_web_settings_and_cache_reuse(tmp_path):
    from pccc_checker.extractors.gemini_extractor import backend_kwargs, cached
    g = {"model": "gemini-2.5-flash", "backend": "web", "web": {"model": "Pro", "fallback_models": ["Flash"], "headless": True}}
    assert backend_kwargs(g) == {"model": "Pro", "fallback_models": ["Flash"], "web": {"headless": True}}
    assert backend_kwargs({**g, "backend": "api"})["model"] == "gemini-2.5-flash"
    api = tmp_path / "abc_p3_gemini-2.5-flash_2x2_ph.json"
    api.write_text("[]")
    assert cached(tmp_path / "abc_p3_Pro_2x2_ph.json", "abc_p3_*_2x2_ph.json") == api   # đổi API -> web vẫn dùng cache
    assert cached(tmp_path / "abc_p4_Pro_2x2_ph.json", "abc_p4_*_2x2_ph.json") is None
