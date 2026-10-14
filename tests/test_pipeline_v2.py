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
    # 1 mục bảng = 1 chuyên đề; B7.2 có 17 mục (không có gian lánh nạn); mục dài tách phần .1 .2 …
    # 17 mục của B7.2 + an-toan-cong-nghe do mẫu B47 (cấp khí đốt trung tâm) luôn nạp
    assert len(h["ung_vien"]) == 18 and "gian-lanh-nan" not in h["ung_vien"]
    assert all("/he-thong/B47/" in p for p in h["ung_vien"]["an-toan-cong-nghe"])
    # mẫu hệ thống nạp kèm: B35 vào báo cháy, B34 vào chống tụ khói, B37 + B38 vào chữa cháy
    assert h["ung_vien"]["bao-chay"][0] == "rules/checklists/khach-san/k2/12-bao-chay.md"
    assert any("/he-thong/B35/" in p for p in h["ung_vien"]["bao-chay"])
    assert any("/he-thong/B34/" in p for p in h["ung_vien"]["chong-tu-khoi"])
    assert {"B37", "B38"} <= {p.split("/")[3] for p in h["ung_vien"]["chua-chay"] if "/he-thong/" in p}
    assert all(".".join(p.split("/")[-1].split(".")[:-2]) == "07-thoat-nan" for p in h["ung_vien"]["thoat-nan"])
    assert all((PROJECT_ROOT / p).exists() for fs in h["ung_vien"].values() for p in fs)


def test_rule_keys_override_va_loai_chua_co(tmp_path):
    ov = tmp_path / "ov.json"
    # người dùng chốt nhà hỗn hợp + nhóm F5.1: bảng theo overrides `loai_hinh`, F5 bắt buộc hạng nổ
    ov.write_text('{"x": [{"hm": "HM01", "truong": "nhom_nha", "gia_tri": "F5.1"},'
                  ' {"hm": "HM01", "truong": "loai_hinh", "gia_tri": "hon-hop"}]}', encoding="utf-8")
    (h,) = rule_keys.build_rule_keys(_facts_ks(), "x", ov)["hang_muc"]
    assert (h["loai_hinh"], h["bo"], h["mau"]) == ("hon-hop", "k2", "B5.2")
    assert h["nguon"]["nhom_nha"] == h["nguon"]["loai_hinh"] == "override"
    assert h["thieu"] == ["hang_no"] and h["ung_vien"]["quy-mo"] == ["rules/checklists/hon-hop/k2/01-quy-mo.md"]


@pytest.mark.parametrize("ten,cn,nhom,loai", [
    ("KHÁCH SẠN", "Tầng hầm: đậu xe ô tô; Tầng 3-7: nhà nghỉ", "F1.2", "khach-san"),   # tên thắng công năng phụ
    ("Khối nhà chính", "Bệnh viện đa khoa 200 giường", "F1.1", "benh-vien"),             # F1.1 cần công năng
    ("Khối A", "Trường mầm non", "F1.1", "nha-tre"),
    ("Khối B", "Chợ dân sinh", "F3.1", "cho"),
    ("Khối C", "Khu chỗ đỗ xe", "F3.1", None),                                           # "CHỖ" ≠ "CHỢ"; F3.1 không duy nhất
    ("Nhà 1", "", "F4.3", "van-phong"),                                                   # chỉ còn nhóm F duy nhất
    ("Nhà 2", "", "F1.1", None),                                                          # F1.1 = nhà trẻ hoặc bệnh viện
    ("Nhà 3", "", "F1.2; F3.2", None),                                                    # nhiều nhóm -> hỗn hợp?, người chốt
    ("Phòng bơm và bể nước ngầm PCCC 140m3", "Phòng bơm PCCC", None, "tram-bom"),
    # công trình đặc thù: từ khoá cụ thể thắng từ khoá chung ("KHO" ⊂ "KHO XĂNG DẦU")
    ("Kho xăng dầu Nhà Bè", "", "F5.2", "kho-xang-dau"),
    ("Kho chứa LPG 2000 tấn", "", None, "kho-lpg"),
    ("Trạm chiết nạp LPG", "", None, "tram-chiet-lpg"),
    ("Cửa hàng xăng dầu số 5", "", None, "cua-hang-xang-dau"),
    ("Nhà điều hành", "Nhà máy điện mặt trời 50 MWp", None, "dien-mat-troi"),
    ("Kho chứa vật liệu nổ công nghiệp", "", None, "kho-vlncn"),
    ("Kho chứa LNG", "", None, "kho-lng"),
    ("Trạm biến áp 110kV", "", None, "tram-bien-ap"),
    ("Hầm đường bộ Hải Vân", "", None, "ham-duong-bo"),
    ("Tàu chở khách du lịch", "", None, "ptt-cho-khach"),
    ("Tàu chở xăng dầu 500 tấn", "", None, "ptt-hang-nguy-hiem"),
])
def test_chon_bang_theo_cong_nang(ten, cn, nhom, loai):
    from pccc_checker.pipeline.loai_hinh import chon
    got, _, ghi = chon(ten, cn, nhom)
    assert got == loai, ghi
    if loai is None:
        assert ghi


