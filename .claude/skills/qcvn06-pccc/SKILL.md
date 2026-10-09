---
name: qcvn06-pccc
description: Kiến thức nền QCVN 06:2022/BXD và Sửa đổi 1:2023 (an toàn cháy cho nhà và công trình) để review kết quả kiểm tra bản vẽ PCCC, phân biệt lỗi thật và false-positive, và soạn luật YAML. Dùng khi review findings, thêm luật, hoặc trả lời câu hỏi về yêu cầu thoát nạn/ngăn cháy.
---

# QCVN 06:2022/BXD + Sửa đổi 1:2023 — ghi nhớ cho reviewer

> Tóm tắt đã đối chiếu với bản hợp nhất `docs/regulations/QCVN 06 SỬA ĐỔI BỔ SUNG 10.2023.(pdf|docx)`.
> Khi cần nguyên văn: trích text bằng pymupdf rồi grep theo từ khoá/số khoản — KHÔNG đọc toàn văn (≈600k ký tự).
> Chi tiết những điểm sửa đổi: xem `references/sd01-2023.md`.

## Văn bản
- QCVN 06:2022/BXD ban hành kèm TT 06/2022/TT-BXD (hiệu lực 16/01/2023).
- Sửa đổi 1:2023 ban hành kèm TT 09/2023/TT-BXD ngày 16/10/2023, **hiệu lực 01/12/2023**. Chỉ gồm các nội dung
  sửa đổi/bổ sung; phần không nêu vẫn áp dụng QCVN 06:2022.

## Dữ liệu công trình cần có trước khi kết luận
Nhóm nguy hiểm cháy theo công năng (F1.1…F5.x, Phụ lục A), chiều cao PCCC, số tầng nổi/hầm, bậc chịu lửa (I–V),
cấp nguy hiểm cháy kết cấu (S0–S3), diện tích tầng, số người/tầng, có báo cháy/chữa cháy tự động không.
Thiếu thông tin → nhiều luật không xác định được ngưỡng: ghi rõ giả định thay vì kết luận.

## Thoát nạn (Phần 3) — các điểm hay kiểm tra
- **3.2.9** Lối ra thoát nạn: cao thông thuỷ ≥ 1,9 m; rộng ≥ 1,2 m (gian phòng F1.1 > 15 người; nhóm khác > 50 người,
  trừ F1.3), ≥ 0,8 m các trường hợp còn lại. Cửa 2 cánh chỉ tính bên cánh mở. Nhà cao PCCC > 28 m (trừ F1.3, F1.4):
  cửa thoát nạn từ hành lang chung, sảnh, buồng thang (trừ cửa ra ngoài trời) là cửa chống cháy ≥ EI 30.
- **3.2.10** Cửa trên đường thoát nạn mở theo chiều thoát ra ngoài. Không quy định chiều mở: gian phòng F1.3, F1.4;
  gian phòng ≤ 15 người (trừ hạng A, B); kho ≤ 200 m² không có người thường xuyên; buồng vệ sinh; lối ra chiếu thang loại 3.
- **3.2.11** Cửa buồng thang bộ: có cơ cấu tự đóng, chèn kín khe (trừ cửa mở trực tiếp ra ngoài).
- **3.2.6/3.2.7** Thường ≥ 2 lối ra từ tầng. 3.2.6.2 a) (SĐ1): tầng nhà F1.2, F2, F3, F4.2–F4.4 được 1 lối ra:
  ≤ 15 m (≤ 300 m², ≤ 20 người); 15–21 m (≤ 200 m², ≤ 20 người, chữa cháy TĐ hoặc báo cháy TĐ toàn nhà, lối thoát
  khẩn cấp); 21–25 m (≤ 150 m², ≤ 15 người, báo cháy + chữa cháy TĐ, lối thoát khẩn cấp); kèm điều kiện không để xe/kho A,B,C.
- **3.2.8 (SĐ1)** ≥ 2 lối ra phải phân tán, cách nhau **≥ 1/2 đường chéo lớn nhất** mặt bằng (≥ 1/3 nếu toàn nhà có
  sprinkler). Khoảng cách đo giữa 2 cạnh XA nhất; **nếu giá trị đó < 7 m thì đo giữa 2 cạnh GẦN nhất**.
  (7 m là ngưỡng chọn cách đo, KHÔNG phải yêu cầu tối thiểu.) Hai buồng thang nối bằng hành lang: đo dọc hành lang.
- **3.3.5** Hành lang > 60 m phải chia đoạn bằng vách ngăn cháy loại 2 / vách, màn ngăn khói.
- **3.3.6** Đoạn nằm ngang đường thoát nạn: cao ≥ 2 m; rộng ≥ 1,2 m (hành lang chung > 15 người nhóm F1, > 50 người
  nhóm khác), 0,7 m (lối đến chỗ làm việc đơn lẻ), 1,0 m (còn lại). Trừ phần cánh cửa mở nhô ra hành lang.
- **3.4.2** Thang thoát nạn: độ dốc ≤ 1:1; mặt bậc ≥ 25 cm (trừ thang ngoài nhà); chiều cao bậc 5–22 cm.
- **3.4.3** Chiếu thang không hẹp hơn bản thang; chiếu nghỉ trung gian của bản thang thẳng dài ≥ 1,0 m.
- **3.4.11/3.4.12/3.4.13** L1 và thang loại 3: nhà ≤ 28 m (SĐ1: loại 3 được dùng tới 50 m, chống rơi ngã phần > 28 m);
  L2: ≤ 9 m (12 m nếu lỗ lấy sáng tự mở khi cháy); nhà > 28 m: buồng thang không nhiễm khói, trong đó có N1.
