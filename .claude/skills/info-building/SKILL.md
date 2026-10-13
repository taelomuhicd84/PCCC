---
name: info-building
description: Đọc THÔNG TIN CÔNG TRÌNH (khu đất, hạng mục, bậc chịu lửa, nhóm F, hạng cháy nổ, chiều cao PCCC, cấp S, số tầng, khối tích) từ hồ sơ PDF PCCC và xuất bảng như project_info.md / HTML. Dùng khi người dùng đưa PDF và hỏi "thông tin công trình", "đọc thử", "bảng quy mô", hoặc trước bước check của /check-pccc.
---

# Skill Info Building — đọc thông tin công trình từ hồ sơ PCCC

Mục tiêu: ra bảng **Trường × Hạng mục** (mẫu: `project_info.md` của nhà hàng Thiên Ý) với ký hiệu
`⚠` trang ghi khác nhau · `*` chỉ Gemini đọc (cần kiểm) · `✓` đã xác nhận trong project.yaml · `—` bản vẽ không ghi.
KHÔNG tự đọc ảnh bản vẽ; KHÔNG đọc lại lịch sử cũ — làm theo các bước dưới.

## Quy trình (ít token nhất)

```powershell
$env:PYTHONPATH="src"
python -m pccc_checker gemini-status                       # BƯỚC ĐẦU mỗi lần gọi skill: exit 1 = chưa đăng nhập
python -m pccc_checker pages "<pdf>"                       # 0 token: loại trang + tiêu đề
python -m pccc_checker info "<pdf>" --project data/input/<ho_so>.project.yaml
# Bảng trống nhiều ô -> cho Gemini đọc thêm các trang có bảng quy mô / ghi chú PCCC:
python -m pccc_checker info "<pdf>" --project ... --gemini-info always --info-pages 1,7,10,...
```
0. Gọi skill `gemini-web` (kiểm tra đăng nhập). CHƯA đăng nhập -> vẫn làm phần vector (0 token) và nhờ người dùng xuất cookie
   MỚI rồi nạp bằng `gemini-cookie <file>`. KHÔNG lưu/đọc/in cookie trong chat hay memory.
1. `pages` để chọn trang: bìa, tổng mặt bằng (bảng hạng mục), mặt bằng tầng 1 mỗi hạng mục (ghi chú PCCC), trang nhà phụ trợ.
2. Chạy `info`. Đọc `data/output/<tên>/project_info.md` (ngắn). Chỉ mở `project_info_chi_tiet.md` khi cần nguyên văn căn cứ.
3. Hiện nguyên bảng cho người dùng, hỏi xác nhận trường bắt buộc (bậc chịu lửa, nhóm F, chiều cao PCCC, cấp S, hạng cháy nổ nếu F5).
   KHÔNG tự điền giá trị thay người dùng. Giá trị đã xác nhận -> `data/input/<ho_so>.project.yaml` (mẫu `config/project.example.yaml`).
4. Cần HTML: dựng đúng bố cục project_info.md (tiêu đề, gạch đầu dòng khu đất/hạng mục chính/file, ký hiệu, bảng, mục "* Cần kiểm").

## Gemini — GỌI SKILL `gemini-web` TRƯỚC (đăng nhập, cookie, quy tắc gửi, selector, thời gian đo)
- Bước đầu: skill `gemini-web` (`gemini-status`; cookie chết -> `gemini-cookie`). Mọi quy tắc Playwright nằm ở đó:
  **CHỈ GỬI FILE PDF, KHÔNG BAO GIỜ GỬI HÌNH**; Pro "Thấp" / 1 cuộc trò chuyện; nhiều trang -> chunk 8 trang, TỐI ĐA 10 tab,
  giãn cách như người thật;
  có kết quả -> lưu tạm `data/cache/raw/` rồi xoá cuộc trò chuyện.
- Lệnh chuẩn: `info "<pdf>" --gemini-pages smart` — tự lọc trang gửi Gemini (giữ trang không có chữ + trang có từ khoá
  PCCC/quy mô/mặt bằng; bản scan -> cả hồ sơ). Kiểm chứng Liên Minh: 72 -> 49 trang, kết quả giống hệt bản đủ.
  Cần chắc chắn tuyệt đối thì `--gemini-pages 1-N` (cả hồ sơ). Bản scan chữ nhỏ: vẫn gửi PDF, giá trị nghi ngờ ghi `nghi_ngo.json` (không gửi ảnh).
- File trên **Google Drive** (`D:.DRIVE CÔNG TY\...`) có thể lỗi đọc giữa chừng (file online-only) -> chép về `data/input/` trước.
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

## Bẫy đã gặp (đọc trước khi kết luận)
- **Chữ rác kiểu `3+Ҫ1&+81*`** = font Arial Identity-H thiếu ToUnicode (bản vẽ ICIC). Tool đã tự sửa trong `vector_text`;
  nếu `pages` vẫn ra toàn "other" -> kiểm tra font khác (VNI đã có `vn_encoding.py`).
