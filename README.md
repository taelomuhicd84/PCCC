# PCCC Checker

Đọc bản vẽ **PDF PCCC**, kiểm tra theo **QCVN 06:2022/BXD + Sửa đổi 1:2023**, và **ghi chú vị trí sai trực tiếp lên PDF**
(khung màu + comment), kèm báo cáo Markdown và file DXF mở bằng AutoCAD.

- Gemini đọc ảnh bản vẽ (rẻ) → Claude chỉ điều phối & review văn bản ngắn (tiết kiệm token).
- Chạy được **offline không cần API** với bản vẽ PDF xuất từ CAD (đọc text vector).

## Cài đặt

```powershell
cd "F:\1_ToolMMo\2_VibeCode\New folder\pccc-checker"
pip install -r requirements.txt
copy .env.example .env      # rồi điền GEMINI_API_KEY (lấy tại https://aistudio.google.com/apikey)
```

## Sử dụng

**Cách 1 — trong Claude Code (khuyên dùng, có review của agent):**
```
cd "F:\1_ToolMMo\2_VibeCode\New folder\pccc-checker"
claude
> /check-pccc "D:\HoSo\MB_thoat_nan.pdf" --building config/building.yaml
```

**Cách 2 — dòng lệnh thuần (không tốn token Claude):**
```powershell
$env:PYTHONPATH="src"
python -m pccc_checker run "D:\HoSo\MB_thoat_nan.pdf"                       # hybrid: Gemini + text vector
python -m pccc_checker run ban_ve.pdf --extractor vector                    # offline, không cần API
python -m pccc_checker run ban_ve_A1.pdf --grid 2x2 --pages 3-6             # bản vẽ khổ lớn: cắt 4 ô
python -m pccc_checker run ban_ve.pdf --set function_group=F1.3 --set height_pccc_m=24 --set basements=1
python -m pccc_checker rules                                                # xem danh sách luật
python -m pccc_checker pages ho_so.pdf                                      # phân loại trang (kiến trúc/kết cấu...), 0 token
```
Hoặc kéo thả: `run.bat "duong\dan\ban_ve.pdf"`.

Kết quả tại `data/output/<tên-pdf>/`:
| File | Nội dung |
|---|---|
| `<tên>_annotated.pdf` | PDF gốc + khung đỏ/cam/xanh tại vị trí sai, nhãn `#n`, comment ghi điều khoản |
| `report.md` | Bảng lỗi: mức độ, trang, điều khoản, nội dung |
| `extraction.md` / `.json` | Dữ liệu đọc được từ bản vẽ |
| `drawing.dxf` | Phần tử + lỗi theo layer để mở trong AutoCAD |

Hồ sơ thật (đã thử với hồ sơ thẩm duyệt khách sạn 50 trang kiến trúc + kết cấu):
- Tự lọc trang liên quan (`--pages auto`), đọc font VNI, tra kích thước cửa từ bảng cửa, dùng số liệu người thiết kế ghi
  sẵn (khoảng cách 2 lối thoát nạn, đường chéo), hợp nhất thang theo ký hiệu qua các tầng.
- Mọi giá trị tool tự suy ra (nhóm F theo công năng, chiều cao PCCC ước lượng, sprinkler chưa rõ...) được liệt kê
  ở đầu `report.md` mục "⚠ Giả định" — hãy xác nhận và chạy lại với `--set`, vd:
  `--set has_auto_sprinkler=true --set height_pccc_m=30.55`.
- Gemini free tier giới hạn ~20 request/ngày/model; kết quả đã đọc được cache nên chạy lại không tốn quota.

Thông tin công trình (nhóm F, chiều cao PCCC, bậc chịu lửa…) quyết định ngưỡng của nhiều luật — nếu khung tên không
ghi, hãy khai báo qua `config/building.yaml` (mẫu: `config/building.example.yaml`).

## ⚠️ Lưu ý chuyên môn
- Các luật trong `rules/qcvn06_2022_sd01_2023.yaml` đã đối chiếu với bản hợp nhất QCVN 06:2022 + SĐ1:2023 trong
  `docs/regulations/` (`verified: true`). Khi quy chuẩn thay đổi, cập nhật văn bản rồi chạy `/verify-rules`.
- Bản vẽ khổ lớn / bản scan: dùng `--grid 2x2` (hoặc 3x3) để Gemini đọc chi tiết hơn.
- Đây là công cụ hỗ trợ rà soát; kết luận cuối cùng thuộc về kỹ sư/cơ quan thẩm duyệt PCCC.

## Đồng bộ GitHub
Mỗi lượt làm việc của Claude Code trong thư mục này: test đạt → tự commit + push lên
https://github.com/taelomuhicd84/PCCC. Sửa tay thì chạy `sync.bat "mô tả thay đổi"`.

## Cấu trúc thư mục
```
pccc-checker/
├─ CLAUDE.md                     # hướng dẫn cho Claude Code
├─ sync.bat                      # đồng bộ GitHub khi sửa tay
├─ .claude/
│  ├─ settings.json              # quyền, biến môi trường, Stop hook
│  ├─ hooks/                     # run_tests_on_stop.py, git_sync.py (tự push khi test đạt)
│  ├─ agents/                    # drawing-reader, compliance-reviewer, pdf-annotator, regulation-curator
│  ├─ commands/                  # /check-pccc, /add-rule, /verify-rules
│  └─ skills/qcvn06-pccc/        # kiến thức quy chuẩn cho agent
├─ config/                       # settings.yaml, building.example.yaml
├─ prompts/gemini_extract.md     # prompt gửi Gemini
├─ rules/                        # rule pack YAML (thêm TCVN khác tại đây)
├─ src/pccc_checker/
│  ├─ cli.py  models.py  config.py
│  ├─ pdf/          # render ảnh, text vector
│  ├─ extractors/   # gemini, vector, hybrid
│  ├─ rules/        # engine + checks
│  └─ output/       # annotate_pdf, report_md, export_dxf
├─ scripts/make_sample_pdf.py    # tạo bản vẽ mẫu có lỗi để thử
├─ tests/                        # pytest (offline)
├─ docs/ARCHITECTURE.md
└─ data/{input,output,cache}/
```
Phát triển thêm: xem `docs/ARCHITECTURE.md` mục "Mở rộng".
