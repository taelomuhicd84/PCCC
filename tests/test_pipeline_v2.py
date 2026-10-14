"""Pipeline 8 bước · 2 cổng: intake, facts, rule_keys, consistency (offline, không cần Gemini)."""
from pathlib import Path

import pymupdf
import pytest

from pccc_checker.config import PROJECT_ROOT
from pccc_checker.pdf.render import export_image_tables
from pccc_checker.pipeline import consistency, facts, intake, rule_keys

TEXT = ("MẶT BẰNG TẦNG 1 NHÀ XƯỞNG — bậc chịu lửa bậc IV, hạng nguy hiểm cháy nổ C, chiều cao PCCC 6,5 m, "
        "diện tích xây dựng 2000 m2, khối tích 24340 m3, số tầng 2")


def _png(w=1200, h=400) -> bytes:
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, w, h), False)
    pix.set_rect(pix.irect, (200, 220, 240))
    return pix.tobytes("png")


def _pdf(tmp_path: Path, rotate_img_page: int = 0) -> Path:
    doc = pymupdf.open()
    p = doc.new_page(width=842, height=595)                        # 1: LAYER
    p.insert_textbox(pymupdf.Rect(40, 40, 800, 300), TEXT * 2, fontname="tiro", fontsize=11)
    p = doc.new_page(width=842, height=595)                        # 2: HON-HOP (chữ + bảng ảnh lớn)
    p.insert_textbox(pymupdf.Rect(40, 40, 800, 200), TEXT * 2, fontname="tiro", fontsize=11)
    p.insert_image(pymupdf.Rect(100, 300, 700, 500), stream=_png())
    if rotate_img_page:
        p.set_rotation(rotate_img_page)
    doc.new_page(width=842, height=595)                            # 3: SCAN (không có chữ)
    f = tmp_path / "t.pdf"
    doc.save(f)
    return f


def test_intake_luong_va_hash(tmp_path):
    f = _pdf(tmp_path)
    idx = intake.page_index(f)
    assert [p["luong"] for p in idx] == ["LAYER", "HON-HOP", "SCAN"]
    (box,) = idx[1]["vung_anh"]
    assert all(0 <= v <= 1 for v in box) and box[0] == pytest.approx(100 / 842, abs=1e-3)
    assert intake.diff_hashes(idx, intake.page_index(f)) == []
    doc = pymupdf.open(f)
    doc[0].insert_text((50, 500), "SỬA ĐỔI", fontname="tiro")
    f2 = tmp_path / "t2.pdf"
    doc.save(f2)
    assert intake.diff_hashes(idx, intake.page_index(f2)) == [1]


def test_crops_trang_xoay_khong_cat_hut(tmp_path):
    """Trang xoay 270: ảnh 600x200 pt trên trang chưa xoay -> trên trang hiển thị thành 200x600 (dọc), không bị cắt."""
    f = _pdf(tmp_path, rotate_img_page=270)
    (png,) = export_image_tables(f, [2], tmp_path / "crops")
    pix = pymupdf.Pixmap(str(png))
    assert pix.height > 2.5 * pix.width


def fv(value, method="gemini", status="found", pages=(5,), page=5):
    return {"value": value, "page": page, "text": "x", "method": method, "status": status,
            "candidates": [{"value": value, "page": p, "method": method} for p in pages]}


@pytest.mark.parametrize("f,claude,want", [
    (fv("II", "user", "confirmed"), None, ("II", "H")),
    (fv(6.5, "vector"), None, (6.5, "H")),
    (fv(6.5), None, (6.5, "L")),
    (fv(6.5, pages=(5, 6)), None, (6.5, "M")),
    (fv(3.57), {"gia_tri": 3.57, "trang": 5}, (3.57, "H")),
    (fv(3.57), {"gia_tri": 6.5, "trang": 5}, (6.5, "M")),
    (fv(None, status="conflict"), None, (None, "L")),
    (fv(["F5.2"], "user", "confirmed"), None, ("F5.2", "H")),
])
def test_cell_do_tin_cay(f, claude, want):
    c, _ = facts.cell(f, claude)
    assert (c[0], c[3]) == want


def test_nhom_tinh_bang6():
    assert facts.nhom_tinh("KHÁCH SẠN HOÀNG HÙNG") == "F1.2"
    assert facts.nhom_tinh("Nhà xưởng 2") == "F5.1"
    assert facts.nhom_tinh("NHÀ KHO 1A") == "F5.2"
    assert facts.nhom_tinh("Nhà văn phòng") == "F4.3"
    assert facts.nhom_tinh("Trạm điện") is None


def _info(**hm):
    return {"hang_muc": hm, "khu_dat": {}, "meta": {}, "hang_muc_chinh": next(iter(hm))}


