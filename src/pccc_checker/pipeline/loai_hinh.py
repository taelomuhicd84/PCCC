"""Danh mục LOẠI HÌNH công trình = bộ bảng đối chiếu thẩm duyệt (mẫu B4.x … B18). Nơi DUY NHẤT khai báo:
mẫu Word -> thư mục `rules/checklists/<loại>/<bộ>/`, dải chiều cao PCCC của từng bộ, mã ID dòng, nhóm F, từ khoá công năng.
Dùng bởi scripts/checklists/split_rules.py (tách bảng) và pipeline/rule_keys.py (chọn bảng cho từng hạng mục).

Chọn bảng cho hạng mục (người dùng 14/10/2026: "lấy thông tin công năng từ khâu lấy thông tin"):
  1. memory/overrides.json `loai_hinh` (người dùng chốt) ;
  2. từ khoá trong TÊN hạng mục ; 3. từ khoá trong CÔNG NĂNG (nhiều loại khác nhau -> xét nhà hỗn hợp, ghi chú) ;
  4. nhóm F — chỉ khi nhóm đó ứng với đúng 1 bảng (F1.1 = nhà trẻ HOẶC bệnh viện, F3.1 = chợ HOẶC TTTM -> không chọn).
Từ khoá so trên chữ HOA CÓ DẤU ("CHỢ" ≠ "CHỖ").
"""
from __future__ import annotations

import re
import unicodedata

