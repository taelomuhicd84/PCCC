"""Thư viện check. Mỗi check nhận (rule_yaml, extraction) và yield Finding."""
from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any, Iterable

from ..models import DrawingExtraction, Element, Finding, PageExtraction
from .engine import context, make_finding, match_when, register, resolve_value, targets

PT_TO_MM = 25.4 / 72


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _ei(v: Any) -> int | None:
    m = re.search(r"(\d{2,3})", str(v or ""))
    return int(m.group(1)) if m else None


def page_scale_m_per_pt(page: PageExtraction, default: str | None = None) -> float | None:
    """'1:100' -> số mét thực tế ứng với 1 point trên trang."""
    for s in (page.scale, default):
        m = re.search(r"1\s*[:/]\s*(\d+)", s or "")
        if m:
            return PT_TO_MM * int(m.group(1)) / 1000
    return None


# ------------------------------------------------------------ check tổng quát
@register("min_attr")
def min_attr(rule: dict, d: DrawingExtraction) -> Iterable[Finding]:
    attr = rule["attr"]
    for el in targets(rule, d):
        actual = _num(el.get(attr))
        if actual is None:
            continue
        req, note = resolve_value(rule, context(el, d))
        if req is not None and actual + 1e-6 < float(req):
            yield make_finding(rule, el, actual, req, note)


@register("max_attr")
def max_attr(rule: dict, d: DrawingExtraction) -> Iterable[Finding]:
    attr = rule["attr"]
    for el in targets(rule, d):
        actual = _num(el.get(attr))
        if actual is None:
            continue
        req, note = resolve_value(rule, context(el, d))
        if req is not None and actual - 1e-6 > float(req):
            yield make_finding(rule, el, actual, req, note)


@register("bool_attr")
def bool_attr(rule: dict, d: DrawingExtraction) -> Iterable[Finding]:
    """Thuộc tính phải bằng `value` (true/false). Không có dữ liệu -> bỏ qua."""
    attr, want = rule["attr"], bool(rule.get("value", True))
    for el in targets(rule, d):
        v = el.get(attr)
        if v is not None and bool(v) != want:
            yield make_finding(rule, el, v, want)


@register("required_attr")
def required_attr(rule: dict, d: DrawingExtraction) -> Iterable[Finding]:
    """Phần tử phải thể hiện thông tin `attr` trên bản vẽ (vd cửa ngăn cháy phải ghi EI)."""
    for el in targets(rule, d):
        if el.get(rule["attr"]) in (None, "", []):
            yield make_finding(rule, el, None, rule["attr"])


@register("min_fire_rating")
def min_fire_rating(rule: dict, d: DrawingExtraction) -> Iterable[Finding]:
    for el in targets(rule, d):
        actual = _ei(el.get(rule.get("attr", "fire_rating")))
        if actual is None:
            continue
        req, note = resolve_value(rule, context(el, d))
        if req is not None and actual < _ei(req):
            yield make_finding(rule, el, f"EI{actual}", f"EI{_ei(req)}", note)


@register("compare_attrs")
def compare_attrs(rule: dict, d: DrawingExtraction) -> Iterable[Finding]:
    """left (op) right * factor, vd landing_width_m >= flight_width_m; riser_m <= tread_m (độ dốc 1:1)."""
    ops = {">=": lambda a, b: a >= b - 1e-6, "<=": lambda a, b: a <= b + 1e-6}
    for el in targets(rule, d):
        a, b = _num(el.get(rule["left"])), _num(el.get(rule["right"]))
        if a is None or b is None:
            continue
        b *= float(rule.get("factor", 1))
        if not ops[rule.get("op", ">=")](a, b):
            yield make_finding(rule, el, a, round(b, 3))


@register("condition_flag")
def condition_flag(rule: dict, d: DrawingExtraction) -> Iterable[Finding]:
    """Báo khi điều kiện `when` khớp (vd thang loại 3 trong nhà > 50 m)."""
    for el in targets(rule, d):
        if match_when(rule.get("when"), context(el, d)):
            yield make_finding(rule, el)


@register("missing_data")
def missing_data(rule: dict, d: DrawingExtraction) -> Iterable[Finding]:
    """Phần tử quan trọng thiếu số liệu -> nhắc kiểm tra thủ công (không kết luận sai)."""
    for el in targets(rule, d):
        miss = [a for a in rule["attrs"] if el.get(a) is None]
        if miss:
            yield make_finding(rule, el, None, ", ".join(miss), missing=", ".join(miss))


@register("building_missing")
def building_missing(rule: dict, d: DrawingExtraction) -> Iterable[Finding]:
    miss = [a for a in rule["attrs"] if getattr(d.building, a, None) is None]
    if miss:
        yield make_finding(rule, None, None, ", ".join(miss), missing=", ".join(miss))


# ------------------------------------------------------------ check chuyên biệt
def _exits_by_page(d: DrawingExtraction) -> dict[int, list[Element]]:
    out: dict[int, list[Element]] = defaultdict(list)
    for e in d.elements():
        if e.type == "exit_door" or (e.type in ("door", "fire_door") and e.get("is_exit")):
            out[e.page].append(e)
        elif e.type == "stair" and e.get("is_evacuation") is not False and e.get("counts_as_exit", True):
            out[e.page].append(e)
    return out


