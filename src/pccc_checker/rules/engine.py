"""Rule engine: đọc rule pack YAML và chạy các check (deterministic, KHÔNG tốn token LLM).

Thêm luật mới:
  1. Nếu dùng được check có sẵn (min_attr, max_attr, bool_attr, required_attr, min_fire_rating,
     compare_attrs, condition_flag, missing_data) -> chỉ cần thêm YAML.
  2. Nếu cần logic riêng -> viết hàm trong rules/checks.py và gắn @register("ten_check").
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Iterable

import yaml

from ..models import DrawingExtraction, Element, Finding

CheckFn = Callable[[dict[str, Any], DrawingExtraction], Iterable[Finding]]
REGISTRY: dict[str, CheckFn] = {}


def register(name: str):
    def deco(fn: CheckFn) -> CheckFn:
        REGISTRY[name] = fn
        return fn
    return deco


# ----------------------------------------------------------------- điều kiện
_OPS = {
    "lt": lambda a, b: a < b, "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b, "gte": lambda a, b: a >= b,
    "in": lambda a, b: a in b, "nin": lambda a, b: a not in b, "ne": lambda a, b: a != b,
}


def match_when(when: dict[str, Any] | None, ctx: dict[str, Any]) -> bool:
    """`when` dạng {function_group: F1.1, height_pccc_m_lte: 15, people_per_floor_gt: 15}.
    Giá trị thiếu (None) => điều kiện KHÔNG khớp (thận trọng).
    Khoá đặc biệt `any: [ {...}, {...} ]` = khớp nếu ít nhất một điều kiện con khớp (OR)."""
    for key, expected in (when or {}).items():
        if key == "any":
            if not any(match_when(sub, ctx) for sub in expected):
                return False
            continue
        op = "eq"
        m = re.match(r"(.+)_(lt|lte|gt|gte|in|nin|ne)$", key)
        if m:
            key, op = m.group(1), m.group(2)
        actual = ctx.get(key)
        if actual is None:
            return False
        try:
            ok = (str(actual).upper() == str(expected).upper()) if op == "eq" else _OPS[op](actual, expected)
        except TypeError:
            return False
        if not ok:
            return False
    return True


def context(el: Element | None, d: DrawingExtraction) -> dict[str, Any]:
    ctx = {k: v for k, v in vars(d.building).items()}
    ctx.setdefault("people_per_floor", d.building.max_occupants_per_floor)
    fg = str(d.building.function_group or "")
    ctx["function_class"] = fg.split(".")[0].upper() if fg else None   # F2.1 -> F2
    b = d.building
    if b.has_auto_sprinkler or b.has_auto_fire_alarm:      # 3.2.6.2 a) 15-21 m: chữa cháy TĐ hoặc báo cháy TĐ
        ctx["any_protection"] = True
    elif b.has_auto_sprinkler is False and b.has_auto_fire_alarm is False:
        ctx["any_protection"] = False
    if el:
        ctx.update({k: v for k, v in el.attrs.items() if v is not None})
        ctx["label"] = el.label
    return ctx


def resolve_value(rule: dict[str, Any], ctx: dict[str, Any]) -> tuple[Any, str]:
    """Chọn ngưỡng theo `cases` (case đầu tiên khớp), ngược lại dùng `value`."""
    for case in rule.get("cases", []) or []:
        if match_when(case.get("when"), ctx):
            return case["value"], case.get("note", "")
    return rule.get("value"), rule.get("default_note", "")


def targets(rule: dict[str, Any], d: DrawingExtraction) -> list[Element]:
    types = rule.get("target") or []
    # bỏ qua các dòng của bảng thống kê cửa (không phải cửa thực trên mặt bằng)
    els = [e for e in d.elements() if (not types or e.type in types)
           and not e.attrs.get("schedule_entry") and not e.attrs.get("ref_only")]
    flt = rule.get("filter")
    if flt:
        els = [e for e in els if match_when(flt, context(e, d))]
    return els


def make_finding(rule: dict[str, Any], el: Element | None, actual: Any = None, required: Any = None,
                 extra: str = "", **fmt: Any) -> Finding:
    label = el.label if el else ""
    msg = rule.get("message", rule.get("title", rule["id"])).format(
        actual=actual, required=required, label=label or "(không ký hiệu)", **fmt)
    if extra:
        msg += f" [{extra}]"
    severity = rule.get("severity", "warning")
    attrs_used = {rule.get(k) for k in ("attr", "left", "right")} | set(rule.get("attrs", []))
    unverified = [a for a in (el.attrs.get("_unverified", []) if el else []) if a in attrs_used]
    if unverified and severity == "error":
        severity = "warning"
        msg += f" (số đo {', '.join(unverified)} do Gemini đọc, KHÔNG khớp số nào trên bản vẽ — cần kiểm tra lại)"
    if el and el.attrs.get("dims_from_schedule") and rule.get("attr") in ("width_m", "height_m"):
        msg += f" (kích thước lấy từ bảng cửa {el.attrs['dims_from_schedule']}, có thể là phủ bì)"
    return Finding(
        rule_id=rule["id"], clause=rule.get("clause", ""), severity=severity,
        message=msg, page=el.page if el else None, bbox=el.bbox if el else None,
        element_ids=[el.id] if el else [], actual=actual, required=required,
        verified_rule=bool(rule.get("verified", False)))


def _merge_duplicates(findings: list[Finding]) -> list[Finding]:
    """Cùng luật + cùng nội dung (vd cùng loại cửa D01 lặp ở nhiều tầng) -> 1 finding, ghi danh sách trang."""
    merged: dict[tuple, Finding] = {}
    pages: dict[tuple, list] = {}
    for f in findings:
        key = (f.rule_id, f.message)
        if key in merged:
            if f.page and f.page not in pages[key]:
                pages[key].append(f.page)
            continue
        merged[key], pages[key] = f, [f.page] if f.page else []
    for key, f in merged.items():
        if len(pages[key]) > 1:
            f.message += f" (lặp lại ở trang {', '.join(map(str, pages[key][1:]))})"
    return list(merged.values())


# ----------------------------------------------------------------- loader / runner
def load_rules(paths: list[Path]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for p in paths:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        meta = data.get("meta", {})
        for r in data.get("rules", []):
            r.setdefault("pack", meta.get("name", p.stem))
            rules.append(r)
    return rules


def run_rules(rules: list[dict[str, Any]], d: DrawingExtraction, only: set[str] | None = None) -> list[Finding]:
    from . import checks  # noqa: F401  (đăng ký các check)
    findings: list[Finding] = []
    for rule in rules:
        if not rule.get("enabled", True) or (only and rule["id"] not in only):
            continue
        fn = REGISTRY.get(rule["check"])
        if fn is None:
            findings.append(Finding(rule["id"], rule.get("clause", ""), "info",
                                    f"Check '{rule['check']}' chưa được cài đặt"))
            continue
        findings.extend(fn(rule, d))
    findings = _merge_duplicates(findings)
    order = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: (f.page or 0, order.get(f.severity, 3), f.rule_id))
    return findings
