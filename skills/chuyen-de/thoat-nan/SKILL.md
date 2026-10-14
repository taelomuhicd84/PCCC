# thoat-nan — mục 7 bảng đối chiếu: Lối, đường thoát nạn
Tiểu mục: 7.1 lối thoát nạn (yêu cầu chung tầng hầm/tầng 1/tầng trên; số lối ra gian phòng, từng tầng, từ nhà; bố trí phân tán; cửa thoát nạn — kiểu, chiều mở; chiều cao, chiều rộng lối ra; tầng kỹ thuật; khoảng cách tới lối ra gần nhất); 7.2 đường thoát nạn (đường không được coi là thoát nạn, chiều rộng, chiều cao, giật cấp); 7.3 cầu thang và buồng thang (bản thang, độ dốc, mặt bậc, chiều cao bậc, chiếu thang, khe hở, chiếu sáng; chủng loại thang loại 2, 3, L1, L2, N1–N3; lối lên mái).
Bảng tra: `rule_keys.json → file["thoat-nan"]` (vd `rules/checklists/khach-san/k2/07-thoat-nan*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: mọi hạng mục, xét TỪNG TẦNG. Loại hình chưa có bộ bảng (`rule_keys.file` không có `thoat-nan`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): nhom_nha, cao_pccc_m, so_tang_noi, so_tang_ham; `extraction.json` (cửa, thang, hành lang, kích thước); số người từng gian phòng / tầng (bảng tính thoát nạn); khoảng cách đường thoát nạn ghi trên mặt bằng.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["thoat-nan"]` hoặc `trang <thư mục> --cd thoat-nan`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: luật YAML engine đã kiểm phần cửa/lối ra (lấy qua `findings`, không kiểm lại); còn lại: số lối ra theo số người, chiều rộng/cao thông thủy, kích thước bậc, khoảng cách tới lối ra — so số trong cột Quy định.
   - Cần phán đoán: lối ra có thật là lối ra thoát nạn (qua sảnh thang máy, cửa cuốn/quay → không tính); loại buồng thang có đúng yêu cầu theo chiều cao; chiều mở cửa; hai lối ra có phân tán — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"thoat-nan","rule":"<ID dòng, vd K2-TN-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `thoat-nan` (nếu có) và mục `chung`.