def _edge_dists(a: list[float], b: list[float]) -> tuple[float, float]:
    """(khoảng cách 2 cạnh xa nhất, khoảng cách 2 cạnh gần nhất) giữa 2 lối ra, xấp xỉ theo bbox."""
    far = math.hypot(max(a[2], b[2]) - min(a[0], b[0]), max(a[3], b[3]) - min(a[1], b[1]))
    gx = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
    gy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return far, math.hypot(gx, gy)


def _plan_bbox(page: PageExtraction) -> tuple[list[float] | None, bool]:
    """Khung mặt bằng: ưu tiên plan_bbox do extractor cung cấp; nếu không có thì gộp bbox các phần tử (xấp xỉ)."""
    if page.plan_bbox:
        return page.plan_bbox, False
    els = [e for e in page.elements if e.type in ("room", "corridor", "stair", "exit_door", "door", "fire_door", "lobby")]
    if len(els) < 2:
        return None, True
    return [min(e.bbox[0] for e in els), min(e.bbox[1] for e in els),
            max(e.bbox[2] for e in els), max(e.bbox[3] for e in els)], True


@register("exit_separation")
def exit_separation(rule: dict, d: DrawingExtraction) -> Iterable[Finding]:
    """3.2.8 (SĐ1:2023): >= 2 lối ra phải phân tán, cách nhau >= 1/2 đường chéo lớn nhất mặt bằng
    (1/3 nếu toàn nhà có sprinkler). Khoảng cách đo giữa 2 cạnh xa nhất; nếu giá trị này < 7 m thì đo giữa
    2 cạnh gần nhất. Tool lấy cặp lối ra phân tán nhất trên tầng để so sánh."""
    pages = {p.page: p for p in d.pages}
    sprinkler = bool(d.building.has_auto_sprinkler)
    ratio = float(rule.get("ratio_sprinkler", 1 / 3) if sprinkler else rule.get("ratio", 0.5))
    threshold = float(rule.get("measure_threshold_m", 7.0))
    for pno, exits in _exits_by_page(d).items():
        if len(exits) < 2:
            continue
        page = pages[pno]
        k = page_scale_m_per_pt(page, rule.get("default_scale"))
        plan, approx = _plan_bbox(page)
        if k is None or plan is None:
            yield Finding(rule["id"], rule.get("clause", ""), "info",
                          "Không xác định được tỉ lệ hoặc khung mặt bằng -> chưa kiểm tra được khoảng cách giữa các lối ra",
                          page=pno, verified_rule=bool(rule.get("verified")))
            continue
        diag_m = math.hypot(plan[2] - plan[0], plan[3] - plan[1]) * k
        required = round(diag_m * ratio, 2)
        best = None
        for i in range(len(exits)):
            for j in range(i + 1, len(exits)):
                far, near = _edge_dists(exits[i].bbox, exits[j].bbox)
                far_m = far * k
                dist = far_m if far_m >= threshold else near * k
                if best is None or dist > best[0]:
                    best = (dist, exits[i], exits[j], "cạnh xa nhất" if far_m >= threshold else "cạnh gần nhất")
        dist, e1, e2, how = best
        if dist + 1e-6 < required:
            note = f"đo theo {how}; đường chéo mặt bằng ~{diag_m:.1f} m" + (" (ước lượng)" if approx else "")                 + (", có sprinkler -> 1/3" if sprinkler else ", 1/2 đường chéo")
            f = make_finding(rule, e1, round(dist, 2), required, note,
                             pair=f"{e1.label or e1.id} ↔ {e2.label or e2.id}")
            f.bbox = [min(e1.bbox[0], e2.bbox[0]), min(e1.bbox[1], e2.bbox[1]),
                      max(e1.bbox[2], e2.bbox[2]), max(e1.bbox[3], e2.bbox[3])]
            f.element_ids = [e1.id, e2.id]
            yield f


@register("min_exits_per_floor")
def min_exits_per_floor(rule: dict, d: DrawingExtraction) -> Iterable[Finding]:
    """Mỗi tầng (trang mặt bằng) cần >= 2 lối ra thoát nạn, trừ khi thoả điều kiện 1 lối ra
    (các `single_exit_cases` trong YAML, gồm trường hợp mới của SĐ1:2023)."""
    exits = _exits_by_page(d)
    ctx = context(None, d)
    allowed_single = any(match_when(c, ctx) for c in rule.get("single_exit_cases", []))
    for p in d.pages:
        is_plan = any(e.type in ("room", "corridor", "stair", "exit_door") for e in p.elements)
        if not is_plan:
            continue
        n = len(exits.get(p.page, []))
        if n == 0:
            yield Finding(rule["id"], rule.get("clause", ""), "warning",
                          "Không nhận diện được lối ra thoát nạn nào trên mặt bằng — cần kiểm tra thủ công",
                          page=p.page, verified_rule=bool(rule.get("verified")))
        elif n < 2 and not allowed_single:
            e = exits[p.page][0]
            yield make_finding(rule, e, n, 2)


@register("basement_smoke_lobby")
def basement_smoke_lobby(rule: dict, d: DrawingExtraction) -> Iterable[Finding]:
    """SĐ1:2023: tại mọi tầng hầm, >= 1 lối vào buồng thang thoát nạn phải qua sảnh ngăn khói
    (vách ngăn cháy loại 1). Tool chỉ kiểm tra có thể hiện sảnh ngăn khói/khoang đệm hay không."""
    if not (d.building.basements or 0) > 0:
        return
    has_lobby = any(e.type == "lobby" and e.get("is_smoke_lobby") for e in d.elements())
    if not has_lobby:
        yield make_finding(rule, None)
