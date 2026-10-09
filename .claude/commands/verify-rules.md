---
description: Đối chiếu các luật verified:false với nguyên văn QCVN 06:2022 / Sửa đổi 1:2023 và đánh dấu đã xác minh
argument-hint: <đường dẫn văn bản quy chuẩn (pdf/docx/txt) trong docs/regulations/> [rule-id ...]
allowed-tools: Agent, Bash, Read
---

1. Chạy `python -m pccc_checker rules` (PYTHONPATH=src) để lấy danh sách luật chưa xác minh (*).
2. Gọi subagent `regulation-curator`: đối chiếu từng luật (hoặc các rule-id được chỉ định) với văn bản: $ARGUMENTS
   - Văn bản PDF dài: agent dùng `python -c` + pymupdf để trích text theo từ khoá số điều khoản, không đọc toàn văn.
3. Báo cáo: luật đã xác minh, luật đã sửa giá trị (cũ → mới), luật chưa tìm thấy căn cứ.