- **3.4.1 (SĐ1) – chiều rộng bản thang thoát nạn tối thiểu**: 1,2 m (F1.1 > 15 người/tầng); 1,0 m (F1.1 ≤ 15 người/tầng);
  1,2 m (nhà có > 200 người trên tầng bất kỳ trừ tầng 1); 0,7 m (nhà cao PCCC ≤ 15 m và ≤ 15 người/tầng thoát qua thang);
  0,9 m (các trường hợp còn lại). Không nhỏ hơn chiều rộng lối ra thoát nạn trên nó.
- **SĐ1:2023 – thang bộ loại 3** được dùng thoát nạn cho nhà cao PCCC > 28 m đến 50 m; phần trên 28 m phải có biện
  pháp chống rơi ngã toàn bộ các mặt hở.

## Ngăn cháy / ngăn khói
- Cửa ngăn cháy phải thể hiện giới hạn chịu lửa (EI…); cửa buồng thang có cơ cấu tự đóng, chèn kín khe.
- **3.1.7 (SĐ1) – tầng hầm**: tại mọi tầng hầm, ≥ 1 lối vào buồng thang thoát nạn phải qua sảnh ngăn khói, ngăn bằng
  vách ngăn cháy loại 1 (hoặc giải pháp tương đương). F1.2, F1.3, F2, F3, F4 cao PCCC < 28 m: nếu phải đi qua sảnh
  chung, lối vào buồng thang từ tầng hầm phải qua khoang đệm, có vách ngăn cháy loại 1.

## Đặc điểm hồ sơ thật (rút ra từ hồ sơ KS Hoàng Hùng, 2026-10)
- Font VNI/TCVN3 trong PDF CAD → tool tự chuyển VNI sang Unicode (`pdf/vn_encoding.py`); TCVN3 (.Vn*) chưa hỗ trợ.
- Hồ sơ gộp kiến trúc + kết cấu (50 trang, chỉ ~19 trang liên quan) → `pages` / `--pages auto`.
- Cửa chỉ ghi ký hiệu (D03, D07) trên mặt bằng, kích thước + EI ở trang "CHI TIẾT CỬA" → tool tự tra theo ký hiệu.
- Người thiết kế ghi sẵn "KHOẢNG CÁCH 2 LỐI THOÁT NẠN L=…", "ĐƯỜNG CHÉO CÔNG TRÌNH D=…", "SỨC CHỨA: … NGƯỜI",
  bảng tính chiều dài đường thoát nạn → tool dùng số liệu này cho 3.2.8, reviewer kiểm tra lại tính hợp lý.
- Khung tên thường không ghi nhóm F / chiều cao PCCC → tool suy nhóm F từ công năng (ghi vào assumptions);
  chiều cao PCCC cần lấy từ mặt cắt hoặc hỏi người dùng (`--set height_pccc_m=…`).
- Gemini (1 ảnh/trang A3) đọc tốt ký hiệu & bảng, nhưng **không đáng tin** ở: phán đoán thang thoát nạn hay không,
  loại thang (gán cùng giá trị cho mọi thang trên trang), tự "tính" số đo (vd mặt bậc 238 thay vì 250 ghi trên bản vẽ),
  tự suy "có sprinkler", tự ước lượng chiều cao PCCC. Tool đã chặn: số đo phải khớp text bản vẽ (`_unverified`),
  sprinkler/báo cháy cần chữ làm căn cứ, thang hợp nhất theo ký hiệu và chỉ tin ghi chú trên bản vẽ (căn thẳng hàng).
- 3.2.8 phụ thuộc mạnh vào sprinkler: L ≥ 1/2 đường chéo (không sprinkler) hay ≥ 1/3 (sprinkler toàn nhà).
  Hồ sơ kiến trúc thường không thể hiện sprinkler → luôn hỏi người dùng / hồ sơ cấp nước chữa cháy.
- Tầng "không có người có mặt thường xuyên" (sân thượng, tầng kỹ thuật) hay chỉ có 1 lối ra → xét ngoại lệ 3.2.6.2.
- Gemini free tier ~20 request/ngày/model: hồ sơ 19 trang gần hết quota. Cache giúp chạy lại không tốn quota;
  hết quota thì trang còn lại tự dùng text vector (ghi chú "Gemini không đọc được trang này").

## Cách review false-positive (thường gặp)
- Text tiêu đề/ghi chú có chữ "THOÁT NẠN" bị nhận là cửa thoát nạn.
- Kích thước lấy nhầm của phần tử bên cạnh (vector extractor ghép theo khoảng cách).
- Cửa phòng kỹ thuật/WC không nằm trên đường thoát nạn nhưng bị gắn `is_exit`.
- Tỉ lệ bản vẽ sai (mặt bằng có nhiều tỉ lệ / chi tiết phóng to) hoặc khung mặt bằng sai → kết quả 3.2.8 sai.
- Bản vẽ chi tiết thang (mặt cắt) có số đo bậc khác với mặt bằng → ưu tiên mặt cắt.
