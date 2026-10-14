"""Danh mục bản vẽ (pipeline/sheets.py): tên bản vẽ + ký hiệu từ khung tên, chuyên đề, tra trang."""
import json

import pymupdf
import pytest

from pccc_checker.cli import main
from pccc_checker.pipeline import sheets


def L(text, x0, y0, x1, y1):
    return {"text": text, "bbox": [x0, y0, x1, y1]}


def test_khung_ten_chu_ngang():
    """Kiểu New Motion: nhãn cột trái, giá trị bên dưới; bỏ địa chỉ, lấy cả dòng tiếng Anh, không lấy RE.00."""
    lines = [L("HẠNG MỤC", 2132, 1483, 2168, 1490), L("NHÀ XƯỞNG C-X12", 2146, 1493, 2333, 1503),
             L("TÊN BẢN VẼ", 2132, 1529, 2171, 1536), L("SHEET TITLE", 2132, 1538, 2175, 1546),
             L("BẢNG VẬT LIỆU HOÀN THIỆN", 2180, 1557, 2319, 1567), L("FINISHING MATERIAL SCHEDULE", 2170, 1577, 2329, 1587),
             L("Phú Tân, phường Hòa Phú, thành phố Thủ Dầu Một", 2163, 1422, 2349, 1428),
             L("BẢN VẼ SỐ", 2132, 1636, 2167, 1644), L("RE.00", 2330, 1619, 2347, 1626), L("A-CX12-01-01", 2258, 1640, 2316, 1650)]
    d = sheets.sheet_info(lines)
    assert d["ten_ban_ve"] == "BẢNG VẬT LIỆU HOÀN THIỆN FINISHING MATERIAL SCHEDULE"
    assert d["ky_hieu"] == "A-CX12-01-01" and d["hang_muc"] == "NHÀ XƯỞNG C-X12" and d["nguon_ten"] == "gan_nhan"


def test_khung_ten_trang_xoay():
    """Kiểu Việt Trang / Phú Trường (trang xoay, chữ dọc): tên nằm giữa nhãn HẠNG MỤC và TÊN BẢN VẼ, địa chỉ phía sau."""
    lines = [L("KT 11", 21, 1529, 29, 1552), L("KÍ HIỆU.BV", 36, 1521, 45, 1561), L("KIẾN TRÚC", 67, 1562, 75, 1608),
             L("HẠNG MỤC", 81, 1502, 92, 1556), L("NHÀ XƯỞNG", 130, 1559, 138, 1612),
             L("MẶT ĐỨNG TRỤC 1 - 14 VÀ 14 - 1", 142, 1519, 150, 1653), L("TÊN BẢN VẼ", 186, 1503, 198, 1559),
             L("P. DĨ AN, TP.DĨ AN, TỈNH BÌNH DƯƠNG.", 213, 1533, 220, 1637)]
    d = sheets.sheet_info(lines)
    assert d["ten_ban_ve"].startswith("MẶT ĐỨNG TRỤC 1 - 14") and d["ky_hieu"] == "KT 11"


def test_khong_co_khung_ten_de_trong():
    """Người dùng 14/10/2026: tên bản vẽ chỉ lấy trong ô TÊN BẢN VẼ của khung tên; không tra được -> để trống."""
    d = sheets.sheet_info([L("Kết cấu mái không có tầng áp mái", 0, 0, 100, 10), L("MẶT BẰNG TẦNG 2", 0, 20, 100, 30)])
    assert (d["ten_ban_ve"], d["nguon_ten"]) == ("", "")


def _khung_ten(page, rot=0):
    """Khung tên kẻ ô: [DRAWING TITLE / GHI CHU TONG] trên [DRAWING NO / KT-01]; tên không có từ khoá MẶT BẰNG…"""
    for r in ((600, 480, 820, 530), (600, 530, 820, 580)):
        page.draw_rect(pymupdf.Rect(r), color=(0, 0, 0), width=0.5)
    page.insert_text((604, 490), "DRAWING TITLE", fontname="tiro", fontsize=6)
    page.insert_text((650, 512), "GHI CHU TONG", fontname="tiro", fontsize=10)
    page.insert_text((604, 540), "DRAWING NO", fontname="tiro", fontsize=6)
    page.insert_text((680, 565), "KT-01", fontname="tiro", fontsize=9)
    page.insert_text((300, 300), "MAT BANG TANG 1", fontname="tiro", fontsize=14)   # tiêu đề ngoài khung — không lấy
    if rot:
        page.set_rotation(rot)


@pytest.mark.parametrize("rot", [0, 270])
def test_lay_chu_trong_o_ten_ban_ve(tmp_path, rot):
    doc = pymupdf.open()
    _khung_ten(doc.new_page(width=842, height=595), rot)
    f = tmp_path / "k.pdf"
    doc.save(f)
    (d,) = sheets.danh_muc(f)
    assert (d["ten_ban_ve"], d["ky_hieu"], d["nguon_ten"]) == ("GHI CHU TONG", "KT-01", "o_khung_ten")


def test_o_ten_ban_ve_trong(tmp_path):
    doc = pymupdf.open()
    p = doc.new_page(width=842, height=595)
    p.draw_rect(pymupdf.Rect(600, 480, 820, 530), color=(0, 0, 0), width=0.5)
    p.insert_text((604, 490), "DRAWING TITLE", fontname="tiro", fontsize=6)
    p.insert_text((300, 300), "MAT BANG TANG 1", fontname="tiro", fontsize=14)
    f = tmp_path / "e.pdf"
    doc.save(f)
    (d,) = sheets.danh_muc(f)
    assert (d["ten_ban_ve"], d["nguon_ten"]) == ("", "o_trong")


