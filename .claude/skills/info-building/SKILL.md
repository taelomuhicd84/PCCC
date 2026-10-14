---
name: info-building
description: Đọc THÔNG TIN CÔNG TRÌNH (khu đất, hạng mục, bậc chịu lửa, nhóm F, hạng cháy nổ, chiều cao PCCC, cấp S, số tầng, khối tích) từ hồ sơ PDF PCCC và xuất bảng như project_info.md / HTML. Dùng khi người dùng đưa PDF và hỏi "thông tin công trình", "đọc thử", "bảng quy mô", hoặc trước bước check của /check-pccc.
---

# Skill Info Building — đọc thông tin công trình từ hồ sơ PCCC

Mục tiêu: ra bảng **Trường × Hạng mục** (mẫu: `project_info.md` của nhà hàng Thiên Ý) với ký hiệu
`⚠` trang ghi khác nhau · `*` chỉ Gemini đọc (cần kiểm) · `✓` đã xác nhận trong project.yaml · `—` bản vẽ không ghi.
KHÔNG tự đọc ảnh cả trang bản vẽ; KHÔNG đọc lại lịch sử cũ — làm theo các bước dưới. Ngoại lệ duy nhất: Cổng 1 (bước 2b).

## Quy trình (ít token nhất) — bước 1–3 của pipeline + Cổng 1 (docs/ARCHITECTURE.md)

```powershell
$env:PYTHONPATH="src"
python -m pccc_checker gemini-status                       # BƯỚC ĐẦU mỗi lần gọi skill: exit 1 = chưa đăng nhập
python -m pccc_checker intake "<pdf>"                      # 0 token: page_index.json — loại trang, luồng LAYER/HON-HOP/SCAN, vùng ảnh, mã băm
python -m pccc_checker info "<pdf>" --project data/input/<ho_so>.project.yaml --gemini-pages smart
python -m pccc_checker facts data/output/<tên>             # project_facts.json (ô H/M/L) + cong1.md (kiểm tra logic)
python -m pccc_checker crops "<pdf>" --pages <trang HON-HOP có trường L>   # ảnh bảng cho Cổng 1
```
0. Gọi skill `gemini-web` (kiểm tra đăng nhập). CHƯA đăng nhập -> vẫn làm phần vector (0 token) và nhờ người dùng xuất cookie
   MỚI rồi nạp bằng `gemini-cookie <file>`. KHÔNG lưu/đọc/in cookie trong chat hay memory.
1. `intake`: trang HON-HOP (bảng dán ảnh) và SCAN là chỗ Gemini hay sai -> Cổng 1 xem ảnh các trang này. Chạy lại `intake`
   khi có bản vẽ sửa đổi: nó in các trang đổi băm -> chỉ đọc lại các trang đó (`--gemini-pages <trang đổi>`).
2. `info` rồi `facts`. Đọc `cong1.md` (ngắn). Chỉ mở `project_info_chi_tiet.md` khi cần nguyên văn căn cứ.
2b. **Cổng 1 — skill `cong-claude`**: trường quyết định độ tin cậy L / dính kiểm tra logic -> Claude mở ĐÚNG ảnh bảng
   (`crops/pNN_bangK.png`, ≤ 5 ảnh), ghi giá trị đọc được vào `claude_doc_anh.json` rồi chạy lại `facts`
   (khớp Gemini -> H, lệch -> M theo Claude). Thử BW Đồng An / Phú Trường 14/10/2026: Claude đọc ảnh đúng hết, Gemini sai
   nhiều ô (chiều cao, nhóm nhà, diện tích VP, cao PCCC xưởng). Khác Gemini -> ghi cả hai vào nghi_ngo.json.
