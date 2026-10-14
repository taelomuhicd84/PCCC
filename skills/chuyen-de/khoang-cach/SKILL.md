# khoang-cach — mục 3 bảng đối chiếu: Khoảng cách an toàn PCCC
Tiểu mục: khoảng cách giữa các công trình (Bảng E.1, Đ 4.34 SĐ1); khu đất trống bên cạnh — theo ranh giới (E.3, E.4).
Bảng tra: `rule_keys.json → file["khoang-cach"]` (vd `rules/checklists/<loại hình>/<bộ>/03-khoang-cach*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: khu đất có ≥ 2 nhà hoặc nhà sát ranh giới. Loại hình chưa có bộ bảng (`rule_keys.file` không có `khoang-cach`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): bac_chiu_lua, cap_s, nhóm (nhà ở–công cộng / sản xuất–kho) của TỪNG nhà; khoảng cách ghi bằng số trên tổng mặt bằng; tỉ lệ tường ngoài không bảo vệ chống cháy (nếu xét E.3).
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["khoang-cach"]` hoặc `trang <thư mục> --cd khoang-cach`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: khoảng cách ghi ≥ ngưỡng tra từ bảng trong file (theo cặp bậc chịu lửa + cấp S).
   - Cần phán đoán: cặp nhà nào phải xét; tường ngăn cháy đặc cho phép giảm khoảng cách; công trình lân cận đã xác định hay chưa — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"khoang-cach","rule":"<ID dòng, vd KS2-KC-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `khoang-cach` (nếu có) và mục `chung`.
