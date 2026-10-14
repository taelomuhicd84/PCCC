---
name: danh-gia-cong-nang
description: ĐÁNH GIÁ công năng công trình từ bản vẽ (khác info-building chỉ chép thông tin) — kết luận loại hình / bảng đối chiếu, nhóm F theo công năng, nhà hỗn hợp hay không, và chuyên đề + hệ thống PCCC nào thuộc diện (yêu cầu trang bị). Là CỔNG ÁP DỤNG: chuyên đề chưa được đánh giá ap_dung = true thì không chạy. Dùng sau Cổng 1, trước keys / doi-chieu; hoặc khi người dùng hỏi "công trình này phải kiểm những gì", "cần trang bị hệ thống gì".
---

# Đánh giá công năng → cổng áp dụng chuyên đề

**Khác `info-building`:** info chép đúng chữ trên bản vẽ (không suy). Skill này DỰA VÀO dữ liệu đã đọc để KẾT LUẬN.
Không đọc lại cả bản vẽ: chỉ JSON + phần 1 của mẫu hệ thống; cần nhìn → ảnh cắt `crops` (≤ 3).

```powershell
$env:PYTHONPATH="src"
python -m pccc_checker danh-gia data/output/<hồ sơ>   # khung danh_gia_cong_nang.json (mọi ap_dung = null), giữ ô đã điền
python -m pccc_checker keys data/output/<hồ sơ>       # sau khi điền: rule_keys.file chỉ còn chuyên đề / mẫu ap_dung = true
```

## Đầu vào (đọc ngắn)
`project_facts.json` (công năng, số tầng, cao PCCC, dt, khối tích, nhóm F ban_ve/tinh) · `project_info.json` `meta.khu_vuc`
(phòng/khu trong hạng mục) · `danh_muc_ban_ve.json` (có bản vẽ hệ thống nào) · `rules/qcvn06/00-dinh-nghia.md` (Bảng 6 nhóm nhà)
· `memory/overrides.json` (đã chốt → giữ nguyên, không đánh giá lại).

## Điền `danh_gia_cong_nang.json` cho từng hạng mục
1. **Công năng:** liệt kê khu/tầng → nhóm F từng khu (Bảng 6) → `nhom_nha_tinh`, `cong_nang_danh_gia` (1–2 câu), `can_cu`
   (trang + nguyên văn). ≥ 2 nhóm F khác nhau đáng kể → `hon_hop: true`.
2. **Loại hình** (`loai_hinh`, mã trong `pipeline/loai_hinh.py`): xác nhận hoặc sửa `de_xuat`. Nhà hỗn hợp → `hon-hop` chỉ khi
   các công năng phụ không phải phục vụ công năng chính (gara, nhà hàng trong khách sạn thường là phục vụ → giữ bảng chính,
   ghi lý do). Đổi loại hình → chạy lại `danh-gia` (ứng viên đổi theo bảng mới) rồi điền tiếp.
3. **Chuyên đề bảng công trình** (`chuyen_de.<cd>.ap_dung`): `true` khi hạng mục CÓ đối tượng của mục đó; `false` + lý do khi
   KHÔNG có đối tượng nào (thang máy chữa cháy: cao PCCC / phần ngầm không thuộc diện theo dòng "Yêu cầu trang bị";
   biển quảng cáo: không có biển; gian lánh nạn: ≤ 50 m…). Mục chỉ thiếu vài tiểu mục (không hầm, không thông tầng) vẫn
   `true` — skill chuyên đề tự ghi NA từng dòng.
4. **Mẫu hệ thống** (`he_thong.<Bxx>`): đọc file `doc_truoc` (phần 1 = đối tượng / yêu cầu trang bị) → so với số liệu
   (khối tích, số tầng, nhóm F, dt, hạng nổ) → `true` / `false`, `ly_do` ghi ID dòng + giá trị so. Nhiều mẫu cùng chuyên đề
   (B37–B44 chữa cháy): chỉ `true` mẫu của hệ thống thuộc diện / có trên bản vẽ (sprinkler → B39, khí FM200 → B41…).
5. **Không đủ dữ liệu → để `null`** + `ly_do: "thiếu <trường>, xem trang …"` (vẫn KHÔNG áp dụng). Không đoán.

## Báo kết quả (ngắn)
Bảng mỗi hạng mục: loại hình / mẫu bảng · nhóm F · chuyên đề áp dụng | không áp dụng | chờ (thiếu gì). Người dùng sửa →
ghi `memory/overrides.json` (`loai_hinh`) hoặc sửa thẳng file rồi `keys`.
