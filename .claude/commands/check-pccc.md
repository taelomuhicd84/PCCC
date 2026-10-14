---
description: Kiểm tra bản vẽ PDF PCCC theo QCVN 06:2022 + SĐ1:2023 — pipeline 8 bước, 2 cổng Claude, ghi chú vị trí sai lên PDF
argument-hint: <đường-dẫn-pdf> [--extractor hybrid|gemini|vector] [--grid 2x2] [--project project.yaml] [--no-review]
allowed-tools: Agent, Bash, Read, Skill
---

Bạn là "đầu não" điều phối. Mục tiêu: dùng ít token Claude nhất — KHÔNG tự đọc ảnh/PDF cả trang, chỉ đọc JSON/MD ngắn
và ảnh cắt ở 2 cổng. Nguyên tắc + schema: `docs/ARCHITECTURE.md`. Lệnh: `python -m pccc_checker …` (PYTHONPATH=src).

Đầu vào: $ARGUMENTS   ·   `<out>` = `data/output/<tên pdf>/`

1. **intake** (0 token): `intake <pdf>` → `page_index.json`. Hồ sơ đã chạy trước: nó in các trang đổi băm → bước 2 chỉ
   đọc lại các trang đó.
2. **Thông tin tổng thể** — skill `info-building` (gọi `gemini-web` kiểm tra đăng nhập trước):
   `info <pdf> [--project data/input/<hồ sơ>.project.yaml] --gemini-pages smart`.
3. **facts**: `facts <out>` → `project_facts.json` + `cong1.md`.
4. **CỔNG 1** — skill `cong-claude`: soát `cong1.md`, xem ảnh cắt trường L / lỗi logic (trang HON-HOP), ghi
   `claude_doc_anh.json` → chạy lại `facts`. KHÔNG hỏi người dùng: trường bắt buộc thiếu/mâu thuẫn, `ban_ve ≠ tinh` →
   ghi `nghi_ngo.json` mục `mau_thuan_tren_ban_ve` (trang + nơi ghi từng giá trị), chạy tiếp; luật phụ thuộc ra XM.
   KHÔNG tự suy giá trị thay người dùng. Mọi hạng mục đều là hạng mục chính (kiểm tất cả).
4b. **Va chạm** (chỉ trong full quy trình này) — skill `xu-ly-va-cham`: `va-cham <out>` → Claude chỉ vị trí ô trong ảnh cắt / bỏ va chạm do Gemini đọc
   lệch (`va_cham_claude.json`) → `va-cham <out> --annotate` → `*_va_cham.pdf` + `Note phản hồi.docx`. Không hỏi, không chọn giá trị.
5. **keys**: `keys <out>` → `rule_keys.json` (loại hình, bộ bảng, file từng chuyên đề).
6. **Trích xuất phần tử + luật YAML**: subagent `drawing-reader` (extract) → `hm-pages <out>` (soát nhanh `hm_pages.json`:
   trang tổng thể = "chung", sửa tay nếu gán sai) → `check <out>/extraction.json` (0 token, chạy riêng từng hạng mục).
7. **Đối chiếu chuyên đề** — skill `doi-chieu` (chỉ khi rule_keys có file bảng tra; loại hình chưa có bảng → bỏ qua, báo).
   Rồi `findings <out>` gộp kết quả engine vào `findings.jsonl` (script tự hạ KD thiếu bằng chứng → XM).
8. **CỔNG 2** — trừ khi `--no-review`: skill `cong-claude` (mọi KD + XM, mẫu 10% D). Cần phán đoán chuyên môn sâu trên
   findings.json của engine → subagent `compliance-reviewer`. Sau đó `findings --check <out>/findings.jsonl`.
9. **Xuất**: subagent `pdf-annotator` (PDF ghi chú + DXF + report), rồi chạy lại `va-cham <out> --annotate` để
   `Note phản hồi.docx` gộp cả va chạm + KD/XM (xếp theo trang). Word đối chiếu: chưa có `fill_docx.py` → báo.
10. **Báo cáo người dùng** (tiếng Việt, ngắn): file đầu ra; số D/KD/XM/NA; 5 lỗi KD nghiêm trọng nhất (mã dòng, trang,
    điều khoản); XM do thiếu gì; giả định; luật (*) chưa đối chiếu nguyên văn; kết quả cần kỹ sư PCCC xác nhận.
    Bài học mới → đề xuất ở `memory/lessons.md` mục "Chờ duyệt". Loại lỗi lặp lại → đề xuất `/add-rule`.
