#!/usr/bin/env python3
"""Tach bang doi chieu .md (da qua docx_to_md.py) thanh 1 file / MUC LON cua bang + dat ID ben vung.
Dung trong PCCC: python -I scripts/checklists/split_rules.py <work/md dir> rules/checklists [B7.2 B10 ...]
  <work/md dir> chua b41.md ... b18.md (ten = file_md(mau)); khong ghi mau -> moi mau co file trong thu muc.
Dau ra: <out>/<loai>/<bo>/NN-<slug>[.<phan>].md, <out>/<loai>/src_map.json, <out>/<loai>/_report.txt
Loai hinh / bo / ma ID: src/pccc_checker/pipeline/loai_hinh.py. Muc lon -> chuyen de theo TEN muc: pipeline/chuyen_de.py.
Muc dai hon GIOI_HAN ky tu -> chia nhieu phan theo tieu muc cap 2 (7.1, 7.2...), moi phan nap 1 luot (2-4k token)."""
import sys, re, json, os, collections

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))
from pccc_checker.pipeline.chuyen_de import BY_SLUG, muc_of  # noqa: E402
from pccc_checker.pipeline.loai_hinh import LOAI, MAU, file_md, ma_id  # noqa: E402

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


def _tt(r):
    return r[1].replace(" ", "").rstrip(".")  # B22 ghi "1." cho muc lon


def parts_of(rs):
    """Gom cac tieu muc cap 2 lien tiep thanh phan <= GIOI_HAN ky tu; muc ngan -> 1 phan."""
    if sum(len(row_line("X", r)) for r in rs) <= GIOI_HAN:
        return [rs]
    groups, cur = [], []
    for r in rs:
        # dong tieu de muc lon (TT = "7") di cung tieu muc dau, khong thanh phan rieng
        if re.fullmatch(r"\d+\.\d+", _tt(r)) and any(not re.fullmatch(r"\d+", _tt(x)) for x in cur):
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


def split_one(mau, rows, report):
    """-> {slug: [rows]}, {slug: so muc goc}."""
    buckets, so_goc, cur, cur_no = collections.OrderedDict(), {}, None, None
    for r in rows:
        tt, name = _tt(r), r[2].split("<br>")[0]
        if tt == "TT" or all(re.fullmatch(r"\d+", c.strip() or "x") for c in r[1:6]):
            continue  # dong tieu de cot / dong danh so cot "1 | 2 | 3 | 4 | 5"
        m2 = re.fullmatch(r"(\d+)\.\d+", tt)
        if m2 and cur_no and m2.group(1) != cur_no:
            # bang thieu dong tieu de muc lon (B9: co 7.1, 7.2 nhung khong co dong "7") -> nhan muc theo ten tieu muc
            cd = muc_of(name)
            if cd and cd != cur:
                report.append(f"[{mau}] CANH BAO thieu dong tieu de muc {m2.group(1)}: '{tt} {name[:40]}' -> '{cd}'")
                cur, cur_no = cd, m2.group(1)
                so_goc.setdefault(cd, m2.group(1))
        if re.fullmatch(r"\d+", tt):  # muc lon
            cd = muc_of(name)
            if cd is None:
                # vd "1 Doi tuong trang bi", "2 Quy dinh chung" danh so lai trong 1 muc -> giu o muc dang xet
                report.append(f"[{mau}] muc so {tt} '{name[:50]}' khong phai muc lon -> giu trong '{cur}'")
            elif cd in buckets and cd != cur:
                report.append(f"[{mau}] CANH BAO muc '{name[:50]}' -> '{cd}' da co truoc do, gop vao")
                cur, cur_no = cd, tt
            else:
                cur, cur_no = cd, tt
                so_goc.setdefault(cd, tt)
        if cur is None:
            report.append(f"[{mau}] bo qua dong ngoai muc: {r[0]}")
            continue
        buckets.setdefault(cur, []).append(r)
    return buckets, so_goc


