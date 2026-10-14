# an-toan-cong-nghe — mục bảng đối chiếu công trình đặc thù (B19–B28): An toàn công nghệ
Tiểu mục (tuỳ bảng): yêu cầu chung cửa hàng xăng dầu, thu hồi hơi xăng dầu (B19); đường ống công nghệ, nước thải nhiễm dầu (B20);
sang chiết nạp, tồn chứa / xếp / tồn trữ chai LPG, vị trí nguồn gây cháy, kho chứa hàng (B21); bố trí lắp đặt, an toàn công nghệ,
kho chứa chai (B23); vị trí lắp đặt và an toàn công nghệ bồn bể (B24); hệ thống thu gom khu chế biến, giao nhận (B25).
Bảng tra: `rule_keys.json → file["an-toan-cong-nghe"]` (vd `rules/checklists/kho-lpg/chung/22-an-toan-cong-nghe.md`).

Mẫu hệ thống nạp kèm: `rules/checklists/he-thong/B47/` (phần của mục này) — đọc mục yêu cầu trang bị trước; không thuộc diện → NA.

1. Khi nào dùng: chỉ khi `rule_keys.file` có `an-toan-cong-nghe` (loại hình đặc thù); không có file → không chạy, không ghi dòng.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): sức chứa (m³ xăng dầu, kg/chai LPG, tấn LNG), số và dung tích bồn/bể, cột bơm,
   vị trí bồn so với nhà và ranh giới, van/thiết bị an toàn, hệ thống thu hồi hơi / thu gom, nguồn gây cháy gần khu tồn chứa.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (`trang <thư mục> --cd an-toan-cong-nghe`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét. Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới QCVN/TCVN chưa có → XM ghi tên văn bản):
   - Script / so số: dung tích, số lượng chai/bồn, khoảng cách bồn — so số trong cột Quy định.
   - Cần phán đoán: bố trí bồn, van, đường ống, nguồn gây cháy trên sơ đồ công nghệ — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`).
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"an-toan-cong-nghe","rule":"<ID dòng, vd LPG-ATCN-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng → NA, ghi lý do. Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `an-toan-cong-nghe` (nếu có) và mục `chung`.
