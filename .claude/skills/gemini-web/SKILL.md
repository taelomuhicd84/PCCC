---
name: gemini-web
description: Điều khiển Gemini web (gemini.google.com) bằng Playwright + cookie để đọc bản vẽ PDF — đăng nhập/nạp cookie, kiểm tra phiên, gửi PDF theo chunk song song an toàn (tối đa 10 tab, giãn cách như người thật), lưu tạm kết quả rồi xoá cuộc trò chuyện. Gọi TRƯỚC khi đọc thông tin công trình (skill info-building) hoặc khi Gemini báo chưa đăng nhập / cookie chết / bị coi là bot.
---

# Skill Gemini web — Playwright điều khiển gemini.google.com

Code: `src/pccc_checker/extractors/gemini_web.py` (trình duyệt, đăng nhập, gửi/nhận, xoá chat) và
`extractors/info_gemini.py` (gộp trang thành PDF, chia chunk, lưu tạm). Cấu hình: `config/settings.yaml` mục `gemini.web`.
Người dùng chấp nhận rủi ro ToS (không dùng API key). KHÔNG đọc/in `.env`, cookie, không lưu cookie ra file rời.

## 1. Kiểm tra / đăng nhập (bước đầu mỗi lần dùng)
```powershell
$env:PYTHONPATH="src"
python -m pccc_checker gemini-status                 # exit 1 = chưa đăng nhập / cookie chết
python -m pccc_checker gemini-cookie "<file.json>"   # nạp cookie 1 lần -> .env (GEMINI_COOKIES), xoá file gốc, tự kiểm tra
```
- Theo docs người dùng `D:/Nhap-Claude/gemini-web-automation-prompts.md`: mỗi lượt mở **trình duyệt sạch**, nạp cookie
  TRƯỚC khi vào trang; trước khi đóng **lưu cookie Google vừa cấp lại (1PSIDTS) vào .env** -> cookie sống lâu, không phải xuất lại.
- Cookie mới được lưu sau MỖI kết quả + mỗi 60 s (`save_cookies`). Trước đây chỉ lưu khi đóng -> dừng ngang (TaskStop)
  2 lần làm .env giữ 1PSIDTS cũ -> cookie chết (13/10). Hạn chế dừng ngang; cần dừng thì chạy `gemini-status` ngay sau.
- Nhiều chunk chạy theo HÀNG ĐỢI: tab xong -> mở chunk kế (luôn ≤ 10 tab); tab treo quá `timeout_s` (300 s) -> bỏ, gửi lại PDF
  chunk nhỏ hơn. (Trước: chờ cả nhóm 10 tab -> 1 tab treo làm cả lượt đợi 10 phút.)
- Nhận: JSON Cookie-Editor, chuỗi `a=b; c=d`, giá trị 1PSID trần. Cần cả `__Secure-1PSID` + `__Secure-1PSIDTS`.
- Kiểm tra đăng nhập: chờ ≤ 30 s (ô nhập đứng yên 3 s = sống; nút đúng chữ "Đăng nhập"/"Sign in" hoặc accounts.google.com = chết).
  1 tab báo chết giữa lúc chạy nhiều tab có thể là báo nhầm -> chạy `gemini-status` lại trước khi nhờ người dùng.
- Cookie chết: xem ngày trong tên file (`..._json_<ms>`, `..._dd-mm-yyyy`); nhờ xuất MỚI từ cửa sổ ẩn danh rồi đóng (không đăng xuất).
- Không có cookie -> profile tool `data/chrome_gemini` + `gemini-login` (đăng nhập tay).
- ĐÃ LOẠI, đừng đề xuất lại: điều khiển/chép profile Chrome của người dùng (Chrome 136+ cấm; bản chép mất đăng nhập), MCP làm cầu nối.

## 2. Quy tắc gửi (yêu cầu người dùng — bắt buộc)
- **CHỈ GỬI FILE PDF — KHÔNG BAO GIỜ GỬI HÌNH ẢNH** (người dùng nhắc lại 2026-10-13: "gửi file pdf đừng gửi hình cho gemini nữa").
  Kể cả dự phòng: trang nào đọc qua PDF lỗi thì gửi lại PDF (chunk nhỏ hơn) hoặc bỏ qua + cảnh báo; code đã chặn đường gửi
  ảnh (`info_gemini.read_page`, `gemini_extractor.extract_page` với backend web). Không đề xuất `--upload png` / tile ảnh.
