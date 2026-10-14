# quy-mo
Số tầng, chiều cao, diện tích khoang cháy tối đa theo nhóm nhà và bậc chịu lửa. Bảng tra: `rule_keys.json → file["quy-mo"]` (vd `rules/checklists/khach-san/k2/…`).

1. Khi nào dùng: mọi hạng mục. Loại hình chưa có bộ bảng (rule_keys.loai_hinh không có file) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (project_facts.json / extraction.json): so_tang_noi, so_tang_ham, so_tang_nha, cao_pccc_m, dt_xay_dung_m2, dt_san_tong_m2, khoi_tich_m3, nhom_nha, bac_chiu_lua, cap_s
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của chuyên đề: `rule_keys.trang_theo_chuyen_de["quy-mo"]` hoặc `trang <thư mục> --cd quy-mo`).
   - Chỉ dùng ô có độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét + `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa.
   Không mở lại bản vẽ, không nạp file chuyên đề khác.
4. Cách kiểm: số tầng / chiều cao / diện tích so ngưỡng bằng số (script); diện tích khoang cháy cần Bảng H.2 — chưa có → XM. Phần cần phán đoán: phân loại khoang cháy, tầng lửng/tum có tính vào số tầng không (1.4.50) — chỉ xem ảnh cắt vùng (≤ 3 ảnh), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng tiêu đề mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"quy-mo","rule":"<ID dòng>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả, vd không có tầng hầm) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `quy-mo` (nếu có) và mục `chung`.