3. Hiện nguyên bảng cho người dùng. **KHÔNG hỏi lại** (yêu cầu 14/10/2026): mâu thuẫn giữa trang/bảng, trường bắt buộc
   thiếu -> ghi `nghi_ngo.json` mục `mau_thuan_tren_ban_ve` kèm trang + nơi ghi từng giá trị;
   báo ngắn trong kết quả. Skill này CHỈ xuất thông tin (bảng/HTML + nghi_ngo.json): KHÔNG chạy facts/keys/va-cham/check
   trừ khi người dùng bảo chạy full quy trình (yêu cầu 14/10/2026 — đang test từng phần, tránh tốn token). KHÔNG tự điền giá trị thay người dùng. **Mọi hạng mục đều là hạng mục chính** — không hỏi
   chọn hạng mục chính, không ghi "(chính)". Số liệu người dùng tự chốt -> `data/input/<ho_so>.project.yaml` (mẫu
   `config/project.example.yaml`); quyết định phân loại (vd "HM02 coi là F1.3") -> `memory/overrides.json`.
4. Cần HTML: dựng đúng bố cục project_info.md (tiêu đề, gạch đầu dòng khu đất/số hạng mục/file, ký hiệu, bảng, mục "* Cần kiểm").
   Ký hiệu HTML: ☑ Claude đã đọc ảnh (H/M) · ✓ người dùng xác nhận · * chỉ Gemini (L) · ⚠ các trang ghi khác nhau.
   Dựng HTML xong chạy `trang data/output/<tên> --html` -> thêm mục **Danh mục bản vẽ** (trang → ký hiệu, tên bản vẽ,
   hạng mục, chuyên đề; yêu cầu người dùng 14/10/2026). `info` tự ghi `danh_muc_ban_ve.json/.md` (0 token, đọc khung tên).
   Trang không có lớp chữ (scan / lỗi font như Liên Minh) -> trống, ghi rõ trong HTML.
5. Tiếp theo (nếu kiểm tra đầy đủ): `keys` -> skill `doi-chieu` -> Cổng 2.

## Gemini — GỌI SKILL `gemini-web` TRƯỚC (đăng nhập, cookie, quy tắc gửi, selector, thời gian đo)
- Bước đầu: skill `gemini-web` (`gemini-status`; cookie chết -> `gemini-cookie`). Mọi quy tắc Playwright nằm ở đó:
  **CHỈ GỬI FILE PDF, KHÔNG BAO GIỜ GỬI HÌNH**; 4 Argon "Thấp" / 1 cuộc trò chuyện; nhiều trang -> chunk 8 trang, TỐI ĐA 10 tab,
  giãn cách như người thật;
  có kết quả -> lưu tạm `data/cache/raw/` rồi xoá cuộc trò chuyện.
- Lệnh chuẩn: `info "<pdf>" --gemini-pages smart` — tự lọc trang gửi Gemini (giữ trang không có chữ + trang có từ khoá
  PCCC/quy mô/mặt bằng; bản scan -> cả hồ sơ). Kiểm chứng Liên Minh: 72 -> 49 trang, kết quả giống hệt bản đủ.
  Cần chắc chắn tuyệt đối thì `--gemini-pages 1-N` (cả hồ sơ). Bản scan chữ nhỏ: vẫn gửi PDF, giá trị nghi ngờ ghi `nghi_ngo.json` (không gửi ảnh).
- File trên **Google Drive** (`D:\1.DRIVE CÔNG TY\...`) có thể lỗi đọc giữa chừng (file online-only) -> chép về `data/input/` trước.
- Cache Gemini: `data/cache/` theo hash PDF + trang + model (+ `_png`). Nghi cache sai -> xoá `data/cache/<hash>*`
  (hash trong project_info.json `meta.pdf_hash`).
- **Xuất kết quả (người dùng hay yêu cầu):** HTML theo bố cục project_info.md + file `nghi_ngo.json` cùng thư mục (mâu thuẫn
  kèm số trang + nguyên văn, giá trị chỉ Gemini đọc, thiếu trường bắt buộc). Mục training: KHÔNG hỏi xác nhận, chỉ ghi chú
  trang nào ghi gì (có thể thiết kế nhầm).

