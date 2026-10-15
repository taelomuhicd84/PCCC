"""Gói đối chiếu (pipeline/goi.py): lọc dòng bảng tra bằng script, kiểm chứng trả lời Gemini, kết quả gọn."""
from pccc_checker.pipeline import goi

MD = """---
chuyen_de: thoat-nan
---
| ID | TT | Nội dung đối chiếu | Lưu ý khi đối chiếu | Quy định | Điều khoản |
|---|---|---|---|---|---|
| GR-TN-001 | - | Lối, đường thoát nạn |  |  |  |
| GR-TN-004 | - | Tầng hầm |  | Các lối ra từ tầng hầm là lối thoát nạn khi ra ngoài trực tiếp | Đ 3.2.2 QCVN 06:2022 |
| GR-TN-040 | - | Chiều rộng bản thang |  | Không nhỏ hơn 1,2 m<br>nếu trên 15 người | Đ 3.4.1 |
| GR-TN-031 | - | Gara trên mặt đất |  | Đối với Gara ô tô trên mặt đất: | Bảng 3 QCVN 13:2018 |
| GR-TN-026 | - | Chiều cao thông thủy |  | Chiều cao thông thủy của lối ra thoát nạn phải không nhỏ hơn 1,9 m | Đ 3.2.9 |
"""
MOT_TANG = dict(hm="HM03", ten="NHÀ XE", tang_noi=1, co_ham=False, cao=3.5, nhom=None, bac="IV", s="S0", hang="C", dt=900)


def _rows(tmp_path):
    f = tmp_path / "07-thoat-nan.md"
    f.write_text(MD, encoding="utf-8")
    return goi.parse_rows(f)


def test_parse_va_phan_loai(tmp_path):
    rows = {r["id"]: r for r in _rows(tmp_path)}
    assert len(rows) == 5 and "nếu trên 15 người" in rows["GR-TN-040"]["qd"] and "<br>" not in rows["GR-TN-040"]["qd"]
    dk = goi.luat_dieu_kien()
    kq = {i: goi.phan_loai(r, MOT_TANG, dk)[0] for i, r in rows.items()}
    assert kq == {"GR-TN-001": "TD", "GR-TN-004": "NA", "GR-TN-040": "NA", "GR-TN-031": "XET", "GR-TN-026": "XET"}
    assert goi.bang_refs(rows["GR-TN-031"]) == ["qcvn13-3"]       # QCVN 13 Bảng 3 đã nạp vào kho knowled -> XET kèm bảng, không còn XM


def test_khong_cat_khi_thieu_so_lieu(tmp_path):
    rows = {r["id"]: r for r in _rows(tmp_path)}
    chua_biet = dict(MOT_TANG, tang_noi=None, co_ham=None)
    dk = goi.luat_dieu_kien()
    assert goi.phan_loai(rows["GR-TN-004"], chua_biet, dk)[0] == "XET"      # số liệu thiếu -> Claude xét, không tự NA
    assert goi.phan_loai(rows["GR-TN-040"], dict(MOT_TANG, tang_noi=3), dk)[0] == "XET"
    assert goi.phan_loai(rows["GR-TN-004"], dict(MOT_TANG, co_ham=True), dk)[0] == "XET"


def test_tu_khoa_doi_tuong_can_chu_vector():
    r = dict(id="X-1", nd="Máy biến áp", luu_y="", qd="Đặt ở tầng 1", dk="Đ 1")
    dk = goi.luat_dieu_kien()
    co_chu = {1: ["MẶT BẰNG", "trạm điện 24 m2"], 2: ["ghi chú"]}
    khong = {1: ["MẶT BẰNG"], 2: ["ghi chú"]}
    assert goi.phan_loai(r, MOT_TANG, dk, khong)[0] == "NA"
    assert goi.phan_loai(r, MOT_TANG, dk, co_chu)[0] == "XET"
    scan = {1: [""], 2: [""], 3: ["ghi chú"]}                               # hồ sơ scan nhiều: không dám kết luận
    assert goi.phan_loai(r, MOT_TANG, dk, scan)[0] == "XET"


def test_gemini_d_phai_co_trich_dan_that():
    lines = {25: ["Hành lang thoát nạn rộng 1.2m", "Số lượng người có mặt là 180 người"]}
    tl = ("GR-A | D | 25 | đủ rộng | Hành lang thoát nạn rộng 1.2m\n"
          "GR-B | D | 25 | bịa | Cửa rộng 2.4m có 3 cánh\n"
          "GR-C | KD | 25 | hẹp | Hành lang thoát nạn rộng 1.2m\n"
          "GR-E | NA | | không có thang | ")
    kq = goi.phan_tich_gemini(tl, ["GR-A", "GR-B", "GR-C", "GR-D", "GR-E"], lines)
    assert kq["GR-A"]["tt"] == "D"
    assert kq["GR-B"]["tt"] == "XM" and "trích dẫn" in kq["GR-B"]["ly_do"]
    assert kq["GR-C"]["tt"] == "XM" and "nghi KD" in kq["GR-C"]["ly_do"]
    assert kq["GR-D"]["tt"] == "XM" and kq["GR-E"]["tt"] == "NA"


def test_gemini_d_voi_dong_can_bang_so_ha_xm():
    lines = {20: ["Nhà xe bậc chịu lửa IV, cột R15"]}
    tl = "GR-BCL-001 | D | 20 | đạt Bảng 4 | Nhà xe bậc chịu lửa IV, cột R15"
    assert goi.phan_tich_gemini(tl, ["GR-BCL-001"], lines)["GR-BCL-001"]["tt"] == "D"
    kq = goi.phan_tich_gemini(tl, ["GR-BCL-001"], lines, {"GR-BCL-001"})
    assert kq["GR-BCL-001"]["tt"] == "XM" and "Bảng số chưa chép" in kq["GR-BCL-001"]["ly_do"]


def test_ket_qua_gon_va_cache_key(tmp_path):
    f = tmp_path / "a.ket-qua.txt"
    f.write_bytes("﻿GR-TN-009 | D | 25 | 5 lối ≥ 2\nGR-TN-021 | KD | 25 | sai | «cửa mở vào» | 0.1,0.2,0.3,0.4\n".encode("utf-8"))
    d = goi.doc_ket_qua(f)
    assert d[0]["rule"] == "GR-TN-009" and d[0]["trang"] == 25 and d[1]["bbox"] == [0.1, 0.2, 0.3, 0.4]
    r = dict(id="X", nd="a", luu_y="", qd="b", dk="c")
    k1 = goi.khoa_cache(r, MOT_TANG, "chu")
    assert k1 == goi.khoa_cache(dict(r), MOT_TANG, "chu")
    assert k1 != goi.khoa_cache(r, MOT_TANG, "chữ khác") and k1 != goi.khoa_cache(r, dict(MOT_TANG, cao=9), "chu")
