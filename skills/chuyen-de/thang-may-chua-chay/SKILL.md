# thang-may-chua-chay — mục 9 bảng đối chiếu: Thang máy chữa cháy
Tiểu mục: yêu cầu trang bị (theo chiều cao PCCC, phần ngầm, gara nhiều tầng hầm); yêu cầu kỹ thuật; vị trí, số lượng, bán kính phục vụ; giếng thang, sảnh (khoang đệm), họng chờ khô D65, kích thước cabin, tải trọng, tốc độ, nút điều khiển.
Bảng tra: `rule_keys.json → file["thang-may-chua-chay"]` (vd `rules/checklists/khach-san/k2/09-thang-may-chua-chay*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: khi dòng 'Yêu cầu trang bị' của bảng áp dụng cho hạng mục (chiều cao PCCC, độ sâu phần ngầm, số tầng hầm gara); không thuộc diện → toàn mục NA. Loại hình chưa có bộ bảng (`rule_keys.file` không có `thang-may-chua-chay`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): cao_pccc_m, so_tang_ham; số và vị trí thang máy chữa cháy, sảnh/khoang đệm và diện tích, khoảng cách cửa thang → điểm xa nhất mặt bằng tầng.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["thang-may-chua-chay"]` hoặc `trang <thư mục> --cd thang-may-chua-chay`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: bán kính phục vụ, diện tích sảnh, kích thước cabin, tải trọng — so số trong cột Quy định.
   - Cần phán đoán: thang có giếng riêng không; sảnh có là khoang đệm ngăn cháy; có họng chờ khô — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
   Dòng ghi "Thực hiện theo bảng đối chiếu B50" → XM "chưa có mẫu B50" cho tới khi mẫu được chuẩn hoá.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"thang-may-chua-chay","rule":"<ID dòng, vd K2-TMCC-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `thang-may-chua-chay` (nếu có) và mục `chung`.
