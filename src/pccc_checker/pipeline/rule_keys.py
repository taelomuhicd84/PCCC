"""Bước 4 — rule_keys.json: "khóa tra" của từng hạng mục -> bộ bảng tra và file cần nạp cho từng chuyên đề.

Skill chuyên đề chỉ nạp đúng file liệt kê ở đây (2–4k token), không nạp cả quy chuẩn. Ánh xạ khớp `rules/_index.md`.
Thiếu khóa quyết định -> chuyên đề đó trả XM kèm tên trường thiếu, không đoán.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..config import PROJECT_ROOT
from .chuyen_de import MUC

CHECKLISTS = "rules/checklists"
LUON_NAP = ["rules/_index.md", "rules/qcvn06/00-dinh-nghia.md"]

# chuyên đề = mục lớn của bảng đối chiếu (pipeline/chuyen_de.py) -> tên file gốc trong thư mục bộ bảng
CHUYEN_DE = {slug: f"{nn}-{slug}" for nn, slug, *_ in MUC}
LOAI_HINH = {"F1.2": "khach-san", "F4.3": "van-phong", "F5.1": "nha-xuong", "F5.2": "kho"}
# loại hình đã có bộ bảng tra .md -> dải chiều cao PCCC (Đ 1.4.9) của từng bộ, theo tên mẫu bảng đối chiếu
# (B7.1/7.2/7.3 khách sạn 28/50/150 m; khi thêm B4.x chung cư: 28/75/150, B5.x hỗn hợp, B6.x văn phòng: 28/50/150)
# thêm loại hình = thư mục rules/checklists/<loại>/ + 1 dòng ở đây + LOAI_HINH + rules/_index.md
BO = {"khach-san": [(28, "k1"), (50, "k2"), (150, "k3")]}
CO_BANG = set(BO)
CAN = ["nhom_nha", "cao_pccc_m", "bac_chiu_lua", "cap_s"]


def bo_bang(loai: str, cao_pccc: float | None) -> str | None:
    """Bộ bảng theo chiều cao PCCC; vượt dải cao nhất -> "ngoai-pham-vi"; thiếu chiều cao -> None."""
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


def keys_for(h: dict, overrides: list[dict]) -> dict:
    ov = {o["truong"]: o for o in overrides if o.get("hm") in (h["id"], h["ten"][0])}
    k, nguon = {}, {}
    for f in CAN + ["hang_no", "so_tang_noi", "so_tang_ham"]:
        if f in ov:
            k[f], nguon[f] = ov[f]["gia_tri"], "override"
        else:
            k[f], nguon[f] = _val(h, f)
    nhom = str(k["nhom_nha"]).split(";")[0].strip() if k["nhom_nha"] else None
    loai = LOAI_HINH.get(nhom or "", "chua-co")
    try:
        cao = float(k["cao_pccc_m"]) if k["cao_pccc_m"] is not None else None
    except ValueError:
        cao = None
    can = CAN + (["hang_no"] if nhom and nhom.startswith("F5") else [])
    thieu = [f for f in can if k.get(f) is None]
    bo, files, ghi_chu = None, {}, []
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
    else:
        ghi_chu.append(f"loại hình '{loai}' chưa có bộ bảng tra .md -> mọi chuyên đề XM; chỉ chạy luật YAML")
    if any(nguon.get(f) == "tinh" for f in can):
        ghi_chu.append("có khóa lấy theo công năng (tinh), chưa có chữ trên bản vẽ -> Cổng 1 phải xác nhận")
    return {"hm": h["id"], "ten": h["ten"][0], "loai_hinh": loai, "bo": bo, "khoa": k, "nguon": nguon,
            "thieu": thieu, "file": files, "ghi_chu": ghi_chu}


def build_rule_keys(facts: dict, ho_so: str, overrides_path: Path | None = None) -> dict:
    ov = load_overrides(ho_so, overrides_path)
    return {"schema": "rule_keys/1", "luon_nap": LUON_NAP, "hang_muc": [keys_for(h, ov) for h in facts["hang_muc"]]}
