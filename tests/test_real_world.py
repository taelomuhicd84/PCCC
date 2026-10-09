"""Các tình huống gặp ở hồ sơ thật (KS Hoàng Hùng): font VNI, bảng cửa, số liệu ghi sẵn, suy ra nhóm F."""
from __future__ import annotations

import pymupdf

from pccc_checker.config import RULES_DIR
from pccc_checker.extractors.postprocess import apply_door_schedule, infer_function_group, parse_declared
from pccc_checker.models import BuildingInfo, DrawingExtraction, Element, PageExtraction
from pccc_checker.pdf.classify import classify_page
from pccc_checker.pdf.vn_encoding import vni_to_unicode
from pccc_checker.rules import load_rules, run_rules

RULES = [RULES_DIR / "qcvn06_2022_sd01_2023.yaml"]


def test_vni_decoding():
    cases = {
        "MAËT BAÈNG TAÀNG 1": "MẶT BẰNG TẦNG 1", "TÆ LEÄ BV:": "TỈ LỆ BV:", "BUOÀNG ÑEÄM": "BUỒNG ĐỆM",
        "CHUÛ NGHÓA": "CHỦ NGHĨA", "Ñoäc laäp - Töï do - Haïnh phuùc": "Độc lập - Tự do - Hạnh phúc",
        "VÒ TRÍ LOÁI TIEÁP CAÄN": "VỊ TRÍ LỐI TIẾP CẬN", "cöûa ngaên chaùy": "cửa ngăn cháy", "TRÔÛ": "TRỞ",
    }
    for src, want in cases.items():
        assert vni_to_unicode(src) == want


def test_parse_declared_values():
    d = parse_declared(["KHOẢNG CÁCH 2 LỐI THOÁT NẠN L=20.5M", "ĐƯỜNG CHÉO CÔNG TRÌNH D=38.2M", "- SỨC CHỨA: 100 NGƯỜI"])
    assert d == {"exit_distance_m": 20.5, "plan_diagonal_m": 38.2, "occupants": 100}


def _d(*pages: PageExtraction, building=None) -> DrawingExtraction:
    return DrawingExtraction("x.pdf", BuildingInfo.from_dict(building or {}), list(pages))


def test_door_schedule_fills_plan_doors():
    sched = PageExtraction(24, 1000, 1000, category="door_schedule", elements=[
        Element("s1", "fire_door", 24, [0, 0, 1, 1], "D07", {"width_m": 0.9, "height_m": 2.1, "fire_rating": "EI60"}),
        Element("s2", "door", 24, [0, 0, 1, 1], "D03", {"width_m": 0.7, "height_m": 2.2})])
    plan = PageExtraction(8, 1000, 1000, scale="1:100", category="plan", elements=[
        Element("a", "door", 8, [0, 0, 5, 5], "D07", {"leads_to": "stair"}),
        Element("b", "exit_door", 8, [0, 0, 5, 5], "D 03", {"is_exit": True})])
    d = _d(sched, plan)
    assert apply_door_schedule(d) == 2
    a, b = plan.elements
    assert a.type == "fire_door" and a.attrs["fire_rating"] == "EI60"
    assert b.attrs["width_m"] == 0.7
    ids = {f.rule_id: f for f in run_rules(load_rules(RULES), d)}
    assert ids["EXIT-DOOR-WIDTH"].element_ids == ["b"]           # chỉ cửa thực, không báo dòng bảng cửa
    assert all("s1" not in f.element_ids and "s2" not in f.element_ids for f in ids.values())


def test_infer_function_group_from_use():
    d = _d()
    infer_function_group(d, ["CÔNG TRÌNH: KHÁCH SẠN HOÀNG HÙNG"])
    assert d.building.function_group == "F1.2" and d.building.assumptions
    d2 = _d(building={"function_group": "F1.3"})
    infer_function_group(d2, ["CÔNG TRÌNH: KHÁCH SẠN"])
    assert d2.building.function_group == "F1.3"                  # không ghi đè giá trị đọc được


def test_exit_separation_uses_declared_values():
    p = PageExtraction(8, 1000, 1000, scale="1:100", category="plan", elements=[
        Element("a", "exit_door", 8, [0, 0, 5, 5], "D1", {"is_exit": True}),
        Element("b", "exit_door", 8, [20, 0, 25, 5], "D2", {"is_exit": True})])
    p.declared = {"exit_distance_m": 20.5, "plan_diagonal_m": 38.2}
    assert not run_rules(load_rules(RULES), _d(p), only={"EXIT-SEPARATION"})   # 20.5 >= 19.1
    p.declared = {"exit_distance_m": 15.0, "plan_diagonal_m": 38.2}
    assert run_rules(load_rules(RULES), _d(p), only={"EXIT-SEPARATION"})


