---
name: cong-claude
description: Hai cổng kiểm tra của Claude trong pipeline PCCC — Cổng 1 duyệt dữ liệu đầu vào (project_facts.json, cong1.md, ảnh cắt vùng lệch) trước khi chạy skill chuyên đề; Cổng 2 duyệt kết luận (findings.jsonl: mọi dòng KD + XM, lấy mẫu 10% dòng D) trước khi xuất Word/ghi chú PDF. Dùng sau lệnh `facts` (Cổng 1) và sau bước đối chiếu (Cổng 2), hoặc khi người dùng hỏi "duyệt", "soát", "cổng 1/2".
---

# Cổng Claude (skill 07)

Claude đứng ở 2 điểm mà một lỗi sẽ lan ra toàn bộ kết quả. Không đọc lại cả bản vẽ — chỉ đọc JSON, báo cáo do
script sinh, và ảnh cắt đúng vùng nghi vấn (≤ 5 ảnh/lần, `crops` hoặc vùng `vung_anh` trong page_index.json).
Nạp kèm: `memory/lessons.md` (mục `chung` + mục của bước đang duyệt), `memory/overrides.json` (mục hồ sơ).

## Cổng 1 — dữ liệu đầu vào (sau `facts`, trước `keys`/chuyên đề)
Đầu vào: `cong1.md` (bảng trường quyết định + kiểm tra logic), `project_facts.json`, `page_index.json`.
1. Trường quyết định (công năng, số tầng, chiều cao PCCC, diện tích, nhóm nhà, hạng nổ, bậc chịu lửa) mà độ tin cậy
   L, giá trị null có ứng viên, hoặc dính kiểm tra logic `loi` → xem ảnh cắt của đúng bảng/trang đó.
   Trang HON-HOP: luôn đọc ảnh bảng quy mô (Gemini hay đọc lệch cột bảng ảnh — lessons `doc-thong-tin`).
2. Kết luận từng trường: **Đúng** (giữ) · **Sửa** (giá trị mới + trang + bảng) · **Đọc lại** (trang cần Gemini đọc lại).
3. `nhom_nha.ban_ve` lệch `tinh`, hoặc `tinh` chưa có `ban_ve` → ghi vào mâu thuẫn (bước 5), KHÔNG tự chọn.
4. Ghi:
   - Sửa từ ảnh → `data/output/<hồ sơ>/claude_doc_anh.json`: `[{hm, truong (khoá project_info), gia_tri, trang, bang}]`
     rồi chạy lại `facts` (Claude khớp Gemini → H; lệch → M, lấy giá trị Claude).
   Mọi hạng mục đều là hạng mục chính — kiểm tất cả, không chọn một.
   - `verdict.json` (cùng thư mục): `{"cong": 1, "ngay": "...", "muc": [{"hm","truong","ket_luan","gia_tri","trang","ly_do"}]}`.
   - Đọc lại → `info <pdf> --gemini-info always --gemini-pages <trang>` chỉ các trang đó, KHÔNG chạy lại cả bộ.
5. **KHÔNG hỏi người dùng** (yêu cầu 14/10/2026): giá trị lệch giữa các trang/bảng, trường bắt buộc còn thiếu,
   ban_ve ≠ tinh → ghi `nghi_ngo.json` mục `mau_thuan_tren_ban_ve`:
   `{hang_muc, truong, gia_tri: {"<bảng/ghi chú> tr.N": giá trị, ...}, trang: [N, ...], ghi_chu}` — đủ trang + nơi ghi
   từng giá trị. Chỉ khi chạy full quy trình (/check-pccc): sau Cổng 1 gọi skill `xu-ly-va-cham`. Trường chưa chốt → các dòng phụ thuộc ra XM.
   Chỉ khi người dùng TỰ chốt → `data/input/<hồ sơ>.project.yaml`; quyết định phân loại → `memory/overrides.json`.
6. Qua cổng khi: trường quyết định đã H/M, hoặc đã ghi vào mâu thuẫn (để XM). Chạy tiếp `keys`, không dừng chờ.

## Cổng 2 — kết luận (sau đối chiếu, trước xuất Word/PDF)
Đầu vào: `findings.jsonl` (đã qua `findings --check`), `rule_keys.json`, đúng file bảng tra của dòng đang xét.
1. Mọi dòng **KD**: có đủ trang + bbox + evid + điều khoản? `evid` có thật là chữ trên bản vẽ (so `project_facts.evid`
   / `extraction.md`)? Ngưỡng `yc` có đúng dòng bảng tra (ID `rule`)? Sai/thiếu → hạ XM, ghi `ly_do`.
2. KD dựa trên số đo từ trang SCAN hoặc conf L → xem ảnh cắt vùng `bbox` trước khi giữ KD.
3. Mọi dòng **XM**: nêu rõ thiếu gì + trang nên đọc bổ sung; nếu dữ liệu đã có ở JSON → kết luận lại D/KD.
4. Lấy mẫu ~10% dòng **D** (ít nhất 3): kiểm như KD; sai 1 dòng → soát toàn bộ D của chuyên đề đó.
5. Không thêm điều khoản ngoài bảng tra (dòng như vậy luôn XM). Không nâng XM → KD khi chưa có bằng chứng.
6. Ghi `verdict.json` mục `{"cong": 2, ...}` (id dòng, giữ/hạ/sửa, lý do), sửa `findings.jsonl`, chạy lại
   `findings --check <file>`. Dòng KD thiếu bằng chứng của một chuyên đề → quay lại skill chuyên đề đó, không chạy lại cả bộ.

## Sau 2 cổng
Xuất (script): Word đối chiếu (chưa có `fill_docx.py` — tạm báo cáo MD/HTML) → `annotate` PDF.
Đề xuất bài học mới vào `memory/lessons.md` mục "Chờ duyệt" (mẫu 1 dòng); chỉ chuyển lên mục chính khi người dùng xác nhận.
