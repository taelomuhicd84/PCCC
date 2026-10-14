"""Danh mục chuyên đề = các MỤC LỚN của bảng đối chiếu thẩm duyệt (B4.x chung cư, B5.x hỗn hợp, B6.x văn phòng,
B7.x khách sạn… cùng một bộ mục; bảng > 50 m có thêm "Gian lánh nạn" nên số thứ tự các mục sau lùi 1).

Nơi DUY NHẤT khai báo chuyên đề: 1 mục bảng = 1 skill `skills/chuyen-de/<slug>/SKILL.md` = 1 file bảng tra
`rules/checklists/<loại hình>/<bộ>/<NN>-<slug>[.<phần>].md`. Nhận mục theo TÊN (không theo số thứ tự trong bảng).
Dùng bởi: scripts/checklists/split_rules.py, pipeline/rule_keys.py, pipeline/sheets.py, pipeline/consistency.py.
"""
from __future__ import annotations

import re
import unicodedata

# (NN cố định, slug, mã ngắn cho ID dòng, tên mục, nhận dạng tên mục (bỏ dấu), từ khoá tên bản vẽ (bỏ dấu))
MUC = [
    ("01", "quy-mo", "QM", "Xác định chiều cao PCCC, số tầng, nhóm nhà, hạng nguy hiểm cháy nổ, cấp nguy hiểm cháy",
     r"XAC DINH CHIEU CAO|NHOM NHA|^THONG TIN",
     r"TONG\s*MAT\s*BANG|MAT\s*BANG\s*(TONG\s*THE|DINH\s*VI|VI\s*TRI)|QUY\s*MO|THONG\s*KE\s*(HANG\s*MUC|DIEN\s*TICH)|"
     r"THUYET\s*MINH|BIA|DANH\s*MUC|GHI\s*CHU\s*PCCC|CO\s*CAU\s*SU\s*DUNG\s*DAT|MASTER\s*PLAN|SITE\s*PLAN|MAT\s*CAT|SECTION"),
    ("02", "bac-chiu-lua", "BCL", "Bậc chịu lửa",
     r"BAC CHIU LUA",
     r"BAC\s*CHIU\s*LUA|GIOI\s*HAN\s*CHIU\s*LUA|KET\s*CAU|MAT\s*CAT|GHI\s*CHU\s*PCCC|SECTION"),
    ("03", "khoang-cach", "KC", "Khoảng cách an toàn PCCC",
     r"KHOANG CACH",
     r"TONG\s*MAT\s*BANG|MAT\s*BANG\s*(TONG\s*THE|DINH\s*VI)|KHOANG\s*CACH|MASTER\s*PLAN|SITE\s*PLAN"),
    ("04", "giao-thong-xe-chua-chay", "GT", "Đường giao thông, bãi đỗ xe chữa cháy, lối vào từ trên cao",
     r"DUONG (GIAO THONG|VA BAI)|XE CHUA CHAY",
     r"GIAO\s*THONG|DUONG\s*(CHO\s*)?XE|BAI\s*DO\s*XE|TONG\s*MAT\s*BANG|MAT\s*BANG\s*TONG\s*THE|"
     r"MAT\s*DUNG|LOI\s*VAO|CUA\s*SO\s*CUU\s*NAN|ELEVATION"),
    ("05", "bo-tri-cong-nang", "CN", "Bố trí công năng",
     r"BO TRI CONG NANG",
     r"MAT\s*BANG\s*(TANG|LAU|TRET|HAM|MAI|LUNG)|MAT\s*BANG\s*BO\s*TRI|FLOOR\s*PLAN|\bPLANS?\b(?!.*MASTER)"),
    ("06", "ngan-chay", "NC", "Giải pháp ngăn cháy, chống cháy lan",
     r"NGAN CHAY",
     r"NGAN\s*CHAY|KHOANG\s*CHAY|MAT\s*CAT|MAT\s*BANG\s*(TANG|LAU|TRET|HAM)|VAT\s*LIEU|HOAN\s*THIEN|HANH\s*LANG|"
     r"GIEN?G\s*KY\s*THUAT|HOP\s*KY\s*THUAT"),
    ("07", "thoat-nan", "TN", "Lối, đường thoát nạn",
     r"^(LOI, DUONG |GIAI PHAP )?THOAT NAN",
     r"THOAT\s*NAN|CAU\s*THANG|THANG\s*(BO|SAT|THEP|THOAT)|BUONG\s*THANG|CUA\s*(DI|THOAT)|THONG\s*KE\s*CUA|"
     r"MAT\s*BANG\s*(TANG|LAU|TRET|HAM)|STAIR|DOOR|EXIT\s*PLAN|ESCAPE"),
    ("08", "gian-lanh-nan", "GLN", "Gian lánh nạn",
     r"LANH NAN",
     r"LANH\s*NAN"),
    ("09", "thang-may-chua-chay", "TMCC", "Thang máy chữa cháy",
     r"THANG MAY CHUA CHAY",
     r"THANG\s*MAY"),
    ("10", "chong-tu-khoi", "KHOI", "Giải pháp chống tụ khói (hút khói, tăng áp)",
     r"TU KHOI|HUT KHOI",
     r"HUT\s*KHOI|THOAT\s*KHOI|TANG\s*AP|THONG\s*GIO|TU\s*KHOI"),
    ("11", "binh-chua-chay", "BCC", "Bình chữa cháy (phương tiện chữa cháy ban đầu)",
     r"BINH CHUA CHAY|CHUA CHAY BAN DAU",
     r"BINH\s*CHUA|BAN\s*DAU"),
    ("12", "bao-chay", "BAO", "Hệ thống báo cháy",
     r"BAO CHAY",
     r"BAO\s*CHAY"),
    ("13", "chua-chay", "CC", "Hệ thống chữa cháy",
     r"^(HE THONG )?CHUA CHAY",
     r"CHUA\s*CHAY|SPRINKLER|SPINKLER|TRU\s*CHUA|HONG\s*CHUA|BOM|BE\s*NUOC|DRENCHER"),
    ("14", "cap-dien", "DIEN", "Giải pháp cấp điện cho hệ thống PCCC",
     r"CAP DIEN|HE THONG DIEN|NGUON DIEN",
     r"CAP\s*DIEN|DIEN\s*(PCCC|DONG\s*LUC)|NGUYEN\s*LY\s*DIEN|MAY\s*PHAT"),
    ("15", "chieu-sang-su-co", "CS", "Đèn chiếu sáng sự cố, chỉ dẫn thoát nạn, loa thông báo",
     r"CHIEU SANG SU CO",
     r"CHIEU\s*SANG|SU\s*CO|EXIT|CHI\s*DAN|LOA"),
    ("16", "pha-do-bao-ho", "PD", "Dụng cụ phá dỡ thông thường, phương tiện bảo hộ chống khói",
     r"PHA DO|MAT NA",
     r"PHA\s*DO|BAO\s*HO|MAT\s*NA"),
    ("17", "chong-set", "SET", "Phương án chống sét",
     r"CHONG SET",
     r"CHONG\s*SET|THU\s*SET"),
    ("18", "lien-lac", "LL", "Hệ thống liên lạc",
     r"LIEN LAC",
     r"LIEN\s*LAC|DIEN\s*THOAI"),
]
SLUGS = [m[1] for m in MUC]
BY_SLUG = {m[1]: m for m in MUC}
# tên mục nào chứa tên mục khác ("đèn chiếu sáng sự cố và chỉ dẫn THOÁT NẠN", "THANG MÁY CHỮA CHÁY") -> xét trước
_THU_TU_NHAN = ["chieu-sang-su-co", "thang-may-chua-chay", "binh-chua-chay", "bao-chay", "gian-lanh-nan",
                "pha-do-bao-ho", "cap-dien"] + SLUGS
_NHAN = [(s, re.compile(BY_SLUG[s][4])) for s in dict.fromkeys(_THU_TU_NHAN)]
_TU_KHOA = [(m[1], re.compile(m[5])) for m in MUC]


def plain(s: str) -> str:
    """Chữ hoa, bỏ dấu, gộp khoảng trắng — so khớp tên mục / tên bản vẽ."""
    s = unicodedata.normalize("NFD", s.upper().replace("Đ", "D"))
    return re.sub(r"\s+", " ", "".join(c for c in s if unicodedata.category(c) != "Mn")).strip()


def muc_of(ten_muc: str) -> str | None:
    """Tên mục lớn trong bảng đối chiếu -> slug chuyên đề; không nhận ra -> None."""
    p = plain(ten_muc)
    return next((s for s, rx in _NHAN if rx.search(p)), None)


def cd_of_sheet(ten_ban_ve_plain: str) -> list[str]:
    """Tên bản vẽ (đã bỏ dấu) -> các chuyên đề cần đọc trang đó."""
    return [s for s, rx in _TU_KHOA if rx.search(ten_ban_ve_plain)]
