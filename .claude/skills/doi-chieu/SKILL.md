---
name: doi-chieu
description: Đối chiếu hạng mục × chuyên đề với bảng tra .md (skill 04) — script lọc bảng tra thành "gói" (lệnh goi), Gemini làm lượt đầu (goi-gemini), subagent doi-chieu-worker xét phần còn nghi; ghi findings.jsonl 4 trạng thái D/KD/XM/NA. Dùng sau Cổng 1 khi cần kết luận theo bảng đối chiếu (khách sạn k1/k2/k3, gara, kho…), hoặc khi người dùng hỏi "đối chiếu", "kiểm chuyên đề thoát nạn/quy mô…".
---

# Đối chiếu theo chuyên đề (skill 04) — tiết kiệm token

Điều kiện: đã qua Cổng 1 (`cong-claude`) và đánh giá công năng (skill `knowled`, module `danh-gia-cong-nang`), có `rule_keys.json` (`keys`). Khung chung: `skills/chuyen-de/_khung.md`.
**LUẬT SẮT: ngữ cảnh chính KHÔNG đọc bảng tra `rules/checklists/**` và KHÔNG đọc chữ bản vẽ.** Một bảng công trình ~30–35k token
cho 7 chuyên đề; việc đó do script + Gemini + subagent làm, ngữ cảnh chính chỉ nhận ≤ 15 dòng tóm tắt.

```powershell
$env:PYTHONPATH="src"
python -m pccc_checker keys data/output/<hồ sơ>                       # rule_keys.json (sau danh-gia)
python -m pccc_checker goi data/output/<hồ sơ> [--den thoat-nan] [--cd quy-mo,...] [--hm HM03,HM04] [--bang gara/chung]
python -m pccc_checker goi-gemini data/output/<hồ sơ> [--thu]         # Gemini làm lượt đầu (chạy nền, chậm); gọi skill gemini-web trước
# -> subagent doi-chieu-worker xét goi/*.can-claude.md, rồi nó chạy: goi-nhap data/output/<hồ sơ>
python -m pccc_checker findings --check data/output/<hồ sơ>/findings.jsonl
```

## Thứ tự
1. `goi`: mỗi (nhóm hạng mục giống nhau × chuyên đề) → `goi/<HM>_<cd>.md`. Script đã ghi vào `findings.jsonl` (nguon `script`):
   dòng tiêu đề bỏ · NA do `rules/dieu_kien.yaml` (không có tầng hầm/thang/máy biến áp… ) · XM khi quy định chỉ dẫn tới bảng số
   chưa chép · dòng đã xét với đúng số liệu + chữ bản vẽ (bộ nhớ đệm `goi/cache.json`, chạy lại 0 token). Không `--bang` →
   theo `rule_keys.file` (mọi chuyên đề đã áp dụng). `quy-mo` luôn trước; `--den thoat-nan` = mục 01…07.
2. `goi-gemini`: gộp ≤ 45 dòng / lượt, gửi 1 PDF đúng trang (chỉ PDF, theo skill `gemini-web`). Script KIỂM CHỨNG: Gemini nói D mà
   trích dẫn không có trong chữ vector của trang → hạ XM; Gemini nói KD → hạ XM "nghi KD" cho Claude. Chỉ D/NA đã kiểm chứng vào đệm.
   Gemini chưa đăng nhập / không dùng được → bỏ bước này, giao subagent xét thẳng `goi/<HM>_<cd>.md` (mục "Cần Claude xét").
3. Giao subagent `doi-chieu-worker` (prompt: thư mục hồ sơ) — nó đọc `goi/*.can-claude.md`, ghi `*.ket-qua.txt`
   (`ID | TT | trang | lý do | evid | bbox`), chạy `goi-nhap`. Nhiều nhóm hạng mục độc lập → nhiều subagent song song.
4. Chạy `findings --check`, đọc tóm tắt (đếm D/KD/XM/NA), rồi sang Cổng 2 (`cong-claude`). Cần nguyên văn 1 dòng bảng → `dong <ID>`.

## Quy tắc chính xác
- Cột "Quy định" của gói là căn cứ duy nhất; dòng dẫn tới bảng số chưa chuẩn hoá (Bảng 1–5, E.1, G.9, H.2… xem "Còn thiếu" trong
  `rules/_index.md`) → XM, ghi tên bảng thiếu. Không bổ sung số từ trí nhớ.
- Số liệu hạng mục thiếu khoá quyết định → XM, không đoán. Ô độ tin cậy L chỉ được XM.
- Rà danh sách "NA tự động" trong đầu mỗi gói; sai → sửa `rules/dieu_kien.yaml` rồi chạy lại `goi` (không sửa tay findings).
- `memory/lessons.md` mục `chung` + chuyên đề; quyết định đã chốt: `memory/overrides.json`.

## Xuất bảng đối chiếu Word (bước cuối)
```powershell
python -m pccc_checker xuat-bang data/output/<hồ sơ> --hm HM01 [--gemini]   # -> bang_doi_chieu/<HM>_<mẫu>.docx
```
Điền findings.jsonl vào `datamau/B*.docx` đúng công năng: cột Nội dung thiết kế (văn phong mẫu B17) + Kết luận (Đạt | Không đạt (tr.X) | Cần xác minh (tr.X) | Không áp dụng | Chưa đánh giá).
`--gemini`: Gemini viết lại cột thiết kế + sửa chính tả theo lô (file text, không PDF); script chặn số bịa/“đảm bảo” sai; Claude chỉ kiểm mẫu.
**Font:** style Normal của mẫu là `.VnTime` → mọi run phải Times New Roman tường minh (`chuan_font` tự vá, `font_loi` phải = 0). Sau xuất kiểm bằng Word → PDF, tìm chuỗi méo (cỏch|dõn|Tờn|cụng). Cần `thong_tin_chung.json` (ten, dia_diem, chu_dau_tu, co_quan_thiet_ke, tom_tat) trong thư mục hồ sơ.
