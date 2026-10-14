#!/usr/bin/env python3
"""Tach bang doi chieu .md (da qua docx_to_md.py) thanh 1 file / MUC LON cua bang + dat ID ben vung.
Dung trong PCCC: python -I scripts/checklists/split_rules.py <work/md dir> rules/checklists
Dau ra: <out>/khach-san/k{1,2,3}/NN-<slug>[.<phan>].md, src_map.json, _report.txt
Muc lon -> chuyen de theo TEN muc (src/pccc_checker/pipeline/chuyen_de.py, noi duy nhat khai bao chuyen de).
Muc dai hon GIOI_HAN ky tu -> chia nhieu phan theo tieu muc cap 2 (7.1, 7.2...), moi phan nap 1 luot (2-4k token)."""
import sys, re, json, os, collections

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))
from pccc_checker.pipeline.chuyen_de import BY_SLUG, muc_of  # noqa: E402

BANDS = {  # file -> (ma bo, nhan)
    "b71": ("k1", "<= 28 m"),
    "b72": ("k2", "> 28 m den <= 50 m"),
    "b73": ("k3", "> 50 m den <= 150 m"),
}
GIOI_HAN = 12000  # ky tu / file (~3-4k token)


def parse(path):
    rows = []
    for ln in open(path, encoding="utf-8"):
        m = re.match(r"^\| (R\d+) \| (.*) \|$", ln.rstrip("\n"))
        if m:
            cells = (re.split(r"(?<!\\) \| ", m.group(2)) + [""] * 5)[:5]
            rows.append([m.group(1)] + cells)
    return rows


def row_line(rid, r):
    return "| " + " | ".join([rid, r[1], r[2], r[3], r[4], r[5]]) + " |"


def parts_of(rs):
    """Gom cac tieu muc cap 2 lien tiep thanh phan <= GIOI_HAN ky tu; muc ngan -> 1 phan."""
    if sum(len(row_line("X", r)) for r in rs) <= GIOI_HAN:
        return [rs]
    groups, cur = [], []
    for r in rs:
        # dong tieu de muc lon (TT = "7") di cung tieu muc dau, khong thanh phan rieng
        if re.fullmatch(r"\d+\.\d+", r[1].replace(" ", "")) and any(not re.fullmatch(r"\d+", x[1].replace(" ", "")) for x in cur):
            groups.append(cur)
            cur = []
        cur.append(r)
    groups.append(cur)
    out, cur = [], []
    for g in groups:
        if cur and sum(len(row_line("X", r)) for r in cur + g) > GIOI_HAN:
            out.append(cur)
            cur = []
        cur += g
    return out + [cur]


def run(mddir, out):
    root = os.path.join(out, "khach-san")
    src_map, report = {}, []
    for f, (band, label) in BANDS.items():
        rows = parse(os.path.join(mddir, f + ".md"))
        buckets, so_goc, cur = collections.OrderedDict(), {}, None
        for r in rows:
            tt, name = r[1].replace(" ", ""), r[2].split("<br>")[0]
            if tt == "TT":  # dong tieu de cua mau
                continue
            if re.fullmatch(r"\d+", tt):  # muc lon
                cur = muc_of(name)
                if cur is None:
                    report.append(f"[{band}] CANH BAO muc lon khong nhan dang (bo qua): {tt} {name[:60]}")
                    continue
                so_goc[cur] = tt
            if cur is None:
                report.append(f"[{band}] bo qua dong ngoai muc: {r[0]}")
                continue
            buckets.setdefault(cur, []).append(r)
        d = os.path.join(root, band)
        os.makedirs(d, exist_ok=True)
        for old in os.listdir(d):
            os.remove(os.path.join(d, old))
        total = 0
        for slug, rs in sorted(buckets.items(), key=lambda kv: BY_SLUG[kv[0]][0]):
            nn, _, short, ten = BY_SLUG[slug][:4]
            parts, i = parts_of(rs), 0
            for pi, prs in enumerate(parts, 1):
                phan = f".{pi}" if len(parts) > 1 else ""
                lines = [
                    "---",
                    f"chuyen_de: {slug}",
                    f"muc: {so_goc[slug]} - {ten}  (so thu tu muc trong bang goc {f.upper().replace('B7', 'B7.')})",
                    f"phan: {pi}/{len(parts)}  tieu muc: {', '.join(dict.fromkeys(r[1] for r in prs if re.fullmatch(r'[0-9.]+', r[1].replace(' ', '')) and '.' in r[1]))}",
                    "ap_dung: loai_hinh=khach-san ; chieu_cao_pccc " + label,
                    f"nguon: bang doi chieu mau {f.upper().replace('B7', 'B7.')} (khach san {label}); QCVN 06:2022/BXD + Sua doi 1:2023 va cac TCVN ghi o cot Dieu khoan",
                    f"so_dong: {len(prs)}",
                    "---",
                    "| ID | TT | Nội dung đối chiếu | Lưu ý khi đối chiếu | Quy định | Điều khoản |",
                    "|---|---|---|---|---|---|",
                ]
                for r in prs:
                    i += 1
                    rid = f"{band.upper()}-{short}-{i:03d}"
                    src_map[rid] = {"band": band, "src": f, "row": r[0], "cd": slug}
                    lines.append(row_line(rid, r))
                path = os.path.join(d, f"{nn}-{slug}{phan}.md")
                open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
                report.append(f"[{band}] {os.path.basename(path):<34} rows={len(prs):>3}  chars={os.path.getsize(path):>6}")
            total += len(rs)
        report.append(f"[{band}] TONG {total} / {len(rows) - 1} dong nguon (tru dong tieu de)")
    json.dump(src_map, open(os.path.join(root, "src_map.json"), "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(root, "_report.txt"), "w", encoding="utf-8").write("\n".join(report))
    print("\n".join(report))


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