def test_consistency_ha_kd_thieu_bang_chung():
    rules = {"KS2-TN-012"}
    ok = {"rule": "KS2-TN-012", "tt": "KD", "trang": 5, "bbox": [0.1, 0.1, 0.2, 0.2], "evid": "1 lối ra"}
    rows, log = consistency.validate([
        ok, dict(ok, bbox=None), dict(ok, rule="REVIEW-X"), dict(ok, tt="Đạt"), dict(ok, tt="XM", evid=None),
    ], rules)
    assert [r["tt"] for r in rows] == ["KD", "XM", "XM", "XM", "XM"]
    assert len(log) == 3 and "thiếu bbox" in rows[1]["ly_do"]
    assert len({r["id"] for r in rows}) == 5


def test_known_rules_gom_checklist_va_yaml():
    ids = consistency.known_rules()
    assert {"KS2-TN-012", "KS3-TN-001", "EXIT-DOOR-WIDTH"} <= ids


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


def test_chuyen_de_theo_ten_muc_bang_doi_chieu():
    from pccc_checker.pipeline.chuyen_de import muc_of
    # tên mục lớn thật trong các bảng B4–B18 (số thứ tự khác nhau giữa bảng, nhận theo tên)
    assert muc_of("Xác định chiều cao an toàn PCCC, số tầng, nhóm nhà") == "quy-mo"
    assert muc_of("Đường và bãi đỗ cho xe chữa cháy") == "giao-thong-xe-chua-chay"
    assert muc_of("Giải pháp thoát nạn") == muc_of("Lối, đường thoát nạn") == "thoat-nan"
    assert muc_of("Hệ thống đèn chiếu sáng sự cố và chỉ dẫn thoát nạn và hệ thống loa") == "chieu-sang-su-co"
    assert muc_of("Thang máy chữa cháy") == "thang-may-chua-chay"
    assert muc_of("Trang bị bình chữa cháy") == muc_of("Phương tiện chữa cháy ban đầu") == "binh-chua-chay"
    assert muc_of("Hệ thống chữa cháy bằng nước") == "chua-chay"
    assert muc_of("Hệ thống điện cho PCCC") == "cap-dien"
    assert muc_of("Mặt nạ lọc độc và mặt nạ phòng độc cách ly.") == "pha-do-bao-ho"
    assert muc_of("Nội dung lạ") is None


def test_bo_bang_khach_san_du_muc():
    d = PROJECT_ROOT / "rules" / "checklists" / "khach-san"
    for bo, n in (("k1", 17), ("k2", 17), ("k3", 18)):
        cds = {p.name.split(".")[0][3:] for p in (d / bo).glob("*.md")}
        assert cds <= set(rule_keys.CHUYEN_DE) and len(cds) == n, bo


def test_hang_muc_phong_bom_nap_mau_b36(tmp_path):
    info = _info(**{"PHÒNG BƠM PCCC": {"chieu_cao_pccc": fv(3, "user", "confirmed")}})
    (h,) = rule_keys.build_rule_keys(facts.build_facts(info), "x", tmp_path / "none.json")["hang_muc"]
    assert h["loai_hinh"] == "tram-bom" and h["ung_vien"]["tram-bom"]
    assert all("/he-thong/B36/" in p for p in h["ung_vien"]["tram-bom"])


def test_ten_file_md_khong_trung_giua_cac_mau():
    # B4.1 (chung cư) và B41 (chữa cháy khí) từng trùng "b41.md" -> bảng chung cư bị ghi đè (14/10/2026)
    from pccc_checker.pipeline.loai_hinh import HE_THONG, MAU, file_md
    names = [file_md(m) for m in list(MAU) + list(HE_THONG)]
    assert len(names) == len(set(names))
    assert file_md("B4.1") != file_md("B41")


def test_mau_he_thong_nap_dung_chuyen_de():
    d = PROJECT_ROOT / "rules" / "checklists" / "he-thong"
    assert (d / "B45" / "20-co-gioi.md").exists() and (d / "B45" / "16-pha-do-bao-ho.md").exists()
    assert (d / "B50" / "09-thang-may-chua-chay.md").exists()
    (h,) = rule_keys.build_rule_keys(_facts_ks(), "x", PROJECT_ROOT / "none.json")["hang_muc"]
    tm = h["ung_vien"]["thang-may-chua-chay"]
    assert tm[0].endswith("k2/09-thang-may-chua-chay.md") and any("/he-thong/B50/" in p for p in tm)
    assert any("/he-thong/B47/" in p for p in h["ung_vien"]["an-toan-cong-nghe"])   # B47 luôn nạp


