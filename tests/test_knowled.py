"""knowled — kho kiến thức: tra không dấu, trạng thái chờ duyệt/verified, nạp file, file nguồn sẵn có."""
from pccc_checker.pipeline import knowled


def test_tra_khong_dau_va_file_nguon_san_co():
    kq = knowled.tim("tang ham")                       # không dấu vẫn ra 1.4.57 Tầng hầm trong 00-dinh-nghia.md
    assert kq and any("hầm" in m["tieu_de"].lower() for _, m, _ in kq)
    assert all(m["trang_thai"] == "verified" for _, m, _ in kq if "00-dinh-nghia" in m["id"])


def test_muc_hat_giong_da_nap():
    ids = {m["id"] for m in knowled.muc_kho()}
    assert {"nha-xe-gara-hay-kho", "loai-hinh-nha-hang", "bang-qcvn-chua-chep"} <= ids
    m = knowled.lay("nha-xe-gara-hay-kho")
    assert m["trang_thai"] == "cho_duyet" and m["nhom"] == "cong-nang"          # chưa xác nhận -> chỉ gợi ý
    assert knowled.tim("nhà xe gara", 3)[0][1]["id"] == "nha-xe-gara-hay-kho"
    assert knowled.lay("khong-co") is None


def test_bang_6_nhom_nha_nguyen_van_tu_word():
    m = knowled.lay("bang-6-phan-nhom-nha")
    assert m and m["trang_thai"] == "verified" and m["nhom"] == "quy-chuan"
    nhom = set(__import__("re").findall(r"^\| (F\d(?:\.\d)?) \|", m["noi_dung"], __import__("re").M))
    assert nhom == {"F1", "F2", "F3", "F4", "F5"} | {f"F{a}.{b}" for a, n in ((1, 4), (2, 4), (3, 6), (4, 4), (5, 3)) for b in range(1, n + 1)}
    assert "tiệc" in knowled.lay("bang-6-phan-nhom-nha")["noi_dung"].lower() or "tổ chức sự kiện" in m["noi_dung"]
    top = knowled.tim("nhà hàng tổ chức sự kiện ăn uống", 3)
    assert any(x["id"] == "bang-6-phan-nhom-nha" for _, x, _ in top)


def test_nap_moi_cho_duyet_roi_duyet(tmp_path, monkeypatch):
    monkeypatch.setattr(knowled, "KHO", tmp_path / "knowledge")
    nguon = tmp_path / "a.md"
    nguon.write_text("Karaoke có phòng hát thuộc F2.3 theo nguyên văn.\n", encoding="utf-8")
    p = knowled.them(nguon, None, "Phòng hát karaoke", "cong-nang", "karaoke, phòng hát", "tài liệu A")
    assert p.name == "phong-hat-karaoke.md" and knowled.lay("phong-hat-karaoke")["trang_thai"] == "cho_duyet"
    assert "karaoke" in knowled.ghi_muc_luc().read_text(encoding="utf-8")
    knowled.duyet("phong-hat-karaoke")
    assert knowled.lay("phong-hat-karaoke")["trang_thai"] == "verified"
    assert knowled.tim("phòng hát")[0][1]["id"] == "phong-hat-karaoke"