@pytest.mark.parametrize("ten,cd", [
    ("MẶT BẰNG THOÁT NẠN TẦNG 1 NHÀ XƯỞNG 08", "thoat-nan"), ("MẶT BẰNG HÚT KHÓI TỔNG THỂ", "chong-tu-khoi"),
    ("SƠ ĐỒ NGUYÊN LÍ HỆ THỐNG BÁO CHÁY", "bao-chay"), ("MẶT BẰNG TÔNG THỂ", "khoang-cach"),
    ("AXIS Y1-Y11 ELEVATION", "giao-thong-xe-chua-chay"), ("BẢNG THỐNG KÊ CỬA ĐI VÀ CỬA SỔ", "thoat-nan"),
    ("MẶT BẰNG BỐ TRÍ ĐÈN CHIẾU SÁNG SỰ CỐ", "chieu-sang-su-co"), ("MẶT BẰNG CHỮA CHÁY SPRINKLER TẦNG 2", "chua-chay"),
    ("CHI TIẾT BTB1", "thoat-nan"), ("CHI TIẾT TB3", "thoat-nan"),
])
def test_chuyen_de(ten, cd):
    assert cd in sheets.chuyen_de(ten)


@pytest.mark.parametrize("ten,co,khong", [
    # quy tắc người dùng 14/10/2026: mặt đứng/cắt -> lối vào trên cao + ngăn cháy phương đứng; mặt bằng -> chỉ phương ngang
    ("MẶT ĐỨNG TRỤC A-C", {"giao-thong-xe-chua-chay", "ngan-chay.dung"}, {"ngan-chay.ngang"}),
    ("MẶT CẮT 2-2", {"giao-thong-xe-chua-chay", "ngan-chay.dung"}, {"ngan-chay.ngang"}),
    ("MẶT BẰNG TẦNG 4, 5, 6", {"ngan-chay.ngang", "thoat-nan", "bo-tri-cong-nang"}, {"ngan-chay.dung"}),
    ("MẶT BẰNG TẦNG BÁN HẦM", {"ngan-chay.ngang"}, {"ngan-chay.dung"}),
    ("CHI TIẾT THANG MÁY CHỮA CHÁY", {"thang-may-chua-chay"}, {"chua-chay", "thoat-nan"}),
    ("CHI TIẾT CỬA", {"thoat-nan", "ngan-chay"}, set()),
    ("CHI TIẾT BÃI ĐỖ XE PCCC", {"giao-thong-xe-chua-chay"}, {"chua-chay"}),
    ("MẶT BẰNG BỐ TRÍ MÁY BƠM PCCC", {"tram-bom"}, {"chua-chay"}),
])
def test_chuyen_de_theo_loai_ban_ve(ten, co, khong):
    cds = set(sheets.chuyen_de(ten))
    assert co <= cds and not (khong & cds), cds


def test_chuyen_de_hang_muc_phong_bom_va_tra_trang():
    assert sheets.chuyen_de("MẶT BẰNG TẦNG 1", hang_muc="PHÒNG BƠM VÀ BỂ NƯỚC NGẦM PCCC") == ["tram-bom"]
    dm = [{"trang": 1, "chuyen_de": ["ngan-chay.ngang"]}, {"trang": 2, "chuyen_de": ["ngan-chay.dung"]},
          {"trang": 3, "chuyen_de": ["ngan-chay"]}]
    assert sheets.pages_for(dm, "ngan-chay") == [1, 2, 3]
    assert sheets.pages_for(dm, "ngan-chay.dung") == [2, 3]


def test_insert_html_khong_nhan_doi():
    dm = [{"trang": 1, "ky_hieu": "KT-01", "ten_ban_ve": "MẶT BẰNG TẦNG 1", "hang_muc": "", "nguon_ten": "khung_ten",
           "chuyen_de": ["thoat-nan"]}]
    page = '<div class="card">\n  <h1>X</h1>\n</div>'
    once = sheets.insert_html(page, dm)
    twice = sheets.insert_html(once, dm)
    assert once == twice and once.count("Danh mục bản vẽ") == 1 and once.rstrip().endswith("</div>")
    assert "Không đọc được" in sheets.to_html([dict(dm[0], ten_ban_ve="")])


def test_cli_trang(tmp_path, capsys):
    doc = pymupdf.open()
    for title, so in (("DETAIL OF STAIR 1", "KT-01"), ("LAYOUT FIRE ALARM 1", "BC-01")):   # font tiro không có dấu
        p = doc.new_page(width=842, height=595)
        p.insert_text((600, 500), "DRAWING TITLE", fontname="tiro", fontsize=8)
        p.insert_text((600, 515), title, fontname="tiro", fontsize=10)
        p.insert_text((600, 545), "DRAWING NO", fontname="tiro", fontsize=8)
        p.insert_text((600, 560), so, fontname="tiro", fontsize=10)
    f = tmp_path / "t.pdf"
    doc.save(f)
    out = tmp_path / "out"
    out.mkdir()
    main(["trang", str(out), "--pdf", str(f), "--cd", "thoat-nan"])
    assert capsys.readouterr().out.splitlines()[0] == "1"
    dm = json.loads((out / "danh_muc_ban_ve.json").read_text(encoding="utf-8"))
    assert [(d["ten_ban_ve"], d["ky_hieu"]) for d in dm] == [("DETAIL OF STAIR 1", "KT-01"), ("LAYOUT FIRE ALARM 1", "BC-01")]
