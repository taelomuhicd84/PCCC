# bac-chiu-lua — mục 2 bảng đối chiếu: Bậc chịu lửa
Tiểu mục: giới hạn chịu lửa từng cấu kiện theo bậc (Bảng 2, Bảng 4, A.1, Phụ lục H; cấu kiện bọc chống cháy cần thuyết minh tính toán).
Bảng tra: `rule_keys.json → file["bac-chiu-lua"]` (vd `rules/checklists/<loại hình>/<bộ>/02-bac-chiu-lua*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: mọi hạng mục. Loại hình chưa có bộ bảng (`rule_keys.file` không có `bac-chiu-lua`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): bac_chiu_lua{ban_ve,tinh}, cap_s, so_tang_noi, cao_pccc_m; bảng cấu kiện / GHCL (R, REI, EI) của cột, dầm, sàn, tường buồng thang, bản thang, tường ngoài không chịu lực (thường là bảng ảnh hoặc thuyết minh).
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["bac-chiu-lua"]` hoặc `trang <thư mục> --cd bac-chiu-lua`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: GHCL ghi trên bản vẽ ≥ GHCL yêu cầu của bậc (khi bảng tra/Bảng 4 có số).
   - Cần phán đoán: vật liệu thực tế (thép không bọc, tôn) có đạt GHCL ghi không; bậc chịu lửa có phù hợp số tầng/chiều cao (Phụ lục H) — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"bac-chiu-lua","rule":"<ID dòng, vd KS2-BCL-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `bac-chiu-lua` (nếu có) và mục `chung`.
