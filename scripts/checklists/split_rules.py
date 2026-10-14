#!/usr/bin/env python3
"""Tach bang doi chieu .md (da qua docx_to_md.py) thanh cac file nho theo chuyen de + dat ID ben vung.
Dung: python3 -I split_rules.py <work/md dir> <rules out dir>
Dung trong PCCC: python -I scripts/checklists/split_rules.py <work/md dir> rules/checklists
Dau ra: <out>/khach-san/k{1,2,3}/NN-<chuyen-de>.md, src_map.json, _report.txt"""
import sys, re, json, os, collections

BANDS = {  # file -> (ma bang, nhan, can duoi, can tren)
    "b71": ("k1", "<= 28 m", 0, 28),
    "b72": ("k2", "> 28 m den <= 50 m", 28, 50),
    "b73": ("k3", "> 50 m den <= 150 m", 50, 150),
}
# ma chuyen de -> (so thu tu file, ten file, ma ngan cho ID)
CD = {
    "TT":   ("01", "thong-tin-quy-mo", "TT"),
    "BCL":  ("02", "bac-chiu-lua", "BCL"),
    "KC":   ("03", "khoang-cach", "KC"),
    "DX":   ("04", "duong-bai-do-xe", "DX"),
    "LV":   ("05", "loi-vao-tren-cao", "LV"),
    "CN":   ("06", "bo-tri-cong-nang", "CN"),
    "NC":   ("07", "ngan-chay-ngang-doc", "NC"),
    "NCN":  ("08", "ngan-chay-cong-nang", "NCN"),
    "HL":   ("09", "ngan-chay-hanh-lang-ong-vat-lieu", "HL"),
    "TC":   ("10", "ngan-chay-tuong-cua-vach-gara", "TC"),
    "TNL":  ("11", "thoat-nan-loi-thoat", "TNL"),
    "TND":  ("12", "thoat-nan-duong-thoat", "TND"),
    "TNT":  ("13", "thoat-nan-cau-thang", "TNT"),
    "GLN":  ("14", "gian-lanh-nan", "GLN"),
    "TMCC": ("15", "thang-may-chua-chay", "TMCC"),
    "KHOI": ("16", "hut-khoi-tang-ap", "KHOI"),
    "BCC":  ("17", "binh-chua-chay", "BCC"),
    "BAO":  ("18", "bao-chay", "BAO"),
    "CC":   ("19", "chua-chay", "CC"),
    "HT":   ("20", "dien-chieu-sang-su-co-khac", "HT"),
}
TOP = [  # (tu khoa trong ten muc cap 1, ma)
    ("xác định chiều cao", "TT"), ("bậc chịu lửa", "BCL"), ("khoảng cách an toàn", "KC"),
    ("đường giao thông", "DX"), ("bố trí công năng", "CN"),
    ("ngăn cháy, chống cháy lan", "NC"), ("lối, đường thoát nạn", "TNL"),
    ("gian lánh nạn", "GLN"), ("thang máy chữa cháy", "TMCC"), ("chống tụ khói", "KHOI"),
    ("bình chữa cháy", "BCC"), ("báo cháy", "BAO"), ("hệ thống chữa cháy", "CC"),
    ("cấp điện", "HT"), ("đèn chiếu sáng", "HT"), ("dụng cụ phá dỡ", "HT"),
    ("chống sét", "HT"), ("liên lạc", "HT"),
]
L2_NC = [  # muc 6.x theo ten
    ("ngăn cháy theo chiều ngang", "NC"), ("ngăn cháy theo chiều đứng", "NC"),
    ("ngăn cháy theo công năng", "NCN"), ("giữa các phòng căn hộ", "NC"),
    ("hành lang giữa", "HL"), ("đường ống kỹ thuật", "HL"), ("trần treo", "HL"),
    ("vật liệu hoàn thiện", "HL"), ("cơ cấu tự đóng", "HL"), ("kênh giếng", "HL"),
    ("tường ngăn cháy", "TC"), ("ngăn cháy thang máy", "TC"), ("khoang đệm", "TC"),
    ("buồng rác", "TC"), ("cửa ngăn cháy", "TC"), ("vách ngăn cháy", "TC"), ("đối với gara", "TC"),
]
L2_TN = [("lối thoát nạn", "TNL"), ("đường thoát nạn", "TND"), ("cầu thang", "TNT")]

