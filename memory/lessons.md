# memory/lessons.md — L3 bài học (nạp theo mục khi chạy skill liên quan, tối đa 50 dòng/mục)

Mẫu 1 dòng: **bối cảnh → sai gì → cách đúng → ví dụ**. Chỉ ghi vào mục "Đã duyệt" sau khi người dùng xác nhận
sửa chữa; bài học mới do Claude đề xuất để ở "Chờ duyệt" cuối file.

## chung (mọi skill)
- Đơn vị bản vẽ → nhầm mm với m (6500 đọc thành 6500 m) → kích thước CAD là mm, cao độ/chiều cao là m; số > 200 ở trường "m" là mm → Phú Trường tr.22 "CHIỀU CAO PCCC | 6500".
- Tầng lửng / kỹ thuật / tum / áp mái → tính sai số tầng → theo 1.4.50 (rules/qcvn06/00-dinh-nghia.md): tum/lửng chỉ loại trừ khi thoả điều kiện CHÚ THÍCH; áp mái không tính → khách sạn Hoàng Hùng tr.3 ghi 10 tầng, tr.4 ghi 11.
- Hạng nổ vs nhóm nhà → nhầm "hạng C" với "nhóm F5.1" hay ngược lại → hạng (A–E) chỉ cho F5 (sản xuất/kho); nhóm theo Bảng 6 → "Hạng sản xuất: Hạng C" = hạng cháy nổ.
- Trục đánh số lại giữa các hạng mục cùng bộ → gán nhầm trục hạng mục khác → axes.json theo từng HM, không gộp.
- Chiều cao kiến trúc vs chiều cao PCCC → lấy đỉnh mái làm chiều cao PCCC → 1.4.9 đo từ mặt đường xe chữa cháy; PCCC ≤ chiều cao công trình (facts tự kiểm).

## doc-thong-tin (skill 01 · info-building)
- Font Arial Identity-H thiếu ToUnicode → chữ rác `3+Ҫ1&+81*` → tool tự sửa trong vector_text; `pages` vẫn ra toàn "other" thì kiểm font khác (VNI có vn_encoding.py) → bản vẽ ICIC.
- Font VNI → vỡ dấu "TÖÔØNG NGAÊN CHAÙY" → intake giải mã tự động → khách sạn Hoàng Hùng (7 mẫu đã kiểm).
- Bảng Excel dán dạng ảnh → lớp chữ không có số, Gemini đọc lệch cột → luồng HON-HOP: Claude đọc ảnh cắt (`crops`), ghi `claude_doc_anh.json` → BW Đồng An tr.7 (Gemini 20,45 thay vì 21,00; F4.2 thay vì F5.2).
- Trang xoay 90/270 → `crops` cắt hụt bảng (bbox ảnh theo trang chưa xoay) → đã sửa `image_rect()` (nhân rotation_matrix) → Phú Trường tr.5.
- Ghi chú vẽ bằng nét (không có trong lớp chữ) → chỉ Gemini đọc được → giữ với độ tin cậy L nếu câu căn cứ có nhãn trường; câu có trong lớp chữ mà số không khớp → Gemini bịa, loại.
- Cấp S0 → lấy từ câu "tường ngoài không chịu lực có cấp nguy hiểm cháy S0" (cấu kiện, không phải cả nhà) → ghi chú cho người dùng, không tự chốt → BW Đồng An tr.17, 30.
- Chiều cao PCCC trên mặt đứng → chỉ là nhãn, số nằm ở nét kích thước → không có trong text, cần đọc ảnh.
- Tên hạng mục trong project.yaml khác tên trên bảng → bảng tách đôi cột → dùng đúng tên bảng ("NHÀ KHO 1A", không phải "Kho 1A").
- Khu vực trong 1 nhà (khu văn phòng, khu trung chuyển, "phụ trợ") → bị tách thành cột hạng mục → hạng mục = dòng của BẢNG THỐNG KÊ HẠNG MỤC; khu vực ghi `meta.khu_vuc`.
- Gemini lệch dòng trong bảng → TRẠM ĐIỆN cao "-" bị gán 4,2 m của TRẠM BƠM → ghi nghi_ngo.json → Liên Minh tr.3–4.
- Nhà xưởng nhiều xưởng đánh số → mỗi mặt bằng ghi "TẦNG 1 NHÀ XƯỞNG CHO THUÊ 02, 03: 2000 M2" → tool tách từng xưởng; ghi chú tên trần "Nhà xưởng cho thuê có hạng C, F5.1" áp cho mọi xưởng → Phú Trường.
- Số có dấu cách nghìn "36 510 m3" → bị cắt còn 36 → đã sửa.
- Thuyết minh chữa cháy ngoài nhà ghi cho tên chung ("Chọn nhà xưởng 08…") → không gán khối tích cho xưởng nào, chỉ cảnh báo, hỏi người dùng → Phú Trường tr.127.
- Nhà kho F5.x → thiếu hạng cháy nổ → bắt buộc; thông số từng gian nằm trong "BẢNG TÍNH KHOẢNG CÁCH… CHO GIAN PHÒNG" trên mặt bằng tầng.
- File trên Google Drive (online-only) → lỗi đọc giữa chừng → chép về `data/input/` trước.
- Gemini đọc bảng ảnh trang xoay → sai hàng loạt (VP 800 thay 600 m², cao PCCC xưởng 3,57 thay 5,97/6,5, bậc xưởng 8 II thay IV) → với HON-HOP luôn để Claude đọc ảnh bảng quy mô → Phú Trường tr.5, 60 (duyệt 14/10/2026).
- Hai bảng trên cùng trang ghi khác số tầng / diện tích → lấy một bảng → báo cả hai cho người dùng chọn → Phú Trường tr.5 (xưởng 01: 1 hay 2 tầng; trạm bơm 16 hay 25 m²) (duyệt 14/10/2026).

