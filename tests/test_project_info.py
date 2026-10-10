"""Test bước `info` (offline): regex nhãn - giá trị, chuẩn hoá, conflict, project.yaml, cannot_check."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from pccc_checker.config import RULES_DIR
from pccc_checker.models import BuildingInfo, DrawingExtraction, Element, PageExtraction
from pccc_checker.pdf.vn_encoding import vni_to_unicode
from pccc_checker.project_info import (CONFIRMED, CONFLICT, FOUND, MISSING, ProjectInfo, apply_user, load_spec,
                                       match_text, merge, parse_number, row_strings, scan_page, tag_hang_muc)
from pccc_checker.rules import load_rules, run_rules

SPEC = load_spec()
RULES = [RULES_DIR / "qcvn06_2022_sd01_2023.yaml"]


def _m(text: str) -> dict:
    return {k: v for k, v, _ in match_text(text)}


def _hit(key, value, page, method="vector"):
    return {"key": key, "value": value, "unit": None, "page": page, "text": f"{key}={value}", "method": method}


# ------------------------------------------------------------------ regex + chuẩn hoá
@pytest.mark.parametrize("text,key,value", [
    ("Bậc chịu lửa: II", "bac_chiu_lua", "II"),
    ("BẬC CHỊU LỬA CÔNG TRÌNH: BẬC III", "bac_chiu_lua", "III"),
    ("- Công trình có bậc chịu lửa bậc IV.", "bac_chiu_lua", "IV"),
    ("NHÓM NHÀ | F2.1", "nhom_nha", ["F2.1"]),
    ("Karaoke thuộc nhóm nhà F2.1 có chiều cao PCCC là 6m < 15m", "nhom_nha", ["F2.1"]),
    ("Nhóm nguy hiểm cháy theo công năng: F1.3; F4.3", "nhom_nha", ["F1.3", "F4.3"]),
    ("Karaoke thuộc nhóm nhà F2.1 có chiều cao PCCC là 6m < 15m", "chieu_cao_pccc", 6.0),
    ("CHIỀU CAO PCCC (M) | 6", "chieu_cao_pccc", 6.0),
    ("Chiều cao PCCC: 12,5 m", "chieu_cao_pccc", 12.5),
    ("CHIỀU CAO PCCC=6M", "chieu_cao_pccc", 6.0),
    ("Chiều cao công trình: 15,3m", "chieu_cao_cong_trinh", 15.3),
    ("CẤP NGUY HIỂM CHÁY | S0", "cap_nguy_hiem_chay_ket_cau", "S0"),
    ("Cấp nguy hiểm cháy kết cấu của nhà: S1", "cap_nguy_hiem_chay_ket_cau", "S1"),
    ('CÓ CẤP NGUY HIỂM CHÁY "SO" ĐẢM BẢO', "cap_nguy_hiem_chay_ket_cau", "S0"),      # chữ O gõ nhầm số 0
    ("Hạng nguy hiểm cháy nổ: C1", "hang_chay_no", "C1"),
    ("HẠNG NGUY HIỂM CHÁY VÀ CHÁY NỔ CỦA NHÀ: hạng D", "hang_chay_no", "D"),
    ("Diện tích xây dựng: 450,5 m2", "dien_tich_xay_dung", 450.5),
    ("DIỆN TÍCH XÂY DỰNG | 1.433 m²", "dien_tich_xay_dung", 1433.0),
    ("Tổng diện tích sàn: 1.234,5m2", "tong_dien_tich_san", 1234.5),
    ("KHỐI TÍCH  ( M3 ) | 4811.83", "khoi_tich", 4811.83),
    ("Khối tích: 4.811,83 m³", "khoi_tich", 4811.83),
    ("Khối tích công trình: 12500 m3", "khoi_tich", 12500.0),
    ("SỐ TẦNG | 02 | BẢNG H.7", "so_tang_noi", 2),
    ("Quy mô: 5 tầng nổi, 1 tầng hầm", "so_tang_noi", 5),
    ("Quy mô: 5 tầng nổi, 1 tầng hầm", "so_tang_ham", 1),
    ("Số tầng hầm: không có", "so_tang_ham", 0),
    ("CÔNG TRÌNH: KARAOKE HOÀNG ANH 2", "ten_cong_trinh", "KARAOKE HOÀNG ANH 2"),
    ("CÔNG NĂNG | KARAOKE", "cong_nang", "KARAOKE"),
    ("***Tổng diện tích khu đất hạng mục thẩm duyệt PCCC: 1433.4m2.", "dien_tich_khu_dat", 1433.4),
    ("TỔNG DIỆN TÍCH KHU ĐẤT | 1433.4 (M2)", "dien_tich_khu_dat", 1433.4),
    ("CHIỀU CAO MÁI (M) | 8.55", "chieu_cao_cong_trinh", 8.55),
    ("Tầng tum: 01 tầng tum thang", "tang_tum_ky_thuat", "01 tầng tum thang"),
])
def test_regex(text, key, value):
    assert _m(text).get(key) == value


@pytest.mark.parametrize("text,key", [
    ("* Công trình có cấp nguy hiểm cháy S0 theo bảng 5", "ten_cong_trinh"),   # không có "CÔNG TRÌNH:"
    ("HẠNG MỤC CÔNG TRÌNH XIN PHÉP", "hang_chay_no"),
    ("MẶT BẰNG TẦNG 2", "so_tang_noi"),
    ("YÊU CẦU THIẾT KẾ: BẬC II", "bac_chiu_lua"),                            # bảng tham chiếu Bảng 4
    ("CHIỀU CAO MÁI (M) | 8.55", "chieu_cao_pccc"),
])
def test_regex_no_false_match(text, key):
    assert key not in _m(text)


def test_vni_decoded_text():
    raw = "BAÄC CHÒU LÖÛA: II"                     # font VNI-Times trong PDF CAD
    text = vni_to_unicode(raw)
    assert text == "BẬC CHỊU LỬA: II"
    assert _m(text)["bac_chiu_lua"] == "II"


@pytest.mark.parametrize("s,dot,val", [
    ("12,5", False, 12.5), ("12.5", False, 12.5), ("1.234,5", False, 1234.5), ("1,234.5", False, 1234.5),
    ("1.433", True, 1433.0), ("1.433", False, 1.433), ("4811.83", True, 4811.83), ("1,234,567", False, 1234567.0),
])
def test_parse_number(s, dot, val):
    assert parse_number(s, thousands_dot=dot) == pytest.approx(val)


def test_row_strings_join_table_cells():
    texts = [{"text": "BẬC CHỊU LỬA", "bbox": [729, 642, 784, 650]},
             {"text": "II", "bbox": [896, 640, 900, 648]},
             {"text": "CẤP NGUY HIỂM CHÁY", "bbox": [729, 661, 814, 669]},
             {"text": "S0", "bbox": [893, 660, 902, 667]}]
    assert "BẬC CHỊU LỬA | II" in row_strings(texts)
    got = {h["key"]: h["value"] for h in scan_page(texts, 5)}
    assert got == {"bac_chiu_lua": "II", "cap_nguy_hiem_chay_ket_cau": "S0"}


# ------------------------------------------------------------------ hợp nhất
def test_conflict_between_pages():
    info = merge([_hit("chieu_cao_pccc", 6.0, 5), _hit("chieu_cao_pccc", 5.1, 43), _hit("chieu_cao_pccc", 6.0, 15)],
                 SPEC)
    fv = info.get("chieu_cao_pccc")
    assert fv.status == CONFLICT and fv.value is None
    assert sorted((c["page"], c["value"]) for c in fv.candidates) == [(5, 6.0), (15, 6.0), (43, 5.1)]
    assert "chieu_cao_pccc" in info.problems(SPEC)
    assert info.to_building(SPEC)["height_pccc_m"] is None             # không tự chọn


def test_same_value_on_many_pages_is_found():
    info = merge([_hit("bac_chiu_lua", "II", 5), _hit("bac_chiu_lua", "II", 10)], SPEC)
    fv = info.get("bac_chiu_lua")
    assert fv.status == FOUND and fv.value == "II" and fv.page == 5


def test_invalid_value_dropped_with_warning():
    info = merge([_hit("bac_chiu_lua", "VI", 3), _hit("nhom_nha", ["F6.1"], 3),
                  _hit("cap_nguy_hiem_chay_ket_cau", "S4", 3)], SPEC)
    assert info.get("bac_chiu_lua").status == MISSING
    assert info.get("nhom_nha").status == MISSING
    assert info.get("cap_nguy_hiem_chay_ket_cau").status == MISSING
    assert len(info.warnings) == 3


@pytest.mark.parametrize("nhom,required", [(["F5.1"], True), (["F5.3"], True), (["F2.1"], False), (["F1.3"], False)])
def test_hang_chay_no_required_only_for_f5(nhom, required):
    info = merge([_hit("nhom_nha", nhom, 1)], SPEC)
    assert ("hang_chay_no" in info.required_keys(SPEC)) is required
    assert ("hang_chay_no" in info.problems(SPEC)) is required


def test_project_yaml_overrides():
    info = merge([_hit("chieu_cao_pccc", 6.0, 5), _hit("chieu_cao_pccc", 5.1, 43), _hit("bac_chiu_lua", "II", 5)], SPEC)
    apply_user(info, {"fire_inputs": {"chieu_cao_pccc": 6, "bac_chiu_lua": "iii", "nhom_nha": "F2.1"},
                      "ten_cong_trinh": "Karaoke"}, SPEC)
    h, b, n = info.get("chieu_cao_pccc"), info.get("bac_chiu_lua"), info.get("nhom_nha")
    assert (h.status, h.value, h.method) == (CONFIRMED, 6, "user") and len(h.candidates) == 2
    assert (b.status, b.value) == (CONFIRMED, "III")                     # ghi đè giá trị đọc được
    assert n.value == ["F2.1"] and info.get("ten_cong_trinh").value == "Karaoke"
    assert info.to_building(SPEC)["function_group"] == "F2.1"


def test_project_yaml_invalid_value_rejected():
    info = merge([], SPEC)
    apply_user(info, {"bac_chiu_lua": "VII"}, SPEC)
    assert info.get("bac_chiu_lua").status == MISSING and info.warnings


def test_roundtrip_json():
    info = merge([_hit("nhom_nha", ["F2.1"], 5), _hit("chieu_cao_pccc", 6.0, 5)], SPEC)
    info.meta = {"pdf_hash": "abc"}
    again = ProjectInfo.from_dict(json.loads(json.dumps(info.to_dict())))
    assert again.get("nhom_nha").value == ["F2.1"] and again.meta["pdf_hash"] == "abc"
    assert info.to_dict()["schema_version"] == 1


# ------------------------------------------------------------------ nhiều hạng mục
def _hang_muc_hits():
    hits = [_hit("ten_cong_trinh", "KARAOKE HOÀNG ANH 2 VÀ CÁC CÔNG TRÌNH PHỤ TRỢ", 1),
            _hit("bac_chiu_lua", "II", 10)]                                       # thuyết minh chung
    for page, cn, nhom, h, kt in ((5, "KARAOKE", "F2.1", 6.0, 4811.83), (43, "NHÀ Ở", "F1.4", 5.1, 346.55),
                                  (44, "NHÀ Ở", "F1.4", 5.1, 346.55), (56, "NHÀ XE", "F5.3", 3.2, 26.79)):
        hits += [_hit("cong_nang", cn, page), _hit("nhom_nha", [nhom], page), _hit("chieu_cao_pccc", h, page),
                 _hit("khoi_tich", kt, page), _hit("bac_chiu_lua", "II", page)]
    tag_hang_muc(hits)
    return hits


def test_hang_muc_values_differ_without_conflict():
    info = merge(_hang_muc_hits(), SPEC)
    assert info.hang_muc_chinh == "KARAOKE"                                      # khớp tên công trình
    assert set(info.hang_muc) == {"KARAOKE", "NHÀ Ở", "NHÀ XE"}
    for key, want in (("cong_nang", "KARAOKE"), ("nhom_nha", ["F2.1"]), ("chieu_cao_pccc", 6.0),
                      ("khoi_tich", 4811.83), ("bac_chiu_lua", "II")):
        fv = info.get(key)
        assert (fv.status, fv.value) == (FOUND, want), key
    assert info.hang_muc["NHÀ Ở"]["chieu_cao_pccc"].value == 5.1
    assert info.hang_muc["NHÀ XE"]["nhom_nha"].value == ["F5.3"]
    assert "chieu_cao_pccc" not in info.problems(SPEC)
    assert any("nhiều hạng mục" in w for w in info.warnings)
    again = ProjectInfo.from_dict(json.loads(json.dumps(info.to_dict())))
    assert again.hang_muc_chinh == "KARAOKE" and again.hang_muc["NHÀ Ở"]["khoi_tich"].value == 346.55


def test_hang_muc_main_by_volume_and_by_user():
    hits = [h for h in _hang_muc_hits() if h["key"] != "ten_cong_trinh"]
    assert merge(hits, SPEC).hang_muc_chinh == "KARAOKE"                         # khối tích lớn nhất
    info = merge(hits, SPEC, hang_muc_chinh="nhà ở")
    assert info.hang_muc_chinh == "NHÀ Ở" and info.get("chieu_cao_pccc").value == 5.1


def test_conflict_inside_same_hang_muc_still_reported():
    hits = _hang_muc_hits() + [_hit("cong_nang", "KARAOKE", 6), _hit("chieu_cao_pccc", 7.5, 6)]
    tag_hang_muc(hits)
    assert merge(hits, SPEC).get("chieu_cao_pccc").status == CONFLICT


def test_general_page_conflicts_with_main():
    hits = _hang_muc_hits() + [_hit("bac_chiu_lua", "III", 12)]                  # thuyết minh chung ghi khác
    assert merge(hits, SPEC).get("bac_chiu_lua").status == CONFLICT


def test_project_yaml_khu_dat_and_hang_muc():
    info = merge(_hang_muc_hits(), SPEC)
    apply_user(info, {"khu_dat": {"dien_tich_khu_dat": 1433.4},
                      "hang_muc": {"karaoke": {"fire_inputs": {"chieu_cao_pccc": 6.5}},
                                   "NHÀ Ở": {"fire_inputs": {"bac_chiu_lua": "iii"}},
                                   "Nhà bơm": {"project_info": {"so_tang_noi": 1}, "fire_inputs": {"nhom_nha": "F5.2"}}}},
               SPEC)
    assert info.get("dien_tich_khu_dat").value == 1433.4 and info.get("dien_tich_khu_dat").status == CONFIRMED
    assert info.hang_muc["KARAOKE"]["chieu_cao_pccc"].value == 6.5            # tên khớp không phân biệt hoa/thường
    assert info.get("chieu_cao_pccc").value == 6.5                              # hạng mục chính -> thông tin chung
    assert info.hang_muc["NHÀ Ở"]["bac_chiu_lua"].value == "III" and info.get("bac_chiu_lua").value == "II"
    assert info.hang_muc["Nhà bơm"]["nhom_nha"].value == ["F5.2"]               # hạng mục chỉ có trong project.yaml


def test_project_yaml_switch_main_hang_muc():
    info = merge(_hang_muc_hits(), SPEC)
    apply_user(info, {"hang_muc_chinh": "nhà ở", "fire_inputs": {"chieu_cao_pccc": 5.5}}, SPEC)
    assert info.hang_muc_chinh == "NHÀ Ở" and info.get("nhom_nha").value == ["F1.4"]
    assert info.get("chieu_cao_pccc").value == 5.5 and info.hang_muc["NHÀ Ở"]["chieu_cao_pccc"].value == 5.5


def test_khu_dat_key_rejected_inside_hang_muc():
    info = merge(_hang_muc_hits(), SPEC)
    apply_user(info, {"hang_muc": {"KARAOKE": {"ten_cong_trinh": "X"}}}, SPEC)
    assert any("không dùng ở đây" in w for w in info.warnings)


def test_example_project_yaml_is_valid():
    from pccc_checker.config import CONFIG_DIR
    info = merge(_hang_muc_hits(), SPEC)
    n = len(info.warnings)
    apply_user(info, yaml.safe_load((CONFIG_DIR / "project.example.yaml").read_text(encoding="utf-8")), SPEC)
    assert info.warnings[n:] == [] and info.hang_muc_chinh == "KARAOKE"


# ------------------------------------------------------------------ cannot_check
# ------------------------------------------------------------------ bảng dạng cột, câu ghi chú, hạng mục đánh số
def _t(text, x0, y0, x1, y1):
    return {"text": text, "bbox": [x0, y0, x1, y1]}


# Bảng thống kê hạng mục dạng cột (rút từ hồ sơ Nhà hàng Thiên Ý tr.3): "HẠNG C" là ô gộp chung NH01 + NH02
COLUMN_TABLE = [
    _t("HẠNG MỤC", 1037, 747, 1089, 762),
    _t("CHIỀU CAO", 1206, 739, 1256, 754), _t("MÁI (m)", 1213, 753, 1249, 768),
    _t("CHIỀU CAO", 1265, 739, 1315, 754), _t("PCCC (m)", 1270, 752, 1311, 766),
    _t("SỐ", 1348, 741, 1361, 756), _t("TẦNG", 1342, 755, 1368, 770),
    _t("KHỐI TÍCH", 1389, 741, 1430, 753), _t("(m3)", 1401, 752, 1418, 766),
    _t("HẠNG NGUY", 1438, 737, 1486, 749), _t("HIỂM", 1452, 748, 1473, 761), _t("CHÁY, NỔ", 1443, 760, 1482, 773),
    _t("NHÀ HÀNG 01", 1032, 778, 1096, 793), _t("7", 1232, 780, 1236, 791), _t("5", 1288, 780, 1292, 791),
    _t("01", 1351, 780, 1359, 791), _t("9587.2", 1397, 780, 1421, 791),
    _t("HẠNG C", 1449, 795, 1477, 806),
    _t("NHÀ HÀNG 02", 1032, 807, 1096, 822), _t("6", 1232, 809, 1236, 820), _t("5", 1288, 809, 1292, 820),
    _t("01", 1351, 809, 1359, 820), _t("1622.78", 1395, 809, 1423, 820),
    _t("NHÀ XE 01 & 02", 1033, 836, 1104, 851), _t("3.5", 1284, 838, 1295, 849), _t("11163.42", 1393, 838, 1425, 849),
    _t("HẠNG C", 1449, 838, 1477, 849),
    _t("BỂ NƯỚC NGẦM PCCC", 1030, 865, 1132, 880), _t("-", 1288, 864, 1291, 875), _t("36", 1405, 864, 1415, 877),
    _t("TỔNG DIỆN TÍCH ĐẤT : 6075 M2", 1003, 941, 1206, 960),
]


def test_column_table():
    from pccc_checker.project_info import column_tables
    got = {(h["hang_muc"], h["key"]): h["value"] for h in column_tables(COLUMN_TABLE, 3)}
    assert got[("NHÀ HÀNG 01", "chieu_cao_pccc")] == 5.0 and got[("NHÀ HÀNG 01", "chieu_cao_cong_trinh")] == 7.0
    assert got[("NHÀ HÀNG 01", "khoi_tich")] == 9587.2 and got[("NHÀ HÀNG 01", "so_tang_noi")] == 1
    assert got[("NHÀ HÀNG 02", "khoi_tich")] == 1622.78
    assert got[("NHÀ HÀNG 01", "hang_chay_no")] == "C" and got[("NHÀ HÀNG 02", "hang_chay_no")] == "C"   # ô gộp
    assert got[("NHÀ XE 01 & 02", "hang_chay_no")] == "C" and got[("BỂ NƯỚC NGẦM PCCC", "khoi_tich")] == 36.0
    assert ("BỂ NƯỚC NGẦM PCCC", "chieu_cao_pccc") not in got                                       # ô "-"


def test_column_table_needs_two_known_columns():
    from pccc_checker.project_info import column_tables
    title_block = [_t("HẠNG MỤC", 1046, 765, 1082, 772), _t("& CÁC CÔNG TRÌNH PHỤ TRỢ", 1051, 642, 1151, 649)]
    assert column_tables(title_block, 1) == []


@pytest.mark.parametrize("line,names", [
    ("Nhà hàng 1 & 2 thuộc nhóm nhà F3.2 có chiều cao PCCC là", ["Nhà hàng 1", "Nhà hàng 2"]),
    ("- Nhà xe 01 & 02 có chiều cao PCCC là 3.5m < 10m.", ["Nhà xe 1", "Nhà xe 2"]),
    ("Nhà hàng có bậc chịu lửa bậc IV, cấp nguy hiểm cháy S0:", ["Nhà hàng"]),
    ("Karaoke thuộc nhóm nhà F2.1 có chiều cao PCCC là 6m", ["Karaoke"]),
    ("* Công trình có cấp nguy hiểm cháy S0 theo bảng 5", []),                  # "Công trình" chung -> không gán
    ("3.Công trình có chiều cao PCCC <15m", []),
])
def test_subject_names(line, names):
    from pccc_checker.project_info import subject_names
    assert subject_names(line) == names


def test_sentence_with_subject_tags_hang_muc():
    texts = [_t("- Nhà hàng 02 có chiều cao PCCC là 5m < 10m.", 39, 969, 360, 990)]
    h = scan_page(texts, 9)
    assert [(x["key"], x["value"], x.get("hang_muc")) for x in h] == [("chieu_cao_pccc", 5.0, "Nhà hàng 02")]
    assert _m("3.Công trình có chiều cao PCCC <15m").get("chieu_cao_pccc") is None       # giới hạn, không phải giá trị


def test_numbered_hang_muc_not_merged_and_bare_name_applies_to_all():
    hits = [dict(_hit("chieu_cao_pccc", 5.0, 3), hang_muc="NHÀ HÀNG 01"),
            dict(_hit("chieu_cao_pccc", 5.0, 3), hang_muc="NHÀ HÀNG 02"),
            dict(_hit("nhom_nha", ["F3.2"], 5), hang_muc="Nhà hàng 1"),
            dict(_hit("nhom_nha", ["F3.2"], 5), hang_muc="Nhà hàng 2"),
            dict(_hit("bac_chiu_lua", "IV", 8), hang_muc="Nhà hàng"),             # tên trần -> áp cho cả NH01, NH02
            dict(_hit("chieu_cao_pccc", 3.5, 3), hang_muc="NHÀ XE 01 & 02"),
            dict(_hit("khoi_tich", 11163.42, 3), hang_muc="NHÀ XE 01 & 02"),      # tổng 2 nhà -> không chép
            _hit("ten_cong_trinh", "NHÀ HÀNG THIÊN Ý", 1)]
    info = merge(hits, SPEC)
    assert sorted(info.hang_muc) == ["NHÀ HÀNG 01", "NHÀ HÀNG 02", "NHÀ XE 1", "NHÀ XE 2"]
    for n in ("NHÀ HÀNG 01", "NHÀ HÀNG 02"):
        hm = info.hang_muc[n]
        assert hm["bac_chiu_lua"].value == "IV" and hm["nhom_nha"].value == ["F3.2"] and hm["chieu_cao_pccc"].value == 5.0
    assert info.hang_muc["NHÀ XE 1"]["chieu_cao_pccc"].value == 3.5
    assert info.hang_muc["NHÀ XE 1"]["khoi_tich"].status == MISSING
    assert info.hang_muc_chinh.startswith("NHÀ HÀNG")


def test_prefix_merge_only_for_words():
    hits = [dict(_hit("nhom_nha", ["F1.4"], 43), hang_muc="NHÀ Ở"),
            dict(_hit("khoi_tich", 346.55, 6), hang_muc="NHÀ Ở NHÂN VIÊN"),
            dict(_hit("bac_chiu_lua", "IV", 6), hang_muc="Mái che"),
            dict(_hit("khoi_tich", 522.63, 6), hang_muc="MÁI CHE (KHÔNG CHỨA XE)")]
    info = merge(hits, SPEC)
    assert sorted(info.hang_muc) == ["MÁI CHE (KHÔNG CHỨA XE)", "NHÀ Ở NHÂN VIÊN"]


def test_tag_by_page_title():
    from pccc_checker.project_info import tag_by_title
    hits = [dict(_hit("khoi_tich", 346.55, 6), hang_muc="NHÀ Ở NHÂN VIÊN"),
            dict(_hit("khoi_tich", 26.79, 6), hang_muc="PHÒNG TRỰC PCCC"),
            _hit("chieu_cao_pccc", 5.1, 50), _hit("chieu_cao_pccc", 3.2, 56), _hit("chieu_cao_pccc", 6.0, 15)]
    tag_by_title(hits, {50: "MẶT ĐỨNG TRỤC A-B VÀ B-A NHÀ Ở NHÂN VIÊN", 56: "MẶT BẰNG PHÒNG TRỰC PCCC",
                        15: "MẶT ĐỨNG TRỤC A-F"})
    assert [h.get("hang_muc") for h in hits[2:]] == ["NHÀ Ở NHÂN VIÊN", "PHÒNG TRỰC PCCC", None]


def test_verify_gemini_drops_values_not_on_page():
    from pccc_checker.project_info import verify_gemini
    blob = "CHIỀU CAO MÁI (m) 3.50 | KHỐI TÍCH 11163.42 | TỔNG DIỆN TÍCH KHU ĐẤT: 1433.4m2 | BẬC CHỊU LỬA II | F3.2"
    pages = {4: blob + " " * 50}
    hits = [dict(_hit("chieu_cao_cong_trinh", 3.5, 4, "gemini"), text="CHIỀU CAO MÁI (m) 3.50"),
            dict(_hit("khoi_tich", 11163.42, 4, "gemini"), text="KHỐI TÍCH 11163.42"),
            dict(_hit("dien_tich_khu_dat", 1433.4, 4, "gemini"), text="TỔNG DIỆN TÍCH KHU ĐẤT: 1433.4m2"),
            _hit("nhom_nha", ["F3.2"], 4, "gemini"),
            _hit("nhom_nha", ["F5.2"], 4, "gemini"),            # không có trên trang -> Gemini tự suy
            dict(_hit("bac_chiu_lua", "IV", 4, "gemini"), text="BẬC CHỊU LỬA IV"),   # "II" có nhưng "IV" không
            _hit("bac_chiu_lua", "IV", 4, "vector")]            # vector không bị kiểm
    warns = verify_gemini(hits, pages)
    assert [(h["key"], h["method"]) for h in hits] == [("chieu_cao_cong_trinh", "gemini"), ("khoi_tich", "gemini"),
                                                       ("dien_tich_khu_dat", "gemini"), ("nhom_nha", "gemini"),
                                                       ("bac_chiu_lua", "vector")]
    assert len(warns) == 2 and "F5.2" in warns[0]
    # đúng số nhưng câu căn cứ không có nhãn của trường ("LẦU 2" -> số tầng 2) -> bỏ
    h2 = [dict(_hit("so_tang_noi", 2, 4, "gemini"), text="MẶT BẰNG LẦU 2"),
          dict(_hit("tong_dien_tich_san", 200.0, 4, "gemini"), text="DIỆN TÍCH MỖI TẦNG: 200M2")]
    assert len(verify_gemini(h2, {4: "MẶT BẰNG LẦU 2 | DIỆN TÍCH MỖI TẦNG: 200M2" + " " * 50})) == 2 and h2 == []


def test_regex_land_area_variants():
    assert _m("TỔNG DIỆN TÍCH ĐẤT : 6075 M2")["dien_tich_khu_dat"] == 6075.0
    assert "dien_tich_khu_dat" not in _m("DIỆN TÍCH ĐẤT KHÔNG XÂY DỰNG GIỮA KARAOKE | 224.66 M2")
    assert "khoi_tich" not in _m("KHỐI TÍCH | 01:2023 QC06-BXD/2022:")             # số hiệu văn bản


# ------------------------------------------------------------------ nhà hỗn hợp theo tầng (hồ sơ VP The Sun)
FLOOR_TABLE = [
    _t("TẦNG", 792, 49, 840, 73), _t("DIỆN TÍCH", 928, 31, 1012, 54), _t("(M2)", 954, 50, 985, 75),
    _t("KHỐI TÍCH", 1142, 31, 1227, 54), _t("(M3)", 1170, 51, 1199, 76), _t("CÔNG NĂNG", 1353, 40, 1457, 63),
    _t("CHẤP THUẬN / FOR APPROVAL", 1517, 50, 1581, 58), _t("CHỦ ĐẦU TƯ", 1550, 96, 1613, 109),
    _t("NHÀ Ở", 1378, 95, 1439, 119), _t("TẦNG BÁN HẦM", 779, 102, 912, 126), _t("536.5", 1162, 103, 1206, 127),
    _t("( F1.4)", 1379, 111, 1431, 134),
    _t("TẦNG TRỆT", 782, 162, 881, 186), _t("SẢNH", 1384, 162, 1432, 186),
    _t("VĂN PHÒNG", 1354, 215, 1459, 239), _t("TẦNG LỬNG", 785, 222, 889, 245), _t("( F4.3)", 1379, 231, 1431, 255),
    _t("LẦU 1", 789, 282, 837, 305), _t("NHÀ Ở", 1378, 275, 1440, 299), _t("( F1.4)", 1380, 291, 1431, 315),
]


def test_floor_table_gives_building_groups_not_hang_muc():
    from pccc_checker.project_info import column_tables
    hits = [h for h in column_tables(FLOOR_TABLE, 5) if h["key"] == "nhom_nha"]
    assert [(h["key"], h["value"], h.get("hang_muc")) for h in hits] == [("nhom_nha", ["F1.4", "F4.3"], None)]
    assert "TẦNG BÁN HẦM F1.4" in hits[0]["text"]


SUN_FLOORS = [("TẦNG BÁN HẦM", 185.0), ("TẦNG TRỆT", 178.56), ("TẦNG LỬNG", 134.23), ("LẦU 1", 200.0),
              ("LẦU 2", 200.0), ("LẦU 3", 200.0), ("LẦU 4", 200.0), ("LẦU 5", 200.0), ("SÂN THƯỢNG", 43.2)]


def test_count_floors_the_sun():
    """Hồ sơ The Sun: bản vẽ ghi TỔNG SỐ TẦNG 8 TẦNG (QCVN 06 1.4.50)."""
    from pccc_checker.project_info import count_floors
    r = count_floors(SUN_FLOORS, SPEC["so_tang"])
    assert (r["so_tang_nha"], r["so_tang_noi"], r["so_tang_ham"], r["so_tang_ban_ham"]) == (8, 7, 0, 1)
    assert "21.6%" in r["tum"] and "không tính" in r["tum"]          # 43.2 / 200 <= 30%
    assert any("SÂN THƯỢNG" in a for a in r["assumptions"])


def test_count_floors_lung_tum_ham_rules():
    from pccc_checker.project_info import count_floors
    rules = SPEC["so_tang"]
    floors = [("TẦNG HẦM 2", 500), ("TẦNG HẦM 1", 500), ("TẦNG 1", 400), ("TẦNG LỬNG", 30),   # lửng 7.5% <= 10%
              ("TẦNG 2", 400), ("TẦNG LỬNG KỸ THUẬT", 35), ("TẦNG 3", 400), ("TUM", 150), ("MÁI", None)]
    r = count_floors(floors, rules)
    assert r["so_tang_ham"] == 2 and r["so_tang_ban_ham"] == 0
    # chỉ 01 lửng được miễn; tum 150/400 = 37.5% > 30% -> tính
    assert (r["so_tang_nha"], r["so_tang_noi"]) == (5, 5)          # tầng 1,2,3 + lửng thứ 2 + tum
    assert "tính là 1 tầng" in r["tum"]
    r2 = count_floors([("TẦNG TRỆT", 200), ("SÂN THƯỢNG", 50), ("TUM", 10)], rules)
    assert r2["so_tang_nha"] == 2                                         # sân thượng còn tum bên trên -> tầng thường


def test_total_floors_label_is_so_tang_nha():
    assert _m("TỔNG SỐ TẦNG | 8 TẦNG") == {"so_tang_nha": 8}
    assert _m("SỐ TẦNG | 02")["so_tang_noi"] == 2


def test_floor_subset_is_not_conflict():
    info = merge([dict(_hit("nhom_nha", ["F1.4", "F4.3"], 5), text="bảng theo tầng"),
                  _hit("nhom_nha", ["F4.3"], 7), _hit("nhom_nha", ["F1.4"], 9)], SPEC)
    fv = info.get("nhom_nha")
    assert fv.status == FOUND and fv.value == ["F1.4", "F4.3"]
    assert "nhom_nha" in info.problems(SPEC)                      # nhà nhiều nhóm -> cần xác nhận nhóm áp dụng


def test_gemini_floor_is_not_hang_muc():
    from pccc_checker.extractors.info_gemini import to_hits
    data = {"fields": {
        "khoi_tich": [{"value": "600", "hang_muc": "LẦU 1", "text": "KHỐI TÍCH 600"}],
        "nhom_nha": [{"value": "F1.4", "hang_muc": "LẦU 1", "text": "( F1.4)"},
                     {"value": "F4.3", "hang_muc": "VĂN PHÒNG", "text": "TẦNG CÓ CÔNG NĂNG VĂN PHÒNG (F4.3)"}],
        "bac_chiu_lua": [{"value": "II", "hang_muc": "TẦNG TRỆT", "text": "NHÀ CÓ BẬC CHỊU LỬA: BẬC II"}],
        "chieu_cao_pccc": [{"value": "6", "hang_muc": "Karaoke", "text": "CHIỀU CAO PCCC 6"}]}}
    hits = {(h["key"], str(h["value"]), h["hang_muc"]) for h in to_hits(data, 5)}
    assert hits == {("bac_chiu_lua", "II", None), ("chieu_cao_pccc", "6.0", "Karaoke"),
                    ("nhom_nha", "['F1.4', 'F4.3']", None)}          # khối tích từng tầng bị bỏ


@pytest.mark.parametrize("value", ["KIẾN TRÚC", "HỆ THỐNG CHỮA CHÁY", "BÌNH CHỮA CHÁY", "EXIT-EM", "HẠNG MỤC: KẾT CẤU"])
def test_discipline_is_not_project_name(value):
    info = merge([_hit("ten_cong_trinh", value, 2, "gemini")], SPEC)
    assert info.get("ten_cong_trinh").status == MISSING


def test_title_block_and_generic_subject():
    from pccc_checker.project_info import subject_names
    assert "cong_nang" not in _m("CÔNG NĂNG | CHẤP THUẬN / FOR APPROVAL")
    assert subject_names("NHÀ CÓ BẬC CHỊU LỬA: BẬC II; CẤP NGUY HIỂM KẾT CẤU: S0") == []
    assert _m("TỔNG KHỐI TÍCH | 4444,96 m3")["khoi_tich"] == 4444.96
    assert _same_title("VĂN PHÒNG CHO THUÊ KẾT HỢP NHÀ Ở-THE SUN BUILDING", "VĂN PHÒNG CHO THUÊ KẾT HỢP NHÀ Ở THE SUN BUILDING")


def _same_title(a, b):
    from pccc_checker.project_info import _same
    return _same(a, b, text=True)


def _ext(*els) -> DrawingExtraction:
    return DrawingExtraction("x.pdf", BuildingInfo(), [PageExtraction(1, 1000, 800, elements=list(els))])


def test_rules_cannot_check_when_height_conflict():
    info = merge([_hit("chieu_cao_pccc", 6.0, 5), _hit("chieu_cao_pccc", 30.0, 9), _hit("nhom_nha", ["F2.1"], 5),
                  _hit("bac_chiu_lua", "II", 5), _hit("cap_nguy_hiem_chay_ket_cau", "S0", 5)], SPEC)
    bmap = SPEC["building_map"]
    blocked = {bmap[k]: why for k, why in info.problems(SPEC).items() if k in bmap}
    assert set(blocked) == {"height_pccc_m"}
    door = Element("d", "exit_door", 1, [0, 0, 10, 10], "D1", {"is_exit": True, "width_m": 0.7, "height_m": 2.0,
                                                               "leads_to": "stair"})
    f = run_rules(load_rules(RULES), _ext(door), only={"EXIT-DOOR-EI30-28M", "EXIT-DOOR-WIDTH"}, blocked=blocked)
    by = {x.rule_id: x for x in f}
    assert by["EXIT-DOOR-EI30-28M"].status == "cannot_check"            # filter phụ thuộc chiều cao PCCC
    assert "mâu thuẫn" in by["EXIT-DOOR-EI30-28M"].message
    assert by["EXIT-DOOR-WIDTH"].status == "violation"                  # không phụ thuộc chiều cao -> vẫn kiểm tra


def test_soft_dependency_runs_with_default_threshold():
    door = Element("d", "exit_door", 1, [0, 0, 10, 10], "D1", {"is_exit": True, "width_m": 0.7})
    f = run_rules(load_rules(RULES), _ext(door), only={"EXIT-DOOR-WIDTH"},
                  blocked={"function_group": "thiếu nhóm nhà theo công năng"})
    assert {x.status for x in f} == {"cannot_check", "violation"}       # 0.7 < 0.8 vẫn báo lỗi


def test_no_blocked_keeps_old_behavior():
    door = Element("d", "exit_door", 1, [0, 0, 10, 10], "D1", {"is_exit": True, "width_m": 0.7})
    f = run_rules(load_rules(RULES), _ext(door), only={"EXIT-DOOR-WIDTH"})
    assert all(x.status == "violation" for x in f)


def test_check_cli_with_and_without_project_info(tmp_path):
    """Lệnh check chạy được trên extraction.json cũ (không có project_info.json) và dùng project_info khi có."""
    from pccc_checker.cli import main
    d = DrawingExtraction("x.pdf", BuildingInfo(function_group="F1.3", height_pccc_m=30.0), [PageExtraction(1, 100, 100)])
    ext = tmp_path / "extraction.json"
    ext.write_text(json.dumps(d.to_dict()), encoding="utf-8")
    main(["check", str(ext)])
    assert "Thông tin công trình" not in (tmp_path / "report.md").read_text(encoding="utf-8")
    info = merge([_hit("chieu_cao_pccc", 6.0, 5), _hit("chieu_cao_pccc", 9.0, 7)], SPEC)
    (tmp_path / "project_info.json").write_text(json.dumps(info.to_dict()), encoding="utf-8")
    main(["check", str(ext)])
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "## Thông tin công trình" in report and "Luật không kiểm tra được" in report
    findings = json.loads((tmp_path / "findings.json").read_text(encoding="utf-8"))
    assert any(f["status"] == "cannot_check" for f in findings)


# ------------------------------------------------------------------ golden (file PDF thật, người dùng điền)
GOLDEN_DIR = Path(__file__).parent / "golden"


def _check_field(fv, key, want, where=""):
    got = fv.value if fv.usable else [c["value"] for c in fv.candidates] if fv.status == CONFLICT else None
    if want == "conflict":
        assert fv.status == CONFLICT, f"{where}{key}: mong đợi conflict, đọc được {fv.status} {got}"
    elif isinstance(want, (int, float)) and isinstance(got, (int, float)):
        assert got == pytest.approx(want), f"{where}{key}"
    else:
        if isinstance(got, list) and all(isinstance(x, str) for x in got):   # nhóm nhà: ["F1.4", "F4.3"] ~ "F1.4; F4.3"
            got = "; ".join(got)
        assert str(got).upper() == str(want).upper(), f"{where}{key}"


@pytest.mark.parametrize("golden", sorted(GOLDEN_DIR.glob("*.yaml")), ids=lambda p: p.stem)
def test_golden_pdf(golden):
    """Golden: khu_dat / project_info / fire_inputs (hạng mục chính) + tuỳ chọn hang_muc_chinh, hang_muc: {tên: {...}}."""
    g = yaml.safe_load(golden.read_text(encoding="utf-8")) or {}
    pdf = Path(__file__).resolve().parents[1] / g.get("pdf", "")
    expected = {k: v for sec in ("khu_dat", "project_info", "fire_inputs") for k, v in (g.get(sec) or {}).items() if v is not None}
    per_hm = {name: {k: v for sec in ("project_info", "fire_inputs") for k, v in ((d or {}).get(sec) or {}).items()
                     if v is not None} for name, d in (g.get("hang_muc") or {}).items()}
    per_hm = {n: v for n, v in per_hm.items() if v}
    if not expected and not per_hm and not g.get("hang_muc_chinh"):
        pytest.skip(f"{golden.name}: chưa điền giá trị mong đợi")
    if not pdf.is_file():
        pytest.skip(f"không có file PDF {pdf}")
    from pccc_checker.config import load_settings
    from pccc_checker.project_info import FieldValue, _find_hang_muc, read_project_info
    info = read_project_info(pdf, load_settings(), gemini="never", log=lambda *_: None)
    if g.get("hang_muc_chinh"):
        assert _find_hang_muc(info, g["hang_muc_chinh"]) == info.hang_muc_chinh, \
            f"hạng mục chính: mong đợi {g['hang_muc_chinh']}, đọc được {info.hang_muc_chinh}"
    for key, want in expected.items():
        _check_field(info.get(key), key, want)
    for name, fields in per_hm.items():
        found = _find_hang_muc(info, name)
        assert found, f"không tìm thấy hạng mục {name} (có: {list(info.hang_muc)})"
        for key, want in fields.items():
            _check_field(info.hang_muc[found].get(key) or FieldValue(), key, want, f"[{name}] ")
