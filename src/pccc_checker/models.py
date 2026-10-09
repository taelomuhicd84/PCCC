"""Data model dùng chung cho toàn pipeline.

Quy ước toạ độ: bbox luôn ở hệ toạ độ TRANG PDF (point, gốc trên-trái, như PyMuPDF).
Extractor (Gemini/vector) chịu trách nhiệm quy đổi về hệ này.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Các loại phần tử mà extractor được phép trả về (mở rộng tại đây khi thêm tính năng).
ELEMENT_TYPES = {
    "exit_door",        # cửa/lối ra thoát nạn
    "door",             # cửa thường trên đường thoát nạn
    "fire_door",        # cửa ngăn cháy
    "stair",            # thang bộ / buồng thang
    "corridor",         # hành lang
    "room",             # phòng / gian phòng
    "lobby",            # sảnh / sảnh ngăn khói / khoang đệm
    "fire_wall",        # tường/vách ngăn cháy
    "elevator",
    "ramp",
    "evac_route",       # đường thoát nạn (polyline)
    "equipment",        # thiết bị PCCC (bình, họng, đầu báo...) - để mở rộng TCVN khác
    "other",
}


@dataclass
class Element:
    id: str
    type: str
    page: int
    bbox: list[float]                    # [x0, y0, x1, y1] theo point PDF
    label: str = ""
    attrs: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    source: str = "unknown"              # gemini | vector | manual

    def get(self, key: str, default: Any = None) -> Any:
        return self.attrs.get(key, default)


@dataclass
class BuildingInfo:
    function_group: str | None = None     # F1.1, F1.3, F4.3 ...
    height_pccc_m: float | None = None    # chiều cao PCCC
    floors_above: int | None = None
    basements: int | None = None
    fire_resistance_level: str | None = None   # I, II, III, IV, V
    structural_hazard_class: str | None = None  # S0..S3
    floor_area_m2: float | None = None
    max_occupants_per_floor: int | None = None
    has_auto_fire_alarm: bool | None = None
    has_auto_sprinkler: bool | None = None
    assumptions: list[str] = field(default_factory=list)   # giá trị do tool suy ra (không đọc trực tiếp)

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> "BuildingInfo":
        d = d or {}
        known = {k: d.get(k) for k in cls.__dataclass_fields__ if k != "assumptions"}
        return cls(**known, assumptions=list(d.get("assumptions") or []))


@dataclass
class PageExtraction:
    page: int
    width: float
    height: float
    sheet_title: str = ""
    scale: str = ""                       # "1:100"
    plan_bbox: list[float] | None = None  # khung bao mặt bằng tầng (để tính đường chéo, 3.2.8)
    category: str = ""                    # plan | stair | door_schedule | section | site | ... (pdf/classify.py)
    declared: dict[str, Any] = field(default_factory=dict)  # số liệu người thiết kế ghi trên bản vẽ
    elements: list[Element] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class DrawingExtraction:
    source_pdf: str
    building: BuildingInfo
    pages: list[PageExtraction]
    extractor: str = ""

    def elements(self, type_: str | None = None) -> list[Element]:
        out = [e for p in self.pages for e in p.elements]
        return [e for e in out if type_ is None or e.type == type_]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DrawingExtraction":
        pages = []
        for p in d.get("pages", []):
            els = [Element(**e) for e in p.get("elements", [])]
            pages.append(PageExtraction(
                page=p["page"], width=p["width"], height=p["height"],
                sheet_title=p.get("sheet_title", ""), scale=p.get("scale", ""), plan_bbox=p.get("plan_bbox"),
                category=p.get("category", ""), declared=p.get("declared") or {},
                elements=els, notes=p.get("notes", []),
            ))
        return cls(
            source_pdf=d.get("source_pdf", ""),
            building=BuildingInfo.from_dict(d.get("building")),
            pages=pages,
            extractor=d.get("extractor", ""),
        )


SEVERITIES = ("error", "warning", "info")


@dataclass
class Finding:
    rule_id: str
    clause: str                           # "QCVN 06:2022 3.4.1 (SĐ1:2023)"
    severity: str                         # error | warning | info
    message: str
    page: int | None = None
    bbox: list[float] | None = None
    element_ids: list[str] = field(default_factory=list)
    actual: Any = None
    required: Any = None
    verified_rule: bool = False           # luật đã được kỹ sư đối chiếu văn bản gốc chưa
    reviewer_note: str = ""               # ghi chú từ agent/kỹ sư review
    dismissed: bool = False               # agent/kỹ sư bác bỏ (false positive) -> không ghi lên PDF

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
