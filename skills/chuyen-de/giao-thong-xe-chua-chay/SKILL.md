# giao-thong-xe-chua-chay — mục 4 bảng đối chiếu: Đường giao thông, bãi đỗ xe chữa cháy, lối vào từ trên cao
Tiểu mục: 4.1 đường cho xe chữa cháy (chiều rộng, chiều cao thông thủy); 4.2 bãi đỗ (yêu cầu, chiều rộng, chiều dài theo chu vi và diện tích sàn, có/không sprinkler); 4.2.2 lối vào từ trên cao (vị trí, đặc điểm, kích thước, số lượng); 4.3 độ dốc, khoảng không, tải trọng, đường cụt, bãi quay xe, đoạn tránh xe.
Bảng tra: `rule_keys.json → file["giao-thong-xe-chua-chay"]` (vd `rules/checklists/khach-san/k2/04-giao-thong-xe-chua-chay*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: mọi khu đất; phần lối vào từ trên cao chỉ khi nhóm nhà + chiều cao PCCC thuộc điều kiện ghi trong dòng bảng. Loại hình chưa có bộ bảng (`rule_keys.file` không có `giao-thong-xe-chua-chay`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): cao_pccc_m, nhom_nha, chu vi nhà, diện tích sàn lớn nhất được tiếp cận, có sprinkler hay không; bề rộng đường, kích thước bãi đỗ, khoảng cách bãi → nhà (tổng mặt bằng, bảng tính bãi đỗ); vị trí + kích thước lối vào trên mặt đứng.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["giao-thong-xe-chua-chay"]` hoặc `trang <thư mục> --cd giao-thong-xe-chua-chay`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: bề rộng đường/bãi, chiều dài bãi đỗ theo bảng chu vi, số lối vào từ trên cao theo chiều dài bãi, kích thước lỗ cửa — so với số trong cột Quy định.
   - Cần phán đoán: vật cản (cây, cổng, mái che) trên đường/bãi; khoảng không giữa bãi và lối vào; đường cụt, bãi quay xe; lỗ cửa có bị lam/kính cố định che — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"giao-thong-xe-chua-chay","rule":"<ID dòng, vd K2-GT-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `giao-thong-xe-chua-chay` (nếu có) và mục `chung`.