- Chrome chạy ẨN NỀN (`headless: true`, người dùng yêu cầu — không hiện cửa sổ). Bị Google chặn thì báo người dùng, đổi false.
- Gửi **file PDF** (tool gộp trang thành 1 PDF), model **Pro**, mức suy luận `thinking: Thấp` (nhanh, đủ để đọc bảng/ghi chú).
- Ít trang (≤ `chunk_pages` = 8): **1 cuộc trò chuyện** cho cả lượt; tin nhắn sau nghỉ ngẫu nhiên 5–15 s.
- Nhiều trang: chia chunk 8 trang, mỗi chunk 1 tab = 1 cuộc trò chuyện, **TỐI ĐA 10 tab cùng lúc** (`MAX_TABS`, code khoá —
  15 tab đã bị Google đăng xuất giữa chừng). Mở tab **giãn cách 8–20 s**; trong tab mỗi thao tác (vào trang, chọn model, tải
  file, gõ prompt, bấm gửi) nghỉ **1–3 s** như người thật. Chunk lỗi (JSON hỏng/rỗng) gửi lại 1 lần với chunk nhỏ bằng nửa.
- Có kết quả của phiên nào -> **lưu tạm ngay** câu trả lời gốc vào `data/cache/raw/<hash>_p<a>-<b>_<prompt>.txt` (+ JSON từng
  trang trong `data/cache/`), rồi **XOÁ cuộc trò chuyện đó trên Gemini**. Phiên đơn: xoá khi đóng.
- Bản scan A3 chữ nhỏ: Gemini hạ độ phân giải PDF -> có thể đọc sai/bịa -> ghi `nghi_ngo.json` cho người dùng đối chiếu
  (KHÔNG chuyển sang gửi ảnh). Muốn kiểm 1 vùng: Claude tự crop phóng to xem (không gửi Gemini).
- Mất đăng nhập -> dừng ngay, không đọc từng trang.

## 3. Selector đã kiểm chứng (giao diện tiếng Việt, 13/10/2026) — Google đổi giao diện thì sửa ở `gemini_web.py`
| Việc | Selector |
|---|---|
| Ô nhập | `rich-textarea [contenteditable='true']` |
| Menu model | `[data-test-id='bard-mode-menu-button']` -> mục `3.1 Pro` / `3.8 Flash` (chữ dính mô tả) + mức `Thấp/Trung bình/Cao` |
| Tải file | nút aria "tải lên" -> `[data-test-id='local-images-files-uploader-button']` |
| Gửi / Dừng | aria "Gửi tin nhắn" / "Dừng" |
| Xoá chat | aria "Mở trình đơn thao tác đối với cuộc trò chuyện." -> `[data-test-id='delete-button']` -> nút "Xoá" trong `.cdk-overlay-pane` (chữ "Xoá" dấu trên a) |

Dò selector mới: mở trang bằng `GeminiWeb._open()`, in `aria-label`/`data-test-id` các nút đang hiển thị (không in cookie).

## 4. QUY TRÌNH TỐI ƯU — nhanh mà không bị Google coi là bot (chốt 13/10/2026, từ số đo thực tế)
Thời gian đo: Gemini Pro "Thấp" trả lời 1 chunk 8 trang PDF mất **3–5 phút** (gần như không đổi theo số tab); mở 1 tab giãn
cách 8–20 s; 10 tab ≈ 2 phút chỉ để mở. => Tổng thời gian ≈ (số "đợt" chunk) × 4 phút + thời gian mở tab.
Cách rút ngắn là GIẢM SỐ CHUNK CHỜ NỐI TIẾP, KHÔNG phải tăng tab (15 tab đã bị đăng xuất).
1. **Chuẩn bị (0 token, ~10 s):** `gemini-status` (chết -> nhờ xuất cookie MỚI, kiểm giờ xuất trong tên/giờ file). File trên
   Drive -> chép về trước. Hồ sơ không cần lưu (người dùng nói "không lưu") -> PDF + `--out` vào scratchpad, xong xoá cache
   `data/cache/<hash>*` + `data/cache/raw/<hash>*`.
