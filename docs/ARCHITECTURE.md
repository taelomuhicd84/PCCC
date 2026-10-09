# Kiến trúc PCCC Checker

## Luồng xử lý & phân vai agent

```
                       ┌──────────────── Claude Code (đầu não, /check-pccc) ────────────────┐
                       │  chỉ đọc tóm tắt ≤15 dòng từ subagent, không đọc ảnh bản vẽ          │
                       └───┬──────────────────┬──────────────────────┬──────────────────────┘
                           │ 1                │ 2 (Bash, 0 token)    │ 3                 │ 4
                 drawing-reader (haiku)   rule engine YAML   compliance-reviewer    pdf-annotator (haiku)
                           │                  │                (sonnet)                  │
PDF ─► render tile PNG ─► Gemini vision ─► extraction.json ─► findings.json ─► (review) ─► *_annotated.pdf
   └─► text vector (PyMuPDF) ──┘ (hybrid)      extraction.md     report.md                    drawing.dxf
```

| Thành phần | Vai trò | Chi phí |
|---|---|---|
| Gemini (`gemini-2.5-flash`) | Đọc ảnh bản vẽ → JSON có toạ độ | Rẻ; cache tại `data/cache/` |
| Vector extractor | Đọc text CAD trong PDF (kích thước, ký hiệu, khung tên) | 0 |
| Rule engine | Kiểm tra số liệu theo `rules/*.yaml` | 0 |
| compliance-reviewer | Lọc false-positive, bổ sung lỗi khó mã hoá | Token Claude, chỉ trên văn bản ngắn |
| drawing-reader / pdf-annotator | Chạy CLI, kiểm tra file | Haiku, rất ít |

## Định dạng dữ liệu

- `extraction.json`: `{source_pdf, extractor, building{...}, pages[{page,width,height,scale,sheet_title,elements[...]}]}`
  - element: `{id, type, page, bbox[x0,y0,x1,y1] (point PDF), label, attrs{...mét...}, confidence, source}`
- `findings.json`: list `{rule_id, clause, severity, message, page, bbox, element_ids, actual, required,
  verified_rule, reviewer_note, dismissed}` — reviewer chỉnh trực tiếp file này.
- `extraction.md`: bảng tóm tắt dùng cho LLM (rẻ token). `drawing.dxf`: layer `PCCC_*` (phần tử), `LOI_*` (lỗi).

## Mở rộng

| Muốn | Làm ở đâu |
|---|---|
| Thêm luật theo QCVN 06 | `rules/qcvn06_2022_sd01_2023.yaml` (hoặc `/add-rule`) |
| Thêm quy chuẩn mới (TCVN 3890 thiết bị PCCC, TCVN 5738 báo cháy…) | file mới `rules/<ten>.yaml` + khai báo `config/settings.yaml` |
| Check logic mới | `src/pccc_checker/rules/checks.py` với `@register("ten")` |
| Extractor mới (vd Claude vision, OCR, đọc DWG/DXF trực tiếp) | kế thừa `extractors/base.py::Extractor`, đăng ký trong `extractors/__init__.py` |
| Xuất định dạng mới (Excel, Word) | `src/pccc_checker/output/` + lệnh trong `cli.py` |
| Giao diện (web/GUI) | gọi các hàm trong `cli.py`/module, không nhân bản logic |

## Giới hạn hiện tại
- Kết quả phụ thuộc chất lượng đọc bản vẽ; luôn cần kỹ sư xác nhận.
- Đo khoảng cách dựa trên bbox + tỉ lệ ghi trên bản vẽ (xấp xỉ), chưa dựng hình học tường/phòng.
- Khoảng cách giới hạn đường thoát nạn (3.3.2, Phụ lục G) chưa mã hoá — cần dựng hình học đường đi.
- 3.2.8 dùng khung mặt bằng (Gemini `plan_box_2d` hoặc hình chữ nhật lớn nhất) để tính đường chéo — gần đúng.
