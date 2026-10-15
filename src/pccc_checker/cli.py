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
Pipeline 8 bước · 2 cổng Claude (docs/ARCHITECTURE.md):
  intake   : PDF -> page_index.json (luồng LAYER/HON-HOP/SCAN, vùng ảnh, mã băm từng trang) — 0 token
  hm-pages : trang -> hạng mục (hm_pages.json); check chạy riêng từng hạng mục, ngưỡng theo thông số hạng mục đó
  va-cham  : chỗ bản vẽ tự mâu thuẫn (nghi_ngo.json + trường conflict + kiểm tra logic) -> va_cham.json + PDF ghi chú
  trang    : danh mục bản vẽ (trang -> tên bản vẽ, ký hiệu, chuyên đề); --cd <chuyên đề> -> trang skill đó cần đọc
  facts    : project_info.json -> project_facts.json + cong1.md (ô dữ liệu H/M/L + kiểm tra logic) — Cổng 1 đọc
  keys     : project_facts.json -> rule_keys.json (loại hình, bộ bảng tra, file cần nạp từng chuyên đề)
  findings : findings.json -> findings.jsonl (D/KD/XM/NA; KD thiếu bằng chứng -> XM) | --check <file.jsonl>
"""
from __future__ import annotations

import argparse
import json
import re
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
    gp = getattr(a, "gemini_pages", None)
    if gp == "smart":                       # lọc trước bằng lớp chữ (0 token); vector vẫn đọc mọi trang
        from .pdf.classify import smart_gemini_pages
        from .pdf.render import page_count
        smart, why = smart_gemini_pages(pdf)
        print(f"[info] lọc trang Gemini: {why}: {smart}", file=sys.stderr)
        a.gemini_pages = ",".join(map(str, smart))
        if pages is None:
            pages = list(range(1, page_count(pdf) + 1))
    w = settings["gemini"].setdefault("web", {})
    for k in ("upload", "chunk_pages", "tabs", "thinking"):
        if getattr(a, k, None):
            w[k] = getattr(a, k)
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
    dm = _danh_muc(out, pdf, refresh=True)
    print(f"danh mục bản vẽ: {out / 'danh_muc_ban_ve.md'} ({sum(bool(d['ten_ban_ve']) for d in dm)}/{len(dm)} trang có tên)")
    print(f"project_info: {out / 'project_info.json'}")
    print(f"để kiểm tra: {out / 'project_info.md'}")
    return out / "project_info.json"


def _danh_muc(out: Path, pdf: Path | None = None, refresh: bool = False) -> list[dict]:
    """danh_muc_ban_ve.json: trang -> tên bản vẽ / ký hiệu / hạng mục / chuyên đề (0 token). Chưa có -> đọc khung tên."""
    from .pipeline import sheets
    f = out / "danh_muc_ban_ve.json"
    if f.exists() and not refresh:
        return json.loads(f.read_text(encoding="utf-8"))
    if pdf is None:
        pi = out / "project_info.json"
        pdf = Path((json.loads(pi.read_text(encoding="utf-8")).get("meta") or {}).get("pdf") or "") if pi.exists() else None
    if not pdf or not Path(pdf).is_file():
        raise SystemExit(f"cần PDF gốc để lập danh mục bản vẽ (--pdf), không thấy: {pdf}")
    dm = sheets.danh_muc(Path(pdf))
    _write_json(f, dm)
    (out / "danh_muc_ban_ve.md").write_text(sheets.to_md(dm), encoding="utf-8")
    return dm


def cmd_trang(a, settings) -> None:
    """Tra trang theo chuyên đề / in danh mục bản vẽ; --html chèn mục danh mục vào thong_tin_cong_trinh.html."""
    from .pipeline import sheets
    out = _out_of(a.target)
    dm = _danh_muc(out, Path(a.pdf) if a.pdf else None, refresh=a.lam_lai)
    if a.cd:
        pages = sheets.pages_for(dm, a.cd)
        print(",".join(map(str, pages)))
        for d in dm:
            if d["trang"] in pages:
                print(f"  {d['trang']:>3} {d['ky_hieu']:<12} {d['ten_ban_ve'][:80]}")
    else:
        for d in dm:
            print(f"  {d['trang']:>3} {d['ky_hieu']:<12} {(d['ten_ban_ve'] or '—')[:70]:<70} {','.join(d['chuyen_de'])}")
    if a.html:
        h = out / "thong_tin_cong_trinh.html"
        if not h.exists():
            raise SystemExit(f"chưa có {h}")
        h.write_text(sheets.insert_html(h.read_text(encoding="utf-8"), dm), encoding="utf-8")
        print(f"đã thêm mục Danh mục bản vẽ vào {h}")


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


def hm_owners(out: Path, info, pdf: Path | None = None, refresh: bool = False) -> dict[int, list[str]]:
    """Trang -> hạng mục (`hm_pages.json`, Claude sửa tay được). Chưa có file -> tính từ chữ PDF rồi ghi file."""
    from .pipeline import hm_pages
    f = out / "hm_pages.json"
    if f.exists() and not refresh:
        return {int(k): v for k, v in json.loads(f.read_text(encoding="utf-8"))["trang"].items()}
    pdf = pdf or Path((info.meta or {}).get("pdf") or "")
    if not pdf.is_file():
        raise SystemExit(f"cần PDF để chia trang theo hạng mục (--pdf), không thấy: {pdf}")
    pi = out / "page_index.json"
    idx = json.loads(pi.read_text(encoding="utf-8")) if pi.exists() else []
    owners = hm_pages.from_pdf(pdf, list(info.hang_muc), cats={p["trang"]: p["loai"] for p in idx},
                               titles={p["trang"]: p["tieu_de"] for p in idx})
    _write_json(f, {"ghi_chu": "trang -> hạng mục (tự chia theo tên hạng mục trong chữ trang; sửa tay được). "
                               "'chung' = trang tổng thể, kiểm theo hạng mục mặc định",
                    "hang_muc": hm_pages.by_hm(owners), "trang": {str(p): v for p, v in owners.items()}})
    return owners


def _run_one(d: DrawingExtraction, info, over: dict, rules: list, only) -> list[Finding]:
    from .rules import run_rules
    blocked = _apply_info(d, info, over) if info else {}
    for k, v in over.items():
        setattr(d.building, k, v)
    return run_rules(rules, d, only, blocked=blocked)


def cmd_check(a, settings) -> Path:
    import copy

    from .output.report_md import findings_md
    from .pipeline.hm_pages import CHUNG
    from .project_info import load_spec
    from .rules import load_rules
    ext = Path(a.extraction)
    d = DrawingExtraction.from_dict(json.loads(ext.read_text(encoding="utf-8")))
    over = _building(getattr(a, "building", None), getattr(a, "set", None))
    info = _load_info(ext.parent)       # không có (extraction.json cũ) -> dùng building trong extraction.json
    rules = load_rules(_rule_paths(settings, a.rules))
    only = set(a.only.split(",")) if a.only else None
    out = ext.parent
    if info and len(info.hang_muc) > 1 and not getattr(a, "mot_hm", False):
        # mọi hạng mục đều là hạng mục chính: mỗi hạng mục kiểm trên trang của nó, ngưỡng theo thông số của nó
        owners = hm_owners(out, info, Path(a.pdf) if getattr(a, "pdf", None) else None)
        spec = load_spec()
        groups: dict[str, list] = {}
        for p in d.pages:
            for name in owners.get(p.page, [CHUNG]):
                groups.setdefault(name, []).append(p)
        findings = []
        for name in [*info.hang_muc, CHUNG]:
            if name not in groups:
                continue
            sub = copy.deepcopy(d)
            sub.pages = copy.deepcopy(groups[name])
            fs = _run_one(sub, info if name == CHUNG else info.for_hang_muc(name, spec), over, rules, only)
            for f in fs:
                f.hang_muc = name
            findings += fs
            n_err = sum(f.status != "cannot_check" and f.severity == "error" for f in fs)
            n_cc = sum(f.status == "cannot_check" for f in fs)
            print(f"  {name}: {len(groups[name])} trang · {n_err} lỗi · {n_cc} không kiểm được")
        missing = [n for n in info.hang_muc if n not in groups]
        if missing:
            print(f"  chưa có trang trong extraction (không kiểm): {', '.join(missing)}")
    else:
        findings = _run_one(d, info, over, rules, only)
    _write_json(out / "findings.json", [f.to_dict() for f in findings])
    (out / "report.md").write_text(findings_md(d, findings, info=info), encoding="utf-8")
    if not info:
        print("(không có project_info.json — dùng thông tin công trình trong extraction.json)")
    sev = {s: sum(f.severity == s and f.status != "cannot_check" for f in findings) for s in ("error", "warning", "info")}
    sev["cannot_check"] = sum(f.status == "cannot_check" for f in findings)
    print(f"findings: {out / 'findings.json'} {sev}")
    return out / "findings.json"


def cmd_hm_pages(a, settings) -> Path:
    out = _out_of(a.target)
    info = _load_info(out)
    if not info or not info.hang_muc:
        raise SystemExit(f"chưa có project_info.json có hạng mục trong {out} — chạy `info` trước")
    owners = hm_owners(out, info, Path(a.pdf) if a.pdf else None, refresh=True)
    from .pipeline.hm_pages import by_hm
    for name, pages in by_hm(owners).items():
        print(f"  {name}: {len(pages)} trang — {_ranges(pages)}")
    print(f"hm_pages: {out / 'hm_pages.json'}")
    return out / "hm_pages.json"


def _note_phan_hoi(out: Path, items: list, pdf: Path, pdf_notes: list[str]) -> Path:
    """Word "Note phản hồi.docx": mọi vị trí ghi chú (va chạm + KD/XM của findings.jsonl nếu có), xếp theo trang."""
    from .output import note_phan_hoi as nph
    from .pipeline.consistency import read_jsonl
    rows = nph.rows_va_cham(items)
    fj, pf = out / "findings.jsonl", out / "project_facts.json"
    if fj.exists():
        names = {h["id"]: h["ten"][0] for h in json.loads(pf.read_text(encoding="utf-8"))["hang_muc"]} if pf.exists() else {}
        rows += nph.rows_findings(read_jsonl(fj), names)
        ann = out / f"{pdf.stem}_annotated.pdf"
        if ann.exists():
            pdf_notes = [*pdf_notes, ann.name]
    return nph.build(rows, out / nph.TEN_FILE, pdf.stem, pdf_notes)


def cmd_va_cham(a, settings) -> Path:
    from .pipeline import va_cham
    out = _out_of(a.target)
    info = json.loads((out / "project_info.json").read_text(encoding="utf-8")) if (out / "project_info.json").exists() else {}
    pdf = Path(a.pdf) if a.pdf else Path((info.get("meta") or {}).get("pdf") or "")
    if not pdf.is_file():
        raise SystemExit(f"không thấy PDF gốc: {pdf} — dùng --pdf")
    items = va_cham.collect(out)
    pi = out / "page_index.json"
    va_cham.locate(items, pdf, json.loads(pi.read_text(encoding="utf-8")) if pi.exists() else None)
    fx = out / "va_cham_claude.json"
    if fx.exists():
        for x in va_cham.apply_claude(items, json.loads(fx.read_text(encoding="utf-8")), pdf):
            print(f"  claude: {x}")
    _write_json(out / "va_cham.json", {"pdf": str(pdf), "va_cham": items})
    (out / "va_cham.md").write_text(va_cham.to_md(items), encoding="utf-8")
    con = sum(not it.get("bo") for it in items)
    print(f"va_cham: {out / 'va_cham.json'} — {con} va chạm ({len(items) - con} đã bỏ), "
          + ", ".join(f"{k} {sum(it['loai'] == k and not it.get('bo') for it in items)}" for k in ("ban_ve", "doc_lech", "logic")))
    need = va_cham.can_claude(items)
    if need:
        print(f"Claude cần chỉ vị trí ({len(need)}) -> ghi va_cham_claude.json rồi chạy lại:")
        for x in need:
            print(f"  {x}")
    if a.annotate:
        pdf_out = out / f"{pdf.stem}_va_cham.pdf"
        print(f"PDF ghi chú: {pdf_out} ({va_cham.annotate(pdf, items, pdf_out)} ghi chú)")
        print(f"Word: {_note_phan_hoi(out, items, pdf, [pdf_out.name])}")
    return out / "va_cham.json"


def _ranges(pages: list[int]) -> str:
    out, start = [], None
    for i, p in enumerate(pages):
        if start is None:
            start = p
        if i + 1 == len(pages) or pages[i + 1] != p + 1:
            out.append(str(start) if start == p else f"{start}-{p}")
            start = None
    return ",".join(out)


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


def cmd_crops(a, settings) -> None:
    """Cắt bảng dán dạng ảnh ra PNG (0 token) — Claude mở đúng ảnh để kiểm giá trị * mà Gemini đọc."""
    from .pdf.render import export_image_tables, page_count
    pdf = Path(a.pdf)
    pages = _pages(a.pages) if a.pages else list(range(1, page_count(pdf) + 1))
    files = export_image_tables(pdf, pages, _out_dir(pdf, a.out) / "crops")
    for f in files:
        print(f)
    print(f"{len(files)} bảng ảnh")


def cmd_intake(a, settings) -> Path:
    from .pipeline.intake import diff_hashes, page_index, summary
    pdf = Path(a.pdf)
    f = _out_dir(pdf, a.out) / "page_index.json"
    old = json.loads(f.read_text(encoding="utf-8")) if f.exists() else None
    idx = page_index(pdf)
    _write_json(f, idx)
    print(f"page_index: {f} — {summary(idx)}")
    for p in idx:
        if p["luong"] != "LAYER":
            print(f"  {p['trang']:>3} {p['luong']:<8} {p['loai']:<14} {len(p['vung_anh'])} vùng ảnh  {p['tieu_de'][:50]}")
    if old is not None:
        changed = diff_hashes(old, idx)
        print(f"so với lần trước: {len(changed)} trang đổi {changed if changed else ''}".rstrip())
    return f


def _out_of(path: str) -> Path:
    p = Path(path)
    return p if p.is_dir() else p.parent


def cmd_facts(a, settings) -> Path:
    from .pipeline.facts import build_facts, gate1_md
    out = _out_of(a.target)
    info = json.loads((out / "project_info.json").read_text(encoding="utf-8"))
    pdf = Path(a.pdf) if a.pdf else Path((info.get("meta") or {}).get("pdf") or "")
    facts = build_facts(info, out, pdf if pdf.is_file() else None)
    _write_json(out / "project_facts.json", facts)
    (out / "cong1.md").write_text(gate1_md(facts), encoding="utf-8")
    conf = [c for h in facts["hang_muc"] for k, c in h.items() if isinstance(c, list) and len(c) == 4]
    print(f"project_facts: {out / 'project_facts.json'} — {len(facts['hang_muc'])} hạng mục, ô "
          + ", ".join(f"{t} {sum(c[3] == t and c[0] is not None for c in conf)}" for t in "HML")
          + f", {len(facts['kiem_tra'])} kiểm tra logic")
    print(f"Cổng 1: {out / 'cong1.md'}")
    return out / "project_facts.json"


def _nguon_doi_tuong(out: Path) -> dict:
    """Khu vực trong hạng mục (project_info meta.khu_vuc) + danh mục bản vẽ -> dò dấu hiệu đối tượng (phòng bơm…)."""
    pi, dm = out / "project_info.json", out / "danh_muc_ban_ve.json"
    kv = json.loads(pi.read_text(encoding="utf-8")).get("meta", {}).get("khu_vuc") if pi.exists() else None
    return {"khu_vuc": kv or [], "danh_muc": json.loads(dm.read_text(encoding="utf-8")) if dm.exists() else []}


def cmd_danh_gia(a, settings) -> Path:
    """Khung danh_gia_cong_nang.json (skill danh-gia-cong-nang điền); chạy lại giữ quyết định đã điền."""
    from .pipeline import danh_gia
    from .pipeline.rule_keys import build_rule_keys
    out = _out_of(a.target)
    facts = json.loads((out / "project_facts.json").read_text(encoding="utf-8"))
    cu = danh_gia.doc(out)
    dg = danh_gia.khung(build_rule_keys(facts, out.name, danh_gia=cu, **_nguon_doi_tuong(out)), cu)
    _write_json(out / danh_gia.TEN_FILE, dg)
    for h in dg["hang_muc"]:
        n = sum(v["ap_dung"] is None for v in [*h["chuyen_de"].values(), *h["he_thong"].values()])
        print(f"{h['hm']} {h['ten']}: đề xuất {h['de_xuat']['loai_hinh']} ({h['de_xuat']['mau']}) · "
              f"{len(h['chuyen_de'])} chuyên đề + {len(h['he_thong'])} mẫu hệ thống · {n} ô chưa đánh giá")
        for k, v in [*h["chuyen_de"].items(), *h["he_thong"].items()]:
            if v.get("nguon") == "dau_hieu":
                print(f"   ✓ {k}: {v['ly_do'][:120]}")
    print(f"danh_gia_cong_nang: {out / danh_gia.TEN_FILE}")
    return out / danh_gia.TEN_FILE


def cmd_keys(a, settings) -> Path:
    from .pipeline import danh_gia
    from .pipeline.rule_keys import build_rule_keys
    out = _out_of(a.target)
    facts = json.loads((out / "project_facts.json").read_text(encoding="utf-8"))
    rk = build_rule_keys(facts, out.name, danh_gia=danh_gia.doc(out), **_nguon_doi_tuong(out))
    if (out / "danh_muc_ban_ve.json").exists():          # skill chuyên đề chỉ đọc đúng các trang của mình
        from .pipeline.sheets import pages_for
        dm = _danh_muc(out)
        tags = {c for d in dm for c in d["chuyen_de"]}
        # khóa cả slug ("ngan-chay") lẫn tiểu mục ("ngan-chay.dung") để skill tra trực tiếp
        rk["trang_theo_chuyen_de"] = {cd: pages_for(dm, cd) for cd in sorted(tags | {t.split(".")[0] for t in tags})}
    _write_json(out / "rule_keys.json", rk)
    for h in rk["hang_muc"]:
        print(f"{h['hm']} {h['ten']}: {h['loai_hinh']}{'/' + h['bo'] if h['bo'] else ''}"
              f"{' · thiếu ' + ', '.join(h['thieu']) if h['thieu'] else ''}{' · ' + '; '.join(h['ghi_chu']) if h['ghi_chu'] else ''}")
    print(f"rule_keys: {out / 'rule_keys.json'}")
    return out / "rule_keys.json"


def cmd_findings(a, settings) -> Path:
    from .pipeline.consistency import from_engine, read_jsonl, summary, validate, write_jsonl
    if a.check:
        f = Path(a.check)
        rows = read_jsonl(f)
    else:
        out = _out_of(a.target)
        f = out / "findings.jsonl"
        eng = json.loads((out / "findings.json").read_text(encoding="utf-8"))
        ext = out / "extraction.json"
        pf = out / "project_facts.json"
        ids = {h["ten"][0]: h["id"] for h in json.loads(pf.read_text(encoding="utf-8"))["hang_muc"]} if pf.exists() else {}
        rows = from_engine(eng, json.loads(ext.read_text(encoding="utf-8")) if ext.exists() else None, a.hm, ids)
        if f.exists() and not a.replace:      # giữ dòng do skill chuyên đề / reviewer ghi (khác nguồn engine)
            rows = [r for r in read_jsonl(f) if r.get("nguon") != "engine"] + [dict(r, nguon="engine") for r in rows]
        else:
            rows = [dict(r, nguon="engine") for r in rows]
    rows, log = validate(rows)
    write_jsonl(f, rows)
    for x in log:
        print(f"  {x}")
    print(f"findings: {f} — {summary(rows)}")
    return f


def cmd_knowled(a, settings) -> None:
    """Kho kiến thức (skill knowled): tra / xem / nạp / duyệt — nạp theo nhu cầu, không nạp cả kho."""
    from .pipeline import knowled
    if a.act == "tim":
        kq = knowled.tim(" ".join(a.args), a.top, a.nhom)
        for sc, m, tr in kq:
            print(f"{m['id']} [{'✓' if m['trang_thai'] == 'verified' else '? chờ duyệt'}] {m['tieu_de']}\n    …{tr}…")
        if not kq:
            print("không có trong kho — ghi vào knowledge/thieu/ hoặc nhờ người dùng nạp (knowled them)")
    elif a.act == "doc":
        for i in a.args:
            m = knowled.lay(i)
            print(f"# {m['id']} [{m['trang_thai']}] {m['tieu_de']} — nguồn: {m['nguon']}\n{m['noi_dung'][: a.toi_da]}" if m
                  else f"{i}: không có trong kho")
    elif a.act == "ds":
        print(f"đã ghi {knowled.ghi_muc_luc()} — {len(knowled.muc_kho())} mục (gồm file nguồn mặc định)")
    elif a.act == "them":
        f = knowled.them(Path(a.args[0]), a.id, a.tieu_de or Path(a.args[0]).stem, a.nhom, a.tu_khoa or "", a.nguon or "", a.duyet)
        print(f"đã nạp {f} ({'verified' if a.duyet else 'chờ duyệt — `knowled duyet <id>` sau khi đối chiếu nguyên văn'})")
    elif a.act == "duyet":
        print(f"đã duyệt {knowled.duyet(a.args[0])}")


def cmd_xuat_bang(a, settings) -> None:
    """findings.jsonl -> điền vào Word mẫu datamau/B*.docx (Nội dung thiết kế + Kết luận) -> <thư mục>/bang_doi_chieu/.
    --gemini: Gemini viết lại cột Nội dung thiết kế theo văn phong mẫu + sửa chính tả (script kiểm số liệu; Claude giám sát)."""
    from .output import bang_doi_chieu, viet_tk
    out = Path(a.target)
    if a.gemini:
        from .extractors.gemini_extractor import backend_kwargs
        from .extractors.gemini_web import GeminiWeb
        ds = [d for d in bang_doi_chieu.thu_dong(out, a.hm) if d[3].get("ly_do") or d[3].get("evid")]
        facts = (out / "thong_tin_chung.json").read_text(encoding="utf-8") if (out / "thong_tin_chung.json").exists() else "{}"
        facts = json.loads(facts).get("tom_tat", "")
        vf = out / "goi" / "tk_bang.json"
        kq = json.loads(vf.read_text(encoding="utf-8")) if vf.exists() else {}
        todo = [d for d in ds if d[0] not in kq]
        kw = backend_kwargs(dict(settings["gemini"], backend="web"))["web"]
        web = GeminiWeb(**{**kw, "timeout_s": a.timeout})
        for i in range(0, len(todo), a.dong):
            lo = todo[i:i + a.dong]
            dv = {d[0]: viet_tk.dong_dau_vao(d[0], d[1], d[2], d[3], facts) for d in lo}
            tf = out / "goi" / f"tk_lo{i // a.dong + 1}.txt"
            viet_tk.tao_file(tf, list(dv.values()))
            text = web.generate(settings["gemini"]["web"]["model"], tf.read_bytes(), viet_tk.LENH, tf.name, "text/plain")
            (out / "goi" / f"tk_lo{i // a.dong + 1}.gemini.txt").write_text(text, encoding="utf-8")
            ok = 0
            got = viet_tk.parse(text)
            for d in lo:
                tk, gc = got.get(d[0], ("", ""))
                why = viet_tk.kiem(d[0], d[3], tk, gc, dv[d[0]])
                kq[d[0]] = dict(tk=tk, gc=gc, nguon="gemini") if not why else dict(tk="", gc="", nguon="script", tu_choi=why)
                ok += not why
            vf.write_text(json.dumps(kq, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  lô {i // a.dong + 1}: {len(lo)} dòng — nhận {ok}, từ chối {len(lo) - ok} (giữ bản script)")
    for p, st in bang_doi_chieu.xuat(out, a.hm):
        print(f"{p} — điền {st['dien']} hàng, chưa đánh giá {st['chua_danh_gia']}, không thấy hàng {st['khong_hang']}")


def cmd_cong_nang(a, settings) -> None:
    """Đề xuất công năng TỪNG hạng mục (nhóm F, hỗn hợp theo quy tắc 70 %) -> cong_nang_de_xuat.json; --ap-dung điền ô chắc chắn vào danh_gia_cong_nang.json."""
    from .pipeline import cong_nang, danh_gia
    from .pipeline.loai_hinh import chon
    from .pipeline.rule_keys import _cung_hm
    out = _out_of(a.target)
    facts = json.loads((out / "project_facts.json").read_text(encoding="utf-8"))
    pi = out / "project_info.json"
    kv = (json.loads(pi.read_text(encoding="utf-8")).get("meta") or {}).get("khu_vuc") or [] if pi.exists() else []
    rs = cong_nang.luat()
    res = []
    for h in facts["hang_muc"]:
        ten = h["ten"][0]
        khu, canh = cong_nang.khu_cua_hm(kv, ten, _cung_hm)
        san = (h.get("dt_san_tong_m2") or [None])[0]
        r = cong_nang.danh_gia_hm(ten, khu, san, rs, canh)
        r.update(hm=h["id"], tong_san=san, khu=[k["ten"] for k in khu][:12])
        res.append(r)
    (out / "cong_nang_de_xuat.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    nhan = dict(don_nang="đơn năng", hon_hop="HỖN HỢP", khong_chac="KHÔNG CHẮC", ky_thuat="kỹ thuật/PCCC")
    dg = danh_gia.doc(out)
    n_ap = 0
    for r in res:
        k = r["ket_luan"].replace("-", "_")
        ty = " · ".join(f"{g} {v:.0%}" for g, v in r["ty_le"].items())
        print(f"{r['hm']} {r['ten']}: {nhan.get(k, k)}" + (f" — chính {r['chinh']}" if r["chinh"] else "") + (f" [{ty}]" if ty else ""))
        for c in r["canh_bao"]:
            print(f"     ⚠ {c}")
        for c in r.get("ghi_chu", []):
            print(f"     ℹ {c}")
        if a.ap_dung and dg and r["ket_luan"] in ("don-nang", "hon-hop"):
            d = danh_gia.cho_hm(dg, r["hm"])
            if d is None:
                continue
            d["nhom_nha_tinh"] = d["nhom_nha_tinh"] or r["chinh"]
            d["hon_hop"] = r["ket_luan"] == "hon-hop" if d["hon_hop"] is None else d["hon_hop"]
            d["cong_nang_danh_gia"] = d["cong_nang_danh_gia"] or r["can_cu"]
            if not d["can_cu"]:
                d["can_cu"] = [r["can_cu"]]
            if r["ket_luan"] == "hon-hop" and not d["loai_hinh"]:
                d["loai_hinh"] = "hon-hop"
            elif r["ket_luan"] == "don-nang" and not d["loai_hinh"]:
                lh, _, _ = chon(r["ten"], " ".join(r["khu"]), r["chinh"], None)
                d["loai_hinh"] = lh or d["loai_hinh"]
            n_ap += 1
    if a.ap_dung and dg:
        _write_json(out / danh_gia.TEN_FILE, dg)
        print(f"đã điền {n_ap} hạng mục chắc chắn vào {danh_gia.TEN_FILE}; hạng mục KHÔNG CHẮC để Claude/người dùng quyết")
    print(f"cong_nang_de_xuat: {out / 'cong_nang_de_xuat.json'}")


def cmd_dong(a, settings) -> None:
    """In đủ 1 dòng bảng tra (khi gói `goi` đã cắt bớt cột Quy định)."""
    from .pipeline.goi import dong_day_du
    for i in a.id:
        print(dong_day_du(i) or f"{i}: không có trong bảng tra")


def cmd_goi(a, settings) -> None:
    """Gói đối chiếu: script lọc dòng bảng tra (tiêu đề / NA / XM tự động / đã có trong bộ nhớ đệm) rồi chỉ đưa dòng cần xét."""
    from .pipeline import goi
    from .pipeline.chuyen_de import MUC
    from .pipeline.consistency import read_jsonl, write_jsonl
    from .pipeline.sheets import pages_for
    out = _out_of(a.target)
    facts = json.loads((out / "project_facts.json").read_text(encoding="utf-8"))
    want = set(a.hm.split(",")) if a.hm else None
    hms = [goi.tom_tat_hm(h) for h in facts["hang_muc"] if want is None or h["id"] in want]
    slugs = [s for _, s, *_ in MUC]
    rkf = out / "rule_keys.json"
    ap = {h["hm"]: h.get("file") or {} for h in json.loads(rkf.read_text(encoding="utf-8"))["hang_muc"]} if rkf.exists() and not a.bang else {}
    if not a.bang and not ap:
        raise SystemExit("cần --bang <loại hình/bộ> hoặc rule_keys.json (chạy `keys` sau `danh-gia`)")
    cds = slugs[:slugs.index(a.den) + 1] if a.den else [c.strip() for c in (a.cd or "").split(",") if c.strip()]
    if not cds:                                           # không chỉ định: mọi chuyên đề đã áp dụng theo rule_keys
        cds = [s for s in slugs if any(s in f for f in ap.values())]
    if not cds:
        raise SystemExit("không có chuyên đề nào áp dụng (rule_keys.file rỗng) — chạy danh-gia/keys hoặc dùng --cd/--den + --bang")
    nhom: dict[tuple, list[dict]] = {}
    for t in hms:
        nhom.setdefault(goi.khoa_nhom(t) + (json.dumps(ap.get(t["hm"], {}), sort_keys=True),), []).append(t)
    bases = {re.sub(r"\s*\d+.*$", "", h["ten"][0]).upper() for h in facts["hang_muc"]}
    dk = goi.luat_dieu_kien()
    dm = _danh_muc(out) if (out / "danh_muc_ban_ve.json").exists() else []
    pdf = Path(a.pdf) if a.pdf else Path((json.loads((out / "project_info.json").read_text(encoding="utf-8")).get("meta") or {}).get("pdf") or "")
    lines = goi.doc_lines(pdf) if pdf.is_file() else {}
    fj = out / "findings.jsonl"
    cu = read_jsonl(fj) if fj.exists() else []
    gd = out / "goi"
    gd.mkdir(exist_ok=True)
    cache = goi.doc_cache(gd)
    moi: list[dict] = []
    tong = dict(raw=0, goi=0, xet=0, tong=0, hit=0)

    def dong(x, cd, r, tt, why, **kw):
        return dict(id=f"S-{x['hm']}-{r['id']}", hm=x["hm"], tang=None, cd=cd, rule=r["id"], yc="", ht="", tt=tt, ly_do=why,
                    truc=None, trang=kw.get("trang"), bbox=kw.get("bbox"), conf=kw.get("conf", "H"), evid=kw.get("evid", ""),
                    nguon=kw.get("nguon", "script"))

    for g in nhom.values():
        t0, ids = g[0], [x["hm"] for x in g]
        for cd in cds:
            files = goi.files_for(a.bang, cd) if a.bang else [PROJECT_ROOT / x for x in ap.get(t0["hm"], {}).get(cd, [])]
            if not files:
                continue
            tr = pages_for(dm, cd) if dm else []
            base = re.sub(r"\s*\d+.*$", "", t0["ten"]).upper()
            ten_tr = {d["trang"]: (d["ten_ban_ve"] or "").upper() for d in dm}
            khac = [b for b in bases if b != base and base not in b and b not in base]
            # giữ trang của hạng mục này + trang chung (tên bản vẽ không nêu hạng mục nào khác), bỏ trang riêng hạng mục khác
            tr = [p for p in tr if base in ten_tr.get(p, "") or not any(b in ten_tr.get(p, "") for b in khac)] or tr[:4]
            txt_all = goi.chu_trang(lines, tr) if lines else {}
            chu = " ".join(txt_all.values())                  # luôn vào khoá bộ nhớ đệm: bản vẽ đổi chữ thì xét lại
            txt = txt_all if a.kem_chu else {}
            xet, tdc, na, xm, hit, keys, bang_hm = [], 0, [], [], 0, {}, {}
            for f in files:
                for r in goi.parse_rows(f):
                    k, why = goi.phan_loai(r, t0, dk, lines or None)
                    if k == "TD":
                        tdc += 1
                    elif k == "XET":
                        key = goi.khoa_cache(r, t0, chu)
                        keys[r["id"]] = key
                        if key in cache:                       # đã xét với đúng dòng + số liệu + chữ bản vẽ này
                            hit += 1
                            c = cache[key]
                            moi += [dong(x, cd, r, c["tt"], c["ly_do"], trang=c.get("trang"), bbox=c.get("bbox"), evid=c.get("evid", ""),
                                         conf="M", nguon="cache") for x in g]
                        else:
                            xet.append(r)
                            if goi.bang_refs(r):
                                bang_hm.setdefault(r["id"], goi.bang_refs(r))
                    else:
                        (na if k == "NA" else xm).append((r, why))
                        moi += [dong(x, cd, r, k, why) for x in g]
            L = [f"# Gói đối chiếu · {cd} · {', '.join(ids)} ({', '.join(x['ten'] for x in g)}) · bảng {a.bang or ', '.join(sorted({Path(x).parent.name for x in ap.get(t0['hm'], {}).get(cd, [])}))}",
                 f"Số liệu: tầng nổi {t0['tang_noi']} · hầm {'có' if t0['co_ham'] else 'không' if t0['co_ham'] is False else '?'} · cao {t0['cao']} m · "
                 f"nhóm {t0['nhom'] or '?'} · bậc {t0['bac'] or '?'} · S {t0['s'] or '?'} · hạng {t0['hang'] or '?'} · dt {t0['dt']}",
                 f"Script đã xử lý: {tdc} tiêu đề (bỏ) · {len(na)} NA · {len(xm)} XM · {hit} dòng lấy từ bộ nhớ đệm — đã ghi findings.jsonl, KHÔNG đọc lại"]
            if na:
                L.append("NA tự động (rà nhanh, sai thì sửa rules/dieu_kien.yaml): " + "; ".join(f"{r['id']} {r['nd'][:30]}" for r, _ in na))
            if xm:
                L.append("XM tự động (bảng số liệu chưa có): " + "; ".join(r["id"] for r, _ in xm))
            L += ["", f"## Chữ trên bản vẽ (trang {', '.join(map(str, tr)) or '—'}; đã bỏ khung tên)"]
            L += [f"[tr.{p}] {s}" for p, s in txt.items()] or [f"(không kèm chữ để nhẹ gói; Gemini xem PDF các trang này. Cần chữ: goi --kem-chu)"]
            L += ["", f"## Cần Claude xét ({len(xet)} dòng) — ghi kết quả gọn vào {'+'.join(ids)}_{cd}.ket-qua.txt"]
            for r in xet:
                L.append(f"- {r['id']} · {r['nd']}" + (f" ‖ LƯU Ý: {goi._cat(r['luu_y'], 300, r['id'])}" if r["luu_y"] else "")
                         + f" ‖ QĐ: {goi._cat(r['qd'], goi.CAT_QD, r['id'])} ‖ ĐK: {r['dk']}")
            bt = goi.bang_text([i for v in bang_hm.values() for i in v])
            pb = gd / f"{'+'.join(ids)}_{cd}.bang.md"
            if bt:
                pb.write_text(bt + "\n", encoding="utf-8")
                L += ["", "Bảng số tham chiếu (nguyên văn, trong kho knowled): "
                      + ", ".join(f"qcvn06-bang-{i}" for i in dict.fromkeys(i for v in bang_hm.values() for i in v) if goi.bang_co(i))
                      + f" — gói không kèm để nhẹ; đọc bằng `knowled doc <id>` khi dòng cần số (Gemini đã được gửi kèm)."]
            elif pb.exists():
                pb.unlink()
            p = gd / f"{'+'.join(ids)}_{cd}.md"
            p.write_text("\n".join(L) + "\n", encoding="utf-8")
            (gd / f"{'+'.join(ids)}_{cd}.keys.json").write_text(json.dumps(keys), encoding="utf-8")
            (gd / f"{'+'.join(ids)}_{cd}.meta.json").write_text(json.dumps(dict(ids=ids, cd=cd, pages=tr, xet=[r["id"] for r in xet], bang=bang_hm),
                                                                          ensure_ascii=False), encoding="utf-8")
            raw = sum(len(f.read_text(encoding="utf-8")) for f in files)
            n = tdc + len(na) + len(xm) + hit + len(xet)
            tong["raw"] += goi.tok("x" * raw); tong["goi"] += goi.tok(p.read_text(encoding="utf-8")); tong["xet"] += len(xet)
            tong["tong"] += n; tong["hit"] += hit
            print(f"  {'+'.join(ids)} {cd}: {n} dòng → bỏ {tdc} tiêu đề · {len(na)} NA · {len(xm)} XM · {hit} đệm · "
                  f"cần xét {len(xet)} · ~{goi.tok('x' * raw)} → ~{goi.tok(p.read_text(encoding='utf-8'))} token — {p.name}")
    giu = [r for r in cu if not (r.get("nguon") in ("script", "cache", "gemini") and r.get("cd") in cds and r.get("hm") in {x["hm"] for x in hms})]
    write_jsonl(fj, giu + moi)
    print(f"tổng: ~{tong['raw']} token bảng tra thô → ~{tong['goi']} token gói ({tong['xet']}/{tong['tong']} dòng cần Claude xét, "
          f"{tong['hit']} từ bộ nhớ đệm); {len(moi)} dòng NA/XM/đệm do script ghi vào {fj.name}")


def cmd_goi_gemini(a, settings) -> None:
    """Gemini làm lượt đầu mọi dòng 'cần xét' (gửi PDF đúng trang + dòng quy định, gộp nhiều chuyên đề / lượt vì Gemini web
    chậm theo SỐ LƯỢT); script kiểm chứng trích dẫn; chỉ phần còn nghi -> goi/*.can-claude.md cho Claude."""
    from .extractors.gemini_extractor import backend_kwargs
    from .extractors.gemini_web import GeminiWeb
    from .pipeline import goi
    from .pipeline.consistency import read_jsonl, summary, validate, write_jsonl
    out = _out_of(a.target)
    gd = out / "goi"
    pdf = Path(a.pdf) if a.pdf else Path((json.loads((out / "project_info.json").read_text(encoding="utf-8")).get("meta") or {}).get("pdf") or "")
    lines = goi.doc_lines(pdf)
    fj = out / "findings.jsonl"
    rows = read_jsonl(fj) if fj.exists() else []
    cache = goi.doc_cache(gd)
    cds = set(a.cd.split(",")) if a.cd else None
    metas = []
    for mf in sorted(gd.glob("*.meta.json"), key=lambda x: x.name):
        m = json.loads(mf.read_text(encoding="utf-8"))
        m["stem"] = mf.name[: -len(".meta.json")]
        if (cds and m["cd"] not in cds) or not m["xet"] or (not a.lai and any(r.get("rule") == m["xet"][0] and r.get("nguon") == "gemini" for r in rows)):
            continue
        m["dong"] = {x.split(" ")[0]: x for x in goi.doc_dong_xet(gd / f"{m['stem']}.md")}
        m["keys"] = json.loads((gd / f"{m['stem']}.keys.json").read_text(encoding="utf-8"))
        m["so_lieu"] = next(ln for ln in (gd / f"{m['stem']}.md").read_text(encoding="utf-8-sig").splitlines() if ln.startswith("Số liệu:"))[8:]
        metas.append(m)
    lo: list[list[dict]] = []                               # lô: cùng nhóm hạng mục, ≤ a.dong dòng, ≤ a.toi_da_trang trang
    for m in sorted(metas, key=lambda x: (x["ids"], x["cd"])):
        if lo and lo[-1][0]["ids"] == m["ids"] and sum(len(x["xet"]) for x in lo[-1]) + len(m["xet"]) <= a.dong \
                and len({p for x in lo[-1] + [m] for p in x["pages"] if p in lines}) <= a.toi_da_trang:
            lo[-1].append(m)
        else:
            lo.append([m])
    web, tong, ra_na = None, dict(g=0, d=0, na=0, claude=0), []
    try:
        for L in lo:
            pages = sorted({p for x in L for p in x["pages"] if p in lines})
            if not pages:
                print(f"  {'+'.join(L[0]['ids'])} {[x['cd'] for x in L]}: không có trang bản vẽ để gửi — để Claude xét")
                continue
            dong = [x["dong"][r] for x in L for r in x["xet"]]
            bt = "\n\n".join(b for b in (goi.doc_bang(gd / f"{x['stem']}.bang.md") for x in L) if b)
            prompt = goi.prompt_gemini(L[0]["so_lieu"], pages, dong, bt)
            ten = f"{'+'.join(L[0]['ids'])} [{', '.join(x['cd'] for x in L)}]"
            if a.thu:
                print(f"  lô {ten}: {len(dong)} dòng · {len(pages)} trang · prompt ~{goi.tok(prompt)} token (chưa gửi)")
                continue
            tf = gd / f"{L[0]['stem']}.gemini.txt"
            if a.lai and tf.exists():                       # phân tích lại câu trả lời đã lưu, không gọi Gemini
                text = tf.read_text(encoding="utf-8")
            else:
                if web is None:
                    kw = backend_kwargs(dict(settings["gemini"], backend="web"))["web"]
                    web = GeminiWeb(**{**kw, "timeout_s": a.timeout})
                text = web.generate(settings["gemini"]["web"]["model"], goi.pdf_trang(pdf, pages), prompt, "goi.pdf", "application/pdf")
                tf.write_text(text, encoding="utf-8")
            for x in L:
                can_bang = {r for r, ids_b in x.get("bang", {}).items() if goi.bang_thieu(ids_b)}
                kq = goi.phan_tich_gemini(text, x["xet"], lines, can_bang)
                can = []
                for rid, k in kq.items():
                    rows = [r for r in rows if not (r.get("rule") == rid and r.get("hm") in x["ids"] and r.get("cd") == x["cd"])]
                    rows += [dict(id=f"G-{hm}-{rid}", hm=hm, tang=None, cd=x["cd"], rule=rid, yc="", ht="", tt=k["tt"], ly_do=k["ly_do"],
                                  truc=None, trang=k["trang"], bbox=None, conf="M" if k["tt"] == "D" else "L", evid=k["evid"],
                                  nguon="gemini") for hm in x["ids"]]
                    tong["g"] += 1
                    if k["tt"] == "NA":                 # NA Gemini không kiểm chứng được bằng trích dẫn -> chỉ rà soát, KHÔNG vào đệm
                        tong["na"] += 1
                        ra_na.append(f"{rid} tr.{k['trang'] or '?'} | {k['ly_do'][:110]}")
                    elif k["tt"] == "D":                # D có trích dẫn thật -> vào bộ nhớ đệm
                        tong["d"] += 1
                        if rid in x["keys"]:
                            cache[x["keys"][rid]] = {c: k[c] for c in ("tt", "ly_do", "trang", "evid")} | {"bbox": None}
                    else:
                        tong["claude"] += 1
                        can.append(f"- {rid} [{k['g'] or '—'}→XM] tr.{k['trang'] or '?'} · Gemini: {k['ly_do'][:160]}"
                                   + (f" · «{k['evid'][:120]}»" if k["evid"] else "") + "\n    DÒNG: " + x["dong"][rid][:700])
                if can:
                    cited = sorted({k["trang"] for k in kq.values() if k["tt"] not in ("D", "NA") and k["trang"] in lines})[:3] or \
                        [q for q in x["pages"] if q in lines][:2]
                    chu_t = goi.chu_trang(lines, cited)
                    (gd / f"{x['stem']}.can-claude.md").write_text(
                        f"# Còn nghi sau Gemini · {x['cd']} · {'+'.join(x['ids'])} · trang {x['pages']}\n" + "\n".join(can)
                        + ("\n\n## Bảng số tham chiếu của các dòng trên\n"
                           + goi.bang_text([i for rid_ in kq if kq[rid_]["tt"] not in ("D", "NA") for i in x.get("bang", {}).get(rid_, [])])
                           if any(x.get("bang", {}).get(rid_) for rid_ in kq if kq[rid_]["tt"] not in ("D", "NA")) else "")
                        + "\n\n## Chữ trên bản vẽ các trang Gemini viện dẫn (đã bỏ khung tên)\n"
                        + "\n".join(f"[tr.{q}] {t}" for q, t in chu_t.items()) + "\n", encoding="utf-8")
            print(f"  lô {ten}: gửi {len(dong)} dòng/{len(pages)} trang → xong")
    finally:
        if web is not None:
            web.close()
    if ra_na:
        (gd / "_ra-soat-na.md").write_text("# NA do Gemini kết luận (conf L, chưa vào bộ nhớ đệm) — rà nhanh, sai thì đổi trạng thái\n"
                                           + "\n".join("- " + z for z in ra_na) + "\n", encoding="utf-8")
    rows, log = validate(rows)
    write_jsonl(fj, rows)
    (gd / "cache.json").write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"tổng {tong['g']} dòng qua Gemini: D kiểm chứng {tong['d']} · NA chờ rà {tong['na']} (_ra-soat-na.md) · còn cho Claude {tong['claude']} — {summary(rows)}")


def cmd_goi_nhap(a, settings) -> None:
    """Nhập kết quả gọn Claude ghi (goi/*.ket-qua.txt) -> findings.jsonl (mở rộng cho từng hạng mục trong nhóm) + bộ nhớ đệm."""
    from .pipeline import goi
    from .pipeline.consistency import read_jsonl, summary, validate, write_jsonl
    out = _out_of(a.target)
    gd = out / "goi"
    fj = out / "findings.jsonl"
    rows = read_jsonl(fj) if fj.exists() else []
    cache = goi.doc_cache(gd)
    n = 0
    for f in sorted(gd.glob("*.ket-qua.txt")):
        stem = f.name[: -len(".ket-qua.txt")]
        ids, cd = stem.rsplit("_", 1)[0].split("+"), stem.rsplit("_", 1)[1]
        keys = json.loads((gd / f"{stem}.keys.json").read_text(encoding="utf-8")) if (gd / f"{stem}.keys.json").exists() else {}
        for k in goi.doc_ket_qua(f):
            rows = [r for r in rows if not (r.get("rule") == k["rule"] and r.get("hm") in ids and r.get("cd") == cd)]
            for hm in ids:
                rows.append(dict(id=f"C-{hm}-{k['rule']}", hm=hm, tang=None, cd=cd, rule=k["rule"], yc="", ht="", tt=k["tt"],
                                 ly_do=k["ly_do"], truc=None, trang=k["trang"], bbox=k["bbox"], conf="M", evid=k["evid"], nguon="claude"))
            n += 1
            if k["rule"] in keys:
                cache[keys[k["rule"]]] = {x: k[x] for x in ("tt", "ly_do", "trang", "bbox", "evid")}
    rows, log = validate(rows)
    write_jsonl(fj, rows)
    (gd / "cache.json").write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    for x in log:
        print(f"  {x}")
    print(f"đã nhập {n} dòng kết quả — {fj.name}: {summary(rows)}; bộ nhớ đệm {len(cache)} dòng")


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
    ok = web.login(manual=True)
    web.close()
    if ok:                  # đăng nhập tay thay cookie .env: bỏ cookie cũ để lần chạy sau không ghi đè lên phiên mới
        env = PROJECT_ROOT / ".env"
        if env.exists():
            keep = [ln for ln in env.read_text(encoding="utf-8").splitlines()
                    if not ln.startswith(("GEMINI_COOKIES=", "GEMINI_1PSID=", "GEMINI_1PSIDTS="))]
            env.write_text("\n".join(keep) + "\n", encoding="utf-8")
    print("Đã đăng nhập Gemini web, phiên lưu trong profile Chrome của tool (bỏ cookie cũ trong .env)." if ok
          else "Chưa đăng nhập được (cửa sổ bị đóng hoặc quá 10 phút) — chạy lại lệnh.")


def cmd_gemini_cookie(a, settings):
    """Nạp cookie JSON (Cookie-Editor) VÀO PROFILE Chrome của tool 1 lần -> Chrome tự gia hạn, không phải xuất lại.
    Bỏ cookie khỏi .env (để không ghi đè phiên trong profile), xoá file gốc. Không in giá trị cookie."""
    from .extractors.gemini_extractor import backend_kwargs
    from .extractors.gemini_web import GeminiWeb, clear_env_cookies, parse_cookies
    raw = Path(a.file).read_text(encoding="utf-8")
    n = len(parse_cookies(raw))
    clear_env_cookies(PROJECT_ROOT / ".env")
    web = GeminiWeb(**backend_kwargs(dict(settings["gemini"], backend="web"))["web"])
    try:
        ok = web.seed_profile(raw)
    finally:
        web.close()
    if not a.keep:
        Path(a.file).unlink()
    print(f"Đã nạp {n} cookie vào profile Chrome của tool" + ("" if a.keep else ", đã xoá file gốc"))
    if ok:
        print("Gemini web: ĐÃ đăng nhập — phiên nằm trong profile, Chrome tự gia hạn; không cần xuất cookie lại.")
    else:
        print("Gemini web: cookie đã chết (Google đã thay) — xuất cookie MỚI từ cửa sổ ẩn danh rồi nạp lại.")
    sys.exit(0 if ok else 1)


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
        sp.add_argument("--gemini-pages", help="thêm: Gemini đọc các trang này, vd 4,15 | 1-N cả hồ sơ | smart: lọc "
                                               "trước bằng lớp chữ (>= 80%% trang đọc được), không thì cả hồ sơ")
        sp.add_argument("--upload", choices=["pdf", "png"],
                        help="Gemini web: gửi 1 file PDF | ảnh PNG 2x2 nét mỗi trang (mặc định theo settings)")
        sp.add_argument("--chunk-pages", type=int, help="Gemini web: > số trang này -> chia chunk, mỗi chunk 1 tab")
        sp.add_argument("--tabs", type=int, help="Gemini web: số tab song song khi chia chunk")
        sp.add_argument("--thinking", help="Gemini web: mức suy luận trong menu (Thấp | Trung bình | Cao)")

    sp = sub.add_parser("info"); sp.add_argument("pdf"); sp.add_argument("--out"); common_info(sp)
    sp = sub.add_parser("extract"); common_extract(sp)
    sp = sub.add_parser("check")
    sp.add_argument("extraction"); sp.add_argument("--rules", action="append")
    sp.add_argument("--only", help="chỉ chạy các rule id, phân tách bằng dấu phẩy")
    sp.add_argument("--building"); sp.add_argument("--set", action="append")
    sp.add_argument("--pdf", help="PDF gốc (chia trang theo hạng mục khi chưa có hm_pages.json)")
    sp.add_argument("--mot-hm", action="store_true", help="kiểm cả hồ sơ theo 1 hạng mục (cách cũ)")
    sp = sub.add_parser("hm-pages", help="chia trang theo hạng mục -> hm_pages.json (check chạy riêng từng hạng mục)")
    sp.add_argument("target"); sp.add_argument("--pdf")
    sp = sub.add_parser("trang", help="danh mục bản vẽ: trang -> tên bản vẽ; --cd <chuyên đề> chỉ in trang của chuyên đề đó")
    sp.add_argument("target"); sp.add_argument("--cd", help="vd thoat-nan, bao-chay (skills/chuyen-de = mục bảng đối chiếu)")
    sp.add_argument("--pdf"); sp.add_argument("--html", action="store_true", help="chèn mục vào thong_tin_cong_trinh.html")
    sp.add_argument("--lam-lai", action="store_true", help="đọc lại khung tên (bỏ danh_muc_ban_ve.json cũ)")
    sp = sub.add_parser("va-cham", help="chỗ bản vẽ tự mâu thuẫn -> va_cham.json/.md (+ PDF ghi chú + Word 'Note phản hồi' với --annotate)")
    sp.add_argument("target"); sp.add_argument("--pdf"); sp.add_argument("--annotate", action="store_true")
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
    sp = sub.add_parser("crops", help="cắt bảng dán dạng ảnh ra PNG để Claude kiểm giá trị *")
    sp.add_argument("pdf"); sp.add_argument("--pages", help="vd 7,10 (mặc định cả hồ sơ)"); sp.add_argument("--out")
    sp = sub.add_parser("intake", help="lập chỉ mục trang: luồng LAYER/HON-HOP/SCAN + mã băm (0 token)")
    sp.add_argument("pdf"); sp.add_argument("--out")
    sp = sub.add_parser("facts", help="project_info.json -> project_facts.json + cong1.md (Cổng 1)")
    sp.add_argument("target", help="thư mục kết quả hoặc project_info.json"); sp.add_argument("--pdf")
    sp = sub.add_parser("danh-gia", help="khung danh_gia_cong_nang.json: cổng áp dụng chuyên đề (skill danh-gia-cong-nang điền)")
    sp.add_argument("target")
    sp = sub.add_parser("keys", help="project_facts.json (+ danh_gia_cong_nang.json) -> rule_keys.json")
    sp.add_argument("target")
    sp = sub.add_parser("findings", help="findings.json -> findings.jsonl (D/KD/XM/NA) + chặn KD thiếu bằng chứng")
    sp.add_argument("target", nargs="?", help="thư mục kết quả"); sp.add_argument("--check", help="chỉ kiểm 1 file .jsonl")
    sp.add_argument("--hm", default="HM01", help="mã hạng mục cho dòng engine không ghi hạng mục (mặc định HM01)")
    sp.add_argument("--replace", action="store_true", help="ghi đè cả dòng do skill chuyên đề/reviewer ghi")
    sp = sub.add_parser("goi", help="gói đối chiếu: script lọc dòng bảng tra (tiêu đề/NA/XM) trước, chỉ đưa dòng cần Claude xét")
    sp.add_argument("target"); sp.add_argument("--bang", help="vd gara/chung (thư mục trong rules/checklists); bỏ trống = theo rule_keys.json")
    sp.add_argument("--cd", help="chuyên đề, phân tách dấu phẩy"); sp.add_argument("--den", help="mọi chuyên đề từ mục 01 đến đây, vd thoat-nan")
    sp.add_argument("--hm", help="HM03,HM04 (mặc định mọi hạng mục)"); sp.add_argument("--pdf")
    sp.add_argument("--kem-chu", action="store_true", dest="kem_chu", help="kèm chữ vector các trang vào gói (mặc định không, nặng token)")
    sp = sub.add_parser("goi-nhap", help="nhập goi/*.ket-qua.txt (Claude ghi gọn) -> findings.jsonl + bộ nhớ đệm"); sp.add_argument("target")
    sp = sub.add_parser("goi-gemini", help="Gemini làm lượt đầu các dòng cần xét; script kiểm chứng; Claude chỉ xét phần còn nghi")
    sp.add_argument("target"); sp.add_argument("--pdf"); sp.add_argument("--cd"); sp.add_argument("--thu", action="store_true", help="chỉ in cỡ prompt, không gửi")
    sp.add_argument("--toi-da-trang", type=int, default=8, dest="toi_da_trang")
    sp.add_argument("--lai", action="store_true", help="phân tích lại câu trả lời Gemini đã lưu (goi/*.gemini.txt), không gửi lại")
    sp.add_argument("--dong", type=int, default=20, help="tối đa dòng / lượt gửi Gemini")
    sp.add_argument("--timeout", type=int, default=600, help="giây chờ mỗi lượt")
    sp = sub.add_parser("knowled", help="kho kiến thức: tim <câu> | doc <id> | ds | them <file> --nhom .. | duyet <id>")
    sp.add_argument("act", choices=["tim", "doc", "ds", "them", "duyet"]); sp.add_argument("args", nargs="*")
    sp.add_argument("--top", type=int, default=5); sp.add_argument("--nhom"); sp.add_argument("--toi-da", type=int, default=6000, dest="toi_da")
    sp.add_argument("--id"); sp.add_argument("--tieu-de", dest="tieu_de"); sp.add_argument("--tu-khoa", dest="tu_khoa"); sp.add_argument("--nguon")
    sp.add_argument("--duyet", action="store_true", help="them: coi là đã đối chiếu nguyên văn (verified)")
    sp = sub.add_parser("xuat-bang", help="điền kết quả vào Word mẫu đối chiếu (datamau): Nội dung thiết kế + Kết luận -> bang_doi_chieu/")
    sp.add_argument("target"); sp.add_argument("--hm")
    sp.add_argument("--gemini", action="store_true", help="Gemini viết lại cột Nội dung thiết kế (văn phong mẫu, sửa chính tả)")
    sp.add_argument("--dong", type=int, default=30); sp.add_argument("--timeout", type=int, default=600)
    sp = sub.add_parser("cong-nang", help="đề xuất công năng từng hạng mục (nhóm F, nhà hỗn hợp theo 70 %%) — module danh-gia-cong-nang của knowled")
    sp.add_argument("target"); sp.add_argument("--ap-dung", action="store_true", dest="ap_dung", help="điền hạng mục chắc chắn vào danh_gia_cong_nang.json")
    sp = sub.add_parser("dong", help="in đủ 1 dòng bảng tra theo ID"); sp.add_argument("id", nargs="+")
    sub.add_parser("gemini-login", help="mở Chrome để đăng nhập Gemini web (backend: web)")
    sub.add_parser("gemini-status", help="kiểm tra đã đăng nhập Gemini web chưa (exit 1 nếu chưa)")
    sp = sub.add_parser("gemini-cookie", help="nạp cookie JSON (Cookie-Editor) vào .env một lần, xoá file gốc")
    sp.add_argument("file"); sp.add_argument("--keep", action="store_true", help="không xoá file JSON gốc")

    a = p.parse_args(argv)
    settings = load_settings(Path(a.settings) if a.settings else None)
    try:
        {"info": cmd_info, "extract": cmd_extract, "check": cmd_check, "annotate": cmd_annotate, "dxf": cmd_dxf,
         "run": cmd_run, "rules": cmd_rules, "pages": cmd_pages, "crops": cmd_crops, "gemini-login": cmd_gemini_login,
         "intake": cmd_intake, "hm-pages": cmd_hm_pages, "trang": cmd_trang, "va-cham": cmd_va_cham, "facts": cmd_facts, "keys": cmd_keys, "danh-gia": cmd_danh_gia, "findings": cmd_findings,
         "knowled": cmd_knowled, "cong-nang": cmd_cong_nang, "xuat-bang": cmd_xuat_bang, "goi": cmd_goi, "goi-nhap": cmd_goi_nhap, "goi-gemini": cmd_goi_gemini, "dong": cmd_dong, "gemini-status": cmd_gemini_status, "gemini-cookie": cmd_gemini_cookie}[a.cmd](a, settings)
    except PermissionError as e:                        # chưa đăng nhập Gemini web: dừng ngay, không đọc từng trang
        print(f"⚠ {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
