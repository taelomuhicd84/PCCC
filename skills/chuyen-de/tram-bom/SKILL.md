# tram-bom — trạm bơm cấp nước chữa cháy (mẫu hệ thống B36, không phải mục của bảng công trình)
Trang: mọi trang của hạng mục phòng/trạm bơm PCCC (`trang <thư mục> --cd tram-bom`) + bản vẽ có tên trạm bơm / máy bơm.
Bảng tra: `rule_keys.json → file["tram-bom"]` — CHƯA có (mẫu B36 chưa chuẩn hoá) → mọi kết luận XM "chưa có mẫu B36".

1. Khi nào dùng: hồ sơ có phòng/trạm bơm chữa cháy (hạng mục riêng hoặc phòng trong nhà).
2. Cần từ JSON (`project_facts.json` / `extraction.json`): hạng mục phòng bơm (diện tích, bậc chịu lửa, vị trí so với nhà chính,
   lối ra), số và loại máy bơm (chính, dự phòng, bù áp), nguồn điện / động cơ diesel, bể nước (dung tích), đường ống hút/đẩy.
   - Thiếu trường → dòng XM kèm tên trường thiếu + trang nên đọc bổ sung.
   - Chỉ dùng ô độ tin cậy H/M; ô L → kết luận tối đa XM.
3. Nạp bảng: file B36 khi đã chuẩn hoá (cùng quy trình `docx_to_md.py` → bảng .md). Không mở lại bản vẽ.
4. Cách kiểm — cột "Quy định" của mẫu B36 là căn cứ DUY NHẤT (không lấy điều khoản QCVN 02:2020/BCA từ trí nhớ):
   - Script / so số: số bơm dự phòng, dung tích bể so lưu lượng × thời gian chữa cháy (khi bảng có số).
   - Cần phán đoán: phòng bơm có ngăn cháy, lối ra trực tiếp ra ngoài; bơm có nguồn ưu tiên — chỉ xem ảnh cắt vùng (≤ 3 ảnh).
5. Đầu ra: mỗi dòng bảng tra = 1 dòng `findings.jsonl` với `"cd":"tram-bom"`, `"rule":"<ID dòng B36>"`; chưa có bảng → 1 dòng XM
   `"rule":"tram-bom"`, `"ly_do":"chưa có mẫu B36"`. Ghi xong chạy `python -m pccc_checker findings --check <findings.jsonl>`.
6. Lỗi hay gặp: `memory/lessons.md` mục `tram-bom` (nếu có) và mục `chung`.