## Hạng mục = BẢNG THỐNG KÊ HẠNG MỤC CÔNG TRÌNH (yêu cầu người dùng 2026-10-13)
- Cột kết quả = đúng các dòng của bảng thống kê (KÝ HIỆU | HẠNG MỤC | KÍCH THƯỚC | CHIỀU CAO | DIỆN TÍCH), thường ở tổng mặt
  bằng / mặt bằng định vị. Thông số PCCC lấy từ bảng/ghi chú trên mặt bằng TỪNG hạng mục rồi gán vào đúng tên trong bảng.
- Khu vực bên trong 1 hạng mục (phòng, "công năng phụ trợ", "văn phòng phụ trợ", khu chứa hàng) = ghi nhớ (`meta.khu_vuc`,
  mục riêng trong HTML) nhưng KHÔNG thành cột. Code: prompt `bang_thong_ke`/`khu_vuc`, `project_info._limit_to_table`.
- Gemini có thể lệch dòng trong bảng (Liên Minh: TRẠM ĐIỆN cao "-" bị gán 4,2 m của TRẠM BƠM) -> ghi nghi_ngo.json.
- Bảng HTML: cột đầu tiêu đề "Hạng mục" (không phải "Trường").

## Bẫy đã gặp
Đã chuyển sang `memory/lessons.md` mục `chung` + `doc-thong-tin` (nạp trước khi kết luận). Bài học mới: ghi mục
"Chờ duyệt" của file đó, người dùng xác nhận mới chuyển lên.

## Ví dụ đã làm
`BẢN VẼ TD LUẬT PHÚ TRƯỜNG.pdf` (178 trang, tr.5 xoay 270° có 4 bảng ảnh: thống kê hạng mục, hạng mục chính, nhà phụ
trợ, cân bằng đất): 8 nhà xưởng (01: 900 m², 02,03,04,08: 2000, 05,06,07: 2400), bậc IV, F5.1, hạng C, S0, cao PCCC
5,97 (01) / 6,5 m (02–08); văn phòng F4.3 600 m² cao PCCC 5,97; xưởng 01 bảng ghi 1 tầng ↔ 2 tầng (ghi mâu thuẫn);
thuyết minh chữa cháy tr.127 lệch bảng. Claude đọc ảnh -> `claude_doc_anh.json`.
`19. BVPCCC .signed….pdf` (FUMEI, 203 trang SCAN, A3): bảng "QUY MÔ PCCC" chữ đỏ nhỏ tr.12 (5 nhà: NX1 C/19,8 m/II/S0/3 tầng/
12.856 m²/189.823,2 m³; NX2 C/28 m/II/S0/3 tầng/5.201,5 m²/131.198,22 m³), danh sách hạng mục tr.4, chiều cao PCCC 9,15 m tr.10.
Gửi PDF đọc sai bảng chữ nhỏ (đã đối chiếu tay bằng ảnh phóng to) -> ghi nghi_ngo.json. `BVTK TD LIÊN MINH.pdf` (72 trang có text, 114 MB, trên Drive): nhà kho + xưởng cơ khí,
bảng thống kê tr.3–4: xưởng cơ khí 54×26 cao 9 m 1404 m², nhà kho 1188 m², nhà bảo vệ 20, trạm điện 24,6 (cao "-"),
trạm bơm 25 (4,2 m), bể nước PCCC 116,96 (1,95 m); kho F5.2 hạng C, xưởng F5.1 hạng D, bậc IV, S0, cao PCCC 7 m (tr.3–4).
`114.TD.30.01.2024 BV KT BW ĐỒNG AN.pdf` (42 trang A0): bảng hạng mục ở tr.7, ghi chú PCCC kho 1A tr.10–13, kho 1B tr.22–25,
nhà phụ trợ tr.40. Đã xác nhận: kho bậc II, F5.2, hạng C, cao PCCC 16,75 m, S0; phụ trợ bậc III hạng E -> `data/input/bw_dong_an.project.yaml`.
