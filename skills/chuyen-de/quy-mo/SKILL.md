# quy-mo — mục 1 bảng đối chiếu: Xác định chiều cao PCCC, số tầng, nhóm nhà, hạng nguy hiểm cháy nổ, cấp nguy hiểm cháy
Tiểu mục: đối tượng/phân cấp thẩm duyệt; số tầng và tầng hầm (Đ 1.4.50); chiều cao PCCC (Đ 1.4.9); nhóm nhà, nhà hỗn hợp (Đ 1.4.41); cấp nguy hiểm cháy kết cấu (Bảng 5).
Bảng tra: `rule_keys.json → file["quy-mo"]` (vd `rules/checklists/khach-san/k2/01-quy-mo*.md`; mục dài có nhiều phần `.1`, `.2`…).

1. Khi nào dùng: mọi hạng mục — chạy ĐẦU TIÊN: kết luận mục này quyết định bộ bảng (k1/k2/k3) và khóa tra của mọi mục sau. Loại hình chưa có bộ bảng (`rule_keys.file` không có `quy-mo`) → không chạy, ghi 1 dòng XM.
2. Cần từ JSON (`project_facts.json` / `extraction.json`): so_tang_noi, so_tang_ham, so_tang_nha, cao_pccc_m, cao_cong_trinh_m, dt_xay_dung_m2, dt_san_tong_m2, khoi_tich_m3, cong_nang, nhom_nha{ban_ve,tinh}, cap_s; `project_facts.kiem_tra`.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung (chỉ trang của mục: `rule_keys.trang_theo_chuyen_de["quy-mo"]` hoặc `trang <thư mục> --cd quy-mo`).
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG file trong `rule_keys.json` cho hạng mục đang xét, nhiều phần thì từng phần một lượt
   (+ `rules/qcvn06/00-dinh-nghia.md` khi cần định nghĩa). Không mở lại bản vẽ, không nạp file mục khác.
4. Cách kiểm — cột "Quy định" là căn cứ DUY NHẤT (ngưỡng lấy từ bảng, không từ trí nhớ; dẫn tới bảng số chưa có → XM ghi tên bảng):
   - Script / so số: lấy lại kết quả kiểm logic của `facts` (số tầng nhà ≥ số tầng nổi, cao PCCC ≤ cao công trình, tổng sàn ≥ diện tích XD); chiều cao PCCC nằm đúng khoảng của bộ bảng đang dùng.
   - Cần phán đoán: nhà một công năng hay nhà hỗn hợp (khách sạn có hội trường, nhà hàng, gara hầm → có thể phải dùng bộ nhà hỗn hợp — ghi XM, không tự đổi bộ); tầng kỹ thuật/tum/áp mái có tính số tầng; mái có người thường xuyên khi tính chiều cao PCCC — chỉ xem ảnh cắt vùng (≤ 3 ảnh, lệnh `crops`), không xem cả trang.
5. Đầu ra: mỗi dòng bảng tra có nội dung kiểm (bỏ dòng chỉ là tiêu đề tiểu mục) = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"quy-mo","rule":"<ID dòng, vd K2-QM-001>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng (điều kiện kèm không thoả) → NA, ghi lý do.
   Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `quy-mo` (nếu có) và mục `chung`.
