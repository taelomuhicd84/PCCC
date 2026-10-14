# binh-chua-chay — mục 11 bảng đối chiếu: Bình chữa cháy (phương tiện chữa cháy ban đầu)
Tiểu mục: yêu cầu trang bị bình chữa cháy xách tay, có bánh xe; lựa chọn, tính toán trang bị (loại nguy hiểm, công suất bình, khoảng cách di chuyển, diện tích bảo vệ).
Bảng tra: `rule_keys.json → file["binh-chua-chay"]` (vd `rules/checklists/khach-san/k2/11-binh-chua-chay*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: mọi hạng mục. Loại hình chưa có bộ bảng (`rule_keys.file` không có `binh-chua-chay`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): cong_nang từng khu (để xác định loại nguy hiểm); vị trí + loại bình trên mặt bằng PCCC.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["binh-chua-chay"]` hoặc `trang <thư mục> --cd binh-chua-chay`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: khoảng cách di chuyển tới bình, diện tích bảo vệ mỗi bình — so bảng trong file.
   - Cần phán đoán: loại nguy hiểm của khu; bình đặt đủ ở mọi khu vực — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
   Dòng ghi "Thực hiện theo bảng đối chiếu B45" → XM "chưa có mẫu B45" cho tới khi mẫu được chuẩn hoá.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"binh-chua-chay","rule":"<ID dòng, vd K2-BCC-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `binh-chua-chay` (nếu có) và mục `chung`.
