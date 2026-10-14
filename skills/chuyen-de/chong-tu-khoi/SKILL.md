# chong-tu-khoi — mục 10 bảng đối chiếu: Giải pháp chống tụ khói (hút khói, tăng áp)
Tiểu mục: 9.1 hệ thống tăng áp (yêu cầu trang bị: giếng thang máy, buồng thang không nhiễm khói, khoang đệm; yêu cầu kỹ thuật); 9.2 thoát khói (sảnh, hành lang, khoảng thông tầng, gian phòng; quạt hút khói, GHCL ống hút khói).
Bảng tra: `rule_keys.json → file["chong-tu-khoi"]` (vd `rules/checklists/<loại hình>/<bộ>/10-chong-tu-khoi*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: khi có đối tượng phải tăng áp/hút khói theo dòng bảng (buồng thang N2/N3, hành lang không thông gió tự nhiên, thông tầng, tầng hầm…). Loại hình chưa có bộ bảng (`rule_keys.file` không có `chong-tu-khoi`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): cao_pccc_m, so_tang_ham; loại buồng thang, hành lang (chiều dài, có cửa sổ mở), sảnh thông tầng, gian phòng không có cửa sổ; bản vẽ/thuyết minh hệ thống.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["chong-tu-khoi"]` hoặc `trang <thư mục> --cd chong-tu-khoi`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: phần lớn không kiểm bằng số được khi chưa có mẫu kỹ thuật → XM.
   - Cần phán đoán: đối tượng nào bắt buộc trang bị; hệ thống có thể hiện trên bản vẽ hay chỉ trong thuyết minh; GHCL ống hút khói — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
   Mẫu hệ thống B34 ĐÃ CÓ: `rules/checklists/he-thong/B34/*` nằm sẵn trong `rule_keys.file["chong-tu-khoi"]` (sau file bảng công trình).
   Dòng "Thực hiện theo B34" → đối chiếu từng dòng của mẫu; mục 1 của mẫu = đối tượng trang bị: không thuộc diện → cả mẫu NA.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"chong-tu-khoi","rule":"<ID dòng, vd KS2-KHOI-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `chong-tu-khoi` (nếu có) và mục `chung`.
