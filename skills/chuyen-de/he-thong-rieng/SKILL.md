# he-thong-rieng
Báo cháy, chữa cháy tự động, họng nước, cấp nước, chiếu sáng sự cố, thang máy chữa cháy, cấp điện. Bảng tra: `rule_keys.json → file["he-thong-rieng"]` (vd `rules/checklists/khach-san/k2/…`).

1. Khi nào dùng: mọi hạng mục (mỗi hệ thống 1 file con). Loại hình chưa có bộ bảng (rule_keys.loai_hinh không có file) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (project_facts.json / extraction.json): nhom_nha, cao_pccc_m, khoi_tich_m3, dt_san_tong_m2; thuyết minh hệ thống, lưu lượng chữa cháy ngoài nhà
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của chuyên đề: `rule_keys.trang_theo_chuyen_de["he-thong-rieng"]` hoặc `trang <thư mục> --cd he-thong-rieng`).
   - Chỉ dùng ô có độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét + `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa.
   Không mở lại bản vẽ, không nạp file chuyên đề khác.
4. Cách kiểm: lưu lượng/khối tích so bảng (script); mẫu B35–B50 chưa có → XM. Phần cần phán đoán: hệ thống có trên bản vẽ hay chỉ trong thuyết minh — chỉ xem ảnh cắt vùng (≤ 3 ảnh), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng tiêu đề mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"he-thong-rieng","rule":"<ID dòng>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả, vd không có tầng hầm) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `he-thong-rieng` (nếu có) và mục `chung`.
