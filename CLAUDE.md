# PCCC Checker — hướng dẫn cho Claude Code

Tool kiểm tra bản vẽ PDF PCCC theo **QCVN 06:2022/BXD + Sửa đổi 1:2023** (TT 09/2023/TT-BXD, hiệu lực 01/12/2023),
ghi chú vị trí sai trực tiếp lên PDF. Người dùng là kỹ sư/người làm hồ sơ PCCC, giao tiếp **tiếng Việt**.

## Kiến trúc (đọc docs/ARCHITECTURE.md nếu cần chi tiết)

```
PDF ──extract──> extraction.json/.md ──check──> findings.json/report.md ──review──> ──annotate──> *_annotated.pdf (+ drawing.dxf)
     Gemini/vector      (dữ liệu bản vẽ)     rule engine YAML (0 token)   agent Claude       PyMuPDF
```

- `src/pccc_checker/extractors/` — "mắt": Gemini vision (`gemini`), text vector PDF (`vector`, offline), `hybrid` (mặc định).
- `src/pccc_checker/rules/` — "luật": engine + thư viện check; **nội dung luật nằm trong `rules/*.yaml`**, không hard-code trong Python.
- `src/pccc_checker/output/` — ghi chú PDF, báo cáo MD, xuất DXF.
- `prompts/` — prompt gửi Gemini. `config/settings.yaml` — model, dpi, rule packs. `.env` — `GEMINI_API_KEY`.
- Kết quả: `data/output/<tên-pdf>/`. Cache Gemini: `data/cache/` (chạy lại không tốn API).

## Nguyên tắc tiết kiệm token (QUAN TRỌNG)

1. **Claude KHÔNG tự đọc ảnh bản vẽ.** Gemini đọc ảnh; Claude chỉ đọc `extraction.md` / `findings.json` (văn bản ngắn).
2. Việc lặp/cơ học (chạy CLI, kiểm tra file) giao cho subagent model nhỏ (`drawing-reader`, `pdf-annotator` – haiku).
3. Phán đoán chuyên môn (bác bỏ false-positive, bổ sung lỗi luật không mã hoá được) giao `compliance-reviewer` (sonnet).
4. Luật kiểm tra được bằng số → viết vào YAML để engine chạy, đừng để LLM kiểm tra lại mỗi lần.
5. Subagent chỉ trả về tóm tắt ≤ 15 dòng + đường dẫn file; dữ liệu lớn nằm trong file.

## Lệnh

```bash
set PYTHONPATH=src            # (PowerShell: $env:PYTHONPATH="src")
python -m pccc_checker run <pdf> [--extractor hybrid|gemini|vector] [--grid 2x2] [--building config/building.yaml] [--set height_pccc_m=24]
python -m pccc_checker extract|check|annotate|dxf|rules ...
python -m pytest -q           # test offline, không cần API key
python scripts/make_sample_pdf.py data/input/sample.pdf
```

Slash command: `/check-pccc <pdf>` (quy trình đầy đủ nhiều agent), `/add-rule`, `/verify-rules`.

## Quy ước khi phát triển

- Thêm luật: ưu tiên YAML với check có sẵn (`min_attr`, `max_attr`, `bool_attr`, `required_attr`, `min_fire_rating`,
  `compare_attrs`, `condition_flag`, `missing_data`, `building_missing`); chỉ viết Python mới (`@register`) khi bắt buộc.
  Mỗi luật phải có `id`, `clause`, `source` (QCVN06|SD01), `severity`, `message`, `verified`. Thêm test vào `tests/`.
- Thêm loại phần tử bản vẽ: cập nhật `ELEMENT_TYPES` (models.py) + `prompts/gemini_extract.md` + layer DXF.
- Thêm quy chuẩn khác (TCVN 3890, TCVN 5738...): tạo rule pack mới trong `rules/` và khai báo ở `config/settings.yaml`.
- Toạ độ `bbox` luôn là point PDF gốc trên-trái. Thuộc tính đo dài luôn **mét**.
- **Không bao giờ** đặt `verified: true` cho luật nếu chưa đối chiếu nguyên văn (`docs/regulations/`, bản hợp nhất QCVN 06:2022 + SĐ1:2023).
- `.env` và `api.txt` chứa API key — không đọc/in nội dung ra màn hình, không commit.
- Không commit `.env`, `data/input`, `data/output`.
- Chạy `python -m pytest -q` trước khi báo xong.

## Đồng bộ GitHub (tự động)

Repo: https://github.com/taelomuhicd84/PCCC (nhánh `main`). Stop hook `.claude/hooks/run_tests_on_stop.py` chạy
pytest khi Claude kết thúc mỗi lượt: test PASS → tự commit + push (`git_sync.py`); FAIL → bắt Claude sửa tiếp, không push.
Sửa tay ngoài Claude Code → chạy `sync.bat [message]`. Không bao giờ commit `.env`, `api.txt`, `data/`.
