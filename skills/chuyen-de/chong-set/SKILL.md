# chong-set — mục 17 bảng đối chiếu: Phương án chống sét
Tiểu mục: phương án chống sét cho công trình.
Bảng tra: `rule_keys.json → file["chong-set"]` (vd `rules/checklists/<loại hình>/<bộ>/17-chong-set*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: mọi hạng mục. Loại hình chưa có bộ bảng (`rule_keys.file` không có `chong-set`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): bản vẽ/thuyết minh chống sét: kim thu sét, dây dẫn, tiếp địa.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["chong-set"]` hoặc `trang <thư mục> --cd chong-set`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: không có số để so → kết luận theo có/không thể hiện.
   - Cần phán đoán: phương án có trong hồ sơ hay không — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
   Mẫu hệ thống B49 ĐÃ CÓ: `rules/checklists/he-thong/B49/*` nằm sẵn trong `rule_keys.file["chong-set"]` (sau file bảng công trình).
   Đọc phần 1 của mẫu (đối tượng / yêu cầu trang bị) trước: không thuộc diện → cả mẫu NA, không đọc tiếp.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"chong-set","rule":"<ID dòng, vd KS2-SET-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `chong-set` (nếu có) và mục `chung`.
