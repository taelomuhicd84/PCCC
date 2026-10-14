# cap-dien — mục 14 bảng đối chiếu: Giải pháp cấp điện cho hệ thống PCCC
Tiểu mục: nguồn điện ưu tiên cho thiết bị PCCC, cáp/dây dẫn chống cháy, tủ điện PCCC, nguồn dự phòng.
Bảng tra: `rule_keys.json → file["cap-dien"]` (vd `rules/checklists/khach-san/k2/14-cap-dien*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: mọi hạng mục có thiết bị PCCC dùng điện. Loại hình chưa có bộ bảng (`rule_keys.file` không có `cap-dien`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): bản vẽ/thuyết minh hệ thống điện: sơ đồ nguyên lý, máy phát, tủ ưu tiên, loại cáp.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["cap-dien"]` hoặc `trang <thư mục> --cd cap-dien`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: không có số để so → kết luận theo có/không thể hiện.
   - Cần phán đoán: có 2 nguồn / nguồn dự phòng; cáp cấp cho thiết bị PCCC có chống cháy — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
   Dòng ghi "Thực hiện theo bảng đối chiếu B48" → XM "chưa có mẫu B48" cho tới khi mẫu được chuẩn hoá.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"cap-dien","rule":"<ID dòng, vd K2-DIEN-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `cap-dien` (nếu có) và mục `chung`.
