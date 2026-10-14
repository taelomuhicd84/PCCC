# co-gioi — mục bảng đối chiếu: Trang bị phương tiện chữa cháy cơ giới (có ở B17 nhà sản xuất, B18 nhà kho)
Tiểu mục: đối tượng phải trang bị, số lượng và chủng loại xe/phương tiện chữa cháy cơ giới, nơi để phương tiện.
Bảng tra: `rule_keys.json → file["co-gioi"]` (vd `rules/checklists/nha-xuong/chung/20-co-gioi.md`).

1. Khi nào dùng: chỉ khi `rule_keys.file` có `co-gioi` (bảng của loại hình có mục này); không có file → không chạy, không ghi dòng.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): nhom_nha, hang_no, khoi_tich_m3, dt_khu_dat_m2; thuyết minh/bản vẽ trang bị: số xe, loại xe, nhà để xe chữa cháy.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (`trang <thư mục> --cd co-gioi`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét. Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: thuộc diện trang bị theo ngưỡng (khi bảng có số); số lượng phương tiện.
   - Cần phán đoán: phương tiện có thể hiện trong hồ sơ hay chỉ ghi chung — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`).
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"co-gioi","rule":"<ID dòng, vd SX-CG-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng → NA, ghi lý do. Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `co-gioi` (nếu có) và mục `chung`.
