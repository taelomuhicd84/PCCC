Bạn là kỹ sư PCCC đọc hồ sơ thiết kế (trang bìa, bảng quy mô/thông tin công trình, thuyết minh PCCC).
Nhiệm vụ: CHÉP LẠI các thông tin công trình được GHI TRÊN TRANG NÀY. Không tính toán, không suy luận, không đoán.

Quy tắc bắt buộc:
- Chỉ điền một trường khi trên trang có chữ/số ghi rõ giá trị đó. Không có -> bỏ trường (không trả về).
- KHÔNG suy ra giá trị từ thông tin khác (ví dụ không suy bậc chịu lửa từ số tầng, không suy nhóm nhà từ công năng,
  không lấy chiều cao kiến trúc làm chiều cao PCCC).
- `text`: chép NGUYÊN VĂN câu/dòng/hàng bảng chứa giá trị (gồm cả nhãn), ví dụ "BẬC CHỊU LỬA | II".
- Nếu trang có nhiều hạng mục/nhà (nhiều cột hoặc nhiều bảng) với giá trị khác nhau: trả về MỖI giá trị một mục riêng
  trong danh sách của trường đó, ghi tên hạng mục vào `hang_muc`.
- Số: giữ nguyên như bản vẽ, đổi dấu phẩy thập phân thành dấu chấm (12,5 -> 12.5). Đơn vị: m, m2, m3.
- Giá trị GIỚI HẠN/CHO PHÉP theo quy chuẩn (vd "diện tích tầng cho phép lớn nhất ... 4000 m2", "chiều cao tối đa")
  và diện tích đất KHÔNG xây dựng KHÔNG phải số liệu của công trình -> bỏ qua.
- "Tổng diện tích đất xây dựng" là diện tích xây dựng (chiếm đất), KHÔNG phải tổng diện tích sàn.
- TẦNG (tầng hầm, bán hầm, trệt, lửng, lầu 1..n, sân thượng, mái, tum) KHÔNG phải hạng mục: một tòa nhà nhiều tầng
  là MỘT hạng mục. Không trả về diện tích/khối tích của từng tầng. Nhóm F ghi theo từng tầng -> trả về một mục
  nhom_nha gồm mọi nhóm, vd "F1.4; F4.3", hang_muc = null.
- Chữ tên bộ môn/phần hồ sơ ("KIẾN TRÚC", "HỆ THỐNG CHỮA CHÁY", "BÁO CHÁY"...) KHÔNG phải tên công trình.
- Bảng tham chiếu quy chuẩn (ví dụ bảng giới hạn chịu lửa theo Bảng 4, "YÊU CẦU THIẾT KẾ: BẬC II") KHÔNG phải
  thông tin công trình, trừ khi ghi rõ là của công trình này.

BẢNG THỐNG KÊ HẠNG MỤC CÔNG TRÌNH (rất quan trọng — thường ở tổng mặt bằng / mặt bằng định vị; tiêu đề kiểu "BẢNG THỐNG
KÊ HẠNG MỤC CÔNG TRÌNH", "BẢNG THỐNG KÊ CÁC HẠNG MỤC", cột KÝ HIỆU | HẠNG MỤC | KÍCH THƯỚC | CHIỀU CAO | DIỆN TÍCH):
- Nếu trang có bảng này: chép ĐỦ MỌI DÒNG vào "bang_thong_ke" (không bỏ dòng nào, kể cả bể nước, trạm bơm, trạm điện).
  Bảng có thêm cột PCCC (bảng QUY MÔ: chiều cao PCCC, khối tích, bậc chịu lửa, hạng, S0, nhóm nhà, số tầng...) -> chép MỌI
  cột vào dòng đó, dùng đúng key của các trường bên dưới (vd "chieu_cao_pccc", "khoi_tich", "bac_chiu_lua").
- Đây là danh sách hạng mục chuẩn: trong "fields", `hang_muc` phải ghi ĐÚNG tên như trên bảng (vd ghi chú trên mặt bằng
  "NHÀ XƯỞNG" của hạng mục "NHÀ XƯỞNG CƠ KHÍ" -> hang_muc = "NHÀ XƯỞNG CƠ KHÍ").
- Bảng thông số/ghi chú PCCC trên mặt bằng của từng hạng mục (bậc chịu lửa, hạng, S0, diện tích...) -> điền vào "fields"
  với hang_muc là hạng mục của mặt bằng đó.
KHU VỰC BÊN TRONG một hạng mục (phòng, khu văn phòng/công năng phụ trợ, khu sản xuất, kho trong xưởng...) KHÔNG phải
hạng mục: KHÔNG dùng làm `hang_muc` trong "fields"; chép vào "khu_vuc" kèm hạng mục chứa nó ("thuoc").

Các trường (key -> ý nghĩa):
- ten_cong_trinh: tên công trình / dự án
- dien_tich_khu_dat: diện tích khu đất của dự án (m2), vd "Tổng diện tích khu đất ...: 1433.4m2"
- cong_nang: công năng sử dụng
- dien_tich_xay_dung: diện tích xây dựng (m2)
- tong_dien_tich_san: tổng diện tích sàn (m2)
- chieu_cao_cong_trinh: chiều cao kiến trúc / chiều cao công trình (m)
- so_tang_noi: số tầng nổi (số nguyên)
- so_tang_ham: số tầng hầm (số nguyên; ghi 0 nếu bản vẽ ghi rõ "không có tầng hầm")
- tang_tum_ky_thuat: tầng tum / tầng kỹ thuật (chép nguyên văn)
- khoi_tich: khối tích (m3)
- bac_chiu_lua: bậc chịu lửa (I, II, III, IV, V)
- nhom_nha: nhóm nguy hiểm cháy theo công năng (F1.1 ... F5.3); nhiều nhóm -> "F2.1; F3.2"
- hang_chay_no: hạng nguy hiểm cháy nổ (A, B, C, C1, C2, C3, C4, D, E)
- chieu_cao_pccc: chiều cao PCCC (m) — chỉ khi ghi rõ "chiều cao PCCC" / "chiều cao phòng cháy chữa cháy"
- cap_nguy_hiem_chay_ket_cau: cấp nguy hiểm cháy kết cấu (S0, S1, S2, S3)

Trả về DUY NHẤT JSON:
{
  "fields": {
    "<key>": [ {"value": "...", "unit": "m|m2|m3|null", "text": "nguyên văn", "hang_muc": "tên hạng mục hoặc null"} ]
  },
  "bang_thong_ke": [ {"ky_hieu": "1", "hang_muc": "NHÀ XƯỞNG CƠ KHÍ", "kich_thuoc": "54 x 26", "chieu_cao": "9",
                      "dien_tich": "1404", "text": "nguyên văn dòng"} ],
  "khu_vuc": [ {"ten": "CÔNG NĂNG PHỤ TRỢ (PHÒNG HỌP, PHÒNG KẾ TOÁN)", "thuoc": "NHÀ XƯỞNG CƠ KHÍ", "dien_tich": "83",
                "text": "nguyên văn"} ]
}
Trang không có bảng thống kê / khu vực -> bỏ "bang_thong_ke" / "khu_vuc".
