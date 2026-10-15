---
id: bang-qcvn-chua-chep
tieu_de: Quy chuẩn / bảng số đã nạp và còn thiếu trong kho
nhom: thieu
tu_khoa: bảng còn thiếu, đã nạp, QCVN 13, QCVN 10, TCVN 7568, TCVN 3890, TCVN 5738, bảng chờ duyệt, nạp quy chuẩn
trang_thai: verified
nguon: scripts/knowled_import_qcvn.py, knowled_import_pdf.py, knowled_ocr_gemini.py chạy 15/10/2026
cap_nhat: 2026-10-15
---
**Đã nạp (mỗi mục/bảng 1 file `knowledge/quy-chuan/<mã>-...md`)**
- `qcvn06-bang-*` (63 bảng) + `bang-6-phan-nhom-nha` — từ file Word QCVN 06 hợp nhất. Đã duyệt: Bảng 4, 5, 6, 14, 16, E.3.
- `qcvn13-*` (QCVN 13:2018 gara, 48 mục + 9 bảng) — từ file Word, đối chiếu chéo với bản PDF: Bảng 1–4 và 8 khớp từng số.
  Đã duyệt Bảng 1–8; Bảng A.1 chờ duyệt (bản PDF thiếu nhiều ô, chỉ bản Word đầy đủ).
- `qcvn10-*` (QCVN 10:2025/BCA trang bị phương tiện PCCC, ~80 mục + 17 bảng) — từ file Word, đánh số điều khoản theo kiểu Heading.
  Mục Phụ lục A và H rất dài (chưa tách theo điều khoản con vì số điều trong phụ lục là số tự động của Word). Bảng chờ duyệt.
- `tcvn7568-14-*` (TCVN 7568-14:2025 báo cháy, 80 mục + 2 bảng) — từ PDF có lớp chữ; thay TCVN 5738:2021 (ghi ngay trang đầu).

**Chưa có**
- Thông tư 103/2025 (ngày 04/11/2025) — chỉ có bản scan 64 trang; cần OCR (Gemini hết phiên đăng nhập) hoặc bản Word/PDF có chữ.
- TCVN 6396-72:2010, TCVN 3890 (đã được QCVN 10 thay theo người dùng; mục `thay-the-tcvn-3890-bang-qcvn-10` chờ duyệt),
  QCVN 04:2021, QCVN 02:2020/BCA, các bảng quy hoạch / chấp thuận địa điểm (B1–B3).
- Duyệt bảng: `knowled doc <id>` rồi `knowled duyet <id>` sau khi so với file gốc.

Cơ chế: dòng bảng tra dẫn tới "Bảng N" (kèm QCVN 13 / QCVN 10 / TCVN 7568-14 nếu có nêu) mà bảng có trong kho thì `goi` kèm nguyên văn bảng đó
(`goi/<gói>.bang.md`); bảng chờ duyệt / chưa nạp thì dòng đó chỉ được XM, không D/KD.
