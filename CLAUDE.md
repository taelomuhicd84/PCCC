# PCCC Checker — hướng dẫn cho Claude Code

Tool kiểm tra bản vẽ PDF PCCC theo **QCVN 06:2022/BXD + Sửa đổi 1:2023** (TT 09/2023/TT-BXD, hiệu lực 01/12/2023),
ghi chú vị trí sai trực tiếp lên PDF. Người dùng là kỹ sư/người làm hồ sơ PCCC, giao tiếp **tiếng Việt**.

## Kiến trúc — pipeline 8 bước · 2 cổng Claude (chi tiết: docs/ARCHITECTURE.md)

```
intake ─► info ─► facts ─► [CỔNG 1] ─► keys ─► chuyên đề + luật YAML ─► findings ─► [CỔNG 2] ─► annotate / Word
page_index  project_info  project_facts  verdict   rule_keys   skills/chuyen-de, check   findings.jsonl
```
5 nguyên tắc: (1) đọc bản vẽ một lần, mọi bước sau dùng JSON có bằng chứng; (2) tra theo khóa — chỉ nạp file bảng tra
trong `rule_keys.json`; (3) việc có đáp số chắc chắn giao cho script; (4) không bằng chứng (trang + bbox + nguyên văn +
điều khoản) thì không kết luận KD; (5) chỉ tra từ bảng tra — không có thì XM, không lấy điều khoản từ trí nhớ.
- Trạng thái kết luận: **D** đạt · **KD** không đạt (đỏ) · **XM** cần xác minh (nghiêng, cam) · **NA** không áp dụng.
- Ô dữ liệu `[giá trị, trang, bbox 0–1, H|M|L]`; nhóm nhà/bậc/hạng nổ có `ban_ve` và `tinh` (lệch = phát hiện).
- Cổng 1 / Cổng 2: skill `cong-claude`. Đối chiếu: skill `doi-chieu` + `skills/chuyen-de/<slug>/SKILL.md` — **1 mục lớn của bảng
  đối chiếu = 1 skill = 1 file bảng tra** (18 mục, nhận theo TÊN mục; khai báo duy nhất `pipeline/chuyen_de.py`).
- `src/pccc_checker/pipeline/` — intake, facts, rule_keys, consistency, hm_pages, va_cham, sheets (danh mục bản vẽ). `extractors/` — Gemini web + vector.
  `rules/` — engine YAML; `rules/_index.md` + `rules/qcvn06/00-dinh-nghia.md` luôn nạp; `rules/checklists/` bảng .md.
- Memory dự án (file, Gemini và Claude dùng chung): L0 `GEMINI.md`/`CLAUDE.md` · L1 `memory/glossary.md` ·
  L2 `data/output/<tên>/*.json` · L3 `memory/lessons.md` (ghi mục "Chờ duyệt", người dùng duyệt mới chuyển lên),
  `memory/overrides.json` (quyết định đã chốt — không hỏi lại).
- Kết quả: `data/output/<tên-pdf>/`. Cache Gemini: `data/cache/` (chạy lại không tốn).

## Nguyên tắc tiết kiệm token (QUAN TRỌNG)

1. **Claude KHÔNG tự đọc ảnh cả trang bản vẽ.** Gemini đọc ảnh; Claude chỉ đọc JSON/MD ngắn (`cong1.md`, `findings.jsonl`).
   Ngoại lệ: Cổng 1/2 xem ảnh cắt đúng bảng/vùng nghi vấn (`crops`, ≤ 5 ảnh) — Claude đọc bảng ảnh chính xác hơn Gemini
   (BW Đồng An, Phú Trường 14/10/2026); giá trị đọc được ghi `claude_doc_anh.json`.
2. Việc lặp/cơ học (chạy CLI, kiểm tra file) giao cho subagent model nhỏ (`drawing-reader`, `pdf-annotator` – haiku).
3. Phán đoán chuyên môn (bác bỏ false-positive, bổ sung lỗi luật không mã hoá được) giao `compliance-reviewer` (sonnet).
4. Luật kiểm tra được bằng số → viết vào YAML để engine chạy, đừng để LLM kiểm tra lại mỗi lần.
5. Subagent chỉ trả về tóm tắt ≤ 15 dòng + đường dẫn file; dữ liệu lớn nằm trong file.

## Lệnh

