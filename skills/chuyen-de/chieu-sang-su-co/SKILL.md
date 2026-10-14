# chieu-sang-su-co — mục 15 bảng đối chiếu: Đèn chiếu sáng sự cố, chỉ dẫn thoát nạn, loa thông báo
Tiểu mục: đèn chiếu sáng sự cố, đèn chỉ dẫn thoát nạn, hệ thống loa thông báo và hướng dẫn thoát nạn (TCVN 13456).
Bảng tra: `rule_keys.json → file["chieu-sang-su-co"]` (vd `rules/checklists/<loại hình>/<bộ>/15-chieu-sang-su-co*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: mọi hạng mục. Loại hình chưa có bộ bảng (`rule_keys.file` không có `chieu-sang-su-co`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): bản vẽ chiếu sáng sự cố/chỉ dẫn: vị trí đèn trên đường thoát nạn, buồng thang, lối ra; hệ thống loa.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["chieu-sang-su-co"]` hoặc `trang <thư mục> --cd chieu-sang-su-co`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: khoảng cách giữa các đèn chỉ dẫn (khi bảng có số).
   - Cần phán đoán: đèn chỉ dẫn đặt đủ ở lối ra, chỗ đổi hướng; có loa thông báo khi thuộc diện — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
   Dòng ghi "Thực hiện theo bảng đối chiếu B46" → XM "chưa có mẫu B46" cho tới khi mẫu được chuẩn hoá.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"chieu-sang-su-co","rule":"<ID dòng, vd KS2-CS-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `chieu-sang-su-co` (nếu có) và mục `chung`.