- **Ghi chú vẽ bằng nét** (không có trong lớp chữ): "bậc chịu lửa…", "chiều cao PCCC là…", GFA… chỉ Gemini đọc được -> giữ với `*`
  nếu câu căn cứ có nhãn trường; câu có trong lớp chữ mà số không khớp -> bị loại (Gemini bịa).
- **Tên hạng mục trong project.yaml phải trùng tên trên bảng bản vẽ** ("NHÀ KHO 1A", không phải "Kho 1A"), nếu không bảng tách đôi cột.
- Khu vực trong nhà (KHU VĂN PHÒNG, khu trung chuyển, khu sắp xếp hàng hóa) có thể bị tách thành cột hạng mục -> gộp lại khi trình bày.
- **Cấp S0** hay lấy nhầm từ câu "tường ngoài không chịu lực có cấp nguy hiểm cháy S0" (nói về cấu kiện, không phải cả nhà) -> ghi chú cho người dùng.
- Chiều cao PCCC trên mặt đứng thường chỉ là nhãn, số nằm ở nét kích thước -> không có trong text.
- Nhà kho F5.x: hạng cháy nổ bắt buộc; thông số từng gian (diện tích, chiều cao, khối tích, số người) nằm trong "BẢNG TÍNH KHOẢNG CÁCH… CHO GIAN PHÒNG" trên mặt bằng tầng.

- **Nhà xưởng nhiều xưởng đánh số** (Luật Phú Trường): mỗi mặt bằng ghi `TẦNG 1 NHÀ XƯỞNG CHO THUÊ 02, 03: 2000 M2`
  -> tool tách từng xưởng, tính số tầng / diện tích XD (tầng 1) / tổng sàn, và gán ghi chú trên trang ("BẬC CHỊU LỬA LÀ BẬC IV")
  cho xưởng đó. Ghi chú tên trần "Nhà xưởng cho thuê có hạng C, F5.1" áp cho mọi xưởng đánh số.
- **Số có dấu cách nghìn** "36 510 m3" đã đọc đúng (trước bị cắt còn 36). "Hạng sản xuất: Hạng C" = hạng cháy nổ.
- **Thuyết minh chữa cháy ngoài nhà** ("Chọn nhà xưởng 08… Khối tích 36 510 m3") ghi cho tên chung -> tool KHÔNG gán khối tích
  cho xưởng nào, chỉ cảnh báo; hỏi người dùng xưởng nào.
- Chọn trang cho Gemini: `--gemini-pages 1,4,10,15,...` (bìa, tổng mặt bằng có bảng hạng mục, mặt bằng tầng 1 + mặt cắt mỗi
  nhóm hạng mục, thuyết minh) — tất cả vào 1 PDF. Các trang khác vẫn đọc vector. Luôn là Gemini **web + cookie**, không API.
- Tên nhiều số "Nhà xưởng 02, 03, 04, 08" tách thành 4 xưởng; "Nhà xưởng 01" ~ "NHÀ XƯỞNG CHO THUÊ 01" gộp 1 cột.

## Ví dụ đã làm
`BẢN VẼ TD LUẬT PHÚ TRƯỜNG.pdf` (178 trang): 8 nhà xưởng cho thuê 2 tầng (01: 900 m²/tầng; 02,03,04,08: 2000; 05,06,07: 2400),
bậc IV, F5.1, hạng C, S0; nhà văn phòng F4.3 cao PCCC 5,97 m (tr.6); thuyết minh chữa cháy tr.127. Chiều cao PCCC xưởng chưa có trong text.
`19. BVPCCC .signed….pdf` (FUMEI, 203 trang SCAN, A3): bảng "QUY MÔ PCCC" chữ đỏ nhỏ tr.12 (5 nhà: NX1 C/19,8 m/II/S0/3 tầng/
12.856 m²/189.823,2 m³; NX2 C/28 m/II/S0/3 tầng/5.201,5 m²/131.198,22 m³), danh sách hạng mục tr.4, chiều cao PCCC 9,15 m tr.10.
Gửi PDF đọc sai bảng chữ nhỏ (đã đối chiếu tay bằng ảnh phóng to) -> ghi nghi_ngo.json. `BVTK TD LIÊN MINH.pdf` (72 trang có text, 114 MB, trên Drive): nhà kho + xưởng cơ khí,
bảng thống kê tr.3–4: xưởng cơ khí 54×26 cao 9 m 1404 m², nhà kho 1188 m², nhà bảo vệ 20, trạm điện 24,6 (cao "-"),
trạm bơm 25 (4,2 m), bể nước PCCC 116,96 (1,95 m); kho F5.2 hạng C, xưởng F5.1 hạng D, bậc IV, S0, cao PCCC 7 m (tr.3–4).
`114.TD.30.01.2024 BV KT BW ĐỒNG AN.pdf` (42 trang A0): bảng hạng mục ở tr.7, ghi chú PCCC kho 1A tr.10–13, kho 1B tr.22–25,
nhà phụ trợ tr.40. Đã xác nhận: kho bậc II, F5.2, hạng C, cao PCCC 16,75 m, S0; phụ trợ bậc III hạng E -> `data/input/bw_dong_an.project.yaml`.
