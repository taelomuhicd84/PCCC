"""Bước info không gửi cả bộ scan 200 trang; cookie Gemini: 3 dạng đầu vào, lưu lại vào .env."""
import json

import fitz
import pytest

from pccc_checker.extractors import gemini_web
from pccc_checker.pdf.classify import info_pages


def test_info_pages_caps_scanned_pages(tmp_path):
    pdf = tmp_path / "scan.pdf"
    doc = fitz.open()
    for _ in range(30):
        doc.new_page()                      # trang trắng = trang scan không có text
    doc.save(pdf)
    assert [p for p, _ in info_pages(pdf, max_scan=5)] == [1, 2, 3, 4, 5]


def test_parse_cookie_editor_json():
    raw = json.dumps([{"name": "__Secure-1PSID", "value": "a", "domain": ".google.com", "sameSite": "unspecified",
                       "expirationDate": 1893456000.5, "hostOnly": False, "storeId": "0"},
                      {"name": "__Secure-1PSIDTS", "value": "b", "domain": ".google.com", "sameSite": "lax"},
                      {"name": "EMPTY", "value": "", "domain": ".google.com"}])
    out = {c["name"]: c for c in gemini_web.parse_cookies(raw)}
    assert set(out) == {"__Secure-1PSID", "__Secure-1PSIDTS"}                # cookie rỗng bị bỏ
    assert out["__Secure-1PSID"]["sameSite"] == "None" and out["__Secure-1PSID"]["expires"] == 1893456000
    assert out["__Secure-1PSIDTS"]["sameSite"] == "Lax" and "hostOnly" not in out["__Secure-1PSID"]


def test_parse_header_string_and_bare_value():
    out = gemini_web.parse_cookies("__Secure-1PSID=a; __Secure-1PSIDTS=b")
    assert [(c["name"], c["value"], c["domain"]) for c in out] == [("__Secure-1PSID", "a", ".google.com"),
                                                                    ("__Secure-1PSIDTS", "b", ".google.com")]
    logs = []
    out = gemini_web.parse_cookies("g.a000xyz", log=logs.append)
    assert out[0]["name"] == "__Secure-1PSID" and out[0]["value"] == "g.a000xyz"
    assert logs and "1PSIDTS" in logs[0]                                     # thiếu 1PSIDTS -> cảnh báo


def test_parse_requires_1psid():
    with pytest.raises(ValueError, match="__Secure-1PSID"):
        gemini_web.parse_cookies("SID=a; HSID=b")


def test_env_cookies_from_two_values(monkeypatch):
    monkeypatch.delenv("GEMINI_COOKIES", raising=False)
    monkeypatch.setenv("GEMINI_1PSID", "a")
    monkeypatch.setenv("GEMINI_1PSIDTS", "b")
    names = {c["name"] for c in gemini_web.parse_cookies(gemini_web._env_cookies())}
    assert names == {"__Secure-1PSID", "__Secure-1PSIDTS"}
    monkeypatch.delenv("GEMINI_1PSID")
    assert gemini_web._env_cookies() is None


