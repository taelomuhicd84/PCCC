# duong-bai-do-xe
Đường và bãi đỗ xe chữa cháy: bề rộng, vị trí, khoảng cách tới nhà. Bảng tra: `rule_keys.json → file["duong-bai-do-xe"]` (vd `rules/checklists/khach-san/k2/…`).

1. Khi nào dùng: mọi khu đất. Loại hình chưa có bộ bảng (rule_keys.loai_hinh không có file) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (project_facts.json / extraction.json): cao_pccc_m, dt_xay_dung_m2, khoi_tich_m3; bề rộng đường, chiều dài/rộng bãi đỗ, khoảng cách bãi tới nhà (tổng mặt bằng, bảng tính bãi đỗ)
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của chuyên đề: `rule_keys.trang_theo_chuyen_de["duong-bai-do-xe"]` hoặc `trang <thư mục> --cd duong-bai-do-xe`).
   - Chỉ dùng ô có độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét + `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa.
   Không mở lại bản vẽ, không nạp file chuyên đề khác.
4. Cách kiểm: bề rộng, chiều dài bãi đỗ so ngưỡng (script). Phần cần phán đoán: đường cụt, bãi quay xe, vật cản (cây, cổng) — xem ảnh — chỉ xem ảnh cắt vùng (≤ 3 ảnh), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng tiêu đề mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"duong-bai-do-xe","rule":"<ID dòng>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả, vd không có tầng hầm) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `duong-bai-do-xe` (nếu có) và mục `chung`.