## phan-loai (skill 03)
- Công năng có nhiều nhóm (nhà hàng trong khách sạn, văn phòng trong nhà kho) → gán nhóm chung cho cả nhà → gian phòng đông người có thể thuộc F2/F3; khu văn phòng trong kho vẫn theo nhóm nhà chính nếu < 2.5.5.2.
- Nhóm nhà chỉ suy từ tên → coi như đã chốt → giá trị `tinh` luôn phải qua Cổng 1; `ban_ve` lệch `tinh` là phát hiện.

## thoat-nan
- Kích thước cửa từ bảng cửa → là kích thước phủ bì → thông thuỷ nhỏ hơn ~0,1 m; cửa sát ngưỡng thì ghi cần kiểm thông thuỷ.
- Bảng tính thoát nạn của người thiết kế ghi "Đạt" → tin cột kết luận → đối chiếu số liệu với quy chuẩn, không tin kết luận của họ.
- Thang ghi "không thoát nạn / di chuyển nội bộ" → tính là lối ra → không tính; thang thép ngoài nhà = cầu thang loại 3.

## Chờ duyệt (Claude đề xuất, người dùng chưa xác nhận)
- Kiểm tra logic khối tích lệch (trạm bơm 54,4 m³ > 9 m² × 3,6 m) → tưởng là va chạm → số 9 m² là Gemini lấy nhầm dòng Trạm điện; va chạm thật là 25/16 m² giữa 2 bảng → skill `xu-ly-va-cham` bỏ dòng logic, trỏ va chạm thật → Phú Trường tr.5 (14/10/2026).
- Bảng thống kê hạng mục dạng chữ vector, dòng "6 | PHÒNG MÁY PHÁT ĐIỆN | 5 x 5 | 4.2 | 01 | 25" không có nhãn trường → tool loại cả dòng ("không có nhãn") → cần gán nhãn theo tiêu đề cột của bảng (KÍCH THƯỚC | CHIỀU CAO | SỐ TẦNG | DIỆN TÍCH) → Việt Trang tr.5–6 (14/10/2026).
- File PDF rất nặng (356 MB), trang tổng mặt bằng 2.500–3.000 dòng chữ vector → Gemini "không đọc được file PDF" cả chunk, mất luôn bảng quy mô → kiểm `image_table_pages`, bảng dán ảnh thì Claude đọc crops; bảng chữ vector thì lấy bằng vector_text → New Motion bv336 tr.3, 6 (14/10/2026).