```bash
set PYTHONPATH=src            # (PowerShell: $env:PYTHONPATH="src")
python -m pccc_checker run <pdf> [--extractor hybrid|gemini|vector] [--grid 2x2] [--building config/building.yaml] [--set height_pccc_m=24]
python -m pccc_checker pages <pdf>          # phân loại trang (0 token), --pages auto mặc định chỉ xử lý trang liên quan
python -m pccc_checker crops <pdf> --pages 7,10   # cắt bảng dán dạng ảnh ra PNG (0 token) để kiểm giá trị *
python -m pccc_checker intake <pdf>               # page_index.json: luồng LAYER/HON-HOP/SCAN + băm (in trang đổi)
python -m pccc_checker facts data/output/<tên>    # project_facts.json + cong1.md (Cổng 1)
python -m pccc_checker keys data/output/<tên>     # rule_keys.json
python -m pccc_checker trang data/output/<tên> [--cd thoat-nan] [--html]   # danh mục bản vẽ: trang -> tên bản vẽ / chuyên đề
python -m pccc_checker hm-pages data/output/<tên> # hm_pages.json: trang -> hạng mục (check chạy riêng từng hạng mục)
python -m pccc_checker va-cham data/output/<tên> [--annotate]   # va_cham.json + PDF ghi chú (skill xu-ly-va-cham)
python -m pccc_checker findings data/output/<tên> # findings.json -> findings.jsonl; --check <file> sau khi ghi thêm
python -m pccc_checker extract|check|annotate|dxf|rules ...
python -m pytest -q           # test offline, không cần API key
python scripts/make_sample_pdf.py data/input/sample.pdf
```

Slash command: `/check-pccc <pdf>` (pipeline đầy đủ, 2 cổng), `/add-rule`, `/verify-rules`.
Skill: `info-building` (bước 1–3), `gemini-web`, `cong-claude` (2 cổng), `doi-chieu` (bước 5), `qcvn06-pccc`.

## Quy ước khi phát triển

- Thêm luật: ưu tiên YAML với check có sẵn (`min_attr`, `max_attr`, `bool_attr`, `required_attr`, `min_fire_rating`,
  `compare_attrs`, `condition_flag`, `missing_data`, `building_missing`); chỉ viết Python mới (`@register`) khi bắt buộc.
  Mỗi luật phải có `id`, `clause`, `source` (QCVN06|SD01), `severity`, `message`, `verified`. Thêm test vào `tests/`.
- Thêm loại phần tử bản vẽ: cập nhật `ELEMENT_TYPES` (models.py) + `prompts/gemini_extract.md` + layer DXF.
- Thêm quy chuẩn khác (TCVN 3890, TCVN 5738...): tạo rule pack mới trong `rules/` và khai báo ở `config/settings.yaml`.
- Loại hình / bảng đối chiếu (15 loại, B4.1–B18): khai báo duy nhất `pipeline/loai_hinh.py`; bảng chọn theo CÔNG NĂNG đọc ở bước info
  (tên hạng mục → công năng → nhóm F duy nhất). Thêm loại: 1 dòng `LOAI` + `docx_to_md.py` + `split_rules.py` + dòng `rules/_index.md`
  (`pipeline/rule_keys.py` `BO`). Bảng có mục lớn mới: thêm 1 dòng `MUC` (`pipeline/chuyen_de.py`) + `skills/chuyen-de/<slug>/SKILL.md`
  (khung 6 bước, < 60 dòng); chạy lại `split_rules.py`.
- Bảng tra .md chép nguyên văn quy chuẩn/bảng Word bằng script; không viết điều khoản theo trí nhớ.
- Toạ độ `bbox` luôn là point PDF gốc trên-trái. Thuộc tính đo dài luôn **mét**.
- **Không bao giờ** đặt `verified: true` cho luật nếu chưa đối chiếu nguyên văn (`docs/regulations/`, bản hợp nhất QCVN 06:2022 + SĐ1:2023).
- `.env` và `api.txt` chứa API key — không đọc/in nội dung ra màn hình, không commit.
- Không commit `.env`, `data/input`, `data/output`.
- Chạy `python -m pytest -q` trước khi báo xong.

## Đồng bộ GitHub (tự động)

Repo: https://github.com/taelomuhicd84/PCCC (nhánh `main`). Stop hook `.claude/hooks/run_tests_on_stop.py` chạy
pytest khi Claude kết thúc mỗi lượt: test PASS → tự commit + push (`git_sync.py`); FAIL → bắt Claude sửa tiếp, không push.
Sửa tay ngoài Claude Code → chạy `sync.bat [message]`. Không bao giờ commit `.env`, `api.txt`, `data/`.
