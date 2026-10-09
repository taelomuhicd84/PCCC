---
description: Kiểm tra bản vẽ PDF PCCC theo QCVN 06:2022 + SĐ1:2023 và ghi chú vị trí sai lên PDF (quy trình nhiều agent)
argument-hint: <đường-dẫn-pdf> [--extractor hybrid|gemini|vector] [--grid 2x2] [--building file.yaml] [--no-review]
allowed-tools: Agent, Bash, Read
---

Bạn là "đầu não" điều phối. Mục tiêu: dùng ít token Claude nhất — KHÔNG tự đọc ảnh/PDF, chỉ đọc tóm tắt.

Đầu vào: $ARGUMENTS

Quy trình:
1. **Trích xuất** — gọi subagent `drawing-reader` với đường dẫn PDF và các tham số extractor/grid/pages/building.
   Nếu tóm tắt báo thiếu thông tin công trình quan trọng (nhóm F, chiều cao PCCC, bậc chịu lửa, số tầng hầm) và người
   dùng không truyền `--building`: hỏi người dùng 1 lần (gộp tất cả câu hỏi), hoặc tiếp tục và ghi rõ giả định.
2. **Kiểm tra luật** — tự chạy (rẻ, không cần agent):
   `python -m pccc_checker check data/output/<tên>/extraction.json [--building ...] [--set k=v ...]` (PYTHONPATH=src).
3. **Review** — trừ khi có `--no-review`: gọi subagent `compliance-reviewer` với thư mục kết quả.
4. **Xuất kết quả** — gọi subagent `pdf-annotator` với PDF + findings.json.
5. **Báo cáo cho người dùng** (tiếng Việt, ngắn): đường dẫn PDF đã ghi chú, report.md, drawing.dxf; tổng số lỗi;
   5 lỗi nghiêm trọng nhất; các giả định; nhắc rằng luật đánh dấu (*) chưa được đối chiếu nguyên văn và kết quả cần
   kỹ sư PCCC xác nhận. Nếu reviewer gợi ý luật mới → đề xuất chạy `/add-rule`.
