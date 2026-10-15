"""Bảng số QCVN 06 đã nạp thành module riêng + cơ chế dòng bảng tra dẫn tới bảng (goi)."""
from pccc_checker.pipeline import goi, knowled


def test_moi_bang_mot_module_va_ky_hieu_chuan():
    ids = {m["id"] for m in knowled.muc_kho()}
    assert {"qcvn06-bang-4", "qcvn06-bang-5", "qcvn06-bang-16", "qcvn06-bang-e3", "qcvn06-bang-a1", "qcvn06-bang-g9"} <= ids
    b4 = knowled.lay("qcvn06-bang-4")
    assert b4["trang_thai"] == "verified" and "| IV | R 15 | E 15 | REI 15 | RE 15 | R 15 | REI 45 | R 15 |" in b4["noi_dung"]
    assert "Е" not in b4["noi_dung"] and "З" not in knowled.lay("qcvn06-bang-5")["noi_dung"]      # chữ Kirin lẫn trong file Word đã chuẩn hoá


def test_bang_16_khoi_tich_va_bang_14_bai_do():
    assert "| ≤ 28 400 | 1/6 chu vi và không nhỏ hơn 15 m |" in knowled.lay("qcvn06-bang-16")["noi_dung"]
    assert "Theo Bảng 15 và Bảng 16" in knowled.lay("qcvn06-bang-14")["noi_dung"]


def test_dong_dan_toi_bang_co_trong_kho_thanh_xet_con_bang_khac_van_xm():
    dk = goi.luat_dieu_kien()
    t = dict(hm="HM", ten="x", tang_noi=1, co_ham=False, cao=3.5, nhom=None, bac="IV", s="S0", hang="C", dt=1)
    r = dict(id="X-1", nd="Cấp nguy hiểm cháy kết cấu", luu_y="", qd="Bảng 5", dk="Bảng 5 QCVN 06:2022/BXD")
    assert goi.bang_refs(r) == ["5"] and goi.phan_loai(r, t, dk)[0] == "XET"
    # QCVN 13 đã có trong kho -> XET kèm bảng (không còn XM); "Bảng 3" + "Bảng 3 / QCVN 13" gộp thành 1 bảng
    r13 = dict(r, qd="Bảng 3", dk="Bảng 3 / QCVN 13:2018")
    assert goi.bang_refs(r13) == ["qcvn13-3"] and goi.phan_loai(r13, t, dk)[0] == "XET"
    assert goi.bang_file("qcvn13-3").name == "qcvn13-bang-3.md" and goi.bang_file("tcvn7568-14-1").name == "tcvn7568-14-bang-1.md"
    # chuẩn chưa có trong kho vẫn XM
    rx = dict(r, qd="Bảng 3", dk="Bảng 3 TCVN 9999:2020")
    assert goi.bang_refs(rx) == ["x3"] and goi.phan_loai(rx, t, dk)[0] == "XM"
    assert goi.bang_thieu(["x3"]) and goi.bang_thieu(["999"]) and not goi.bang_thieu(["4", "5", "qcvn13-3"])


def test_bang_cho_duyet_khong_duoc_ket_luan_D():
    assert goi.bang_thieu(["1"]) is True or knowled.lay("qcvn06-bang-1")["trang_thai"] == "verified"
    lines = {20: ["Nhà xe bậc IV R15"]}
    tl = "GR-BCL-001 | D | 20 | đạt | Nhà xe bậc IV R15"
    kq = goi.phan_tich_gemini(tl, ["GR-BCL-001"], lines, {"GR-BCL-001"})
    assert kq["GR-BCL-001"]["tt"] == "XM"
