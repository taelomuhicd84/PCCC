---
description: Thêm/sửa luật kiểm tra trong rules/*.yaml từ nguyên văn điều khoản quy chuẩn
argument-hint: <mô tả luật hoặc trích nguyên văn điều khoản / đường dẫn văn bản>
allowed-tools: Agent, Read
---

Gọi subagent `regulation-curator` với yêu cầu: $ARGUMENTS

Nếu người dùng chưa cung cấp nguyên văn điều khoản, yêu cầu agent vẫn tạo luật nhưng để `verified: false`.
Sau khi agent xong, báo lại ngắn gọn: luật đã thêm/sửa, kết quả test, điểm cần kỹ sư xác nhận.
