# Chỉ mục bảng đối chiếu (checklist) — 25 loại hình B4.1–B28 (bảng chọn loại hình: `rules/_index.md`)

> Mục lục luôn nạp là `rules/_index.md`; file chọn tự động theo hạng mục nằm trong `rule_keys.json` (lệnh `keys`).
> File này là bản chi tiết cho người soát.

33 bảng đối chiếu mẫu (B4.1–B28; B20, B26 là .doc — chuyển .docx bằng Word trước) chuẩn hoá thành .md trong `<loại hình>/<bộ>/`, mỗi dòng 1 ID bền vững (vd `KS2-TN-012`, `BV-TN-003`); `<loại hình>/src_map.json` ID → dòng Word gốc, `_report.txt` cảnh báo khi tách (vd B9 thiếu dòng tiêu đề mục 7), cột Quy định chép nguyên văn
từ bảng Word (nguồn: thư mục 123, đã kiểm 208/206/257 dòng nguồn có đúng 1 lần). Đây là danh mục PHỦ ĐỦ để reviewer
không bỏ sót chuyên đề; luật tự chạy bằng số vẫn nằm ở `rules/qcvn06_2022_sd01_2023.yaml`. Dựng lại khi bảng Word đổi:
`scripts/checklists/docx_to_md.py` rồi `split_rules.py` (cần `pip install python-docx`).

## 1. Chọn bộ bảng theo loại hình và chiều cao
loai_hinh=khach-san, chọn theo **chiều cao PCCC của hạng mục** (Đ 1.4.9, không phải chiều cao đến đỉnh mái):
- cao_pccc ≤ 28 m → `khach-san/k1/` (mẫu B7.1)
- 28 m < cao_pccc ≤ 50 m → `khach-san/k2/` (mẫu B7.2)
- 50 m < cao_pccc ≤ 150 m → `khach-san/k3/` (mẫu B7.3)
- cao_pccc > 150 m → NGOÀI PHẠM VI: dừng và báo người dùng
Hạng mục có nhiều chiều cao PCCC: dùng giá trị lớn nhất để chọn bộ, ghi rõ trong findings.

## 2. Chuyên đề = mục lớn của bảng (1 mục = 1 skill = 1 file)
Số thứ tự mục trong bảng gốc lệch nhau (bảng > 50 m chèn "Gian lánh nạn" ở mục 8) → file đặt số NN CỐ ĐỊNH theo
danh mục chung, cột `muc:` trong front matter ghi số mục của bảng gốc. Mục dài > 12k ký tự tách `.1 .2 …` theo tiểu mục.
| NN | Skill chuyên đề | Mục bảng (B7.2) | Mẫu hệ thống dẫn chiếu |
|---|---|---|---|
| 01 | quy-mo | 1 Xác định chiều cao PCCC, số tầng, nhóm nhà… | |
| 02 | bac-chiu-lua | 2 Bậc chịu lửa | |
| 03 | khoang-cach | 3 Khoảng cách an toàn PCCC | |
| 04 | giao-thong-xe-chua-chay | 4 Đường giao thông (đường, bãi đỗ, lối vào từ trên cao) | |
| 05 | bo-tri-cong-nang | 5 Bố trí công năng | |
| 06 | ngan-chay | 6 Giải pháp ngăn cháy, chống cháy lan (2–3 phần) | |
| 07 | thoat-nan | 7 Lối, đường thoát nạn (3 phần: 7.1 / 7.2 / 7.3) | |
| 08 | gian-lanh-nan | (chỉ k3: mục 8) | |
| 09 | thang-may-chua-chay | 8 Thang máy chữa cháy | B50 |
| 10 | chong-tu-khoi | 9 Giải pháp chống tụ khói | B34 |
| 11 | binh-chua-chay | 10 Bình chữa cháy | B45 |
| 12 | bao-chay | 11 Hệ thống báo cháy | B35 |
| 13 | chua-chay | 12 Hệ thống chữa cháy | B36–B44 |
| 14 | cap-dien | 13 Giải pháp cấp điện | B48 |
| 15 | chieu-sang-su-co | 14 Chiếu sáng sự cố, chỉ dẫn, loa | B46 |
| 16 | pha-do-bao-ho | 15 Dụng cụ phá dỡ, bảo hộ chống khói | |
| 17 | chong-set | 16 Phương án chống sét | B49 |
| 18 | lien-lac | 17 Hệ thống liên lạc | |
ID dòng: `<BỘ>-<mã mục>-NNN` (vd `K2-TN-012`); `src_map.json` ánh xạ ID → dòng R### của bảng Word gốc (để điền Word).

## 3. Luôn nạp kèm
`khach-san/_nguon.md` (danh mục văn bản) — chỉ nạp khi cần ghi nguồn vào file Word.

## 4. Còn thiếu (script chặn, trả XM nếu gặp điều khoản cần số mà chưa có bảng)
- Bảng số của QCVN 06:2022 + Sửa đổi 1:2023 được dẫn trong các dòng: Bảng 1–5 (bậc chịu lửa, cấp nguy hiểm kết cấu), A.1–A.3, E.1/E.3/E.4 (khoảng cách PCCC), G.9, H.2, B.1, B.6; QCVN 13:2018; TCVN 6396-72:2010; TCVN 3890:2023.
- Các mẫu hệ thống: B34, B35, B36–B44, B45, B46, B49, B50.