def test_save_env_cookies_replaces_lines(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_COOKIES", raising=False)
    env = tmp_path / ".env"
    env.write_text("GEMINI_API_KEY=k\nGEMINI_COOKIES=old\nGEMINI_1PSID=x\n", encoding="utf-8")
    src = tmp_path / "c.json"
    src.write_text(json.dumps([{"name": "__Secure-1PSID", "value": "1", "domain": ".google.com"}]), encoding="utf-8")
    assert gemini_web.import_cookie_file(src, env) == 1
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "GEMINI_API_KEY=k" and len(lines) == 2 and lines[1].startswith("GEMINI_COOKIES=[")


def test_bang_thong_ke_limits_hang_muc_columns():
    from pccc_checker.extractors.info_gemini import khu_vuc, to_hits
    from pccc_checker.project_info import load_spec, merge, tag_hang_muc
    p4 = {"bang_thong_ke": [
        {"ky_hieu": "1", "hang_muc": "NHÀ XƯỞNG CƠ KHÍ", "kich_thuoc": "54 x 26", "chieu_cao": "9", "dien_tich": "1404",
         "text": "1 | NHÀ XƯỞNG CƠ KHÍ | 54 x 26 | 9 | 1404"},
        {"ky_hieu": "5", "hang_muc": "TRẠM BƠM PCCC", "chieu_cao": "4.2", "dien_tich": "25", "text": "5 | TRẠM BƠM PCCC"}]}
    p8 = {"fields": {"bac_chiu_lua": [{"value": "IV", "hang_muc": "NHÀ XƯỞNG", "text": "BẬC CHỊU LỬA LÀ BẬC IV"}],
                     "tong_dien_tich_san": [{"value": "83", "hang_muc": "CÔNG NĂNG PHỤ TRỢ",
                                             "text": "TỔNG DIỆN TÍCH SÀN CỦA CÔNG NĂNG PHỤ TRỢ LÀ 83 M2"}]},
          "khu_vuc": [{"ten": "CÔNG NĂNG PHỤ TRỢ", "thuoc": "NHÀ XƯỞNG CƠ KHÍ", "dien_tich": "83", "text": "..."}]}
    hits = to_hits(p4, 4) + to_hits(p8, 8)
    tag_hang_muc(hits)
    info = merge(hits, load_spec())
    assert set(info.hang_muc) == {"NHÀ XƯỞNG CƠ KHÍ", "TRẠM BƠM PCCC"}             # không có cột "CÔNG NĂNG PHỤ TRỢ"
    assert info.hang_muc["NHÀ XƯỞNG CƠ KHÍ"]["bac_chiu_lua"].value == "IV"            # "NHÀ XƯỞNG" -> tên trong bảng
    assert info.hang_muc["TRẠM BƠM PCCC"]["dien_tich_xay_dung"].value == 25
    assert any("CÔNG NĂNG PHỤ TRỢ" in w and "không thống kê" in w for w in info.warnings)
    assert khu_vuc(p8, 8)[0]["thuoc"] == "NHÀ XƯỞNG CƠ KHÍ"


def test_summary_page_is_table_when_no_bang_thong_ke():
    from pccc_checker.project_info import load_spec, merge
    def hit(key, v, hm, page):
        return {"key": key, "value": v, "unit": None, "page": page, "text": f"{key} | {v}", "method": "gemini",
                "hang_muc": hm}
    hits = [{"key": "_bang_thong_ke", "value": "NHÀ KHO B", "unit": None, "page": 25, "text": "", "method": "gemini",
             "hang_muc": "NHÀ KHO B"}]                                    # 1 dòng: không phải bảng hạng mục
    hits += [hit("dien_tich_xay_dung", v, hm, 4) for hm, v in (("Nhà kho A", 1123.3), ("Nhà kho B", 5264.0),
                                                                ("Nhà bảo vệ", 16.0), ("Trạm bơm", 25.0))]
    hits += [hit("bac_chiu_lua", "IV", "NHÀ KHO A", 9), hit("bac_chiu_lua", "III", "Phòng ngủ", 30)]
    info = merge(hits, load_spec())
    assert {k.upper() for k in info.hang_muc} == {"NHÀ KHO A", "NHÀ KHO B", "NHÀ BẢO VỆ", "TRẠM BƠM"}


def _pdf_with_text(tmp_path, lines):
    pdf = tmp_path / "t.pdf"
    doc = fitz.open()
    for ln in lines:
        page = doc.new_page()
        if ln:
            page.insert_text((50, 100), ln, fontname="helv")
    doc.save(pdf)
    return pdf


def test_smart_pages_filters_when_text_readable(tmp_path):
    from pccc_checker.pdf.classify import smart_gemini_pages
    filler = "GHI CHU CUA BAN VE NHA TANG MAT CONG TRINH VA CAC CHI TIET KET CAU"
    lines = [filler] * 10
    lines[6] = "BANG THONG KE HANG MUC CONG TRINH " + filler
    pdf = _pdf_with_text(tmp_path, lines)
    pages, why = smart_gemini_pages(pdf, head=2)
    assert "lọc" in why and 1 in pages and 2 in pages and 5 not in pages


def test_smart_pages_falls_back_to_all_for_scans(tmp_path):
    from pccc_checker.pdf.classify import smart_gemini_pages
    pdf = _pdf_with_text(tmp_path, [""] * 8 + ["GHI CHU CUA BAN VE NHA TANG MAT CONG TRINH VA CHI TIET"] * 2)
    pages, why = smart_gemini_pages(pdf)
    assert pages == list(range(1, 11)) and "cả" in why
