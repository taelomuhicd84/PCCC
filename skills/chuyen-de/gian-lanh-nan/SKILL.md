# gian-lanh-nan — mục 8 bảng đối chiếu: Gian lánh nạn
Tiểu mục: vị trí, số lượng, diện tích, bao che, thông gió/tăng áp, trang bị của gian/tầng lánh nạn.
Bảng tra: `rule_keys.json → file["gian-lanh-nan"]` (vd `rules/checklists/khach-san/k2/08-gian-lanh-nan*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: chỉ khi `rule_keys.file` có `gian-lanh-nan` (bảng > 50 m); bộ không có file → không chạy, không ghi dòng. Loại hình chưa có bộ bảng (`rule_keys.file` không có `gian-lanh-nan`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): cao_pccc_m, so_tang_noi; tầng/gian lánh nạn: vị trí tầng, diện tích, số người phục vụ, kết cấu bao che.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["gian-lanh-nan"]` hoặc `trang <thư mục> --cd gian-lanh-nan`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: diện tích gian lánh nạn theo số người, khoảng cách tầng giữa các gian — so số trong cột Quy định.
   - Cần phán đoán: giải pháp bao che, lối vào gian lánh nạn từ buồng thang — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"gian-lanh-nan","rule":"<ID dòng, vd K2-GLN-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `gian-lanh-nan` (nếu có) và mục `chung`.