def write_bo(out, mau, buckets, so_goc, report, src_map):
    loai, bo, cao = MAU[mau]
    d = os.path.join(out, loai, bo)
    os.makedirs(d, exist_ok=True)
    for old in os.listdir(d):
        os.remove(os.path.join(d, old))
    ten_loai = LOAI[loai][1]
    nhan = f"chieu_cao_pccc <= {cao} m" if cao else "moi chieu cao"
    pre, total = ma_id(loai, bo), 0
    for slug, rs in sorted(buckets.items(), key=lambda kv: BY_SLUG[kv[0]][0]):
        nn, _, short, ten = BY_SLUG[slug][:4]
        parts, i = parts_of(rs), 0
        for pi, prs in enumerate(parts, 1):
            phan = f".{pi}" if len(parts) > 1 else ""
            tms = dict.fromkeys(r[1] for r in prs if re.fullmatch(r"\d+\.[\d.]+", _tt(r)))
            lines = [
                "---",
                f"chuyen_de: {slug}",
                f"muc: {so_goc.get(slug, '?')} - {ten}  (so thu tu muc trong bang goc {mau})",
                f"phan: {pi}/{len(parts)}  tieu muc: {', '.join(tms)}",
                f"ap_dung: loai_hinh={loai} ({ten_loai}) ; {nhan}",
                f"nguon: bang doi chieu mau {mau} ({ten_loai}); QCVN 06:2022/BXD + Sua doi 1:2023 va cac TCVN ghi o cot Dieu khoan",
                f"so_dong: {len(prs)}",
                "---",
                "| ID | TT | Nội dung đối chiếu | Lưu ý khi đối chiếu | Quy định | Điều khoản |",
                "|---|---|---|---|---|---|",
            ]
            for r in prs:
                i += 1
                rid = f"{pre}-{short}-{i:03d}"
                src_map[rid] = {"mau": mau, "bo": bo, "row": r[0], "cd": slug}
                lines.append(row_line(rid, r))
            path = os.path.join(d, f"{nn}-{slug}{phan}.md")
            open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
            report.append(f"[{mau}] {loai}/{bo}/{os.path.basename(path):<30} rows={len(prs):>3} chars={os.path.getsize(path):>6}")
        total += len(rs)
    return total


def run(mddir, out, maus=None):
    maus = maus or [m for m in MAU if os.path.exists(os.path.join(mddir, file_md(m) + ".md"))]
    by_loai = collections.defaultdict(list)
    for m in maus:
        by_loai[MAU[m][0]].append(m)
    for loai, ms in by_loai.items():
        smp = os.path.join(out, loai, "src_map.json")
        src_map = json.load(open(smp, encoding="utf-8")) if os.path.exists(smp) else {}
        src_map = {k: v for k, v in src_map.items() if v.get("mau") not in ms}  # nap lai mau nay -> thay ID cu
        report = []
        for m in ms:
            rows = parse(os.path.join(mddir, file_md(m) + ".md"))
            buckets, so_goc = split_one(m, rows, report)
            n = write_bo(out, m, buckets, so_goc, report, src_map)
            src_n = sum(1 for r in rows if _tt(r) != "TT" and not all(re.fullmatch(r"\d+", c.strip() or "x") for c in r[1:6]))
            report.append(f"[{m}] TONG {n} / {src_n} dong nguon ; {len(buckets)} muc: {', '.join(buckets)}")
        os.makedirs(os.path.join(out, loai), exist_ok=True)
        json.dump(src_map, open(smp, "w", encoding="utf-8"), ensure_ascii=False)
        open(os.path.join(out, loai, "_report.txt"), "w", encoding="utf-8").write("\n".join(report) + "\n")
        print("\n".join(x for x in report if "TONG" in x or "CANH BAO" in x or "khong phai" in x))


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3:] or None)