def test_build_facts_va_kiem_tra_logic():
    info = _info(**{"Nhà xưởng 2": {"chieu_cao_pccc": fv(14.0), "chieu_cao_cong_trinh": fv(13.07),
                                     "nhom_nha": fv("F5.1"), "dien_tich_xay_dung": fv(2000),
                                     "tong_dien_tich_san": fv(1500)}})
    f = facts.build_facts(info)
    h = f["hang_muc"][0]
    assert h["id"] == "HM01" and h["nhom_nha"]["tinh"] == "F5.1" and h["cao_pccc_m"][3] == "L"
    loi = {k["truong"] for k in f["kiem_tra"] if k["muc"] == "loi"}
    assert loi == {"cao_pccc_m", "dt_san_tong_m2", "hang_no"}
    assert "Cổng 1" in facts.gate1_md(f)


@pytest.mark.parametrize("cao,bo", [(None, None), (28, "k1"), (35.25, "k2"), (50, "k2"), (51, "k3"), (151, "ngoai-pham-vi")])
def test_bo_khach_san(cao, bo):
    assert rule_keys.bo_khach_san(cao) == bo


def _facts_ks(cao=35.25, nhom="F1.2"):
    info = _info(**{"KHÁCH SẠN": {"chieu_cao_pccc": fv(cao, "user", "confirmed"), "nhom_nha": fv(nhom, "user", "confirmed"),
                                   "bac_chiu_lua": fv("I", "user", "confirmed"),
                                   "cap_nguy_hiem_chay_ket_cau": fv("S0", "user", "confirmed")}})
    return facts.build_facts(info)


def test_rule_keys_khach_san_k2(tmp_path):
    rk = rule_keys.build_rule_keys(_facts_ks(), "x", tmp_path / "none.json")
    (h,) = rk["hang_muc"]
    assert (h["loai_hinh"], h["bo"], h["thieu"]) == ("khach-san", "k2", [])
    assert len(h["file"]["thoat-nan"]) == 3 and "gian-lanh-nan" not in h["file"]
    assert all((PROJECT_ROOT / p).exists() for fs in h["file"].values() for p in fs)


def test_rule_keys_override_va_loai_chua_co(tmp_path):
    ov = tmp_path / "ov.json"
    ov.write_text('{"x": [{"hm": "HM01", "truong": "nhom_nha", "gia_tri": "F5.1"}]}', encoding="utf-8")
    (h,) = rule_keys.build_rule_keys(_facts_ks(), "x", ov)["hang_muc"]
    assert h["loai_hinh"] == "nha-xuong" and h["nguon"]["nhom_nha"] == "override"
    assert h["thieu"] == ["hang_no"] and not h["file"]


def test_consistency_ha_kd_thieu_bang_chung():
    rules = {"K2-TNL-012"}
    ok = {"rule": "K2-TNL-012", "tt": "KD", "trang": 5, "bbox": [0.1, 0.1, 0.2, 0.2], "evid": "1 lối ra"}
    rows, log = consistency.validate([
        ok, dict(ok, bbox=None), dict(ok, rule="REVIEW-X"), dict(ok, tt="Đạt"), dict(ok, tt="XM", evid=None),
    ], rules)
    assert [r["tt"] for r in rows] == ["KD", "XM", "XM", "XM", "XM"]
    assert len(log) == 3 and "thiếu bbox" in rows[1]["ly_do"]
    assert len({r["id"] for r in rows}) == 5


def test_known_rules_gom_checklist_va_yaml():
    ids = consistency.known_rules()
    assert {"K2-TNL-012", "K3-TNL-001", "EXIT-DOOR-WIDTH"} <= ids


def test_from_engine_bo_dismissed_va_chuan_hoa_bbox():
    ext = {"pages": [{"page": 2, "width": 1000, "height": 500,
                      "elements": [{"id": "e1", "label": "D1 900x2100", "source": "vector", "confidence": 0.9}]}]}
    f = [{"rule_id": "EXIT-DOOR-WIDTH", "clause": "QCVN 06:2022 khoản 3.2.9", "message": "hẹp", "page": 2,
          "bbox": [100, 50, 200, 100], "element_ids": ["e1"], "status": "violation"},
         {"rule_id": "X", "clause": "", "message": "", "dismissed": True}]
    (r,) = consistency.from_engine(f, ext)
    assert r["tt"] == "KD" and r["bbox"] == [0.1, 0.1, 0.2, 0.2] and r["evid"] == "D1 900x2100"
    assert r["cd"] == "thoat-nan" and r["conf"] == "H"


def test_tai_lieu_va_khung_chuyen_de_ton_tai():
    for p in rule_keys.LUON_NAP + ["GEMINI.md", "memory/lessons.md", "memory/glossary.md", "memory/overrides.json"]:
        assert (PROJECT_ROOT / p).exists(), p
    for cd in rule_keys.CHUYEN_DE:
        s = PROJECT_ROOT / "skills" / "chuyen-de" / cd / "SKILL.md"
        assert s.exists() and len(s.read_text(encoding="utf-8").splitlines()) < 60, cd