# loại: (mã ID, tên, [(mẫu, bộ, cao PCCC tối đa m | None = mọi chiều cao)], nhóm F chỉ ứng loại này, từ khoá công năng)
LOAI = {
    "chung-cu": ("CC", "Nhà chung cư", [("B4.1", "k1", 28), ("B4.2", "k2", 75), ("B4.3", "k3", 150)],
                 ["F1.3"], r"CHUNG CƯ|CĂN HỘ"),
    "hon-hop": ("HH", "Nhà hỗn hợp", [("B5.1", "k1", 28), ("B5.2", "k2", 50), ("B5.3", "k3", 150)],
                [], r"HỖN HỢP|ĐA NĂNG"),
    "van-phong": ("VP", "Nhà văn phòng", [("B6.1", "k1", 28), ("B6.2", "k2", 50), ("B6.3", "k3", 150)],
                  ["F4.3"], r"VĂN PHÒNG|TRỤ SỞ|NHÀ LÀM VIỆC|OFFICE"),
    "khach-san": ("KS", "Khách sạn", [("B7.1", "k1", 28), ("B7.2", "k2", 50), ("B7.3", "k3", 150)],
                  ["F1.2"], r"KHÁCH SẠN|NHÀ NGHỈ|NHÀ KHÁCH|HOTEL|MOTEL|RESORT"),
    "nha-tre": ("NT", "Nhà trẻ, trường mẫu giáo, mầm non", [("B8", "chung", None)],
                [], r"NHÀ TRẺ|MẪU GIÁO|MẦM NON"),
    "truong-hoc": ("TH", "Trường tiểu học, THCS, THPT, phổ thông", [("B9", "chung", None)],
                   ["F4.1"], r"TIỂU HỌC|TRUNG HỌC|THCS|THPT|PHỔ THÔNG|TRƯỜNG HỌC"),
    "benh-vien": ("BV", "Bệnh viện", [("B10", "chung", None)],
                  [], r"BỆNH VIỆN|TRUNG TÂM Y TẾ"),
    "cho": ("CHO", "Chợ", [("B11", "chung", None)],
            [], r"\bCHỢ\b"),
    "tttm": ("TM", "Trung tâm thương mại", [("B12", "chung", None)],
             [], r"TRUNG TÂM THƯƠNG MẠI|\bTTTM\b|SIÊU THỊ"),
    "the-thao": ("TT", "Công trình thể thao (sân vận động, nhà thi đấu…)", [("B13", "chung", None)],
                 [], r"SÂN VẬN ĐỘNG|NHÀ THI ĐẤU|THỂ THAO|KHÁN ĐÀI"),
    "rap-chieu-phim": ("RAP", "Rạp chiếu phim", [("B14", "chung", None)],
                       [], r"RẠP CHIẾU|CHIẾU PHIM|CINEMA"),
    "karaoke": ("KR", "Karaoke, vũ trường", [("B15", "chung", None)],
                [], r"KARAOKE|VŨ TRƯỜNG|HỘP ĐÊM|\bBAR\b|\bPUB\b|DISCO"),
    "gara": ("GR", "Gara ô tô", [("B16", "chung", None)],
             [], r"GARA|GA RA|GARAGE|NHÀ ĐỂ XE|ĐẬU XE|ĐỖ XE Ô TÔ"),
    "nha-xuong": ("SX", "Nhà sản xuất", [("B17", "chung", None)],
                  ["F5.1"], r"NHÀ XƯỞNG|XƯỞNG|SẢN XUẤT"),
    "kho": ("KHO", "Nhà kho", [("B18", "chung", None)],
            ["F5.2"], r"NHÀ KHO|\bKHO\b"),
    # công trình đặc thù (xăng dầu, khí đốt, vật liệu nổ, năng lượng) — từ khoá cụ thể thắng từ khoá chung ("KHO")
    "cua-hang-xang-dau": ("XD", "Cửa hàng xăng dầu", [("B19", "chung", None)],
                          [], r"CỬA HÀNG XĂNG|TRẠM XĂNG|CÂY XĂNG|CỬA HÀNG (KINH DOANH )?NHIÊN LIỆU"),
    "kho-xang-dau": ("KXD", "Kho xăng dầu", [("B20", "chung", None)],
                     [], r"KHO XĂNG|KHO DẦU|KHO NHIÊN LIỆU|BỂ CHỨA XĂNG|TỔNG KHO XĂNG"),
    "cua-hang-khi-dot": ("KD", "Cửa hàng kinh doanh khí đốt", [("B21", "chung", None)],
                         [], r"CỬA HÀNG (KINH DOANH )?(KHÍ|GAS|LPG)|CỬA HÀNG CHAI KHÍ"),
    "duong-ong-khi": ("OK", "Đường ống khí", [("B22", "chung", None)],
                      [], r"ĐƯỜNG ỐNG (DẪN |CẤP )?KHÍ"),
    "tram-chiet-lpg": ("TC", "Kho và trạm san chiết nạp LPG", [("B23", "chung", None)],
                       [], r"(SAN|SANG) CHIẾT|CHIẾT NẠP"),
    "kho-lpg": ("LPG", "Kho chứa LPG", [("B24", "chung", None)],
                [], r"KHO (CHỨA )?LPG|BỒN (CHỨA )?LPG|KHO (CHỨA )?KHÍ HÓA LỎNG"),
    "kho-lng": ("LNG", "Kho chứa LNG", [("B25", "chung", None)],
                [], r"KHO (CHỨA )?LNG|\bLNG\b|KHÍ THIÊN NHIÊN HÓA LỎNG"),
    "kho-vlncn": ("VLN", "Kho chứa vật liệu nổ công nghiệp", [("B26", "chung", None)],
                  [], r"KHO (CHỨA )?(VẬT LIỆU|THUỐC) NỔ|VẬT LIỆU NỔ|THUỐC NỔ"),
    "dien-gio": ("DG", "Nhà máy điện gió", [("B27", "chung", None)],
                 [], r"ĐIỆN GIÓ|TURBINE GIÓ|TUA BIN GIÓ"),
    "dien-mat-troi": ("MT", "Nhà máy điện mặt trời", [("B28", "chung", None)],
                      [], r"ĐIỆN MẶT TRỜI|NĂNG LƯỢNG MẶT TRỜI|QUANG ĐIỆN|SOLAR"),
    "tram-bien-ap": ("TBA", "Trạm biến áp", [("B29", "chung", None)],
                     [], r"TRẠM BIẾN ÁP|\bTBA\b|TRẠM ĐIỆN"),
    "ham-duong-bo": ("HAM", "Hầm đường bộ", [("B30", "chung", None)],
                     [], r"HẦM ĐƯỜNG BỘ|HẦM GIAO THÔNG|HẦM XUYÊN"),
    # phương tiện giao thông thủy (không phải nhà): chọn theo tên phương tiện
    "tau-bien": ("TAU", "Phương tiện tàu biển", [("B31", "chung", None)],
                 [], r"TÀU BIỂN"),
    "ptt-hang-nguy-hiem": ("PTH", "Phương tiện thủy nội địa vận chuyển hàng nguy hiểm cháy, nổ", [("B32", "chung", None)],
                           [], r"(TÀU|PHƯƠNG TIỆN|SÀ LAN).{0,30}(HÀNG (HÓA )?NGUY HIỂM|XĂNG|DẦU|KHÍ HÓA LỎNG)"),
    "ptt-cho-khach": ("PTK", "Phương tiện thủy nội địa chở khách", [("B33", "chung", None)],
                      [], r"(TÀU|PHƯƠNG TIỆN|CA NÔ|DU THUYỀN).{0,30}(CHỞ KHÁCH|HÀNH KHÁCH|DU LỊCH)"),
}
# MẪU HỆ THỐNG: không phải loại công trình mà bảng chi tiết của 1 chuyên đề, được bảng công trình dẫn tới
# ("Thực hiện theo bảng đối chiếu B34…"). Lưu ở rules/checklists/he-thong/<mẫu>/, nạp KÈM file chuyên đề đó.
HE_THONG = {  # mẫu: (chuyên đề gắn vào, mã ID, tên, chuyên đề được tách riêng theo tên mục của mẫu, luôn nạp)
    "B34": ("chong-tu-khoi", "HT34", "Hệ thống chống tụ khói", (), False),
    "B35": ("bao-chay", "HT35", "Hệ thống báo cháy", (), False),
    "B36": ("tram-bom", "HT36", "Trạm bơm cấp nước chữa cháy", (), False),
    "B37": ("chua-chay", "HT37", "Cấp nước chữa cháy ngoài nhà", (), False),
    "B38": ("chua-chay", "HT38", "Hệ thống họng nước chữa cháy trong nhà", (), False),
    "B39": ("chua-chay", "HT39", "Hệ thống chữa cháy tự động bằng nước, bọt (sprinkler, drencher)", (), False),
    "B40": ("chua-chay", "HT40", "Hệ thống chữa cháy bằng bọt cố định", (), False),
    "B41": ("chua-chay", "HT41", "Hệ thống chữa cháy bằng khí hóa lỏng", (), False),
    "B42": ("chua-chay", "HT42", "Hệ thống chữa cháy bằng khí nén", (), False),
    "B43": ("chua-chay", "HT43", "Hệ thống chữa cháy tự động bằng khí CO2", (), False),
    "B44": ("chua-chay", "HT44", "Hệ thống chữa cháy bằng Sol-khí", (), False),
    # B45 gồm 3 chuyên đề: bình (xách tay, bột / khí tự động) · cơ giới · phá dỡ, mặt nạ
    "B45": ("binh-chua-chay", "HT45", "Trang bị phương tiện chữa cháy ban đầu", ("co-gioi", "pha-do-bao-ho"), False),
    "B46": ("chieu-sang-su-co", "HT46", "Chiếu sáng sự cố, chỉ dẫn thoát nạn, loa thông báo", (), False),
    # không bảng công trình nào dẫn tới B47 -> luôn nạp, skill xét mục 1 (có hệ thống cấp khí trung tâm không) rồi NA
    "B47": ("an-toan-cong-nghe", "HT47", "Hệ thống cấp khí đốt trung tâm", (), True),
    "B48": ("cap-dien", "HT48", "Nguồn điện cho hệ thống PCCC", (), False),
    "B49": ("chong-set", "HT49", "Hệ thống chống sét", (), False),
    "B50": ("thang-may-chua-chay", "HT50", "Thang máy chữa cháy", (), False),
}
# hạng mục không dùng bảng công trình mà skill hệ thống riêng (người dùng 14/10/2026)
RIENG = {"tram-bom": r"PHÒNG BƠM|TRẠM BƠM|NHÀ BƠM"}

