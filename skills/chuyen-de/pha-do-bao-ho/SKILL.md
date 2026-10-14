# pha-do-bao-ho — mục 16 bảng đối chiếu: Dụng cụ phá dỡ thông thường, phương tiện bảo hộ chống khói
Tiểu mục: dụng cụ phá dỡ thông thường, phương tiện bảo hộ chống khói / mặt nạ (TCVN 3890).
Bảng tra: `rule_keys.json → file["pha-do-bao-ho"]` (vd `rules/checklists/<loại hình>/<bộ>/16-pha-do-bao-ho*.md`; mục dài có nhiều phần `.1`, `.2`…).

Mẫu hệ thống nạp kèm: `rules/checklists/he-thong/B45/` (phần của mục này) — đọc mục yêu cầu trang bị trước; không thuộc diện → NA.

1. Khi nào dùng: mọi hạng mục. Loại hình chưa có bộ bảng (`rule_keys.file` không có `pha-do-bao-ho`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): thuyết minh/bản vẽ trang bị: số lượng, vị trí tủ dụng cụ, mặt nạ.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["pha-do-bao-ho"]` hoặc `trang <thư mục> --cd pha-do-bao-ho`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: số lượng theo đối tượng (khi bảng có số).
   - Cần phán đoán: có thể hiện trang bị trong hồ sơ hay không — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"pha-do-bao-ho","rule":"<ID dòng, vd KS2-PD-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `pha-do-bao-ho` (nếu có) và mục `chung`.
