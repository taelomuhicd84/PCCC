"""Phán đoán công năng TỪNG hạng mục (module `danh-gia-cong-nang` của skill knowled) — phần xác định được bằng số.

Một bản vẽ có nhiều hạng mục, mỗi hạng mục một công năng -> tra bảng đối chiếu theo công năng CỦA HẠNG MỤC ĐÓ. Nhà hỗn hợp (QCVN 06 1.4.41):
"nhà có nhiều công năng sử dụng khác nhau"; CHÚ THÍCH: áp dụng quy định cho nhà hỗn hợp khi diện tích sàn dùng cho MỖI công năng KHÔNG VƯỢT QUÁ 70 %
tổng diện tích sàn (không gồm sàn hệ thống kỹ thuật, PCCC, gian lánh nạn, đỗ xe).

Quy trình: tên khu vực -> (loại, nhóm F) theo `knowledge/cong-nang/_tu-khoa.yaml` (người dùng train) -> cộng diện tích theo nhóm ->
  • có ≥ 2 công năng và công năng lớn nhất ≤ 70 % -> HỖN HỢP
  • công năng lớn nhất > 70 %                      -> nhà đơn năng theo công năng đó
  • thiếu diện tích / khu chưa phân loại / kết luận đổi khi bỏ-hay-cộng khu phụ trợ -> KHÔNG CHẮC (người xem)
Script chỉ ĐỀ XUẤT; không chắc thì để Claude/người dùng quyết, không đoán.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

import yaml

from ..config import PROJECT_ROOT
from .knowled import bo_dau

NGUONG = 0.70
KHOA = PROJECT_ROOT / "knowledge" / "cong-nang" / "_tu-khoa.yaml"
MIN_PHU = 0.90        # tối thiểu phần diện tích khu vực đã phân loại / tổng sàn để dám kết luận


def luat() -> list[dict]:
    rs = yaml.safe_load(KHOA.read_text(encoding="utf-8")) or []
    for r in rs:
        r["_rx"] = re.compile(bo_dau(r["khop"]))
    return rs


def phan_loai(ten: str, rs: list[dict], chi_cong_nang: bool = False) -> dict | None:
    t = bo_dau(ten or "")
    for r in rs:
        if chi_cong_nang and r["loai"] != "cong-nang":
            continue
        if r["_rx"].search(t):
            return r
    return None


def _so(v) -> float | None:
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def khu_cua_hm(khu_vuc: list[dict], ten_hm: str, cung) -> tuple[list[dict], list[str]]:
    """Khu vực thuộc hạng mục (gộp trùng tên; nhiều giá trị -> lấy giá trị gặp nhiều nhất, ghi cảnh báo)."""
    gom: dict[str, list[float]] = defaultdict(list)
    for k in khu_vuc:
        if k.get("thuoc") and cung(k["thuoc"], ten_hm):
            a = _so(k.get("dien_tich"))
            if a is not None:
                gom[k["ten"].strip()].append(a)
    out, canh = [], []
    for ten, vs in gom.items():
        c = Counter(vs)
        v = c.most_common(1)[0][0]
        if len(c) > 1:
            canh.append(f"«{ten}» ghi {sorted(c)} m² giữa các trang — lấy {v}")
        out.append(dict(ten=ten, dien_tich=v))
    return out, canh


def _chia(nhom: dict[str, float]) -> tuple[bool | None, str | None, float]:
    """-> (hỗn hợp?, công năng chính, tỷ lệ lớn nhất). None khi không có công năng nào."""
    tong = sum(nhom.values())
    if tong <= 0:
        return None, None, 0.0
    chinh, a = max(nhom.items(), key=lambda x: x[1])
    ty = a / tong
    return (len([v for v in nhom.values() if v > 0]) >= 2 and ty <= NGUONG), chinh, ty


def danh_gia_hm(ten: str, khu: list[dict], tong_san: float | None, rs: list[dict], canh_khu: list[str] | None = None) -> dict:
    """Đề xuất cho 1 hạng mục. khu = [{ten, dien_tich}] của hạng mục."""
    r = dict(ten=ten, ket_luan="khong-chac", chinh=None, hon_hop=None, ty_le={}, loai_tru={}, chung=0.0, phu_tro=[], chua_phan_loai=[],
             canh_bao=[], ghi_chu=[], can_cu="")
    ban = phan_loai(ten, rs)
    if ban and ban["loai"] == "loai-tru" and ban.get("ly") in ("kỹ thuật", "pccc", "lanh-nan"):
        return dict(r, ket_luan="ky-thuat", can_cu=f"{ban['id']}: hạng mục kỹ thuật/PCCC — dùng bảng riêng (trạm bơm, TBA…), không xét hỗn hợp")
    cn: dict[str, float] = defaultdict(float)
    phu = tc = 0.0
    ham: list[tuple[dict, str]] = []          # khu ở tầng hầm có công năng (hầm "giải trí" né đỗ xe...): phải nêu rõ là gì
    for k in khu:
        x = phan_loai(k["ten"], rs)
        if not x:
            r["chua_phan_loai"].append(k)
        elif x["loai"] == "cong-nang":
            cn[x["nhom"]] += k["dien_tich"]
            if re.search(r"\bham\b", bo_dau(k["ten"])):
                ham.append((k, x["nhom"]))
        elif x["loai"] == "loai-tru":
            r["loai_tru"][x.get("ly", "?")] = r["loai_tru"].get(x.get("ly", "?"), 0) + k["dien_tich"]
        elif x["loai"] == "chung":
            r["chung"] += k["dien_tich"]
        elif x["loai"] == "theo-chinh":                                     # sảnh đón: tính vào công năng chính của hạng mục
            tc += k["dien_tich"]
            r["theo_chinh"] = r.get("theo_chinh", []) + [k["ten"]]
        elif x["loai"] == "phu-tro":
            phu += k["dien_tich"]
            r["phu_tro"].append(k["ten"])
    tong_khu = sum(k["dien_tich"] for k in khu)
    # 1) không có khu vực: theo tên hạng mục (chỉ luật cong-nang; riêng nhà xe/gara = F5.2)
    if not cn:
        ht = phan_loai(ten, rs, chi_cong_nang=True) or (ban if ban and ban.get("ly") == "do-xe" else None)
        nhom = (ht or {}).get("nhom") or ((ht or {}).get("ly") == "do-xe" and "F5.2") or None
        if nhom:
            return dict(r, ket_luan="don-nang", chinh=nhom, hon_hop=False, ty_le={nhom: 1.0},
                        can_cu=f"theo tên hạng mục «{ten}» ({ht['id']}): {nhom}; chưa có diện tích khu vực để xét hỗn hợp"
                        + (" — không có số liệu khu vực: nếu hạng mục có nhiều công năng thì cần bổ sung" if not khu else ""))
        return dict(r, canh_bao=["tên hạng mục và khu vực không khớp luật công năng nào — cần người/Claude phán đoán (thêm dòng vào _tu-khoa.yaml)"])
    if tc:
        c0 = max(cn, key=cn.get)
        cn[c0] += tc
        r["ghi_chu"].append(f"sảnh đón {tc:g} m² ({', '.join(r['theo_chinh'])}) tính vào công năng chính {c0}")
    # 2) có khu vực: thử 2 cách tính khu phụ trợ
    hh_b, chinh_b, ty_b = _chia(dict(cn))                                  # B: bỏ phụ trợ
    cn_a = dict(cn)
    cn_a[chinh_b] = cn_a.get(chinh_b, 0) + phu                             # A: cộng phụ trợ vào công năng chính
    hh_a, chinh_a, ty_a = _chia(cn_a)
    tong_cn = sum(cn.values())
    r["ty_le"] = {k: round(v / tong_cn, 3) for k, v in sorted(cn.items(), key=lambda x: -x[1])}
    r["chinh"], r["hon_hop"] = chinh_b, hh_b
    # 3) kiểm độ chắc
    he_so = sum(k["dien_tich"] for k in khu) / tong_san if tong_san else None
    unc = sum(k["dien_tich"] for k in r["chua_phan_loai"])
    don_chac = len(cn) == 1 and tong_cn / (tong_cn + unc) > NGUONG       # 1 công năng chiếm > 70 % kể cả khi mọi khu chưa phân loại là công năng khác
    for c in canh_khu or []:                                             # diện tích ghi lệch giữa các trang: chỉ chặn khi có ≥ 2 công năng
        (r["ghi_chu"] if len(cn) == 1 else r["canh_bao"]).append(c)
    if unc > (1 - MIN_PHU) * (tong_khu or 1):
        msg = "khu chưa phân loại (thêm vào _tu-khoa.yaml): " + ", ".join(k["ten"] for k in r["chua_phan_loai"][:6])
        (r["ghi_chu"] if don_chac else r["canh_bao"]).append(msg + (" — không đổi kết luận (công năng chính vẫn > 70 %)" if don_chac else ""))
    if tong_san and he_so is not None and he_so < MIN_PHU - 0.3:
        r["canh_bao"].append(f"khu vực đã đọc chỉ {he_so:.0%} tổng sàn {tong_san:g} m² — còn nhiều diện tích chưa biết công năng")
    if hh_a != hh_b or chinh_a != chinh_b:
        r["canh_bao"].append(f"KẾT LUẬN NHẠY: bỏ khu phụ trợ -> {'hỗn hợp' if hh_b else 'đơn năng'} {chinh_b} ({ty_b:.0%}); "
                             f"cộng phụ trợ vào công năng chính -> {'hỗn hợp' if hh_a else 'đơn năng'} {chinh_a} ({ty_a:.0%})")
    if len(cn) > 1 and abs(ty_b - NGUONG) <= 0.03:
        r["canh_bao"].append(f"công năng lớn nhất {ty_b:.0%} sát ngưỡng 70 % (±3 điểm) — kiểm lại diện tích từng khu")
    elif len(cn) > 1 and abs(ty_b - NGUONG) <= 0.10:
        r["ghi_chu"].append(f"công năng lớn nhất {ty_b:.0%}, gần ngưỡng 70 % — nên soát lại diện tích")
    for k, nh in ham:                                                    # hầm có công năng: đề xuất cụ thể + thử kịch bản "hầm = loại trừ (kỹ thuật/đỗ xe)"
        cn2 = dict(cn)
        cn2[nh] = cn2.get(nh, 0) - k["dien_tich"]
        hh2, ch2, ty2 = _chia({a: v for a, v in cn2.items() if v > 0})
        r.setdefault("ham", []).append(dict(ten=k["ten"], dien_tich=k["dien_tich"], de_xuat=f"công năng {nh} (bản vẽ bố trí sử dụng, không để xe)",
                                            neu_loai_tru=("hỗn hợp" if hh2 else f"đơn năng {ch2}") + f" ({ty2:.0%})"))
        if hh2 != hh_b or ch2 != chinh_b:
            r["canh_bao"].append(f"KẾT LUẬN NHẠY (hầm «{k['ten']}»): tính {nh} -> {'hỗn hợp' if hh_b else 'đơn năng'} {chinh_b}; "
                                 f"coi là hầm kỹ thuật/đỗ xe (loại trừ) -> {'hỗn hợp' if hh2 else 'đơn năng'} {ch2}")
    r["ket_luan"] = "hon-hop" if hh_b else "don-nang"
    if r["canh_bao"]:
        r["ket_luan"] = "khong-chac"
    nho = ", ".join(f"{k} {v:.0%}" for k, v in r["ty_le"].items())
    r["can_cu"] = (f"diện tích sàn theo công năng (đã bỏ kỹ thuật/PCCC/lánh nạn/đỗ xe; khu chung & phụ trợ riêng): {nho}; "
                   f"lớn nhất {ty_b:.0%} {'≤' if ty_b <= NGUONG else '>'} 70 % -> "
                   + ("nhà hỗn hợp" if hh_b else f"đơn năng {chinh_b}"))
    return r
