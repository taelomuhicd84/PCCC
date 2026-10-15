---
name: knowled
description: Kho KIẾN THỨC để Claude nạp và so sánh — tra/nạp/duyệt kiến thức (định nghĩa, nhóm nhà theo công năng, công văn hướng dẫn, kinh nghiệm, danh sách còn thiếu) và các module dựa trên kiến thức, trong đó có ĐÁNH GIÁ CÔNG NĂNG (cổng áp dụng chuyên đề). Dùng khi người dùng đưa tài liệu/giải thích để Claude học ("nạp kiến thức", "ghi nhớ quy định này"), khi cần tra một khái niệm trước khi so sánh/đối chiếu, hoặc khi hỏi "công trình này phải kiểm những gì", "cần trang bị hệ thống gì", "đánh giá/phán đoán công năng hạng mục", "nhà hỗn hợp hay không" (quy tắc 70 %, lệnh cong-nang) — gọi TRƯỚC khi gọi các skill chuyên đề.
---

# knowled — nạp kiến thức để so sánh

Một nơi duy nhất để Claude **tra đúng mục cần dùng** thay vì nạp cả tài liệu. Kho: `knowledge/<nhóm>/<id>.md` (nhóm: `cong-nang`,
`quy-chuan`, `huong-dan`, `kinh-nghiem`, `thieu`) + các file sẵn có khai báo ở `knowledge/_nguon.yaml` (định nghĩa QCVN, bài học…).

```powershell
$env:PYTHONPATH="src"
python -m pccc_checker knowled tim "nhà hàng tiệc cưới F3.2" [--nhom cong-nang] [--top 5]   # id + trạng thái + đoạn trích (rẻ)
python -m pccc_checker knowled doc <id> [<id>…]                                          # đọc đúng mục cần
python -m pccc_checker knowled them <file.md|.txt|.docx> --nhom quy-chuan --tieu-de "…" --tu-khoa "a, b" --nguon "…"   # nạp (chờ duyệt)
python -m pccc_checker knowled duyet <id>        # sau khi ĐỐI CHIẾU NGUYÊN VĂN hoặc người dùng xác nhận
python -m pccc_checker knowled ds                # sinh lại knowledge/_index.md
```

## Quy tắc
1. **Tra trước, đọc sau:** `tim` (rẻ) → `doc` đúng id. KHÔNG nạp cả `knowledge/` hay cả file nguồn vào ngữ cảnh.
2. **Trạng thái:** `verified` mới được dùng để kết luận. `cho_duyet` (mới nạp) chỉ để gợi ý → tối đa XM, không bao giờ KD.
   Người dùng chỉ nói miệng → ghi `cho_duyet`, nói rõ; có nguyên văn → đối chiếu rồi `duyet`.
3. **Nạp kiến thức mới:** không viết theo trí nhớ — chép từ tài liệu người dùng đưa (docx/pdf → `them`), ghi `nguon`. Không có tài liệu
   → ghi mục `thieu` (khoảng trống) thay vì bịa; mục `thieu` cho biết cần xin người dùng tài liệu gì.
4. **Không tìm thấy:** nói "kho chưa có", ghi vào nhóm `thieu` nếu ảnh hưởng kết luận; không lấy từ trí nhớ mô hình.
5. Điều khoản số liệu dùng để chạy luật → vẫn chép vào `rules/` qua `/add-rule` (regulation-curator); kho này là kiến thức để HIỂU
   và SO SÁNH, bảng tra `rules/checklists/**` là căn cứ đối chiếu từng dòng.

## Nạp bảng số từ file Word QCVN (mỗi bảng = 1 module, sửa riêng từng file)
`python scripts/knowled_import_qcvn.py "<file.docx>" [--chi 4,e1] [--ghi-de]` → `knowledge/quy-chuan/qcvn06-bang-<số>.md` (vd bang-4, bang-a1,
bang-e4a). Mặc định không ghi đè file đã sửa tay. Bảng ô gộp / nhiều khối vào `cho_duyet`; so với Word rồi `knowled duyet`. Dòng bảng tra
dẫn tới "Bảng N" có trong kho thì `goi` tự kèm nguyên văn bảng đó (xem `goi/*.bang.md`). Nạp quy chuẩn khác (QCVN 13, TCVN): `knowled them`
rồi tách bảng tương tự.

## Module (đọc file khi cần, không nạp sẵn)
- **`danh-gia-cong-nang.md`** — đánh giá công năng → loại hình / bảng đối chiếu, nhóm F, chuyên đề + mẫu hệ thống thuộc diện
  (CỔNG ÁP DỤNG của `doi-chieu`). Dùng kho kiến thức này làm căn cứ phân loại.
