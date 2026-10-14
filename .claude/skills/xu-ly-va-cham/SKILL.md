---
name: xu-ly-va-cham
description: Xử lý va chạm trên bản vẽ PCCC — tìm chỗ cùng một thông số mà các trang/bảng ghi khác nhau (số tầng, diện tích, chiều cao, khối tích, bậc chịu lửa…), xác định trang + vị trí từng giá trị, ghi va_cham.json và ghi chú lên PDF. CHỈ gọi khi người dùng bảo chạy full quy trình (/check-pccc, bước 4b) hoặc yêu cầu rõ "note va chạm lên bản vẽ". KHÔNG gọi khi người dùng chỉ bảo đọc/hiểu bản vẽ hay xuất thông tin công trình.
---

# Xử lý va chạm

Va chạm = **bản vẽ tự mâu thuẫn**: cùng một thông số của cùng một hạng mục, 2 nơi trở lên ghi khác nhau.
Gemini đọc sai KHÔNG phải va chạm. Skill này không hỏi người dùng và không chọn giá trị đúng. Nó chỉ chỉ ra trang nào
cần ghi chú và ghi ở vị trí nào trên trang (yêu cầu người dùng 14/10/2026).

## Đầu vào (đã có sau khi chạy xong thông tin công trình)
`data/output/<hồ sơ>/`: `nghi_ngo.json` (mục `mau_thuan_tren_ban_ve`, Claude ghi ở Cổng 1), `project_info.json`
(trường `conflict`), `project_facts.json` (`kiem_tra`), `page_index.json`, `crops/`.

## Quy trình
```bash
PYTHONPATH=src python -m pccc_checker va-cham "data/output/<hồ sơ>" [--pdf "<pdf>"]     # 0 token
```
1. Script gộp 3 nguồn thành `va_cham.json` + `va_cham.md`, mỗi va chạm `VC-xxx`, mỗi giá trị một vị trí `VC-xxx.n`:
   - `ban_ve`: nghi_ngo.json, hoặc có ít nhất 2 giá trị lấy từ nguồn không phải Gemini.
   - `doc_lech`: có giá trị chỉ Gemini đọc.
   - `logic`: kiểm tra logic giữa 2 trường.
   - Các số lệch nhau ≤ 0,5% coi là làm tròn và tự bỏ.
2. Script định vị từng giá trị: tìm trong lớp chữ (`vector`); không thấy thì lấy khung cả bảng ảnh (`vung_anh`); vẫn không
   thấy thì ghi chú ở góc trang (`trang`). Số ngắn (< 3 ký tự, vd số tầng "2") không dò trong lớp chữ, vì trùng khắp trang.
3. **Claude** xử lý từng dòng script in ở mục "Claude cần chỉ vị trí":
   - `vung_anh`: mở đúng ảnh `crops/pNN_bangK.png` (chưa có thì chạy `crops <pdf> --pages N`), tìm ô chứa giá trị, ước
     bbox 0–1 **trong ảnh** (dòng × cột của bảng).
   - `vector?`: xem `so_cho`; chọn đúng chỗ (ảnh cắt vùng bbox) hoặc để nguyên.
   - `doc_lech`: xem ảnh bảng. Nếu Gemini đọc sai (ảnh ghi giống giá trị kia) → bỏ, ghi lý do. Nếu ảnh ghi khác thật thì giữ.
   - `logic`: giá trị gây lệch do Gemini lấy nhầm dòng → bỏ, ghi lý do và trỏ va chạm thật nếu có.
   - `trang` (SCAN, không có ảnh bảng): chỉ chỉ vị trí khi đã có ảnh cắt; không có thì để ghi chú góc trang.
   - Ghi các quyết định vào `va_cham_claude.json` (xem mẫu dưới). Mỗi lần xem tối đa 5 ảnh.
4. Chạy lại với `--annotate` → `<tên pdf>_va_cham.pdf` (khung cam mỗi vị trí, ghi chú nêu đủ các giá trị + nơi ghi)
   và **Word `Note phản hồi.docx`** cùng thư mục (yêu cầu người dùng 14/10/2026): tổng hợp MỌI vị trí đã ghi chú trên
   bản vẽ, xếp theo trang — mục 1 "Trang cần kiểm" (Tr.N: các mã note), mục 2 bảng Trang | Mã note | Loại | Hạng mục |
   Nội dung | Điều khoản | Vị trí. Có `findings.jsonl` thì gộp thêm dòng Không đạt (chữ đỏ) / Cần xác minh (nghiêng cam).
   Mã note trong Word = mã trên PDF (VC-xxx.n, PC-xxx) để kéo tới kiểm nhanh.
5. Kiểm chứng: render vùng vài khung (`get_pixmap(clip=…, annots=True)`) và xem khung có đúng ô không. Lệch thì sửa bbox
   rồi chạy lại.
6. Báo người dùng (ngắn): số va chạm, mỗi va chạm một dòng gồm hạng mục, thông số, các giá trị kèm trang; số va chạm đã
   bỏ và lý do; đường dẫn PDF + `Note phản hồi.docx`. KHÔNG đề xuất giá trị nào đúng.

## va_cham_claude.json
```json
[{"vt": "VC-001.2", "anh": 3, "bbox_trong_anh": [0.556, 0.279, 0.686, 0.32]},
 {"vt": "VC-005.1", "bbox": [0.10, 0.52, 0.30, 0.58]},
 {"vt": "VC-006.1", "trang": 12, "bbox": [0.4, 0.4, 0.5, 0.45]},
 {"id": "VC-007", "bo": true, "ly_do": "Gemini đọc lệch: ảnh bảng tr.60 ghi IV"}]
```
- `anh` = số K trong `pNN_bangK.png`, đánh số theo thứ tự `vung_anh` của trang trong page_index.json.
- `bbox` không có `anh` = 0–1 của trang đang hiển thị (đã xoay). Script tự đổi toạ độ cho trang xoay 90/270.

## Thêm va chạm Script không tự thấy
Ghi vào `nghi_ngo.json` → `mau_thuan_tren_ban_ve`, mỗi nguồn ghi kèm số trang ("BẢNG … tr.5"):
`{"hang_muc", "truong", "gia_tri": {"<bảng/ghi chú> tr.N": giá trị, ...}, "trang": [N, ...], "ghi_chu"}`. Sau đó chạy lại.

## Ví dụ: Luật Phú Trường (14/10/2026)
Tìm được 9 va chạm, bỏ 5, còn 4 va chạm thật, tất cả ở tr.5 và tr.127:
- Xưởng 01: số tầng 2 hay 1.
- Trạm bơm: diện tích 25 hay 16 m².
- Phòng máy phát: diện tích 25 hay 16 m².
- Xưởng 08: thuyết minh tr.127 ghi khác bảng tr.5.

5 va chạm bị bỏ:
- 1 do làm tròn 11,425 / 11,43.
- Nhà bảo vệ: 2 × 12 = 24 m², không mâu thuẫn.
- Bậc chịu lửa II là Gemini đọc lệch.
- 2 lỗi khối tích do Gemini lấy nhầm dòng Trạm điện.
