"""Bước 4 — rule_keys.json: "khóa tra" của từng hạng mục -> bộ bảng tra và file cần nạp cho từng chuyên đề.

Skill chuyên đề chỉ nạp đúng file liệt kê ở đây (2–4k token), không nạp cả quy chuẩn. Ánh xạ khớp `rules/_index.md`.
Thiếu khóa quyết định -> chuyên đề đó trả XM kèm tên trường thiếu, không đoán.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..config import PROJECT_ROOT
from .chuyen_de import MUC
from .danh_gia import cho_hm, loc
from .loai_hinh import HE_THONG, LOAI, chon

CHECKLISTS = "rules/checklists"
LUON_NAP = ["rules/_index.md", "rules/qcvn06/00-dinh-nghia.md"]

# chuyên đề = mục lớn của bảng đối chiếu (pipeline/chuyen_de.py) -> tên file gốc trong thư mục bộ bảng
CHUYEN_DE = {slug: f"{nn}-{slug}" for nn, slug, *_ in MUC}
# loại hình -> bộ bảng: khai báo ở pipeline/loai_hinh.py (mẫu B4.x…B18, dải chiều cao, từ khoá công năng)
BO = {loai: [(cao, bo) for _, bo, cao in v[2]] for loai, v in LOAI.items()}
CO_BANG = set(BO)
CAN = ["nhom_nha", "cao_pccc_m", "bac_chiu_lua", "cap_s"]


def bo_bang(loai: str, cao_pccc: float | None) -> str | None:
    """Bộ bảng theo chiều cao PCCC (Đ 1.4.9); loại 1 bộ -> bộ đó; vượt dải cao nhất -> "ngoai-pham-vi"; thiếu cao -> None."""
    if BO[loai][0][0] is None:
        return BO[loai][0][1]
    if cao_pccc is None:
        return None
    return next((bo for tran, bo in BO[loai] if cao_pccc <= tran), "ngoai-pham-vi")


def bo_khach_san(cao_pccc: float | None) -> str | None:
    return bo_bang("khach-san", cao_pccc)


def load_overrides(ho_so: str, path: Path | None = None) -> list[dict]:
    """memory/overrides.json: {"<hồ sơ>": [{"hm", "truong", "gia_tri", "ly_do", "ngay", "boi"}]} — quyết định đã chốt."""
    f = path or PROJECT_ROOT / "memory" / "overrides.json"
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8")).get(ho_so, [])


def _val(h: dict, k: str):
    c = h.get(k)
    if isinstance(c, dict):
        b = c.get("ban_ve") or [None]
        return (b[0], "ban_ve") if b[0] is not None else (c.get("tinh"), "tinh" if c.get("tinh") else None)
    return (c[0], "ban_ve") if c and c[0] is not None else (None, None)


def keys_for(h: dict, overrides: list[dict], dgh: dict | None = None) -> dict:
    """`dgh` = mục của hạng mục trong danh_gia_cong_nang.json (None = chưa đánh giá -> không chuyên đề nào áp dụng)."""
    ov = {o["truong"]: o for o in overrides if o.get("hm") in (h["id"], h["ten"][0])}
    if dgh and dgh.get("loai_hinh") and "loai_hinh" not in ov:   # loại hình do bước đánh giá công năng kết luận
        ov["loai_hinh"] = {"gia_tri": dgh["loai_hinh"]}
    k, nguon = {}, {}
    for f in CAN + ["hang_no", "so_tang_noi", "so_tang_ham"]:
        if f in ov:
            k[f], nguon[f] = ov[f]["gia_tri"], "override"
        else:
            k[f], nguon[f] = _val(h, f)
    nhom = str(k["nhom_nha"]).split(";")[0].strip() if k["nhom_nha"] else None
    # bảng đối chiếu theo CÔNG NĂNG đọc ở bước info (tên hạng mục, công năng), nhóm F chỉ là dự phòng
    cn = h.get("cong_nang") or [None]
    loai, can_cu, ghi_chu = chon(h["ten"][0] or "", (cn[0] if isinstance(cn, list) else cn) or "",
                                 str(k["nhom_nha"]) if k["nhom_nha"] else None,
                                 ov.get("loai_hinh", {}).get("gia_tri"))
    loai = loai or "chua-xac-dinh"
    nguon["loai_hinh"] = can_cu or None
    try:
        cao = float(k["cao_pccc_m"]) if k["cao_pccc_m"] is not None else None
    except ValueError:
        cao = None
    can = CAN + (["hang_no"] if nhom and nhom.startswith("F5") else [])
    thieu = [f for f in can if k.get(f) is None]
    bo, files = None, {}
    if loai in CO_BANG:
        bo = bo_bang(loai, cao)
        if bo is None:
            ghi_chu.append("thiếu chiều cao PCCC -> chưa chọn được bộ k1/k2/k3")
        elif bo == "ngoai-pham-vi":
            ghi_chu.append("chiều cao PCCC > 150 m: ngoài phạm vi bộ bảng — dừng, báo người dùng")
        else:
            d = PROJECT_ROOT / CHECKLISTS / loai / bo
            # mục dài đã tách phần NN-slug.1.md, .2.md… (nạp từng phần một lượt); mục bộ không có (vd gian lánh nạn ở k1/k2) -> bỏ
            files = {cd: [f"{CHECKLISTS}/{loai}/{bo}/{p.name}"
                          for p in sorted(d.glob(f"{n}*.md")) if p.stem == n or p.stem.startswith(n + ".")]
                     for cd, n in CHUYEN_DE.items()}
            files = {cd: fs for cd, fs in files.items() if fs}
    elif loai == "tram-bom":
        files = {"tram-bom": []}
    elif loai == "chua-xac-dinh":
        ghi_chu.append("chưa chọn được bảng đối chiếu -> mọi chuyên đề XM; chỉ chạy luật YAML")
    # mẫu hệ thống (B34 chống tụ khói, B35 báo cháy, B36 trạm bơm, B37/B38 chữa cháy) nạp KÈM file chuyên đề của bảng công trình
    # file mẫu `NN-<chuyên đề>[.phần].md` -> chuyên đề theo tên file (B45 tách bình / cơ giới / phá dỡ);
    # mẫu `luon` (B47 cấp khí trung tâm, không bảng công trình nào dẫn tới) nạp cả khi bảng không có mục đó
    co_bang = bool(files)
    for mau, (_, _, _, _, luon) in HE_THONG.items():
        d = PROJECT_ROOT / CHECKLISTS / "he-thong" / mau
        for p in sorted(d.glob("*.md")) if d.is_dir() else []:
            cd = p.stem.split(".")[0][3:]
            if cd in files or (luon and co_bang and loai != "tram-bom"):
                files.setdefault(cd, []).append(f"{CHECKLISTS}/he-thong/{mau}/{p.name}")
    files = {cd: fs for cd, fs in files.items() if fs}
    if any(nguon.get(f) == "tinh" for f in can):
        ghi_chu.append("có khóa lấy theo công năng (tinh), chưa có chữ trên bản vẽ -> Cổng 1 phải xác nhận")
    mau = next((m for m, b, _ in LOAI[loai][2] if b == bo), None) if loai in LOAI else None
    # CỔNG ÁP DỤNG: chỉ chuyên đề / mẫu hệ thống mà đánh giá công năng ghi ap_dung = true mới vào `file`
    ap, khong, cho = loc(files, dgh)
    if cho:
        ghi_chu.append(f"{len(cho)} chuyên đề chờ đánh giá công năng (skill danh-gia-cong-nang) -> chưa áp dụng")
    return {"hm": h["id"], "ten": h["ten"][0], "loai_hinh": loai, "bo": bo, "mau": mau, "khoa": k, "nguon": nguon,
            "thieu": thieu, "file": ap, "ung_vien": files, "khong_ap_dung": khong, "cho_danh_gia": cho,
            "ghi_chu": ghi_chu}


def build_rule_keys(facts: dict, ho_so: str, overrides_path: Path | None = None, danh_gia: dict | None = None) -> dict:
    ov = load_overrides(ho_so, overrides_path)
    return {"schema": "rule_keys/2", "luon_nap": LUON_NAP,
            "hang_muc": [keys_for(h, ov, cho_hm(danh_gia, h["id"])) for h in facts["hang_muc"]]}
