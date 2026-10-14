# rules/_index.md — mục lục bảng tra (LUÔN NẠP, < 1k token)

Khóa tra lấy từ `rule_keys.json` (lệnh `keys`). Mỗi skill chuyên đề nạp ĐÚNG file theo khóa, không nạp cả quy chuẩn.
Không có trong bảng → trạng thái **XM** ("Cần xác minh"), KHÔNG lấy điều khoản từ trí nhớ mô hình.

luon_nap → qcvn06/00-dinh-nghia.md (số tầng, chiều cao PCCC, khối tích, tầng hầm…, Bảng 6 nhóm nhà)

## Loại hình → bộ bảng
| Khóa | Bộ bảng | Trạng thái |
|---|---|---|
| loai_hinh=khach-san (F1.2), cao_pccc ≤ 28 m | checklists/khach-san/k1/ (mẫu B7.1) | có |
| loai_hinh=khach-san, 28 < cao_pccc ≤ 50 m | checklists/khach-san/k2/ (mẫu B7.2) | có |
| loai_hinh=khach-san, 50 < cao_pccc ≤ 150 m | checklists/khach-san/k3/ (mẫu B7.3, có gian lánh nạn) | có |
| cao_pccc > 150 m | — | ngoài phạm vi: dừng, báo người dùng |
| loai_hinh=nha-xuong (F5.1) / kho (F5.2) / van-phong (F4.3) / khác | chưa có | mọi chuyên đề XM, chỉ chạy luật YAML |

Thêm loại hình: thêm thư mục `checklists/<loại hình>/`, một dòng ở bảng trên và ở `LOAI_HINH`/`BO`
(`src/pccc_checker/pipeline/rule_keys.py`). Skill chuyên đề không phải sửa.

## Chuyên đề = mục lớn của bảng đối chiếu → file `NN-<slug>[.<phần>].md` (trong thư mục bộ đã chọn)
1 mục bảng = 1 skill `skills/chuyen-de/<slug>/SKILL.md` = 1 file (mục dài tách phần .1 .2 …, nạp từng phần).
Nhận mục theo TÊN (số thứ tự lệch giữa các bảng); khai báo duy nhất: `src/pccc_checker/pipeline/chuyen_de.py`.
01 quy-mo · 02 bac-chiu-lua · 03 khoang-cach · 04 giao-thong-xe-chua-chay (gồm lối vào từ trên cao) ·
05 bo-tri-cong-nang · 06 ngan-chay · 07 thoat-nan · 08 gian-lanh-nan (chỉ bảng > 50 m) · 09 thang-may-chua-chay ·
10 chong-tu-khoi · 11 binh-chua-chay · 12 bao-chay · 13 chua-chay · 14 cap-dien · 15 chieu-sang-su-co ·
16 pha-do-bao-ho · 17 chong-set · 18 lien-lac

## Luật chạy bằng số (0 token)
`qcvn06_2022_sd01_2023.yaml` — rule engine (`check`). ID YAML cũng là "bảng tra" hợp lệ cho findings.jsonl.

## Phiên bản quy chuẩn đang áp dụng
QCVN 06:2022/BXD (TT 06/2022/TT-BXD, hiệu lực 16/01/2023) + Sửa đổi 1:2023 (TT 09/2023/TT-BXD, hiệu lực 01/12/2023).
Nguyên văn: `docs/regulations/QCVN 06 SỬA ĐỔI BỔ SUNG 10.2023.(pdf|docx)` (bản hợp nhất).

## Còn thiếu (gặp điều khoản cần số mà chưa có bảng → XM)
Bảng số QCVN 06: 1–5, A.1–A.3, E.1/E.3/E.4, G.9, H.2, B.1, B.6; QCVN 13:2018; TCVN 6396-72:2010; TCVN 3890:2023.
Mẫu hệ thống: B34, B35, B36–B44, B45, B46, B49, B50.
