# ngan-chay — mục 6 bảng đối chiếu: Giải pháp ngăn cháy, chống cháy lan
Tiểu mục: 6.1 ngăn cháy ngang (khoang cháy tầng hầm, tầng nổi); 6.2 theo chiều đứng (sàn, sảnh thông tầng, ngăn cháy lan phương đứng); 6.3 theo công năng; 6.4 hành lang; 6.5 ống kỹ thuật, cáp; 6.6 trần treo; 6.7 vật liệu hoàn thiện; 6.8 cơ cấu tự đóng; 6.9 kênh giếng kỹ thuật; 6.10 tường ngăn cháy; 6.11 thang máy; 6.12 khoang đệm thang máy hầm; 6.13 buồng rác; 6.14 cửa ngăn cháy; 6.15 vách ngăn cháy; 6.16 gara.
Bảng tra: `rule_keys.json → file["ngan-chay"]` (vd `rules/checklists/<loại hình>/<bộ>/06-ngan-chay*.md`; mục dài có nhiều phần `.1`, `.2`…).

Trang theo tiểu mục: phương NGANG (6.1, 6.3–6.16) ← mặt bằng tầng `trang_theo_chuyen_de["ngan-chay.ngang"]`; phương ĐỨNG (6.2) ← mặt đứng + mặt cắt `["ngan-chay.dung"]`. Mặt bằng không dùng kết luận phương đứng.

1. Khi nào dùng: mọi hạng mục; tiểu mục không có đối tượng (không có sảnh thông tầng, gara, buồng rác…) → NA kèm lý do. Loại hình chưa có bộ bảng (`rule_keys.file` không có `ngan-chay`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): dt khoang cháy từng tầng, dt_san_tong_m2, bac_chiu_lua, cap_s, nhom_nha từng khu; tường/sàn/vách/cửa ngăn cháy và EI/REI ghi trên bản vẽ; chiều dài hành lang; sảnh thông tầng; giếng kỹ thuật; vật liệu hoàn thiện (thuyết minh, bảng vật liệu).
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["ngan-chay"]` hoặc `trang <thư mục> --cd ngan-chay`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: diện tích khoang cháy ≤ ngưỡng; tổng diện tích lỗ cửa trên bộ phận ngăn cháy so với tỉ lệ cho phép; hành lang quá chiều dài phải chia đoạn; EI ghi ≥ EI yêu cầu.
   - Cần phán đoán: khu nào phải ngăn; dải tường đặc giữa các tầng; cửa có tự đóng; nhóm vật liệu hoàn thiện; giếng thông tầng — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"ngan-chay","rule":"<ID dòng, vd KS2-NC-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `ngan-chay` (nếu có) và mục `chung`.