def test_cong_ap_dung_theo_danh_gia_cong_nang():
    from pccc_checker.pipeline import danh_gia
    fx = _facts_ks()
    (h,) = rule_keys.build_rule_keys(fx, "x", PROJECT_ROOT / "none.json")["hang_muc"]
    # chưa đánh giá công năng -> KHÔNG chuyên đề nào áp dụng (người dùng 14/10/2026)
    assert h["file"] == {} and set(h["cho_danh_gia"]) == set(h["ung_vien"])
    dg = danh_gia.khung({"hang_muc": [h]})
    (d,) = dg["hang_muc"]
    assert "thoat-nan" in d["chuyen_de"] and {"B35", "B39", "B47"} <= set(d["he_thong"])
    assert d["he_thong"]["B35"]["doc_truoc"].endswith("B35/12-bao-chay.1.md")
    d["chuyen_de"]["thoat-nan"]["ap_dung"] = True
    d["chuyen_de"]["chua-chay"]["ap_dung"] = True
    d["he_thong"]["B39"]["ap_dung"] = True          # có sprinkler; B41 (khí) không điền -> không nạp
    d["chuyen_de"]["bao-chay"]["ap_dung"] = False
    d["he_thong"]["B47"]["ap_dung"] = False         # không có cấp khí trung tâm
    (h2,) = rule_keys.build_rule_keys(fx, "x", PROJECT_ROOT / "none.json", danh_gia=dg)["hang_muc"]
    assert set(h2["file"]) == {"thoat-nan", "chua-chay"}
    assert any("/B39/" in p for p in h2["file"]["chua-chay"]) and not any("/B41/" in p for p in h2["file"]["chua-chay"])
    assert {"bao-chay", "an-toan-cong-nghe"} <= set(h2["khong_ap_dung"])
    # chạy lại khung giữ quyết định đã điền
    assert danh_gia.khung({"hang_muc": [h2]}, dg)["hang_muc"][0]["chuyen_de"]["thoat-nan"]["ap_dung"] is True


def _facts_3hm():
    info = _info(**{n: {"chieu_cao_pccc": fv(c, "user", "confirmed"), "nhom_nha": fv(g, "user", "confirmed")}
                    for n, c, g in (("PHÒNG BƠM PCCC", 3, None), ("NHÀ KHO", 9, "F5.2"), ("NHÀ XƯỞNG", 9, "F5.1"))})
    return facts.build_facts(info)


def test_doi_tuong_phong_bom_hang_muc_rieng():
    # TH1: 3 hạng mục Phòng bơm PCCC, Nhà kho, Nhà xưởng -> chỉ hạng mục phòng bơm gọi tram-bom (+ B36)
    from pccc_checker.pipeline import danh_gia
    fx = _facts_3hm()
    dm = [{"trang": 12, "ten_ban_ve": "MẶT BẰNG BỐ TRÍ MÁY BƠM", "hang_muc": "NHÀ XƯỞNG"}]
    rk = rule_keys.build_rule_keys(fx, "x", PROJECT_ROOT / "none.json", danh_muc=dm)
    by = {h["ten"]: h for h in rk["hang_muc"]}
    pb = by["PHÒNG BƠM PCCC"]
    assert pb["loai_hinh"] == "tram-bom" and any("/B36/" in p for p in pb["ung_vien"]["tram-bom"])
    assert any("tr.12" in c for c in pb["doi_tuong"]["tram-bom"])        # bản vẽ máy bơm -> hạng mục phòng bơm
    assert "tram-bom" not in by["NHÀ XƯỞNG"]["ung_vien"] and "tram-bom" not in by["NHÀ KHO"]["ung_vien"]
    (d,) = [x for x in danh_gia.khung(rk)["hang_muc"] if x["ten"] == "PHÒNG BƠM PCCC"]
    assert d["he_thong"]["B36"]["ap_dung"] is True and d["he_thong"]["B36"]["nguon"] == "dau_hieu"


def test_doi_tuong_phong_bom_trong_hang_muc():
    # TH2: phòng bơm là 1 phòng trong nhà xưởng (bảng B17 không có mục trạm bơm) -> nhà xưởng vẫn gọi tram-bom + B36
    from pccc_checker.pipeline import danh_gia
    info = _info(**{"NHÀ XƯỞNG": {"chieu_cao_pccc": fv(9, "user", "confirmed"), "nhom_nha": fv("F5.1", "user", "confirmed")}})
    fx = facts.build_facts(info)
    kv = [{"ten": "PHÒNG BƠM CHỮA CHÁY", "thuoc": "NHÀ XƯỞNG", "page": 5}]
    rk = rule_keys.build_rule_keys(fx, "x", PROJECT_ROOT / "none.json", khu_vuc=kv)
    (h,) = rk["hang_muc"]
    assert h["loai_hinh"] == "nha-xuong" and any("/B36/" in p for p in h["ung_vien"]["tram-bom"])
    assert h["doi_tuong"]["tram-bom"] == ["khu vực trong hạng mục: PHÒNG BƠM CHỮA CHÁY (tr.5)"]
    dg = danh_gia.khung(rk)
    (h2,) = rule_keys.build_rule_keys(fx, "x", PROJECT_ROOT / "none.json", danh_gia=dg, khu_vuc=kv)["hang_muc"]
    assert "tram-bom" in h2["file"] and set(h2["file"]) == {"tram-bom"}   # chỉ chuyên đề có đối tượng tự áp dụng
