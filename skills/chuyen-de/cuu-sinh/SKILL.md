# cuu-sinh — mục bảng đối chiếu phương tiện thủy (B31 tàu biển, B32, B33 phương tiện thủy nội địa): Phương tiện cứu sinh
Tiểu mục: số lượng, chủng loại, vị trí bố trí phương tiện cứu sinh (phao, xuồng cứu sinh, bè…) theo số người trên phương tiện.
Bảng tra: `rule_keys.json → file["cuu-sinh"]` (vd `rules/checklists/ptt-cho-khach/chung/23-cuu-sinh.md`).

1. Khi nào dùng: chỉ khi `rule_keys.file` có `cuu-sinh` (bảng phương tiện thủy); không có file → không chạy, không ghi dòng.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): thông số phương tiện (chiều dài, tải trọng, số khách + thuyền viên),
   số và loại phao / xuồng / bè cứu sinh, vị trí bố trí trên bản vẽ bố trí chung.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (`trang <thư mục> --cd cuu-sinh`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét. Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới quy chuẩn tàu chưa có → XM ghi tên):
   - Script / so số: số phương tiện cứu sinh theo số người — so số trong cột Quy định.
   - Cần phán đoán: vị trí dễ tiếp cận, không bị che chắn — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`).
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"cuu-sinh","rule":"<ID dòng, vd PTK-CSN-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng → NA, ghi lý do. Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `cuu-sinh` (nếu có) và mục `chung`.
