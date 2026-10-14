# rules/_index.md — mục lục bảng tra (LUÔN NẠP, < 1k token)

Khóa tra lấy từ `rule_keys.json` (lệnh `keys`). Mỗi skill chuyên đề nạp ĐÚNG file theo khóa, không nạp cả quy chuẩn.
Không có trong bảng → trạng thái **XM** ("Cần xác minh"), KHÔNG lấy điều khoản từ trí nhớ mô hình.

luon_nap → qcvn06/00-dinh-nghia.md (số tầng, chiều cao PCCC, khối tích, tầng hầm…, Bảng 6 nhóm nhà)

## Loại hình → bộ bảng (chọn theo CÔNG NĂNG, khai báo duy nhất: `src/pccc_checker/pipeline/loai_hinh.py`)
Thứ tự chọn: overrides `loai_hinh` → từ khoá TÊN hạng mục → từ khoá CÔNG NĂNG → nhóm F (chỉ khi F ứng đúng 1 bảng).
Nhiều công năng / không chắc → `chua-xac-dinh` + ghi chú ứng viên (có thể là nhà hỗn hợp B5.x) — người dùng chốt, không đoán.
| Loại hình (thư mục) | Mẫu | Bộ theo chiều cao PCCC | Mã ID | Nhóm F chỉ bảng này | Từ khoá công năng (có dấu) |
|---|---|---|---|---|---|
| chung-cu | B4.1/4.2/4.3 | k1 ≤ 28 · k2 ≤ 75 · k3 ≤ 150 m | CC1–3 | F1.3 | chung cư, căn hộ |
| hon-hop | B5.1/5.2/5.3 | k1 ≤ 28 · k2 ≤ 50 · k3 ≤ 150 m | HH1–3 | — | hỗn hợp, đa năng |
| van-phong | B6.1/6.2/6.3 | k1 ≤ 28 · k2 ≤ 50 · k3 ≤ 150 m | VP1–3 | F4.3 | văn phòng, trụ sở, nhà làm việc |
| khach-san | B7.1/7.2/7.3 | k1 ≤ 28 · k2 ≤ 50 · k3 ≤ 150 m | KS1–3 | F1.2 | khách sạn, nhà nghỉ, nhà khách |
| nha-tre | B8 | chung | NT | — (F1.1 chung với bệnh viện) | nhà trẻ, mẫu giáo, mầm non |
| truong-hoc | B9 | chung | TH | F4.1 | tiểu học, THCS, THPT, phổ thông |
| benh-vien | B10 | chung | BV | — (F1.1) | bệnh viện, trung tâm y tế |
| cho | B11 | chung | CHO | — (F3.1 chung với TTTM) | chợ |
| tttm | B12 | chung | TM | — (F3.1) | trung tâm thương mại, TTTM, siêu thị |
| the-thao | B13 | chung | TT | — | sân vận động, nhà thi đấu, thể thao |
| rap-chieu-phim | B14 | chung | RAP | — | rạp chiếu phim, cinema |
| karaoke | B15 | chung | KR | — | karaoke, vũ trường, bar |
| gara | B16 | chung | GR | — | gara, nhà để xe |
| nha-xuong | B17 | chung | SX | F5.1 | nhà xưởng, sản xuất |
| kho | B18 | chung | KHO | F5.2 | nhà kho, kho |
| (riêng) tram-bom | B36 | — | — | — | phòng bơm, trạm bơm → skill `tram-bom` |
Chiều cao PCCC > dải cao nhất (150 m) → ngoài phạm vi: dừng, báo người dùng.
Thêm loại hình: 1 dòng `LOAI` trong `loai_hinh.py` → `docx_to_md.py` + `split_rules.py <md> rules/checklists <mẫu>`. Skill không sửa.
## Chuyên đề = mục lớn của bảng đối chiếu → file `NN-<slug>[.<phần>].md` (trong thư mục bộ đã chọn)
1 mục bảng = 1 skill `skills/chuyen-de/<slug>/SKILL.md` = 1 file (mục dài tách phần .1 .2 …, nạp từng phần).
Nhận mục theo TÊN (số thứ tự lệch giữa các bảng); khai báo duy nhất: `src/pccc_checker/pipeline/chuyen_de.py`.
01 quy-mo · 02 bac-chiu-lua · 03 khoang-cach · 04 giao-thong-xe-chua-chay (gồm lối vào từ trên cao) ·
05 bo-tri-cong-nang · 06 ngan-chay · 07 thoat-nan · 08 gian-lanh-nan (chỉ bảng > 50 m) · 09 thang-may-chua-chay ·
10 chong-tu-khoi · 11 binh-chua-chay · 12 bao-chay · 13 chua-chay · 14 cap-dien · 15 chieu-sang-su-co ·
16 pha-do-bao-ho · 17 chong-set · 18 lien-lac · 19 tram-bom (mẫu B36, hạng mục phòng bơm) ·
20 co-gioi (chỉ B17, B18) · 21 bien-quang-cao (chỉ B14, B15). Bảng có mục nào thì thư mục bộ có file mục đó.

## Luật chạy bằng số (0 token)
`qcvn06_2022_sd01_2023.yaml` — rule engine (`check`). ID YAML cũng là "bảng tra" hợp lệ cho findings.jsonl.

## Phiên bản quy chuẩn đang áp dụng
QCVN 06:2022/BXD (TT 06/2022/TT-BXD, hiệu lực 16/01/2023) + Sửa đổi 1:2023 (TT 09/2023/TT-BXD, hiệu lực 01/12/2023).
Nguyên văn: `docs/regulations/QCVN 06 SỬA ĐỔI BỔ SUNG 10.2023.(pdf|docx)` (bản hợp nhất).

## Còn thiếu (gặp điều khoản cần số mà chưa có bảng → XM)
Bảng số QCVN 06: 1–5, A.1–A.3, E.1/E.3/E.4, G.9, H.2, B.1, B.6; QCVN 13:2018; TCVN 6396-72:2010; TCVN 3890:2023.
Mẫu hệ thống: B34, B35, B36–B44, B45, B46, B49, B50.
