# Module knowled: Đánh giá công năng → cổng áp dụng chuyên đề

**Khác `info-building`:** info chép đúng chữ trên bản vẽ (không suy). Module này DỰA VÀO dữ liệu đã đọc + kiến thức trong kho để KẾT LUẬN.
Không đọc lại cả bản vẽ: chỉ JSON + phần 1 của mẫu hệ thống; cần nhìn → ảnh cắt `crops` (≤ 3).

```powershell
$env:PYTHONPATH="src"
python -m pccc_checker danh-gia data/output/<hồ sơ>   # khung danh_gia_cong_nang.json (mọi ap_dung = null), giữ ô đã điền
python -m pccc_checker keys data/output/<hồ sơ>       # sau khi điền: rule_keys.file chỉ còn chuyên đề / mẫu ap_dung = true
python -m pccc_checker knowled tim "<tên hạng mục / công năng>"   # kiến thức về loại hình, nhóm F, ca đã gặp
```

## Đầu vào (đọc ngắn)
`project_facts.json` (công năng, số tầng, cao PCCC, dt, khối tích, nhóm F ban_ve/tinh) · `project_info.json` `meta.khu_vuc`
(phòng/khu trong hạng mục) · `danh_muc_ban_ve.json` (có bản vẽ hệ thống nào) · `knowled doc` các mục liên quan (Bảng 6 nhóm nhà
nằm trong `rules/qcvn06/00-dinh-nghia.md`, đã là nguồn của kho) · `memory/overrides.json` (đã chốt → giữ nguyên, không đánh giá lại).

## Điền `danh_gia_cong_nang.json` cho từng hạng mục
0. **Tra kho trước:** `knowled tim "<tên hạng mục>"`. Có mục `verified` → theo đó. Có mục `cho_duyet` → dùng làm gợi ý, ghi rõ trong
   `ly_do` "theo kiến thức chờ duyệt <id>". Hạng mục không có bảng (vd nhà hàng/tiệc cưới) → `chua-xac-dinh`, không đoán.
1. **Công năng TỪNG hạng mục (lệnh `cong-nang`, 0 token):** mỗi hạng mục có công năng riêng → tra bảng theo công năng của CHÍNH hạng mục đó
   (nhà hàng, nhà xe, nhà ở, trạm bơm… không gộp thành một nhà). Chạy `python -m pccc_checker cong-nang data/output/<hồ sơ>`:
   gán khu vực → nhóm F (`knowledge/cong-nang/_tu-khoa.yaml`, theo Bảng 6 `knowled doc bang-6-phan-nhom-nha`), cộng diện tích, áp **quy tắc 70 %** của
   nhà hỗn hợp (QCVN 06 1.4.41: `knowled doc qcvn06-1-4-41-nha-hon-hop`; quy trình `knowled doc cach-xac-dinh-nha-hon-hop`). Kết quả mỗi hạng mục:
   **đơn năng Fx.y** · **HỖN HỢP** · **KHÔNG CHẮC** (kèm lý do) · kỹ thuật/PCCC. `--ap-dung` điền sẵn các ô chắc chắn vào `danh_gia_cong_nang.json`.
   Hạng mục KHÔNG CHẮC → Claude xét: đọc cảnh báo, mở `project_info_chi_tiet.md`/ảnh cắt đúng trang để bổ sung diện tích hoặc phân loại khu; thiếu thì
   để `null` + lý do (không đoán), không dùng kiến thức "chờ duyệt" để kết luận hỗn hợp.
2. **Loại hình** (`loai_hinh`, mã trong `pipeline/loai_hinh.py`): hỗn hợp → `hon-hop` (B5.x, bộ k1/k2/k3 theo chiều cao PCCC); đơn năng → bảng của công năng
   chính (xác nhận hoặc sửa `de_xuat`). Công năng không có bảng (vd nhà hàng/tiệc cưới F3.2) → `chua-xac-dinh`, người dùng chốt. Đổi loại hình → chạy lại
   `danh-gia` rồi điền tiếp. Hạng mục kỹ thuật (trạm bơm, TBA) dùng skill/bảng riêng, không xét hỗn hợp.
   **Học từ ca đã gặp:** khu vực chưa phân loại → thêm 1 dòng vào `_tu-khoa.yaml` (khop, nhom, loai, nguon); ca đặc biệt → `knowled them` (nhóm `cong-nang`).

3. **Chuyên đề bảng công trình** (`chuyen_de.<cd>.ap_dung`): `true` khi hạng mục CÓ đối tượng của mục đó; `false` + lý do khi
   KHÔNG có đối tượng nào (thang máy chữa cháy: cao PCCC / phần ngầm không thuộc diện theo dòng "Yêu cầu trang bị";
   biển quảng cáo: không có biển; gian lánh nạn: ≤ 50 m…). Mục chỉ thiếu vài tiểu mục (không hầm, không thông tầng) vẫn
   `true` — `goi` tự ghi NA từng dòng.
4. **Mẫu hệ thống** (`he_thong.<Bxx>`): đọc file `doc_truoc` (phần 1 = đối tượng / yêu cầu trang bị) → so với số liệu
   (khối tích, số tầng, nhóm F, dt, hạng nổ) → `true` / `false`, `ly_do` ghi ID dòng + giá trị so. Nhiều mẫu cùng chuyên đề
   (B37–B44 chữa cháy): chỉ `true` mẫu của hệ thống thuộc diện / có trên bản vẽ (sprinkler → B39, khí FM200 → B41…).
5. **Có đối tượng thì gọi chuyên đề** (người dùng 14/10/2026): `danh-gia` tự dò `DAU_HIEU` (`pipeline/chuyen_de.py`) trong tên
   hạng mục, công năng, khu vực trong hạng mục, tên bản vẽ → điền sẵn `ap_dung: true`, `nguon: dau_hieu` + căn cứ. Vd phòng bơm:
   hạng mục riêng HOẶC 1 phòng trong nhà kho/xưởng → `tram-bom` + B36 dù bảng của hạng mục không có mục trạm bơm. Bản vẽ có
   tên đối tượng gán cho hạng mục riêng của đối tượng (nếu có). Chỉ sửa thành `false` khi có lý do rõ (ghi `ly_do`).
6. **Không đủ dữ liệu → để `null`** + `ly_do: "thiếu <trường>, xem trang …"` (vẫn KHÔNG áp dụng). Không đoán.

## Học từ ca đã gặp
Người dùng sửa/chốt một đánh giá (loại hình, nhóm F, chuyên đề) → ghi `memory/overrides.json` (`loai_hinh`) VÀ nạp ca đó thành mục
kiến thức: `knowled them` (nhóm `cong-nang`), `cho_duyet` cho tới khi người dùng xác nhận — lần sau `knowled tim` ra ngay.

## Báo kết quả (ngắn)
Bảng mỗi hạng mục: loại hình / mẫu bảng · nhóm F · chuyên đề áp dụng | không áp dụng | chờ (thiếu gì). Người dùng sửa →
ghi `memory/overrides.json` hoặc sửa thẳng file rồi `keys`.

- Đã huấn luyện: sảnh đón (kể cả ghi 'không bố trí công năng') = công năng chính; hầm 'giải trí' né đỗ xe phải đề xuất cụ thể (F2.2 hoặc loại trừ) — xem `knowled doc sanh-don-va-ham-ne-do-xe`.
