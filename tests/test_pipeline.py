"""Test offline (không cần Gemini): bản vẽ mẫu -> vector extractor -> rules -> annotate -> dxf."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from make_sample_pdf import make  # noqa: E402

from pccc_checker.config import RULES_DIR
from pccc_checker.extractors.vector_extractor import VectorTextExtractor
from pccc_checker.models import BuildingInfo, DrawingExtraction, Element, PageExtraction
from pccc_checker.output.annotate_pdf import annotate
from pccc_checker.output.export_dxf import export_dxf
from pccc_checker.rules import load_rules, run_rules

RULES = [RULES_DIR / "qcvn06_2022_sd01_2023.yaml"]


@pytest.fixture(scope="module")
def sample(tmp_path_factory) -> Path:
    return make(tmp_path_factory.mktemp("in") / "sample.pdf")


@pytest.fixture(scope="module")
def extraction(sample) -> DrawingExtraction:
    return VectorTextExtractor().extract(sample, log=lambda *_: None)


def _ids(findings):
    return {f.rule_id for f in findings}


def test_vector_extract_building_info(extraction):
    b = extraction.building
    assert b.function_group == "F1.3"
    assert b.height_pccc_m == 24.5
    assert b.fire_resistance_level == "II"
    assert b.basements == 1
    assert extraction.pages[0].scale == "1:100"


def test_rules_detect_seeded_errors(extraction):
    f = run_rules(load_rules(RULES), extraction)
    ids = _ids(f)
    for expected in ["EXIT-DOOR-WIDTH", "CORRIDOR-WIDTH", "STAIR-FLIGHT-WIDTH", "STAIR-TREAD",
                     "FIRE-DOOR-RATING-SHOWN", "BASEMENT-SMOKE-LOBBY"]:
        assert expected in ids, expected
    assert "STAIR-RISER" not in ids  # bậc 180 mm hợp lệ


def _ext(building: dict, *els: Element) -> DrawingExtraction:
    return DrawingExtraction("x.pdf", BuildingInfo.from_dict(building),
                             [PageExtraction(1, 1000, 1000, scale="1:100", elements=list(els))])


@pytest.mark.parametrize("building,width,should_fail", [
    ({"function_group": "F1.1", "max_occupants_per_floor": 20}, 1.1, True),    # cần 1.2
    ({"function_group": "F1.1", "max_occupants_per_floor": 10}, 1.0, False),   # cần 1.0
    ({"function_group": "F1.3", "height_pccc_m": 12, "max_occupants_per_floor": 10}, 0.75, False),  # 0.7
    ({"function_group": "F1.3", "height_pccc_m": 30}, 0.85, True),              # 0.9
    ({"function_group": "F4.3", "max_occupants_per_floor": 250}, 1.1, True),    # 1.2
])
def test_stair_width_amendment_cases(building, width, should_fail):
    st = Element("s", "stair", 1, [0, 0, 10, 10], "TB", {"flight_width_m": width, "is_evacuation": True})
    f = run_rules(load_rules(RULES), _ext(building, st), only={"STAIR-FLIGHT-WIDTH"})
    assert bool(f) == should_fail


def test_single_exit_allowed_by_amendment():
    ok = {"function_group": "F4.3", "height_pccc_m": 23, "floor_area_m2": 140, "max_occupants_per_floor": 12,
          "has_auto_fire_alarm": True, "has_auto_sprinkler": True}
    d1 = Element("d", "exit_door", 1, [0, 0, 10, 10], "D1", {"is_exit": True})
    assert not run_rules(load_rules(RULES), _ext(ok, d1), only={"MIN-EXITS-PER-FLOOR"})
    for bad in (dict(ok, floor_area_m2=300), dict(ok, function_group="F1.3")):  # F1.3 không thuộc 3.2.6.2 a
        assert run_rules(load_rules(RULES), _ext(bad, d1), only={"MIN-EXITS-PER-FLOOR"})
    low = {"function_group": "F2.1", "height_pccc_m": 9, "floor_area_m2": 280, "max_occupants_per_floor": 18}
    assert not run_rules(load_rules(RULES), _ext(low, d1), only={"MIN-EXITS-PER-FLOOR"})


def _sep(building, d2_x, plan=(0, 0, 800, 600)):
    d = _ext(building, Element("a", "exit_door", 1, [0, 0, 10, 10], "D1", {"is_exit": True}),
             Element("b", "exit_door", 1, [d2_x, 0, d2_x + 10, 10], "D2", {"is_exit": True}))
    d.pages[0].plan_bbox = list(plan)
    return run_rules(load_rules(RULES), d, only={"EXIT-SEPARATION"})


def test_exit_separation_half_diagonal():
    # 1:100 -> 1 pt = 0.03528 m ; mặt bằng 800x600 pt -> chéo ~35.3 m -> cần >= 17.6 m (1/2), 11.8 m (1/3 sprinkler)
    assert _sep({}, 300)                                   # ~10.9 m < 17.6 -> lỗi
    assert not _sep({}, 560)                               # ~20.1 m >= 17.6 -> đạt
    assert not _sep({"has_auto_sprinkler": True}, 340)     # ~12.3 m >= 11.8 -> đạt nhờ sprinkler
    f = _sep({}, 150)                                      # cạnh xa ~5.6 m < 7 -> đo cạnh gần ~4.9 m
    assert f and f[0].actual < 5.5


def test_annotate_and_dxf(sample, extraction, tmp_path):
    findings = run_rules(load_rules(RULES), extraction)
    findings[0].dismissed = True
    out = tmp_path / "out.pdf"
    n = annotate(sample, findings, out)
    assert n == len(findings) - 1
    with pymupdf.open(out) as doc:
        assert len(list(doc[0].annots())) > 0
    dxf = export_dxf(extraction, findings, tmp_path / "d.dxf")
    assert dxf.stat().st_size > 1000


def test_extraction_roundtrip(extraction):
    d2 = DrawingExtraction.from_dict(json.loads(json.dumps(extraction.to_dict())))
    assert len(d2.elements()) == len(extraction.elements())


def _one(building, el, rid):
    return run_rules(load_rules(RULES), _ext(building, el), only={rid})


def test_exit_width_cases_3_2_9():
    door = lambda w, n: Element("d", "exit_door", 1, [0, 0, 5, 5], "D", {"width_m": w, "occupants": n})
    assert _one({"function_group": "F3.1"}, door(1.0, 60), "EXIT-DOOR-WIDTH")       # > 50 người -> 1.2
    assert not _one({"function_group": "F1.3"}, door(1.0, 60), "EXIT-DOOR-WIDTH")   # F1.3 ngoại trừ
    assert _one({"function_group": "F1.1"}, door(1.0, 20), "EXIT-DOOR-WIDTH")       # F1.1 > 15 -> 1.2


def test_ei30_doors_above_28m():
    d = lambda r: Element("d", "exit_door", 1, [0, 0, 5, 5], "D", {"leads_to": "stair", **({"fire_rating": r} if r else {})})
    tall = {"function_group": "F4.3", "height_pccc_m": 40}
    assert _one(tall, d("EI15"), "EXIT-DOOR-EI30-28M")
    assert not _one(tall, d("EI45"), "EXIT-DOOR-EI30-28M")
    assert _one(tall, d(None), "EXIT-DOOR-EI30-28M-MISSING")
    assert not _one(dict(tall, function_group="F1.3"), d("EI15"), "EXIT-DOOR-EI30-28M")


def test_corridor_width_3_3_6():
    c = lambda w, n: Element("c", "corridor", 1, [0, 0, 5, 5], "HL", {"width_m": w, "occupants": n})
    assert _one({"function_group": "F1.3"}, c(1.1, 20), "CORRIDOR-WIDTH")       # F1 > 15 người -> 1.2
    assert not _one({"function_group": "F4.3"}, c(1.1, 40), "CORRIDOR-WIDTH")   # nhóm khác <= 50 -> 1.0
