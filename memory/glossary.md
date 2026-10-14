# memory/glossary.md — L1 kiến thức chung (nạp theo skill)

## Thuật ngữ hệ thống
| Từ | Nghĩa |
|---|---|
| HM | hạng mục = một dòng của BẢNG THỐNG KÊ HẠNG MỤC CÔNG TRÌNH (HM01, HM02… theo thứ tự trong project_facts) |
| khu vực | phần bên trong 1 HM (khu văn phòng, khu xuất nhập hàng) — không thành HM riêng |
| ô dữ liệu | `[giá trị, trang, [x0,y0,x1,y1] 0–1, độ tin cậy]`; không đọc được → `[null, null, null, "L"]` |
| H / M / L | rõ (người dùng xác nhận, chữ vector, 2 nguồn độc lập khớp) / 2 nguồn hoặc lệch đã chọn / chỉ Gemini 1 trang |
| ban_ve / tinh | giá trị chữ ghi trên bản vẽ / giá trị skill 03 suy ra từ công năng (Bảng 6) |
| LAYER / HON-HOP / SCAN | trang chữ vector / vector + bảng dán ảnh / toàn ảnh |
| D / KD / XM / NA | Đạt / Không đạt (chữ đỏ) / Cần xác minh (nghiêng, cam) / không áp dụng (gạch ngang) |
| Cổng 1 / Cổng 2 | Claude duyệt dữ liệu đầu vào / duyệt kết luận (skill `cong-claude`) |
| k1 / k2 / k3 | bộ bảng khách sạn theo chiều cao PCCC ≤ 28 / ≤ 50 / ≤ 150 m (mẫu B7.1/7.2/7.3) |

## Quy ước tầng và trục
- Tầng: T1 (tầng 1/trệt), T2…, TL1 (lửng trên T1), H1, H2 (hầm), BH (bán hầm), Mai, Tum, KT (kỹ thuật).
- "Trục đứng" = hệ cao độ theo phương đứng (mặt cắt, mặt đứng) → `axes.json.cao_do`; "mặt bằng" = lưới trục → `truc_mat_bang`.
  (Người dùng đã xác nhận 14/10/2026.)
- Trục ghi theo hạng mục; cùng tên trục ở 2 HM là 2 trục khác nhau.

## Đơn vị
- Kích thước trên bản vẽ CAD: mm. Cao độ, chiều cao, khoảng cách trong JSON: m. Diện tích m², khối tích m³.
- Số thập phân bản vẽ Việt Nam dùng dấu phẩy ("16,75") hoặc dấu cách nghìn ("36 510"); bảng Excel có thể dùng dấu chấm.

## Công năng → nhóm nhà (gợi ý `tinh`, nguồn Bảng 6 — nguyên văn ở rules/qcvn06/00-dinh-nghia.md)
khách sạn, nhà nghỉ, ký túc xá → F1.2 · chung cư → F1.3 · karaoke, vũ trường, rạp → F2.1 · nhà hàng → F3.2 ·
siêu thị, TTTM, showroom → F3.1 · văn phòng, trụ sở, ngân hàng → F4.3 · nhà xưởng, sản xuất → F5.1 ·
nhà kho, ga ra không sửa chữa → F5.2. Mã: `NHOM_THEO_CONG_NANG` trong `src/pccc_checker/pipeline/facts.py`.

## Quy chuẩn đang áp dụng
QCVN 06:2022/BXD + Sửa đổi 1:2023 (hiệu lực 01/12/2023). Phiên bản ghi trong phần đầu mỗi bảng tra .md.
