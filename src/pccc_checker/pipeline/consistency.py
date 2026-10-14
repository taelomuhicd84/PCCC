"""findings.jsonl — mỗi dòng một kết luận, 4 trạng thái: D (đạt), KD (không đạt), XM (cần xác minh), NA (không áp dụng).

{"id":"PC-012","hm":"HM01","tang":"T1","cd":"thoat-nan","rule":"K2-TNL-012","yc":"≥ 2","ht":"1","tt":"KD",
 "ly_do":"…","truc":"B-C/3","trang":5,"bbox":[0,0,0,0],"conf":"H","evid":"nguyên văn chữ đọc được"}

Script chặn ngay khi ghi (nguyên tắc "không bằng chứng thì không kết luận"):
  - tt = KD mà thiếu trang, bbox hoặc evid -> XM
  - rule không có trong bảng tra (checklist .md / luật YAML) -> XM (không lấy điều khoản từ trí nhớ mô hình)
  - tt lạ -> XM
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..config import PROJECT_ROOT

TT = ("D", "KD", "XM", "NA")
TT_VI = {"D": "Đạt", "KD": "Không đạt", "XM": "Cần xác minh", "NA": "—"}
KEYS = ("id", "hm", "tang", "cd", "rule", "yc", "ht", "tt", "ly_do", "truc", "trang", "bbox", "conf", "evid")
CHECKLIST_ID = re.compile(r"^\|\s*([A-Z]{2,3}\d{0,2}-[A-Z]+-\d{3})\s*\|", re.M)  # KS2-TN-012, BV-TN-003, HT34-KHOI-001 (pipeline/loai_hinh)


def known_rules(root: Path = PROJECT_ROOT) -> set[str]:
    """ID dòng của mọi bảng tra .md + id luật YAML."""
    ids: set[str] = set()
    for f in (root / "rules" / "checklists").rglob("*.md"):
        ids |= set(CHECKLIST_ID.findall(f.read_text(encoding="utf-8")))
    for f in (root / "rules").glob("*.yaml"):
        ids |= set(re.findall(r"^\s*-\s*id:\s*([\w.-]+)", f.read_text(encoding="utf-8"), re.M))
    return ids


def _empty(v) -> bool:
    return v is None or v == "" or v == [] or (isinstance(v, list) and not any(v))


def validate(rows: list[dict], rules: set[str] | None = None) -> tuple[list[dict], list[str]]:
    """-> (dòng đã chuẩn hoá, nhật ký thay đổi). Không bao giờ nâng trạng thái, chỉ hạ."""
    rules = known_rules() if rules is None else rules
    log, out, seen = [], [], set()
    for i, r in enumerate(rows, 1):
        r = {k: r.get(k) for k in KEYS} | {k: v for k, v in r.items() if k not in KEYS}
        if not r["id"] or r["id"] in seen:
            r["id"] = f"PC-{i:03d}"
        seen.add(r["id"])
        why = []
        if r["tt"] not in TT:
            why.append(f"trạng thái '{r['tt']}' không hợp lệ")
        if r["tt"] == "KD":
            miss = [k for k in ("trang", "bbox", "evid") if _empty(r[k])]
            if miss:
                why.append("KD thiếu " + ", ".join(miss))
        if r["tt"] in ("KD", "D") and r["rule"] not in rules:
            why.append(f"rule '{r['rule']}' không có trong bảng tra")
        if why:
            r["ly_do"] = f"{r.get('ly_do') or ''} [hạ {r['tt']}→XM: {'; '.join(why)}]".strip()
            log.append(f"{r['id']}: {r['tt']}→XM ({'; '.join(why)})")
            r["tt"] = "XM"
        out.append(r)
    return out, log


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def cd_of(clause: str) -> str:
    """Chuyên đề (pipeline/chuyen_de.py) theo phần của QCVN 06: 2 phân loại, 3 thoát nạn, 4 ngăn cháy lan,
    5 chữa cháy, 6 tiếp cận chữa cháy."""
    m = re.search(r"(?:khoản|Đ|điều|mục)?\s*(\d)\.\d", clause or "", re.I)
    return {"2": "quy-mo", "3": "thoat-nan", "4": "ngan-chay", "5": "chua-chay",
            "6": "giao-thong-xe-chua-chay"}.get(m.group(1) if m else "", "khac")


def from_engine(findings: list[dict], extraction: dict | None, hm: str = "HM01",
                hm_ids: dict[str, str] | None = None) -> list[dict]:
    """findings.json (rule engine + reviewer) -> dòng findings.jsonl. Bị reviewer bác bỏ -> bỏ.
    Finding có `hang_muc` (check nhiều hạng mục) -> mã HM theo project_facts (`hm_ids`: tên -> HM01…);
    "chung" giữ nguyên; không có -> `hm`."""
    hm_ids = hm_ids or {}
    pages = {p["page"]: p for p in (extraction or {}).get("pages", [])}
    els = {e["id"]: e for p in pages.values() for e in p.get("elements", [])}
    rows = []
    for f in findings:
        if f.get("dismissed"):
            continue
        p = pages.get(f.get("page"))
        bbox = None
        if f.get("bbox") and p:
            x0, y0, x1, y1 = f["bbox"]
            bbox = [round(x0 / p["width"], 4), round(y0 / p["height"], 4), round(x1 / p["width"], 4), round(y1 / p["height"], 4)]
        ee = [els[i] for i in f.get("element_ids", []) if i in els]
        evid = " / ".join(e["label"] for e in ee if e.get("label"))
        conf = "H" if ee and all(e.get("source") == "vector" or e.get("confidence", 0) >= 0.8 for e in ee) else \
               "M" if ee and min(e.get("confidence", 0) for e in ee) >= 0.5 else "L"
        rows.append({
            "id": None, "hm": hm_ids.get(f.get("hang_muc") or "", f.get("hang_muc") or hm), "tang": None, "cd": cd_of(f.get("clause", "")), "rule": f["rule_id"],
            "yc": f.get("required"), "ht": f.get("actual"),
            "tt": "XM" if f.get("status") == "cannot_check" else "KD",
            "ly_do": f.get("message", "") + (f" · {f['reviewer_note']}" if f.get("reviewer_note") else ""),
            "truc": None, "trang": f.get("page"), "bbox": bbox, "conf": conf, "evid": evid or None,
            "dieu_khoan": f.get("clause"),
        })
    return rows


def summary(rows: list[dict]) -> str:
    cnt = {t: sum(r["tt"] == t for r in rows) for t in TT}
    return ", ".join(f"{TT_VI[t] if t != 'NA' else 'NA'} {n}" for t, n in cnt.items())
