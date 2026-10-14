# lien-lac — mục 18 bảng đối chiếu: Hệ thống liên lạc
Tiểu mục: hệ thống liên lạc (điện thoại liên lạc trực tiếp với lực lượng PCCC, phòng trực).
Bảng tra: `rule_keys.json → file["lien-lac"]` (vd `rules/checklists/<loại hình>/<bộ>/18-lien-lac*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: mọi hạng mục. Loại hình chưa có bộ bảng (`rule_keys.file` không có `lien-lac`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): bản vẽ/thuyết minh: điện thoại tại phòng trực điều khiển chống cháy, hệ thống liên lạc nội bộ.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["lien-lac"]` hoặc `trang <thư mục> --cd lien-lac`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: không có số để so → kết luận theo có/không thể hiện.
   - Cần phán đoán: có thể hiện trong hồ sơ hay không — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"lien-lac","rule":"<ID dòng, vd KS2-LL-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `lien-lac` (nếu có) và mục `chung`.
