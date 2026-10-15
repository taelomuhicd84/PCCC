---
id: cach-xac-dinh-nha-hon-hop
tieu_de: Cách xác định nhà hỗn hợp cho TỪNG hạng mục (quy trình áp dụng 1.4.41)
nhom: cong-nang
tu_khoa: nhà hỗn hợp, 70%, công năng, hạng mục, hon-hop, B5, diện tích sàn từng công năng, nhà đơn năng
trang_thai: cho_duyet
nguon: cách hiểu của Claude khi áp dụng QCVN 06 1.4.41 (mục qcvn06-1-4-41-nha-hon-hop); người dùng yêu cầu 15/10/2026 — chưa được duyệt từng điểm
cap_nhat: '2026-10-15'
---
**Nguyên tắc: MỖI HẠNG MỤC có công năng riêng và tra bảng theo công năng của hạng mục đó** — không gộp các hạng mục trong cùng bản vẽ.
(Nhà hàng, nhà xe, nhà ở gia đình, trạm bơm… là các hạng mục khác nhau, mỗi hạng mục một loại hình / bảng đối chiếu.)

Quy trình cho 1 hạng mục (lệnh `cong-nang <thư mục hồ sơ>` làm bước 1–5; kết quả `cong_nang_de_xuat.json`):
1. Lấy danh sách khu vực/phòng của hạng mục kèm diện tích sàn (`project_info.meta.khu_vuc`); trùng tên giữa các trang → lấy giá trị gặp nhiều nhất, ghi cảnh báo.
2. Gán từng khu vào một loại theo `knowledge/cong-nang/_tu-khoa.yaml`: **công năng (nhóm F theo Bảng 6)**, **loại trừ** (kỹ thuật, PCCC, gian lánh nạn, đỗ xe),
   **chung** (hành lang, thang, WC), **phụ trợ** (bếp, kho nhỏ phục vụ công năng chính).
3. Cộng diện tích theo nhóm F, KHÔNG tính khu loại trừ và khu chung (đúng chú thích 1.4.41). Tỷ lệ = diện tích nhóm / tổng các công năng.
4. **Công năng lớn nhất ≤ 70 % và có ≥ 2 công năng → nhà HỖN HỢP** (bảng đối chiếu hỗn hợp B5.x, `hon-hop`).
   **Công năng lớn nhất > 70 % → nhà đơn năng theo công năng đó** (bảng của công năng đó).
5. Không chắc (để người/Claude quyết, không đoán): thiếu diện tích; khu chưa phân loại làm đổi kết luận; kết luận đổi khi tính hoặc bỏ khu phụ trợ
   (báo "KẾT LUẬN NHẠY"); công năng lớn nhất trong khoảng 70 % ± 3 điểm.
6. Chỉ khi hạng mục KHÔNG có số liệu khu vực: theo tên hạng mục (vd NHÀ KHO → F5.2) và ghi rõ chưa xét hỗn hợp.

Các điểm là GIẢ ĐỊNH của Claude (cần người dùng duyệt): khu "chung" bỏ khỏi cả tử và mẫu; khu "phụ trợ" thử cả hai cách; "công năng" tính theo nhóm F con
(F3.1 khác F3.2); bỏ ngoại lệ "phục vụ công năng chính" của bản cũ vì QCVN chỉ dùng tiêu chí diện tích. Nhà chung cư hỗn hợp ở/kinh doanh (1.4.40)
vẫn là nhóm F1.3 theo Bảng 6 nhưng xem bảng chung cư/hỗn hợp — xét riêng khi gặp.

Lỗi hay nhầm: (a) coi "có nhà hàng ở tầng trệt" là hỗn hợp dù nhà hàng chỉ vài % diện tích; (b) tính cả hầm đỗ xe và phòng kỹ thuật vào tổng;
(c) gộp nhiều hạng mục (nhà hàng + nhà xe + nhà ở) thành một nhà hỗn hợp; (d) nhầm "nhà ở gia đình" (F1.4) với chung cư (F1.3).
