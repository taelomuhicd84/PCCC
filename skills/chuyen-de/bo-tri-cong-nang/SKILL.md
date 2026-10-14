# bo-tri-cong-nang
Bố trí công năng: gian F5 trong nhà F1–F4, tầng hầm, công năng nguy hiểm. Bảng tra: `rule_keys.json → file["bo-tri-cong-nang"]` (vd `rules/checklists/khach-san/k2/…`).

1. Khi nào dùng: mọi hạng mục. Loại hình chưa có bộ bảng (rule_keys.loai_hinh không có file) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (project_facts.json / extraction.json): nhom_nha, cong_nang từng tầng/khu vực (meta.khu_vuc), so_tang_ham
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của chuyên đề: `rule_keys.trang_theo_chuyen_de["bo-tri-cong-nang"]` hoặc `trang <thư mục> --cd bo-tri-cong-nang`).
   - Chỉ dùng ô có độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét + `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa.
   Không mở lại bản vẽ, không nạp file chuyên đề khác.
4. Cách kiểm: diện tích gian kho/bếp so ngưỡng 2.5.5.2 (script). Phần cần phán đoán: công năng có được bố trí ở tầng đó không — chỉ xem ảnh cắt vùng (≤ 3 ảnh), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng tiêu đề mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"bo-tri-cong-nang","rule":"<ID dòng>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả, vd không có tầng hầm) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `bo-tri-cong-nang` (nếu có) và mục `chung`.
