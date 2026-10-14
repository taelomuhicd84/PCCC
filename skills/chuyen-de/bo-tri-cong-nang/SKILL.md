# bo-tri-cong-nang — mục 5 bảng đối chiếu: Bố trí công năng
Tiểu mục: 5.1 công năng trong tầng hầm, nửa hầm; 5.2 tầng nổi (Bảng H.2); gara ô tô (QCVN 13); phòng trực điều khiển chống cháy (Đ 6.17).
Bảng tra: `rule_keys.json → file["bo-tri-cong-nang"]` (vd `rules/checklists/<loại hình>/<bộ>/05-bo-tri-cong-nang*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: mọi hạng mục. Loại hình chưa có bộ bảng (`rule_keys.file` không có `bo-tri-cong-nang`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): cong_nang từng tầng / khu vực (`meta.khu_vuc`), so_tang_ham, so_tang_noi, cao_pccc_m; vị trí phòng trực điều khiển chống cháy, gara.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["bo-tri-cong-nang"]` hoặc `trang <thư mục> --cd bo-tri-cong-nang`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: số tầng nổi ≤ số tầng cho phép của Bảng H.2 (khi bảng có số); công năng cấm ở hầm có nằm ở hầm không (so tên phòng).
   - Cần phán đoán: công năng có được bố trí ở tầng đó không; có cần phòng trực điều khiển (theo số tầng, số tầng hầm, tập trung đông người) — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"bo-tri-cong-nang","rule":"<ID dòng, vd KS2-CN-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `bo-tri-cong-nang` (nếu có) và mục `chung`.
