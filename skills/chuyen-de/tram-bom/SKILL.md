# tram-bom — trạm bơm cấp nước chữa cháy (mẫu hệ thống B36, không phải mục của bảng công trình)
Trang: mọi trang của hạng mục phòng/trạm bơm PCCC (`trang <thư mục> --cd tram-bom`) + bản vẽ có tên trạm bơm / máy bơm.
Bảng tra: `rule_keys.json → file["tram-bom"]` = mục "Bơm cấp nước chữa cháy" của bảng công trình (nếu có) + mẫu
`rules/checklists/he-thong/B36/19-tram-bom.*.md` (phạm vi, nhà/phòng đặt trạm bơm, bơm chữa cháy, bơm bù áp, động cơ điện,
động cơ diesel, tủ điều khiển, phụ kiện, theo dõi mực nước, nguồn điện).

1. Khi nào dùng: hồ sơ có phòng/trạm bơm chữa cháy (hạng mục riêng — `rule_keys.loai_hinh = tram-bom` — hoặc phòng trong nhà).
2. Cần từ JSON (`project_facts.json` / `extraction.json`): hạng mục phòng bơm (diện tích, bậc chịu lửa, vị trí so với nhà chính,
   lối ra), số và loại máy bơm (chính, dự phòng, bù áp), lưu lượng / cột áp, nguồn điện / động cơ diesel, tủ điều khiển,
   bể nước (dung tích), đường ống hút/đẩy, thiết bị theo dõi mực nước.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung.
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: ĐÚNG các file trong `rule_keys.file["tram-bom"]`, từng phần một lượt. Không mở lại bản vẽ.
4. Cách kiểm — cột "Quy định" của bảng/mẫu B36 là căn cứ DUY NHẤT (không lấy điều khoản từ trí nhớ):
   - Script / so số: số bơm dự phòng, lưu lượng bơm so với lưu lượng chữa cháy yêu cầu, dung tích bể (khi bảng có số).
   - Cần phán đoán: phòng bơm có ngăn cháy, lối ra trực tiếp ra ngoài; bơm có nguồn ưu tiên — chỉ xem ảnh cắt vùng (≤ 3 ảnh).
5. Đầu ra: mỗi dòng bảng tra = 1 dòng `findings.jsonl`:
   `{"hm","tang","cd":"tram-bom","rule":"<ID dòng, vd HT36-TBOM-012>","yc","ht","tt":"D|KD|XM|NA","ly_do","truc","trang","bbox","conf","evid","dieu_khoan"}`
   - KD phải có trang + bbox (0–1) + evid (chữ nguyên văn trên bản vẽ) + điều khoản; thiếu → tự hạ XM.
   - Không áp dụng → NA, ghi lý do. Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `tram-bom` (nếu có) và mục `chung`.
