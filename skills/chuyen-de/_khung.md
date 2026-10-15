# Khung chung mọi skill chuyên đề (đọc 1 lần / lượt đối chiếu)
0. Chỉ chạy chuyên đề có trong `rule_keys.file` của hạng mục (đã qua cổng đánh giá công năng (`knowled`/danh-gia-cong-nang): ap_dung = true).
   Không có → không chạy, không ghi dòng (NA đã ghi ở `rule_keys.khong_ap_dung`; `cho_danh_gia` → chạy đánh giá trước).
1. Nạp ĐÚNG các file trong `rule_keys.file[<cd>]`, từng phần một lượt (bảng công trình trước, mẫu `he-thong/` sau).
   Không mở lại bản vẽ, không nạp file chuyên đề khác. Cột "Quy định" là căn cứ DUY NHẤT; dẫn tới bảng/QC chưa có → XM.
2. Dữ liệu: `project_facts.json` / `extraction.json`. Chỉ ô H/M được kết luận; ô L → tối đa XM. Thiếu → XM + tên trường
   + trang nên đọc (`rule_keys.trang_theo_chuyen_de[<cd>]`). Cần nhìn → ảnh cắt vùng `crops` (≤ 3), không cả trang.
3. Mỗi dòng bảng có nội dung kiểm (bỏ dòng tiêu đề) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd","rule":"<ID dòng>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   KD bắt buộc trang + bbox (0–1) + evid nguyên văn + điều khoản, thiếu → XM. Điều kiện kèm không thoả → NA + lý do.
4. Xong: `python -m pccc_checker findings --check <findings.jsonl>`. Lỗi hay gặp: `memory/lessons.md` mục `<cd>` + `chung`.
