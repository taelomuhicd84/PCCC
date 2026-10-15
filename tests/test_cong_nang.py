"""Phán đoán công năng từng hạng mục: nhà hỗn hợp theo QCVN 06 1.4.41 (mỗi công năng ≤ 70 % tổng sàn, không tính kỹ thuật/PCCC/lánh nạn/đỗ xe)."""
from pccc_checker.pipeline import cong_nang

RS = cong_nang.luat()


def hm(ten, khu, san=None):
    return cong_nang.danh_gia_hm(ten, [dict(ten=a, dien_tich=b) for a, b in khu], san, RS)


def test_hon_hop_khi_moi_cong_nang_khong_vuot_70():
    r = hm("TÒA NHÀ A", [("Khối khách sạn", 600), ("Nhà hàng", 250), ("Văn phòng cho thuê", 150),
                         ("Phòng kỹ thuật điện", 80), ("Hầm để xe", 300), ("Phòng bơm PCCC", 20)], san=1400)
    assert r["ket_luan"] == "hon-hop" and r["hon_hop"] is True and r["chinh"] == "F1.2"
    assert r["ty_le"] == {"F1.2": 0.6, "F3.2": 0.25, "F4.3": 0.15}
    assert set(r["loai_tru"]) == {"kỹ thuật", "do-xe", "pccc"}               # không tính vào tổng


def test_don_nang_khi_mot_cong_nang_tren_70():
    r = hm("TÒA NHÀ B", [("Văn phòng", 750), ("Cửa hàng tiện ích", 250)], san=1000)
    assert r["ket_luan"] == "don-nang" and r["hon_hop"] is False and r["chinh"] == "F4.3"
    assert r["ty_le"]["F4.3"] == 0.75


def test_ket_luan_nhay_khi_khu_phu_tro_doi_ket_qua():
    # bỏ bếp: 650/950 = 68 % -> hỗn hợp; cộng bếp vào công năng chính: 850/1150 = 74 % -> đơn năng => không chắc
    r = hm("TÒA NHÀ C", [("Văn phòng", 650), ("Nhà hàng", 300), ("Khu bếp", 200)], san=1150)
    assert r["ket_luan"] == "khong-chac" and any("NHẠY" in c for c in r["canh_bao"])


def test_khu_chua_phan_loai_lon_thi_khong_chac_nhung_don_nang_ro_van_chac():
    r = hm("TÒA NHÀ D", [("Văn phòng", 400), ("Nhà hàng", 300), ("Khu XYZ lạ", 300)], san=1000)
    assert r["ket_luan"] == "khong-chac" and any("chưa phân loại" in c for c in r["canh_bao"])
    r2 = hm("NHÀ Ở E", [("Phòng ngủ", 300), ("Phòng khách", 100), ("Phòng thờ", 20), ("Khu lạ", 20)], san=500)
    assert r2["ket_luan"] == "don-nang" and r2["chinh"] == "F1.4"           # F1.4 > 70 % kể cả khi khu lạ là công năng khác


def test_khong_co_khu_vuc_theo_ten_hang_muc():
    assert hm("NHÀ KHO", [])["chinh"] == "F5.2" and hm("NHÀ KHO", [])["ket_luan"] == "don-nang"
    assert hm("NHÀ XE 01", [])["chinh"] == "F5.2"                           # nhà/gara đỗ xe riêng = F5.2 (Bảng 6)
    assert hm("NHÀ HÀNG 01", [])["chinh"] == "F3.2"
    assert hm("TRẠM BƠM PCCC", [])["ket_luan"] == "ky-thuat"
    assert hm("HẠNG MỤC LẠ", [])["ket_luan"] == "khong-chac"


def test_kien_thuc_dinh_nghia_nha_hon_hop_da_nap():
    from pccc_checker.pipeline import knowled
    m = knowled.lay("qcvn06-1-4-41-nha-hon-hop")
    assert m["trang_thai"] == "verified" and "không vượt quá 70% tổng diện tích sàn xây dựng" in m["noi_dung"]
    assert knowled.lay("qcvn06-1-4-40-nha-chung-cu") and knowled.lay("qcvn06-1-4-39-nha") and knowled.lay("qcvn06-1-4-42-nha-san-xuat")
    q = knowled.lay("cach-xac-dinh-nha-hon-hop")
    assert q["trang_thai"] == "cho_duyet" and "70 %" in q["noi_dung"]          # cách hiểu của Claude chưa duyệt -> chỉ gợi ý
    assert {r["nhom"] for r in RS if r["loai"] == "cong-nang"} >= {"F1.2", "F1.4", "F3.2", "F4.3", "F5.1", "F5.2"}


def test_khu_tren_tung_hang_muc_khong_tron_voi_nhau():
    from pccc_checker.pipeline.rule_keys import _cung_hm
    kv = [dict(ten="Sảnh tiệc", thuoc="NHÀ HÀNG 01", dien_tich="500", page=3), dict(ten="Phòng ngủ", thuoc="NHÀ Ở GIA ĐÌNH", dien_tich="30", page=3),
          dict(ten="Sảnh tiệc", thuoc="NHÀ HÀNG 01", dien_tich="500", page=7)]
    khu, canh = cong_nang.khu_cua_hm(kv, "NHÀ HÀNG 01", _cung_hm)
    assert khu == [dict(ten="Sảnh tiệc", dien_tich=500.0)] and canh == []


def test_sanh_don_tinh_vao_cong_nang_chinh_va_ham_giai_tri_co_de_xuat():
    # ca 72 Nguyễn Khoái: sảnh "không bố trí công năng" = sảnh đón của home stay; hầm giải trí phải có đề xuất + kịch bản loại trừ
    r = hm("NHÀ NGHỈ", [("Tầng hầm – khu giải trí", 72.2), ("Tầng 1 – sảnh (không bố trí công năng)", 73.2), ("Tầng lửng – sảnh cafe", 55.9),
                        ("Tầng 2 – home stay", 84.3), ("Tầng 3 – home stay", 84.3), ("Tầng 4 – home stay", 84.3), ("Tầng 5 – home stay", 84.3)])
    assert r["theo_chinh"] and r["chung"] == 0 and r["chinh"] == "F1.2" and r["ty_le"]["F1.2"] > 0.7
    assert r["ham"][0]["de_xuat"].startswith("công năng F2.2") and "đơn năng F1.2" in r["ham"][0]["neu_loai_tru"]
    r2 = hm("NHÀ X", [("Hầm giải trí", 200), ("Phòng ngủ khách sạn", 250), ("Sảnh đón", 50)])   # bỏ hầm: khách sạn 100 % ; tính hầm: 200/450... -> nhạy
    assert r2["ket_luan"] == "khong-chac" and any("hầm" in c for c in r2["canh_bao"])
