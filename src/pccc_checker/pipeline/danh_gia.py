"""Đánh giá công năng (skill `danh-gia-cong-nang`) -> danh_gia_cong_nang.json: CỔNG ÁP DỤNG của mọi chuyên đề.

Khác bước info (chỉ chép chữ trên bản vẽ): bước này DỰA VÀO bản vẽ để KẾT LUẬN công năng (loại hình / bảng đối chiếu,
nhóm F theo công năng, nhà hỗn hợp?) và chuyên đề + hệ thống PCCC nào thuộc diện phải có (yêu cầu trang bị).
Người dùng 14/10/2026: chuyên đề KHÔNG áp dụng cho tới khi khớp công năng và yêu cầu trang bị -> `rule_keys.file`
chỉ gồm chuyên đề / mẫu hệ thống có `ap_dung: true`; null (chưa đánh giá) hay false -> không chạy.

Lệnh `danh-gia <thư mục>` tạo khung (mọi ô ap_dung = null) từ ứng viên của `rule_keys`; chạy lại thì GIỮ quyết định đã điền.
"""
from __future__ import annotations

import json
from pathlib import Path

TEN_FILE = "danh_gia_cong_nang.json"


def _mau_of(path: str) -> str | None:
    p = path.split("/")
    return p[p.index("he-thong") + 1] if "he-thong" in p else None


def khung(rk: dict, cu: dict | None = None) -> dict:
    """Khung đánh giá từ rule_keys (chạy KHÔNG có đánh giá -> `ung_vien`); giữ giá trị đã điền trong `cu`."""
    old = {h["hm"]: h for h in (cu or {}).get("hang_muc", [])}
    out = []
    for h in rk["hang_muc"]:
        o = old.get(h["hm"], {})
        cds, hts = {}, {}
        for cd, fs in h["ung_vien"].items():
            if any(_mau_of(f) is None for f in fs):  # chuyên đề có file của bảng công trình
                cds[cd] = o.get("chuyen_de", {}).get(cd) or {"ap_dung": None, "ly_do": ""}
            for f in fs:
                m = _mau_of(f)
                if m and m not in hts:
                    hts[m] = o.get("he_thong", {}).get(m) or {"chuyen_de": cd, "ap_dung": None, "ly_do": "",
                                                              "doc_truoc": f}  # phần 1 = đối tượng trang bị
        out.append({
            "hm": h["hm"], "ten": h["ten"],
            "de_xuat": {"loai_hinh": h["loai_hinh"], "mau": h.get("mau"), "can_cu": h["nguon"].get("loai_hinh"),
                        "ghi_chu": h["ghi_chu"]},
            # ↓ skill danh-gia-cong-nang điền (null = chưa đánh giá)
            "loai_hinh": o.get("loai_hinh"), "nhom_nha_tinh": o.get("nhom_nha_tinh"), "hon_hop": o.get("hon_hop"),
            "cong_nang_danh_gia": o.get("cong_nang_danh_gia", ""), "can_cu": o.get("can_cu", []),
            "chuyen_de": cds, "he_thong": hts,
        })
    return {"schema": "danh_gia_cong_nang/1", "hang_muc": out}


def doc(out_dir: Path) -> dict | None:
    f = out_dir / TEN_FILE
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def cho_hm(dg: dict | None, hm: str) -> dict | None:
    return next((h for h in (dg or {}).get("hang_muc", []) if h["hm"] == hm), None)


def loc(ung_vien: dict, dgh: dict | None) -> tuple[dict, list[str], list[str]]:
    """-> (file áp dụng, chuyên đề không áp dụng, chuyên đề chờ đánh giá). Mẫu hệ thống lọc riêng theo `he_thong`."""
    dgh = dgh or {}
    cds, hts = dgh.get("chuyen_de", {}), dgh.get("he_thong", {})
    files, khong, cho = {}, [], []
    for cd, fs in ung_vien.items():
        bang = [f for f in fs if _mau_of(f) is None]
        mau = [f for f in fs if _mau_of(f) and (hts.get(_mau_of(f)) or {}).get("ap_dung") is True]
        if bang:
            tt = (cds.get(cd) or {}).get("ap_dung")
        else:  # chuyên đề chỉ có mẫu hệ thống (vd B47 ở khách sạn): theo các mẫu
            v = [(hts.get(_mau_of(f)) or {}).get("ap_dung") for f in fs]
            tt = True if mau else (False if v and all(x is False for x in v) else None)
        if tt is True:
            keep = bang + mau
            if keep:
                files[cd] = keep
        elif tt is False:
            khong.append(cd)
        else:
            cho.append(cd)
    return files, khong, cho
