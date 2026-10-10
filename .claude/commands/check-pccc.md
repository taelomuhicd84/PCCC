---
description: Kiểm tra bản vẽ PDF PCCC theo QCVN 06:2022 + SĐ1:2023 và ghi chú vị trí sai lên PDF (quy trình nhiều agent)
argument-hint: <đường-dẫn-pdf> [--extractor hybrid|gemini|vector] [--grid 2x2] [--project project.yaml] [--no-review]
allowed-tools: Agent, Bash, Read
---

Bạn là "đầu não" điều phối. Mục tiêu: dùng ít token Claude nhất — KHÔNG tự đọc ảnh/PDF, chỉ đọc tóm tắt.

Đầu vào: $ARGUMENTS

Quy trình:
0. **Thông tin công trình** — tự chạy (rẻ, chủ yếu 0 token):
   `python -m pccc_checker info <pdf> [--project project.yaml]` (PYTHONPATH=src) -> `data/output/<tên>/project_info.json`.
   Hiển thị NGUYÊN bảng *trường | giá trị | trang | trạng thái* CLI in ra cho người dùng và HỎI XÁC NHẬN trước khi
   chạy check (gộp mọi câu hỏi 1 lần). Trường bắt buộc `missing`/`conflict` (bậc chịu lửa, nhóm nhà, chiều cao PCCC,
   cấp S; hạng cháy nổ nếu F5): đề nghị người dùng điền vào `project.yaml` (mẫu `config/project.example.yaml`) rồi
   chạy lại `info --project ...`. Người dùng cho phép chạy tiếp khi còn thiếu -> các luật phụ thuộc sẽ `cannot_check`.
   KHÔNG tự suy giá trị thay người dùng.
1. **Trích xuất** — gọi subagent `drawing-reader` với đường dẫn PDF và các tham số extractor/grid/pages/building.
   Thông tin công trình đã lấy ở bước 0 — không hỏi lại.
2. **Kiểm tra luật** — tự chạy (rẻ, không cần agent):
   `python -m pccc_checker check data/output/<tên>/extraction.json [--set k=v ...]` (PYTHONPATH=src) — tự đọc
   `project_info.json` cùng thư mục làm ngưỡng.
3. **Review** — trừ khi có `--no-review`: gọi subagent `compliance-reviewer` với thư mục kết quả.
4. **Xuất kết quả** — gọi subagent `pdf-annotator` với PDF + findings.json.
5. **Báo cáo cho người dùng** (tiếng Việt, ngắn): đường dẫn PDF đã ghi chú, report.md, drawing.dxf; tổng số lỗi;
   5 lỗi nghiêm trọng nhất; số luật `cannot_check` và trường gây ra; các giả định; nhắc rằng luật đánh dấu (*) chưa được đối chiếu nguyên văn và kết quả cần
   kỹ sư PCCC xác nhận. Nếu reviewer gợi ý luật mới → đề xuất chạy `/add-rule`.
