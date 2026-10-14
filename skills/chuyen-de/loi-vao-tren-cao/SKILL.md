# loi-vao-tren-cao
Tiếp cận chữa cháy từ ngoài vào, lối vào trên cao. Bảng tra: `rule_keys.json → file["loi-vao-tren-cao"]` (vd `rules/checklists/khach-san/k2/…`).

1. Khi nào dùng: nhà có cao PCCC đủ lớn theo dòng bảng tra. Loại hình chưa có bộ bảng (rule_keys.loai_hinh không có file) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (project_facts.json / extraction.json): cao_pccc_m; vị trí, kích thước lỗ cửa tiếp cận trên mặt đứng; khoảng cách giữa các lối vào
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của chuyên đề: `rule_keys.trang_theo_chuyen_de["loi-vao-tren-cao"]` hoặc `trang <thư mục> --cd loi-vao-tren-cao`).
   - Chỉ dùng ô có độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét + `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa.
   Không mở lại bản vẽ, không nạp file chuyên đề khác.
4. Cách kiểm: kích thước lỗ cửa, khoảng cách (script). Phần cần phán đoán: lỗ cửa có bị che (lam, kính cố định) không — chỉ xem ảnh cắt vùng (≤ 3 ảnh), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng tiêu đề mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"loi-vao-tren-cao","rule":"<ID dòng>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả, vd không có tầng hầm) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `loi-vao-tren-cao` (nếu có) và mục `chung`.
