# khoang-cach
Khoảng cách PCCC giữa các nhà và tới ranh giới lô đất. Bảng tra: `rule_keys.json → file["khoang-cach"]` (vd `rules/checklists/khach-san/k2/…`).

1. Khi nào dùng: khu đất có ≥ 2 nhà hoặc nhà sát ranh. Loại hình chưa có bộ bảng (rule_keys.loai_hinh không có file) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (project_facts.json / extraction.json): bac_chiu_lua, cap_s, nhom_nha của từng nhà; khoảng cách ghi bằng số trên tổng mặt bằng
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của chuyên đề: `rule_keys.trang_theo_chuyen_de["khoang-cach"]` hoặc `trang <thư mục> --cd khoang-cach`).
   - Chỉ dùng ô có độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét + `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa.
   Không mở lại bản vẽ, không nạp file chuyên đề khác.
4. Cách kiểm: so khoảng cách ghi với ngưỡng (script); Bảng E.1/E.3/E.4 chưa có → XM. Phần cần phán đoán: cặp nhà nào cần xét, tường ngăn cháy đặc làm giảm khoảng cách — chỉ xem ảnh cắt vùng (≤ 3 ảnh), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng tiêu đề mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"khoang-cach","rule":"<ID dòng>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả, vd không có tầng hầm) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `khoang-cach` (nếu có) và mục `chung`.
