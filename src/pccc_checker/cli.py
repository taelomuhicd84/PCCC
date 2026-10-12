"""CLI: python -m pccc_checker <lệnh> ...

Pipeline (mỗi bước ghi file trung gian để các agent làm việc độc lập, không phải truyền dữ liệu lớn qua context):
  info     : PDF  -> project_info.json (thông tin công trình + đầu vào PCCC: bậc chịu lửa, nhóm F, chiều cao PCCC...)
  extract  : PDF  -> extraction.json + extraction.md        (Gemini / vector text)
  check    : extraction.json -> findings.json + report.md   (rule engine, 0 token)
  annotate : PDF + findings.json -> *_annotated.pdf          (ghi chú vị trí sai)
  dxf      : extraction.json (+ findings.json) -> .dxf
  run      : info -> extract -> check -> annotate/dxf
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


def _load_info(out: Path):
    from .project_info import ProjectInfo
    f = out / "project_info.json"
    return ProjectInfo.from_dict(json.loads(f.read_text(encoding="utf-8"))) if f.exists() else None


def _apply_info(d: DrawingExtraction, info, over: dict) -> dict:
    """Ngưỡng của check lấy từ project_info.json (thay cho building do extractor đọc/suy ra).
    Trả về {khoá building: lý do} của các trường bắt buộc missing/conflict (trừ khi --set/--building đã điền)."""
    from .project_info import load_spec
    spec = load_spec()
    bmap = spec["building_map"]
    for k, v in info.to_building(spec).items():
        setattr(d.building, k, v)
    d.building.assumptions = [a for a in d.building.assumptions if a.split("=")[0].split(":")[0] not in bmap.values()]
    blocked = {bmap[k]: why for k, why in info.problems(spec).items() if k in bmap}
    return {k: v for k, v in blocked.items() if over.get(k) is None}


def _print_info(info) -> None:
    from .project_info import hang_muc_table, load_spec, table_rows
    spec = load_spec()
    rows = table_rows(info, spec)
    head, hm = hang_muc_table(info, spec)
    if hm:
        print("Hạng mục trong khu đất:")
        for r in [head, *hm]:
            print("  " + " | ".join(r))
        print()
    w = [max(len(r[i]) for r in rows) for i in range(4)]
    print(f"{'trường':<{w[1]}} | {'giá trị':<{min(w[2], 50)}} | {'trang':<{w[3]}} | trạng thái")
    print("-" * (w[1] + min(w[2], 50) + w[3] + 20))
    for _, label, val, pages, st in rows:
        print(f"{label:<{w[1]}} | {val[:50]:<{min(w[2], 50)}} | {pages:<{w[3]}} | {st}")
    for x in info.warnings:
        print(f"⚠ {x}")


# ------------------------------------------------------------------ commands
def cmd_info(a, settings) -> Path:
    from .project_info import info_markdown, info_summary, load_spec, read_project_info
    pdf = Path(a.pdf)
    out = _out_dir(pdf, a.out)
    pages = _pages(a.info_pages) if getattr(a, "info_pages", None) else None
    info = read_project_info(pdf, settings, a.gemini_info, Path(a.project) if a.project else None,
                             cache_dir=PROJECT_ROOT / "data" / "cache",
                             pages=pages if isinstance(pages, list) else None,
                             gemini_pages=_pages(a.gemini_pages) if getattr(a, "gemini_pages", None) else None,
                             log=lambda m: print(m, file=sys.stderr))
    _write_json(out / "project_info.json", info.to_dict())
    spec = load_spec()
    (out / "project_info.md").write_text(info_summary(info, spec), encoding="utf-8")              # bản gọn
    (out / "project_info_chi_tiet.md").write_text(info_markdown(info, spec), encoding="utf-8")    # mọi căn cứ
    _print_info(info)
    print(f"project_info: {out / 'project_info.json'}")
    print(f"để kiểm tra: {out / 'project_info.md'}")
    return out / "project_info.json"


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
    info = _load_info(ext.parent)       # không có (extraction.json cũ) -> dùng building trong extraction.json
    blocked = _apply_info(d, info, over) if info else {}
    for k, v in over.items():
        setattr(d.building, k, v)
    findings = run_rules(load_rules(_rule_paths(settings, a.rules)), d, set(a.only.split(",")) if a.only else None,
                         blocked=blocked)
    out = ext.parent
    _write_json(out / "findings.json", [f.to_dict() for f in findings])
    (out / "report.md").write_text(findings_md(d, findings, info=info), encoding="utf-8")
    if not info:
        print("(không có project_info.json — dùng thông tin công trình trong extraction.json)")
    sev = {s: sum(f.severity == s and f.status != "cannot_check" for f in findings) for s in ("error", "warning", "info")}
    sev["cannot_check"] = sum(f.status == "cannot_check" for f in findings)
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
        (fj.parent / "report.md").write_text(findings_md(d, findings, str(out_pdf), info=_load_info(fj.parent)),
                                             encoding="utf-8")
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
    cmd_info(a, settings)
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


def cmd_gemini_login(a, settings):
    from .extractors.gemini_extractor import backend_kwargs
    from .extractors.gemini_web import GeminiWeb
    web = GeminiWeb(**{**backend_kwargs(dict(settings["gemini"], backend="web"))["web"], "headless": False})
    print("Đăng nhập Google trong cửa sổ Chrome vừa mở (chờ tối đa 10 phút)...")
    ok = web.login()
    web.close()
    print("Đã đăng nhập Gemini web, cookie lưu trong profile." if ok else "Chưa đăng nhập được — chạy lại lệnh.")


def cmd_gemini_status(a, settings):
    """Kiểm tra nhanh đã đăng nhập Gemini web chưa (profile + cookie .env). Exit 1 nếu chưa."""
    from .extractors.gemini_extractor import backend_kwargs
    from .extractors.gemini_web import GeminiWeb
    web = GeminiWeb(**backend_kwargs(dict(settings["gemini"], backend="web"))["web"])
    ok = web.login(wait_s=0)
    web.close()
    print("Gemini web: ĐÃ đăng nhập" if ok else
          "Gemini web: CHƯA đăng nhập — chạy: python -m pccc_checker gemini-login")
    sys.exit(0 if ok else 1)


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

    def common_info(sp):
        sp.add_argument("--project", help="project.yaml: người dùng xác nhận/bổ sung thông tin (luôn ưu tiên)")
        sp.add_argument("--gemini-info", choices=["auto", "always", "never"], default="auto",
                        help="auto: Gemini chỉ đọc trang không có text / bảng regex không tách được")
        sp.add_argument("--info-pages", help="chỉ đọc các trang này cho bước info, vd 1,5,43")
        sp.add_argument("--gemini-pages", help="thêm: Gemini đọc các trang này (ngoài trang tự chọn), vd 4,15")

    sp = sub.add_parser("info"); sp.add_argument("pdf"); sp.add_argument("--out"); common_info(sp)
    sp = sub.add_parser("extract"); common_extract(sp)
    sp = sub.add_parser("check")
    sp.add_argument("extraction"); sp.add_argument("--rules", action="append")
    sp.add_argument("--only", help="chỉ chạy các rule id, phân tách bằng dấu phẩy")
    sp.add_argument("--building"); sp.add_argument("--set", action="append")
    sp = sub.add_parser("annotate")
    sp.add_argument("pdf"); sp.add_argument("findings"); sp.add_argument("--output")
    sp.add_argument("--min-severity", choices=["error", "warning", "info"])
    sp = sub.add_parser("dxf"); sp.add_argument("extraction"); sp.add_argument("--findings")
    sp = sub.add_parser("run"); common_extract(sp); common_info(sp)
    sp.add_argument("--rules", action="append"); sp.add_argument("--only")
    sp.add_argument("--output"); sp.add_argument("--min-severity", choices=["error", "warning", "info"])
    sp.add_argument("--no-dxf", action="store_true")
    sp = sub.add_parser("rules"); sp.add_argument("--rules", action="append")
    sp = sub.add_parser("pages"); sp.add_argument("pdf")
    sub.add_parser("gemini-login", help="mở Chrome để đăng nhập Gemini web (backend: web)")
    sub.add_parser("gemini-status", help="kiểm tra đã đăng nhập Gemini web chưa (exit 1 nếu chưa)")

    a = p.parse_args(argv)
    settings = load_settings(Path(a.settings) if a.settings else None)
    {"info": cmd_info, "extract": cmd_extract, "check": cmd_check, "annotate": cmd_annotate, "dxf": cmd_dxf,
     "run": cmd_run, "rules": cmd_rules, "pages": cmd_pages, "gemini-login": cmd_gemini_login,
     "gemini-status": cmd_gemini_status}[a.cmd](a, settings)


if __name__ == "__main__":
    main()
