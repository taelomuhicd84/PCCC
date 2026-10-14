# chua-chay — mục 13 bảng đối chiếu: Hệ thống chữa cháy
Tiểu mục: đối tượng trang bị chữa cháy tự động, họng nước chữa cháy trong nhà, cấp nước chữa cháy ngoài nhà, bể nước (trạm bơm / phòng bơm → skill `tram-bom`); nhà nhiều công năng.
Bảng tra: `rule_keys.json → file["chua-chay"]` (vd `rules/checklists/<loại hình>/<bộ>/13-chua-chay*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: mọi hạng mục (mỗi hệ thống 1 nhóm dòng; hệ thống không thuộc diện → NA). Loại hình chưa có bộ bảng (`rule_keys.file` không có `chua-chay`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): nhom_nha, cao_pccc_m, so_tang_noi, khoi_tich_m3, dt_san_tong_m2; thuyết minh/bản vẽ hệ thống: lưu lượng, số họng, dung tích bể.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["chua-chay"]` hoặc `trang <thư mục> --cd chua-chay`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: thuộc diện trang bị theo ngưỡng; lưu lượng/dung tích bể theo khối tích — so số trong cột Quy định.
   - Cần phán đoán: hệ thống có trên bản vẽ hay chỉ thuyết minh; nhà ≥ 2 công năng chọn yêu cầu theo công năng nào — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
   Dòng ghi "Thực hiện theo bảng đối chiếu B36–B44" → XM "chưa có mẫu B36–B44" cho tới khi mẫu được chuẩn hoá.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"chua-chay","rule":"<ID dòng, vd KS2-CC-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `chua-chay` (nếu có) và mục `chung`.
