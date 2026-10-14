"""Trang nào thuộc hạng mục nào — để rule engine chạy riêng từng hạng mục (mọi hạng mục đều là hạng mục chính).

Căn cứ (0 token):
  1. Tên hạng mục trong chữ của trang (khung tên, tiêu đề): 'NHÀ XƯỞNG 01 VÀ NHÀ VĂN PHÒNG' -> 2 hạng mục;
     'NHÀ XƯỞNG CHO THUÊ 02, 03' / 'NHÀ XƯỞNG 05, 06' -> xưởng 2, 3 (5, 6).
  2. Trang tổng thể -> "chung": loại site, tiêu đề có "TỔNG THỂ"/"TỔNG MẶT BẰNG", hoặc nêu hạng mục của >= 3 loại khác
     nhau (bảng thống kê). Trang ghi 'NHÀ XƯỞNG 02, 03, 04, 08' vẫn thuộc 4 xưởng đó.
  3. Trang không nêu hạng mục nào -> theo trang liền trước (cùng bộ bản vẽ); trang tổng thể (site/cover đầu hồ sơ) -> "chung".
Kết quả ghi `hm_pages.json` — Claude sửa tay được ở Cổng 1, `check` đọc lại file này.
"""
from __future__ import annotations

import re

from ..project_info import _hm_key

CHUNG = "chung"
NHIEU_LOAI = 3                 # >= số loại hạng mục (phần tên bỏ số) trên 1 trang -> trang tổng thể
TONG_THE = re.compile(r"TỔNG\s*THỂ|TỔNG\s*MẶT\s*BẰNG", re.I)
SITE = {"site", "cover"}
NUM_LIST = r"((?:\d{1,2}[A-Z]?\s*(?:,|&|VÀ|\+|-)?\s*)+)"


def _base_num(key: str) -> tuple[str, str | None]:
    m = re.fullmatch(r"(.*?)\s+(\d{1,2}[A-Z]?)", key)
    return (m.group(1), m.group(2)) if m else (key, None)


def _nums(s: str) -> set[str]:
    return {re.sub(r"^0+(?=\d)", "", n) for n in re.findall(r"\d{1,2}[A-Z]?", s)}


def line_owners(line: str, hm_names: list[str]) -> set[str]:
    """Hạng mục được nêu trong 1 dòng chữ. Tên có số khớp khi số nằm trong danh sách số theo sau phần tên
    ('NHÀ XƯỞNG CHO THUÊ 02, 03' khớp 'Nhà xưởng 2' qua phần tên 'NHÀ XƯỞNG' + từ chen 'CHO THUÊ')."""
    t = " " + _hm_key(line) + " "
    out = set()
    for name in hm_names:
        base, num = _base_num(_hm_key(name))
        if not base:
            continue
        if num is None:
            if re.search(rf"(?<!\S){re.escape(base)}(?!\s*\d)(?!\S)", t):
                out.add(name)
            continue
        for m in re.finditer(rf"(?<!\S){re.escape(base)}(?:\s+[^\d\s,&]+){{0,3}}?\s+{NUM_LIST}", t):
            if num in _nums(m.group(1)):
                out.add(name)
                break
    # 'NHÀ XE' và 'NHÀ XE 1' cùng khớp -> giữ tên có số
    return {n for n in out if not any(o != n and _hm_key(o).startswith(_hm_key(n) + " ") for o in out)}


def page_owners(lines_by_page: dict[int, list[str]], hm_names: list[str],
                cats: dict[int, str] | None = None, titles: dict[int, str] | None = None) -> dict[int, list[str]]:
    cats, titles = cats or {}, titles or {}
    out: dict[int, list[str]] = {}
    prev: list[str] | None = None
    for p in sorted(lines_by_page):
        own: set[str] = set()
        for ln in lines_by_page[p]:
            if len(ln) <= 90:                      # dòng ghi chú dài hay liệt kê cả hồ sơ, không dùng
                own |= line_owners(ln, hm_names)
        loai = {_base_num(_hm_key(n))[0] for n in own}
        if cats.get(p) == "site" or TONG_THE.search(titles.get(p, "")) or len(loai) >= NHIEU_LOAI:
            out[p] = [CHUNG]
        elif own:
            out[p] = sorted(own, key=hm_names.index)
        elif cats.get(p) in SITE or prev is None:
            out[p] = [CHUNG]
        else:
            out[p] = list(prev)
        if out[p] != [CHUNG] or cats.get(p) in SITE:
            prev = out[p] if out[p] != [CHUNG] else None
    return out


def from_pdf(pdf, hm_names: list[str], pages: list[int] | None = None, cats: dict[int, str] | None = None,
             titles: dict[int, str] | None = None) -> dict[int, list[str]]:
    from ..pdf.render import page_count, vector_text
    pages = pages or list(range(1, page_count(pdf) + 1))
    lines = {p: [t["text"] for t in vector_text(pdf, p)] for p in pages}
    return page_owners(lines, hm_names, cats, titles)


def by_hm(owners: dict[int, list[str]]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for p, names in sorted(owners.items()):
        for n in names:
            out.setdefault(n, []).append(p)
    return out
