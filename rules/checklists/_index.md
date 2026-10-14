# Chỉ mục bảng đối chiếu (checklist) — nạp khi review hồ sơ khách sạn (F1.2)

> Mục lục luôn nạp là `rules/_index.md`; file chọn tự động theo hạng mục nằm trong `rule_keys.json` (lệnh `keys`).
> File này là bản chi tiết cho người soát.

Bảng đối chiếu mẫu B7.1/7.2/7.3 chuẩn hoá thành .md, mỗi dòng 1 ID bền vững (vd `K2-TNL-012`), cột Quy định chép nguyên văn
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

## 2. Chuyên đề → file (trong thư mục bộ đã chọn)
| Skill chuyên đề | File |
|---|---|
| quy-mo | 01-thong-tin-quy-mo |
| bac-chiu-lua | 02-bac-chiu-lua |
| khoang-cach | 03-khoang-cach |
| duong-bai-do-xe | 04-duong-bai-do-xe |
| loi-vao-tren-cao | 05-loi-vao-tren-cao |
| bo-tri-cong-nang | 06-bo-tri-cong-nang |
| ngan-chay-ngang-doc | 07-ngan-chay-ngang-doc ; 10-ngan-chay-tuong-cua-vach-gara |
| ngan-chay-cong-nang | 08-ngan-chay-cong-nang |
| ngan-chay-hanh-lang-ong-vat-lieu | 09-ngan-chay-hanh-lang-ong-vat-lieu |
| thoat-nan | 11-thoat-nan-loi-thoat ; 12-thoat-nan-duong-thoat ; 13-thoat-nan-cau-thang |
| gian-lanh-nan | 14-gian-lanh-nan (chỉ có ở k3) |
| hut-khoi | 16-hut-khoi-tang-ap (tham chiếu mẫu B34) |
| he-thong-rieng | 15-thang-may-chua-chay (B50) ; 17-binh-chua-chay (B45) ; 18-bao-chay (B35) ; 19-chua-chay (B36–B44) ; 20-dien-chieu-sang-su-co-khac (B46, B49…) |

## 3. Luôn nạp kèm
`khach-san/_nguon.md` (danh mục văn bản) — chỉ nạp khi cần ghi nguồn vào file Word.

## 4. Còn thiếu (script chặn, trả XM nếu gặp điều khoản cần số mà chưa có bảng)
- Bảng số của QCVN 06:2022 + Sửa đổi 1:2023 được dẫn trong các dòng: Bảng 1–5 (bậc chịu lửa, cấp nguy hiểm kết cấu), A.1–A.3, E.1/E.3/E.4 (khoảng cách PCCC), G.9, H.2, B.1, B.6; QCVN 13:2018; TCVN 6396-72:2010; TCVN 3890:2023.
- Các mẫu hệ thống: B34, B35, B36–B44, B45, B46, B49, B50.