def test_classify_structure_vs_plan(tmp_path):
    doc = pymupdf.open()
    for title in ("MẶT BẰNG DẦM TẦNG 1 TL : 1/100", "MẶT BẰNG TẦNG 1_TL:1/100", "CHI TIẾT CỬA"):
        pg = doc.new_page()
        pg.insert_text((50, 50), title, fontfile=r"C:\Windows\Fonts\arial.ttf", fontname="vn")
        pg.insert_text((50, 80), "CẦU THANG BỘ NẰM TRONG BUỒNG THANG, CHỐNG CHÁY " * 2,
                       fontfile=r"C:\Windows\Fonts\arial.ttf", fontname="vn", fontsize=5)
    pdf = tmp_path / "set.pdf"
    doc.save(pdf)
    assert [classify_page(pdf, i)[0] for i in (1, 2, 3)] == ["structure", "plan", "door_schedule"]


def test_source_has_no_control_chars():
    """Chặn lỗi '\b' bị ghi thành ký tự backspace thật trong regex (đã từng làm hỏng phân loại trang)."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "src"
    bad = [str(p) for p in root.rglob("*.py")
           if any(ord(c) < 32 and c not in "\n\r\t" for c in p.read_text(encoding="utf-8"))]
    assert not bad, bad


def test_stair_consolidation_by_label():
    from pccc_checker.extractors.postprocess import consolidate_stairs, fix_types

    def plan(no, extra=None):
        els = [Element(f"a{no}", "stair", no, [0, 0, 5, 5], "BTB1", {"stair_type": "loai3", "is_evacuation": False}),
               Element(f"b{no}", "stair", no, [50, 0, 55, 5], "BTB2", {"is_evacuation": True}),
               Element(f"c{no}", "stair", no, [90, 0, 95, 5], "TB3", {}),
               Element(f"e{no}", "stair", no, [99, 0, 99, 5], "THANG MÁY", {})]
        for e in els:
            e.attrs.update((extra or {}).get(e.label, {}))
        return PageExtraction(no, 1000, 1000, category="plan", elements=els)

    notes = {"BTB2": {"_evac_note": True}, "TB3": {"stair_type": "loai3", "_type_note": True}}
    d = _d(plan(8, notes), plan(9, notes), plan(10), PageExtraction(20, 1000, 1000, category="stair", elements=[
        Element("x", "stair", 20, [0, 0, 5, 5], "BTB1", {"flight_width_m": 1.0, "stair_type": "N1"}),
        Element("y", "stair", 20, [0, 0, 5, 5], "CHI TIẾT BẬC THANG 1", {"flight_width_m": 0.13})]))
    fix_types(d)
    consolidate_stairs(d)
    by = {(e.page, e.label): e for e in d.elements()}
    assert by[(8, "BTB1")].attrs["is_evacuation"] is True              # Gemini đoán False nhưng không có ghi chú
    assert by[(10, "BTB2")].attrs["is_evacuation"] is False            # ghi chú ở đa số trang -> áp cho mọi tầng
    assert by[(10, "TB3")].attrs["stair_type"] == "loai3"
    assert by[(8, "BTB1")].attrs["stair_type"] == "N1"                 # ưu tiên trang chi tiết thang
    assert by[(8, "THANG MÁY")].type == "elevator"
    assert by[(20, "CHI TIẾT BẬC THANG 1")].type == "other"
    assert not by[(20, "BTB1")].attrs.get("ref_only")                  # bản đại diện có số đo -> được kiểm tra


def test_unoccupied_floor_single_exit_is_warning():
    p = PageExtraction(14, 1000, 1000, category="plan", sheet_title="MẶT BẰNG TẦNG 9",
                       elements=[Element("t", "stair", 14, [0, 0, 5, 5], "TB3", {"is_evacuation": True})])
    p.declared = {"unoccupied": True}
    f = run_rules(load_rules(RULES), _d(p), only={"MIN-EXITS-PER-FLOOR"})
    assert f and f[0].severity == "warning" and "thường xuyên" in f[0].message