MAU = {mau: (loai, bo, cao) for loai, (_, _, bos, _, _) in LOAI.items() for mau, bo, cao in bos}
_KW = {k: re.compile(v[4]) for k, v in LOAI.items()}
_RIENG = {k: re.compile(v) for k, v in RIENG.items()}


def ma_id(loai: str, bo: str) -> str:
    """Tiền tố ID dòng, duy nhất giữa các loại: KS2-TN-012 (khách sạn bộ k2), BV-TN-003 (bệnh viện 1 bộ)."""
    return LOAI[loai][0] + (bo[1:] if bo.startswith("k") else "")


def file_md(mau: str) -> str:
    """Tên file .md do docx_to_md.py tạo: B7.2 -> b7_2, B41 -> b41 (gạch dưới: B4.1 ≠ B41 — lỗi trùng 14/10/2026)."""
    return "b" + mau[1:].replace(".", "_")


def _up(t: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", (t or "").upper()))


def theo_tu_khoa(text: str) -> list[str]:
    """Loại có từ khoá trong text; chữ khớp nằm trọn trong chữ khớp của loại khác ("KHO" ⊂ "KHO XĂNG") -> bỏ loại chung."""
    u = _up(text)
    hit = {k: [m.span() for m in rx.finditer(u)] for k, rx in _KW.items()}
    hit = {k: v for k, v in hit.items() if v}

    def trong(a, b):
        return all(any(s2 <= s1 and e1 <= e2 and (s1, e1) != (s2, e2) for s2, e2 in hit[b]) for s1, e1 in hit[a])
    return [k for k in hit if not any(trong(k, o) and not trong(o, k) for o in hit if o != k)]


def chon(ten: str, cong_nang: str, nhom: str | None, override: str | None = None) -> tuple[str | None, str, list[str]]:
    """-> (loại | None, căn cứ, ghi chú). Không chắc -> None + ghi chú các bảng ứng viên (không đoán)."""
    if override:
        return override, "override", []
    for k, rx in _RIENG.items():
        if rx.search(_up(ten)):
            return k, "ten", [f"hạng mục dùng skill riêng `{k}`, không dùng bảng công trình"]
    ghi = []
    by_ten = theo_tu_khoa(ten)
    by_cn = [k for k in theo_tu_khoa(cong_nang) if k not in by_ten]
    if len(by_ten) == 1:
        if by_cn:
            ghi.append("công năng còn có: " + ", ".join(LOAI[k][1] for k in by_cn)
                       + " -> cân nhắc bảng nhà hỗn hợp (B5.x); chốt bằng overrides `loai_hinh`")
        return by_ten[0], "ten", ghi
    cands = by_ten or by_cn
    if len(cands) == 1:
        return cands[0], "cong_nang", ghi
    nhoms = sorted({g.strip() for g in re.split(r"[;,/]", nhom or "") if g.strip()})
    if len(cands) > 1 or len({g[:4] for g in nhoms}) > 1:
        ung = cands or nhoms
        return None, "", [f"nhiều công năng ({', '.join(ung)}) -> có thể là nhà hỗn hợp (B5.x) hoặc 1 bảng chính; "
                          "người dùng chốt bằng overrides `loai_hinh`"]
    by_f = [k for k, v in LOAI.items() if nhoms and nhoms[0] in v[3]]
    if len(by_f) == 1:
        return by_f[0], "nhom_nha", ["chọn bảng theo nhóm F (tên/công năng không có từ khoá) -> Cổng 1 xác nhận"]
    return None, "", [f"không xác định được bảng đối chiếu từ tên/công năng/nhóm {nhom or '—'}"]
