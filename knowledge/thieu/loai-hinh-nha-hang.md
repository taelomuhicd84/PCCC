---
id: loai-hinh-nha-hang
tieu_de: Nhà hàng / sảnh tiệc cưới (F3.2) chưa có bảng đối chiếu
nhom: thieu
tu_khoa: nhà hàng, tiệc cưới, sảnh tiệc, F3.2, chưa xác định, chua-xac-dinh, loại hình
trang_thai: verified
nguon: rules/_index.md bảng "Loại hình → bộ bảng" (không có nhà hàng); chạy keys hồ sơ Thiên Ý 15/10/2026
cap_nhat: 2026-10-15
---
`keys` trả `chua-xac-dinh` cho NHÀ HÀNG 01/02 (nhóm F3.2) vì không bộ nào có từ khoá "nhà hàng/tiệc cưới" và F3.2 không ứng đúng 1 bảng.
Hệ quả: mọi chuyên đề của hạng mục XM, chỉ chạy luật YAML. Không đoán bảng; người dùng chốt `loai_hinh` (ghi `memory/overrides.json`)
hoặc cung cấp bảng đối chiếu nhà hàng để thêm 1 dòng `LOAI` trong `pipeline/loai_hinh.py`.
Ứng viên chỉ để người dùng cân nhắc, CHƯA xác nhận: các bảng công trình công cộng đã có (tttm, karaoke, hon-hop).