2. **Một lần chạy, không dừng ngang:** `info "<pdf>" --gemini-pages smart`, Chrome ẩn nền, chạy nền và CHỜ
   thông báo (không TaskStop: mỗi lần dừng ngang để lại chat chưa xoá + rủi ro cookie). Báo trước thời gian:
   ≤ 8 trang ~4 phút (1 phiên) · ≤ 80 trang ~6–8 phút (1 đợt ≤10 tab) · 81–160 trang ~10–12 phút (2 đợt, hàng đợi).
3. **Hàng đợi ≤ 10 tab** (code tự làm): tab xong -> lưu tạm `data/cache/raw/` + cache trang -> xoá chat -> đóng tab -> mở
   chunk kế. Tab treo > 300 s bỏ; chunk lỗi gửi lại PDF chunk nhỏ hơn (1 lần). Cookie tự lưu sau mỗi kết quả + mỗi 60 s.
4. **Chống bot:** ≤ 10 tab cùng lúc (an toàn hơn: 6–8 khi chạy nhiều hồ sơ liền nhau); mở tab cách 8–20 s; mỗi thao tác
   nghỉ 1–3 s; tin nhắn liên tiếp cùng phiên nghỉ 5–15 s; 1 tài khoản Google, không chạy 2 lệnh Gemini song song; giữa 2 hồ
   sơ lớn nghỉ vài phút; không chạy lại cùng hồ sơ khi đã có cache (cache dùng lại, 0 lượt Gemini).
5. **Sau khi xong:** dựng HTML + `nghi_ngo.json` (hoặc chỉ báo trong chat nếu "không lưu"), rồi `gemini-status` để chắc
   cookie vẫn sống cho lần sau.
**LỌC TRANG TRƯỚC (`--gemini-pages smart`, mặc định từ 13/10/2026, người dùng đồng ý):** 0 token, vài giây.
  - ≥ 80% trang có lớp chữ đọc được (≥ 60% chữ cái, ≥ 8 từ) -> gửi: 3 trang đầu + trang KHÔNG có chữ (ảnh/chữ vẽ nét — không
    đánh giá được, luôn gửi) + trang có từ khoá (so khớp đã bỏ dấu): THỐNG KÊ, QUY MÔ, BẬC CHỊU LỬA, HẠNG NGUY HIỂM, NHÓM NHÀ,
    CHIỀU CAO PCCC, KHỐI TÍCH, CẤP NGUY HIỂM, THOÁT NẠN, TỔNG MẶT BẰNG, MẶT BẰNG TẦNG 1/TRỆT, THUYẾT MINH, DIỆN TÍCH XÂY DỰNG…
    Từ khoá có ở > 40% số trang (khung tên "HỒ SƠ PCCC") bị bỏ qua. Dưới 80% (bản scan) -> gửi cả hồ sơ.
  - Đã kiểm chứng: Liên Minh 72 -> 49 trang, kết quả GIỐNG HỆT bản đủ (39/39 giá trị, 6 hạng mục). Thiên Ý 54 -> 35,
    The Sun 125 -> 81 (từ 2 đợt xuống ~1 đợt), Karaoke 60 -> 52. Lỗi cũ đã sửa: lọc theo "PCCC" khung tên (không giảm trang),
    bỏ sót trang không có chữ (Liên Minh tr.8/16/39 chứa bậc chịu lửa/hạng).
  - Code: `pdf/classify.smart_gemini_pages`, CLI `--gemini-pages smart` (vector vẫn đọc mọi trang).

## 5. Thời gian đã đo
FUMEI 20 trang scan: PDF 5,5 phút (ảnh PNG từng thử 41 phút — người dùng đã CẤM gửi ảnh). Liên Minh 72 trang có text: 9 tab × 8 trang, Pro "Thấp" = 3 phút 13 giây.
Một hồ sơ 118 trang: 15 tab bị Google đăng xuất giữa chừng -> hạ về ≤ 10 tab + giãn cách; chạy lại phần còn lại 8 chunk
hàng đợi ẩn nền = 8 phút 44 giây (gồm gửi lại 2 chunk JSON lỗi).
Báo người dùng thời gian dự kiến trước khi chạy.
