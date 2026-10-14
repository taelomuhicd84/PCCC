# ngan-chay-hanh-lang-ong-vat-lieu
Ngăn cháy hành lang, ống kỹ thuật và vật liệu hoàn thiện. Bảng tra: `rule_keys.json → file["ngan-chay-hanh-lang-ong-vat-lieu"]` (vd `rules/checklists/khach-san/k2/…`).

1. Khi nào dùng: nhà có hành lang chung / giếng kỹ thuật. Loại hình chưa có bộ bảng (rule_keys.loai_hinh không có file) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (project_facts.json / extraction.json): chiều dài hành lang, giếng/ống kỹ thuật, vật liệu hoàn thiện (thuyết minh, bảng vật liệu)
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của chuyên đề: `rule_keys.trang_theo_chuyen_de["ngan-chay-hanh-lang-ong-vat-lieu"]` hoặc `trang <thư mục> --cd ngan-chay-hanh-lang-ong-vat-lieu`).
   - Chỉ dùng ô có độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét + `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa.
   Không mở lại bản vẽ, không nạp file chuyên đề khác.
4. Cách kiểm: hành lang > 60 m phải chia đoạn (script); Phụ lục B (B.1, B.6) chưa có → XM. Phần cần phán đoán: nhóm vật liệu hoàn thiện — chỉ xem ảnh cắt vùng (≤ 3 ảnh), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng tiêu đề mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"ngan-chay-hanh-lang-ong-vat-lieu","rule":"<ID dòng>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả, vd không có tầng hầm) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `ngan-chay-hanh-lang-ong-vat-lieu` (nếu có) và mục `chung`.
