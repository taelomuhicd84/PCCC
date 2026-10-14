# bien-quang-cao — mục bảng đối chiếu: Biển quảng cáo (có ở B14 rạp chiếu phim, B15 karaoke, vũ trường)
Tiểu mục: vị trí, vật liệu, kích thước biển quảng cáo / biển hiệu so với lối thoát nạn, lối vào từ trên cao, cửa sổ.
Bảng tra: `rule_keys.json → file["bien-quang-cao"]` (vd `rules/checklists/karaoke/chung/21-bien-quang-cao.md`).

1. Khi nào dùng: chỉ khi `rule_keys.file` có `bien-quang-cao`; không có file → không chạy, không ghi dòng.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): mặt đứng có biển quảng cáo/biển hiệu (vị trí, kích thước, vật liệu), lỗ cửa và lối vào từ trên cao bị che.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (mặt đứng: `trang <thư mục> --cd bien-quang-cao` hoặc `--cd giao-thong-xe-chua-chay`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét. Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ):
   - Script / so số: kích thước, khoảng cách (khi bảng có số).
   - Cần phán đoán: biển có che lối thoát nạn, cửa sổ, lối vào từ trên cao không; vật liệu biển — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`).
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"bien-quang-cao","rule":"<ID dòng, vd KR-QC-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng → NA, ghi lý do. Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `bien-quang-cao` (nếu có) và mục `chung`.
