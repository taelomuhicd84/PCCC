"""CLI: python -m pccc_checker <lệnh> ...

Pipeline (mỗi bước ghi file trung gian để các agent làm việc độc lập, không phải truyền dữ liệu lớn qua context):
  extract  : PDF  -> extraction.json + extraction.md        (Gemini / vector text)
  check    : extraction.json -> findings.json + report.md   (rule engine, 0 token)
  annotate : PDF + findings.json -> *_annotated.pdf          (ghi chú vị trí sai)
  dxf      : extraction.json (+ findings.json) -> .dxf
  run      : chạy cả 4 bước
  rules    : liệt kê luật
  pages    : phân loại trang của bộ hồ sơ (kiến trúc/kết cấu/...) — 0 token
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from .config import PROJECT_ROOT, RULES_DIR, load_settings
from .models import DrawingExtraction, Finding


def _out_dir(pdf: Path, out: str | None) -> Path:
    d = Path(out) if out else PROJECT_ROOT / "data" / "output" / pdf.stem
    d.mkdir(parents=True, exist_ok=True)
    return d


def _pages(spec: str | None) -> list[int] | str | None:
    if not spec or spec == "all":
        return None
    if spec == "auto":
        return "auto"
    res: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            res.extend(range(int(a), int(b) + 1))
        else:
            res.append(int(part))
    return res


def _building(path: str | None, kv: list[str] | None) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) if path else {}
    for item in kv or []:
        k, v = item.split("=", 1)
        data[k] = yaml.safe_load(v)
    return data or {}


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_findings(path: Path) -> list[Finding]:
    return [Finding(**f) for f in json.loads(path.read_text(encoding="utf-8"))]


def _rule_paths(settings: dict, extra: list[str] | None) -> list[Path]:
    return [RULES_DIR / p for p in settings["rules"]["packs"]] + [Path(p) for p in extra or []]


# ------------------------------------------------------------------ commands
def cmd_extract(a, settings) -> Path:
    from .extractors import make_extractor
    from .output.report_md import extraction_md
    pdf = Path(a.pdf)
    out = _out_dir(pdf, a.out)
    grid = tuple(int(x) for x in a.grid.lower().split("x"))
    try:
        ex = make_extractor(a.extractor, settings, cache_dir=PROJECT_ROOT / "data" / "cache", grid=grid)
    except RuntimeError as e:  # thiếu API key -> chạy offline
        if a.extractor == "gemini":
            raise
        print(f"CẢNH BÁO: {e} -> chuyển sang extractor 'vector' (offline).", file=sys.stderr)
        ex = make_extractor("vector", settings)
    d = ex.extract(pdf, _pages(a.pages), _building(a.building, a.set), log=lambda m: print(m, file=sys.stderr))
    _write_json(out / "extraction.json", d.to_dict())
    (out / "extraction.md").write_text(extraction_md(d), encoding="utf-8")
    print(f"extraction: {out / 'extraction.json'} ({len(d.elements())} phần tử)")
    return out / "extraction.json"


def cmd_check(a, settings) -> Path:
    from .output.report_md import findings_md
    from .rules import load_rules, run_rules
    ext = Path(a.extraction)
    d = DrawingExtraction.from_dict(json.loads(ext.read_text(encoding="utf-8")))
    over = _building(getattr(a, "building", None), getattr(a, "set", None))
    for k, v in over.items():
        setattr(d.building, k, v)
    findings = run_rules(load_rules(_rule_paths(settings, a.rules)), d, set(a.only.split(",")) if a.only else None)
    out = ext.parent
    _write_json(out / "findings.json", [f.to_dict() for f in findings])
    (out / "report.md").write_text(findings_md(d, findings), encoding="utf-8")
    sev = {s: sum(f.severity == s for f in findings) for s in ("error", "warning", "info")}
    print(f"findings: {out / 'findings.json'} {sev}")
    return out / "findings.json"


def cmd_annotate(a, settings) -> Path:
    from .output.annotate_pdf import annotate
    from .output.report_md import findings_md
    pdf, fj = Path(a.pdf), Path(a.findings)
    findings = _load_findings(fj)
    out_pdf = Path(a.output) if a.output else fj.parent / f"{pdf.stem}_annotated.pdf"
    n = annotate(pdf, findings, out_pdf, a.min_severity or settings["annotate"]["min_severity"])
    ext = fj.parent / "extraction.json"
    if ext.exists():  # cập nhật report để phản ánh review (dismissed / reviewer_note)
        d = DrawingExtraction.from_dict(json.loads(ext.read_text(encoding="utf-8")))
        (fj.parent / "report.md").write_text(findings_md(d, findings, str(out_pdf)), encoding="utf-8")
    print(f"annotated: {out_pdf} ({n} ghi chú)")
    return out_pdf


def cmd_dxf(a, settings) -> Path:
    from .output.export_dxf import export_dxf
    ext = Path(a.extraction)
    d = DrawingExtraction.from_dict(json.loads(ext.read_text(encoding="utf-8")))
    fj = Path(a.findings) if a.findings else ext.parent / "findings.json"
    findings = [f for f in _load_findings(fj) if not f.dismissed] if fj.exists() else []
    out = export_dxf(d, findings, ext.parent / "drawing.dxf")
    print(f"dxf: {out}")
    return out


def cmd_run(a, settings) -> None:
    ext = cmd_extract(a, settings)
    a.extraction = str(ext)
    fj = cmd_check(a, settings)
    a.findings = str(fj)
    cmd_annotate(a, settings)
    if not a.no_dxf:
        cmd_dxf(a, settings)


def cmd_pages(a, settings) -> None:
    """Liệt kê phân loại từng trang (0 token) — để chọn --pages trước khi gọi Gemini."""
    from .pdf.classify import RELEVANT, classify
    for c in classify(Path(a.pdf)):
        mark = "*" if c["category"] in RELEVANT else " "
        print(f"{mark} {c['page']:>3}  {c['category']:<14} {c['title'][:70]}")
    print("(* = được xử lý khi --pages auto)")


def cmd_rules(a, settings) -> None:
    from .rules import load_rules
    for r in load_rules(_rule_paths(settings, a.rules)):
        flag = "✓" if r.get("verified") else "*"
        on = "" if r.get("enabled", True) else " [TẮT]"
        print(f"{flag} {r['id']:<26} {r.get('source', ''):<7} {r.get('clause', '')}{on}")


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="pccc_checker", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--settings", help="đường dẫn settings.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common_extract(sp):
        sp.add_argument("pdf")
        sp.add_argument("--extractor", choices=["gemini", "vector", "hybrid"], default="hybrid")
        sp.add_argument("--pages", default="auto",
                        help="auto (mặc định: chỉ trang liên quan thoát nạn) | all | vd 1-3,5")
        sp.add_argument("--grid", default="1x1", help="cắt trang thành lưới RxC cho bản vẽ khổ lớn, vd 2x2")
        sp.add_argument("--building", help="building.yaml: thông tin công trình (nhóm F, chiều cao PCCC...)")
        sp.add_argument("--set", action="append", help="ghi đè thông tin công trình, vd --set height_pccc_m=24")
        sp.add_argument("--out", help="thư mục kết quả (mặc định data/output/<tên pdf>)")

    sp = sub.add_parser("extract"); common_extract(sp)
    sp = sub.add_parser("check")
    sp.add_argument("extraction"); sp.add_argument("--rules", action="append")
    sp.add_argument("--only", help="chỉ chạy các rule id, phân tách bằng dấu phẩy")
    sp.add_argument("--building"); sp.add_argument("--set", action="append")
    sp = sub.add_parser("annotate")
    sp.add_argument("pdf"); sp.add_argument("findings"); sp.add_argument("--output")
    sp.add_argument("--min-severity", choices=["error", "warning", "info"])
    sp = sub.add_parser("dxf"); sp.add_argument("extraction"); sp.add_argument("--findings")
    sp = sub.add_parser("run"); common_extract(sp)
    sp.add_argument("--rules", action="append"); sp.add_argument("--only")
    sp.add_argument("--output"); sp.add_argument("--min-severity", choices=["error", "warning", "info"])
    sp.add_argument("--no-dxf", action="store_true")
    sp = sub.add_parser("rules"); sp.add_argument("--rules", action="append")
    sp = sub.add_parser("pages"); sp.add_argument("pdf")

    a = p.parse_args(argv)
    settings = load_settings(Path(a.settings) if a.settings else None)
    {"extract": cmd_extract, "check": cmd_check, "annotate": cmd_annotate, "dxf": cmd_dxf,
     "run": cmd_run, "rules": cmd_rules, "pages": cmd_pages}[a.cmd](a, settings)


if __name__ == "__main__":
    main()
