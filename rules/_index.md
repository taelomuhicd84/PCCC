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
| cua-hang-xang-dau | B19 | chung | XD | — | cửa hàng xăng, trạm xăng, cây xăng |
| kho-xang-dau | B20 | chung | KXD | — | kho xăng, kho dầu, kho nhiên liệu |
| cua-hang-khi-dot | B21 | chung | KD | — | cửa hàng (kinh doanh) khí / gas / LPG |
| duong-ong-khi | B22 | chung | OK | — | đường ống (dẫn/cấp) khí |
| tram-chiet-lpg | B23 | chung | TC | — | san chiết, chiết nạp |
| kho-lpg | B24 | chung | LPG | — | kho (chứa) LPG, bồn LPG |
| kho-lng | B25 | chung | LNG | — | kho (chứa) LNG, khí thiên nhiên hóa lỏng |
| kho-vlncn | B26 | chung | VLN | — | (kho chứa) vật liệu nổ, thuốc nổ |
| dien-gio | B27 | chung | DG | — | điện gió, tua bin gió |
| dien-mat-troi | B28 | chung | MT | — | điện mặt trời, quang điện, solar |
| tram-bien-ap | B29 | chung | TBA | — | trạm biến áp, TBA, trạm điện |
| ham-duong-bo | B30 | chung | HAM | — | hầm đường bộ, hầm giao thông |
| tau-bien | B31 | chung | TAU | — | tàu biển |
| ptt-hang-nguy-hiem | B32 | chung | PTH | — | tàu / sà lan … chở hàng nguy hiểm, xăng, dầu |
| ptt-cho-khach | B33 | chung | PTK | — | tàu / ca nô / du thuyền … chở khách |
| (riêng) tram-bom | B36 | — | HT36 | — | phòng bơm, trạm bơm → skill `tram-bom` + mẫu B36 |

## Mẫu hệ thống → nạp KÈM chuyên đề (`rules/checklists/he-thong/<mẫu>/`, khai báo `HE_THONG` trong `loai_hinh.py`)
Không phải loại công trình: là bảng chi tiết mà dòng "Thực hiện theo bảng đối chiếu B3x" của bảng công trình dẫn tới.
`rule_keys.file[<chuyên đề>]` = file mục của bảng công trình + các phần của mẫu. Mục 1 mỗi mẫu = đối tượng trang bị.
| Mẫu | Chuyên đề | Mã ID | Nội dung |
|---|---|---|---|
| B34 | chong-tu-khoi | HT34 | hút xả khói, cấp không khí (tăng áp) khi có cháy |
| B35 | bao-chay | HT35 | đối tượng trang bị, yêu cầu chung báo cháy tự động |
| B36 | tram-bom | HT36 | nhà/phòng trạm bơm, bơm, bơm bù áp, động cơ, tủ điều khiển, nguồn điện |
| B37 | chua-chay | HT37 | cấp nước chữa cháy ngoài nhà (lưu lượng, thời gian, trụ nước, bể) |
| B38 | chua-chay | HT38 | họng nước chữa cháy trong nhà (số tia, lưu lượng, đường ống, dự trữ) |
| B39 | chua-chay | HT39 | chữa cháy tự động bằng nước, bọt (sprinkler, drencher) |
| B40 | chua-chay | HT40 | chữa cháy bằng bọt cố định |
| B41 | chua-chay | HT41 | chữa cháy bằng khí hóa lỏng (FM200, Novec 1230) |
| B42 | chua-chay | HT42 | chữa cháy bằng khí nén |
| B43 | chua-chay | HT43 | chữa cháy tự động bằng khí CO2 |
| B44 | chua-chay | HT44 | chữa cháy bằng sol-khí |
| B45 | binh-chua-chay · co-gioi · pha-do-bao-ho | HT45 | phương tiện chữa cháy ban đầu (tách 3 chuyên đề theo mục) |
| B46 | chieu-sang-su-co | HT46 | chiếu sáng sự cố, chỉ dẫn thoát nạn, loa thông báo |
| B47 | an-toan-cong-nghe | HT47 | cấp khí đốt trung tâm — LUÔN nạp (không bảng công trình nào dẫn tới), mục 1 quyết định NA |
| B48 | cap-dien | HT48 | nguồn điện cho hệ thống PCCC |
| B49 | chong-set | HT49 | hệ thống chống sét |
| B50 | thang-may-chua-chay | HT50 | thang máy chữa cháy |
Mỗi mẫu: đọc phần 1 (đối tượng / yêu cầu trang bị) trước; không thuộc diện → cả mẫu NA, không đọc tiếp.
Từ khoá cụ thể thắng từ khoá chung: "kho xăng dầu" → kho-xang-dau, không phải kho (B18).
Chiều cao PCCC > dải cao nhất (150 m) → ngoài phạm vi: dừng, báo người dùng.
Thêm loại hình: 1 dòng `LOAI` trong `loai_hinh.py` → `docx_to_md.py` + `split_rules.py <md> rules/checklists <mẫu>`. Skill không sửa.
## Chuyên đề = mục lớn của bảng đối chiếu → file `NN-<slug>[.<phần>].md` (trong thư mục bộ đã chọn)
1 mục bảng = 1 skill `skills/chuyen-de/<slug>/SKILL.md` = 1 file (mục dài tách phần .1 .2 …, nạp từng phần).
Nhận mục theo TÊN (số thứ tự lệch giữa các bảng); khai báo duy nhất: `src/pccc_checker/pipeline/chuyen_de.py`.
01 quy-mo · 02 bac-chiu-lua · 03 khoang-cach · 04 giao-thong-xe-chua-chay (gồm lối vào từ trên cao) ·
05 bo-tri-cong-nang · 06 ngan-chay · 07 thoat-nan · 08 gian-lanh-nan (chỉ bảng > 50 m) · 09 thang-may-chua-chay ·
10 chong-tu-khoi · 11 binh-chua-chay · 12 bao-chay · 13 chua-chay · 14 cap-dien · 15 chieu-sang-su-co ·
16 pha-do-bao-ho · 17 chong-set · 18 lien-lac · 19 tram-bom (mẫu B36, hạng mục phòng bơm) ·
20 co-gioi (B17, B18, B20, B24) · 21 bien-quang-cao (B14, B15) · 22 an-toan-cong-nghe (công trình đặc thù B19–B25) · 23 cuu-sinh (phương tiện thủy B31–B33). Bảng có mục nào thì thư mục bộ có file mục đó.

## Luật chạy bằng số (0 token)
`qcvn06_2022_sd01_2023.yaml` — rule engine (`check`). ID YAML cũng là "bảng tra" hợp lệ cho findings.jsonl.

## Phiên bản quy chuẩn đang áp dụng
QCVN 06:2022/BXD (TT 06/2022/TT-BXD, hiệu lực 16/01/2023) + Sửa đổi 1:2023 (TT 09/2023/TT-BXD, hiệu lực 01/12/2023).
Nguyên văn: `docs/regulations/QCVN 06 SỬA ĐỔI BỔ SUNG 10.2023.(pdf|docx)` (bản hợp nhất).

## Còn thiếu (gặp điều khoản cần số mà chưa có bảng → XM)
Bảng số QCVN 06: 1–5, A.1–A.3, E.1/E.3/E.4, G.9, H.2, B.1, B.6; QCVN 13:2018; TCVN 6396-72:2010; TCVN 3890:2023.
Mẫu hệ thống: đã đủ B34–B50. Bảng quy hoạch / chấp thuận địa điểm / hạ tầng (B1–B3) chưa nạp.