def parse(path):
    rows, header = [], None
    for ln in open(path, encoding="utf-8"):
        ln = ln.rstrip("\n")
        m = re.match(r"^\| (R\d+) \| (.*) \|$", ln)
        if not m:
            continue
        cells = re.split(r"(?<!\\) \| ", m.group(2))
        cells = (cells + [""] * 5)[:5]
        rows.append([m.group(1)] + cells)
    return rows

def pick(name, table):
    n = name.lower()
    for k, v in table:
        if k in n:
            return v
    return None

def run(mddir, out):
    root = os.path.join(out, "khach-san")
    src_map, report = {}, []
    for f, (band, label, lo, hi) in BANDS.items():
        rows = parse(os.path.join(mddir, f + ".md"))
        buckets = collections.OrderedDict()
        cur_top = cur = None
        for r in rows:
            rid, tt, name = r[0], r[1].replace(" ", ""), r[2].split("<br>")[0]
            if tt == "TT":            # dong tieu de cua mau
                continue
            if re.fullmatch(r"\d+", tt):                     # muc cap 1
                cur_top = pick(name, TOP)
                if cur_top is None:
                    report.append(f"[{band}] CANH BAO muc cap 1 khong nhan dang: {tt} {name[:50]}")
                    cur_top = cur_top or "HT"
                cur = cur_top
            elif re.fullmatch(r"\d+\.\d+", tt) or re.fullmatch(r"\d+\.\d+\.\d+", tt):
                if cur_top == "NC" and re.fullmatch(r"\d+\.\d+", tt):
                    c = pick(name, L2_NC)
                    if c: cur = c
                    else: report.append(f"[{band}] CANH BAO muc 6.x khong nhan dang (giu nhom {cur}): {tt} {name[:40]}")
                elif cur_top == "TNL" and re.fullmatch(r"\d+\.\d+", tt):
                    c = pick(name, L2_TN)
                    if c: cur = c
                    else: report.append(f"[{band}] CANH BAO muc 7.x khong nhan dang (giu nhom {cur}): {tt} {name[:40]}")
                elif cur_top == "DX" and tt.count(".") == 2:
                    cur = "LV" if "lối vào" in name.lower() else "DX"
                elif cur_top == "DX" and tt.count(".") == 1:
                    cur = "DX"
            if cur is None:
                report.append(f"[{band}] bo qua dong truoc muc 1: {rid}")
                continue
            buckets.setdefault(cur, []).append(r)
        d = os.path.join(root, band)
        os.makedirs(d, exist_ok=True)
        for old in os.listdir(d):
            os.remove(os.path.join(d, old))
        total = 0
        for code, rs in sorted(buckets.items(), key=lambda kv: CD[kv[0]][0]):
            num, fname, short = CD[code]
            lines = [
                "---",
                f"chuyen_de: {fname}",
                "ap_dung: loai_hinh=khach-san ; chieu_cao_pccc " + label,
                f"nguon: bang doi chieu mau {f.upper().replace('B7', 'B7.')} (khach san {label}); QCVN 06:2022/BXD + Sua doi 1:2023 va cac TCVN ghi o cot Dieu khoan",
                f"so_dong: {len(rs)}",
                "---",
                "| ID | TT | Nội dung đối chiếu | Lưu ý khi đối chiếu | Quy định | Điều khoản |",
                "|---|---|---|---|---|---|",
            ]
            for i, r in enumerate(rs, 1):
                rid = f"{band.upper()}-{short}-{i:03d}"
                src_map[rid] = {"band": band, "src": f, "row": r[0]}
                lines.append("| " + " | ".join([rid, r[1], r[2], r[3], r[4], r[5]]) + " |")
            path = os.path.join(d, f"{num}-{fname}.md")
            open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
            total += len(rs)
            report.append(f"[{band}] {num}-{fname}.md  rows={len(rs):>3}  chars={os.path.getsize(path):>6}")
        report.append(f"[{band}] TONG {total} / {len(rows)-1} dong nguon (tru dong tieu de)")
    json.dump(src_map, open(os.path.join(root, "src_map.json"), "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(root, "_report.txt"), "w", encoding="utf-8").write("\n".join(report))
    print("\n".join(report))

if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
