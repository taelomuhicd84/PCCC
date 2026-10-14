# Kiến trúc PCCC Checker — đọc & góp ý bản vẽ PCCC

Hợp nhất từ tài liệu "Kiến trúc hệ thống đọc & góp ý bản vẽ PCCC" (14/10/2026, `.claude/…docx`) với tool hiện có.
Bản vẽ chỉ bị đọc **một lần**: mọi bước sau làm việc trên JSON + bảng tra .md nhỏ.

## 5 nguyên tắc
1. **Đọc một lần, dùng nhiều lần.** Bản vẽ → JSON kèm bằng chứng (trang, vị trí, nguyên văn). Skill sau không mở lại bản vẽ.
2. **Tra theo khóa, không nạp cả quy chuẩn.** Mỗi skill nạp 1–2 bảng .md khớp loại hình, nhóm nhà, bậc chịu lửa
   (+ hạng nổ nếu sản xuất/kho) — theo `rule_keys.json` và `rules/_index.md`.
3. **Việc có đáp số chắc chắn giao cho mã.** So số, cộng diện tích, kiểm logic, chặn kết luận thiếu bằng chứng, ghi
   chú PDF đều là script; mô hình chỉ xét ca cần phán đoán.
4. **Không bằng chứng thì không kết luận.** KD phải có trang + bbox + nguyên văn + điều khoản; thiếu → tự hạ XM.
5. **Chỉ tra từ file đối chiếu.** Không có trong bảng → XM, không lấy điều khoản từ trí nhớ mô hình.

## Kiến trúc chốt 14/10/2026 — đầu ra là BẢNG ĐỐI CHIẾU, nên mọi thứ xếp theo mục của bảng
Mọi bảng đối chiếu thẩm duyệt (B4.x chung cư, B5.x hỗn hợp, B6.x văn phòng, B7.x khách sạn, B8–B10…) dùng CÙNG một
bộ mục lớn; bảng > 50 m chèn "Gian lánh nạn" làm mục 8 nên số thứ tự các mục sau lùi 1. Vì vậy:
1. **1 mục lớn của bảng = 1 skill chuyên đề = 1 file bảng tra.** 18 mục (bảng ≤ 50 m có 17). Nhận mục theo TÊN, không
   theo số. Khai báo một nơi: `src/pccc_checker/pipeline/chuyen_de.py` (`MUC`: NN cố định, slug, mã ID, tên, mẫu nhận
   tên mục, từ khoá tên bản vẽ) — `split_rules.py`, `rule_keys`, `sheets` (danh mục bản vẽ), `consistency` cùng đọc.
   Trước đây 13 skill gộp/tách khác bảng (he-thong-rieng gộp 5 mục, thoát nạn tách 3 file…) phải giữ 4 bảng ánh xạ.
2. **Mục dài tách phần theo tiểu mục** (`07-thoat-nan.1.md` = 7.1, `.2` = 7.2, `.3` = 7.3), mỗi phần ≤ ~12k ký tự →
   một lượt nạp vẫn 2–4k token, skill vẫn là một.
3. **Chọn bộ bảng = loại hình × dải chiều cao PCCC** (`rule_keys.BO`; khách sạn 28/50/150 m). Thêm B4/B5/B6 = chạy
   `docx_to_md.py` + `split_rules.py` cho bộ mới + 1 dòng `BO` + `LOAI_HINH`; skill không đổi.
4. **Thứ tự chạy = thứ tự bảng Word đầu ra.** Mục 1 `quy-mo` chạy đầu và dùng kết quả Cổng 1 (nó chốt bộ bảng, khóa tra;
   nhà nhiều công năng → XM "xét nhà hỗn hợp", không tự đổi bộ). Các mục sau độc lập → song song theo hạng mục × mục.
5. **ID dòng `K2-TN-012` → `src_map.json` → dòng R### của bảng Word gốc**: bước Word chỉ điền 2 cột cuối theo ID,
   không gõ lại bảng; PDF ghi chú dùng cùng ID.
6. Mục chỉ ghi "Thực hiện theo mẫu B34/B35/B36–B44/B45/B46/B48/B49/B50" → XM tới khi mẫu hệ thống đó được chuẩn hoá
   thành bộ bảng riêng (cùng quy trình docx → md). Thứ tự nên làm: B50, B34, B35, B45 (hồ sơ khách sạn nào cũng có).

7. **Gán chuyên đề cho trang theo LOẠI bản vẽ** (người dùng 14/10/2026, `chuyen_de.cd_of_sheet`): mặt đứng + mặt cắt →
   luôn có lối vào từ trên cao (`giao-thong-xe-chua-chay`) + ngăn cháy phương đứng (`ngan-chay.dung`); mặt bằng tầng →
   chỉ ngăn cháy phương ngang (`ngan-chay.ngang`); chi tiết buồng thang / thang bộ (BTB, TB) → `thoat-nan`; chi tiết thang
   máy chữa cháy → `thang-may-chua-chay`; trang của hạng mục phòng/trạm bơm PCCC → chỉ skill riêng `tram-bom` (NN 19,
   mẫu B36). `trang --cd ngan-chay` lấy cả hai tiểu mục; `--cd ngan-chay.dung` chỉ phương đứng.

| NN | Skill | NN | Skill | NN | Skill |
|---|---|---|---|---|---|
| 01 | quy-mo | 07 | thoat-nan (3 phần) | 13 | chua-chay (B36–B44) |
| 02 | bac-chiu-lua | 08 | gian-lanh-nan (> 50 m) | 14 | cap-dien (B48) |
| 03 | khoang-cach | 09 | thang-may-chua-chay (B50) | 15 | chieu-sang-su-co (B46) |
| 04 | giao-thong-xe-chua-chay | 10 | chong-tu-khoi (B34) | 16 | pha-do-bao-ho |
| 05 | bo-tri-cong-nang | 11 | binh-chua-chay (B45) | 17 | chong-set (B49) |
| 06 | ngan-chay (2–3 phần) | 12 | bao-chay (B35) | 18 | lien-lac |

## Phân vai
| Việc | Gemini (web + cookie) | Claude |
|---|---|---|
| Đọc bản vẽ thô (chữ, ảnh, nhiều trang) | làm chính (`info`, `extract`) | không đọc lại cả bản; chỉ xem ảnh cắt vùng nghi vấn |
| Cổng 1: thông tin tổng thể, phân loại | sửa theo phản hồi (đọc lại đúng trang) | soát chéo, kết luận Đúng / Sửa / Đọc lại |
| Chạy skill chuyên đề theo hạng mục | làm chính (tương lai) | hiện tại: Claude/subagent theo `doi-chieu` |
| Cổng 2: duyệt kết quả đối chiếu | giải trình khi bị hỏi | duyệt mọi KD + XM, lấy mẫu 10% D |
| Xuất Word, ghi chú bản vẽ, memory | — | làm chính (qua script) |

## Pipeline 8 bước · 2 cổng
```
1 intake ─► 2 info (Gemini+vector) ─► 3 facts ─► [CỔNG 1 Claude] ─► 4 keys ─► 5 chuyên đề (+ luật YAML) ─► 6 findings
   page_index.json   project_info.json  project_facts.json   verdict.json   rule_keys.json   findings.jsonl (D/KD/XM/NA)
                                         cong1.md                                                │
                                                                                                 ▼
                              8 annotate PDF / Word  ◄── 7 [CỔNG 2 Claude] ◄── consistency (KD thiếu bằng chứng → XM)
```
Cổng 1 trả "Đọc lại" → chỉ quay về bước 2 cho đúng trang/trường. Cổng 2 thấy KD thiếu bằng chứng → quay về bước 5 cho
đúng chuyên đề. Không bước nào chạy lại cả bộ bản vẽ; bản vẽ sửa đổi → `intake` so mã băm, chỉ đọc lại trang đổi.

| Bước | Lệnh / skill | Đầu ra | Trạng thái |
|---|---|---|---|
| 1 intake | `intake <pdf>` | `page_index.json`: loại trang, luồng LAYER/HON-HOP/SCAN, vùng ảnh (0–1), băm | ✅ |
| 2 thông tin tổng thể | `info <pdf> --gemini-pages smart` · skill `info-building` | `project_info.json/.md` | ✅ |
| 2a danh mục bản vẽ | `info` tự ghi · `trang <thư mục> [--cd …] [--html]` | `danh_muc_ban_ve.json/.md` (trang → ký hiệu, tên bản vẽ, hạng mục, chuyên đề); `rule_keys.trang_theo_chuyen_de` | ✅ |
| 2b trục, kích thước | skill 02 `truc-kich-thuoc` → `axes.json` | | ⏳ chưa có (dùng `extraction.json`) |
| 3 dữ liệu chuẩn | `facts <thư mục>` | `project_facts.json` (ô H/M/L, ban_ve/tinh), `cong1.md` | ✅ |
| Cổng 1 | skill `cong-claude` | `verdict.json`, `claude_doc_anh.json` | ✅ |
| 4 phân loại / khóa tra | `keys <thư mục>` | `rule_keys.json` | ✅ |
| 5 chuyên đề | skill `doi-chieu` + `skills/chuyen-de/*` ; `extract` + `hm-pages` + `check` (luật YAML, từng hạng mục) | dòng findings | ✅ khung · luật YAML ✅ |
| 6 hợp nhất | `findings <thư mục>` / `findings --check <file>` | `findings.jsonl` | ✅ |
| Cổng 2 | skill `cong-claude` | `verdict.json` | ✅ |
| 7 Word | `fill_docx.py` (template + 2 cột) | `bang_doi_chieu.docx` | ⏳ chờ template Word |
| 7b va chạm | `va-cham <thư mục> [--annotate]` · skill `xu-ly-va-cham` | `va_cham.json/.md`, `*_va_cham.pdf`, `Note phản hồi.docx` (mọi vị trí note, xếp theo trang) | ✅ |
| 8 ghi chú PDF | `annotate` (agent `pdf-annotator`) | `*_annotated.pdf`, `drawing.dxf` | ✅ (đọc findings.json) |

## Thư mục (ánh xạ cây trong tài liệu → repo)
| Tài liệu | Repo |
|---|---|
| `GEMINI.md`, `CLAUDE.md` | `GEMINI.md`, `CLAUDE.md` (L0) |
| `skills/core/00–07` | lệnh CLI + `.claude/skills/{info-building, gemini-web, cong-claude, doi-chieu}` |
| `skills/chuyen-de/*` | `skills/chuyen-de/<slug>/SKILL.md` (18 khung = 18 mục bảng đối chiếu, < 60 dòng) |
| `rules/_index.md`, `rules/qcvn06/00-dinh-nghia.md` | như tài liệu (luôn nạp) |
| `rules/qcvn06/<loại hình>/` | `rules/checklists/khach-san/k1|k2|k3/` (B7.1/7.2/7.3) |
| `rules/rules.json` + `compare.py` | `rules/qcvn06_2022_sd01_2023.yaml` + rule engine (`check`) |
| `memory/{glossary.md, lessons.md, overrides.json}` | như tài liệu |
| `scripts/{extract_pdf, consistency, annotate_pdf}.py` | `src/pccc_checker/{pipeline/*, extractors/*, output/*}` |
| `golden/` | `tests/golden/*.yaml` + `tests/test_real_world.py` |
| `projects/<tên>/{input, work, out}` | `data/input/` · `data/output/<tên>/` (work + out chung) · `data/cache/` |

## Schema trung gian
- **Ô dữ liệu**: `[giá trị, trang, [x0,y0,x1,y1] 0–1 gốc trên-trái | null, "H"|"M"|"L"]`; không đọc được → `[null,null,null,"L"]`.
  H = người dùng xác nhận / chữ vector / Gemini + Claude đọc ảnh khớp · M = Gemini ≥ 2 trang khớp / Claude lệch Gemini
  (lấy Claude) / tính toán · L = chỉ Gemini 1 trang. Ô từ trang SCAN chỉ được H khi 2 nguồn độc lập khớp.
- **page_index.json**: `[{trang, loai, tieu_de, luong, so_ky_tu, xoay, vung_anh: [[0–1]], hash}]`.
- **project_facts.json**: `{ten_cong_trinh, dt_khu_dat_m2, hang_muc_chinh, hang_muc: [{id: "HM01", ten, cong_nang,
  so_tang_noi, so_tang_ham, so_tang_nha, cao_cong_trinh_m, cao_pccc_m, dt_xay_dung_m2, dt_san_tong_m2, khoi_tich_m3,
  cap_s, nhom_nha: {ban_ve, tinh}, bac_chiu_lua: {ban_ve, tinh}, hang_no: {ban_ve, tinh}, evid: {trường: nguyên văn}}],
  kiem_tra: [{hm, muc: loi|canh_bao, truong, noi_dung}]}`. `ban_ve` ≠ `tinh` tự nó là một phát hiện.
- **rule_keys.json**: `{luon_nap, hang_muc: [{hm, loai_hinh, bo, khoa, nguon, thieu, file: {chuyên đề: [md]}, ghi_chu}]}`.
- **findings.jsonl**: `{"id","hm","tang","cd","rule","yc","ht","tt","ly_do","truc","trang","bbox","conf","evid","dieu_khoan","nguon"}`,
  `tt` ∈ D / KD / XM / NA. `consistency.validate` hạ KD → XM khi thiếu trang/bbox/evid hoặc rule không có trong bảng tra.
- `axes.json`, `layer_map.json` (ánh xạ layer theo nội dung, Claude xác nhận 1 lần ở Cổng 1): ⏳ chưa làm.

## Bảng tra .md
Mỗi file có front matter `chuyen_de / muc / phan / ap_dung / nguon / so_dong`, mỗi dòng 1 ID bền vững (vd `K2-TN-012`), cột Quy
định nguyên văn. Dựng lại từ Word: `scripts/checklists/docx_to_md.py` → `split_rules.py`. Chọn bộ khách sạn theo
chiều cao PCCC: k1 ≤ 28 m, k2 ≤ 50 m, k3 ≤ 150 m. Thêm loại hình = thư mục mới + 1 dòng `rules/_index.md` +
`LOAI_HINH` + `BO` trong `pipeline/rule_keys.py`; skill chuyên đề không phải sửa.

## Memory 4 tầng
| Tầng | File | Nạp khi | Ai ghi |
|---|---|---|---|
| L0 luật cố định | `GEMINI.md`, `CLAUDE.md` | luôn | người dùng |
| L1 kiến thức chung | `memory/glossary.md`, `rules/_index.md`, `rules/qcvn06/00-dinh-nghia.md` | mục lục luôn; còn lại theo skill | người dùng, Claude đề xuất |
| L2 dự án | `data/output/<tên>/*.json`, `data/input/<tên>.project.yaml`, `claude_doc_anh.json`, `verdict.json` | mở lại dự án / bản sửa đổi | script, Claude |
| L3 bài học | `memory/lessons.md`, `memory/overrides.json` | khi chạy skill liên quan (≤ 50 dòng/mục) | Claude đề xuất, người dùng duyệt |

Quy tắc: chỉ ghi L3 sau khi người dùng xác nhận (đề xuất để ở mục "Chờ duyệt"); mỗi bài học 1 dòng
"bối cảnh → sai gì → cách đúng → ví dụ"; quyết định đã chốt vào `overrides.json` để không hỏi lại.

## Đầu ra
Word và PDF ghi chú sinh từ cùng `findings.jsonl` sau Cổng 2, mã dòng xuất hiện ở cả hai.
Word: giữ bảng đối chiếu gốc + 2 cột "Đạt/Không đạt" (KD chữ đỏ, XM nghiêng cam — người dùng đồng ý) và "Ghi chú"
(`[Lý do] · Trục … · Trang … · Điều …`). PDF: comment tại trang + bbox của từng dòng KD/XM; trang SCAN thì Claude
vẽ khung lên ảnh cắt xem lại trước khi ghi.

## Tiết kiệm token / chống sai
- Phân luồng theo vùng: LAYER lấy chữ bằng script; chỉ vùng ảnh (HON-HOP) và trang SCAN mới cần thị giác, gửi ảnh cắt.
- Gemini: chỉ gửi PDF, `--gemini-pages smart` lọc trang; cache theo băm PDF + trang + prompt.
- Claude chỉ nhìn ngoại lệ: Cổng 1 đọc `cong1.md` + ảnh cắt vài trường; Cổng 2 đọc KD/XM + mẫu 10% D.
- Trường quyết định cần 2 nguồn độc lập (bảng thống kê + mặt cắt, hoặc Gemini + Claude đọc ảnh); `facts` tự kiểm logic
  (PCCC ≤ chiều cao công trình, tổng sàn ≥ diện tích XD, số tầng nhà ≥ số tầng nổi, khối tích hợp lý, F5 có hạng nổ).
- Golden: mỗi lần sửa skill/bảng tra chạy `pytest` (stop hook tự chạy).

## Lộ trình
1. ✅ Xương sống đọc: intake, info, facts, Cổng 1, schema, consistency.
2. ⏳ Một đường chạy trọn khách sạn (Hoàng Hùng, k2): `quy-mo` + `thoat-nan` → findings → Word. Template Word = file
   B7.x gốc (thư mục "Bảng đối chiếu sửa đổi 1"), điền theo `src_map.json`.
3. ⏳ Skill 02 trục/kích thước (`axes.json`: `truc_mat_bang` = lưới trục mặt bằng; `cao_do` = "trục đứng", cao độ theo
   mặt cắt/mặt đứng — người dùng xác nhận 14/10/2026), `layer_map.json` cho PDF xuất từ DWG.
4. ⏳ Bộ bảng nhà xưởng / kho / văn phòng; bảng số QCVN (1–5, E.1, G.9, H.2…) và mẫu hệ thống B34–B50.
5. ⏳ Gemini chạy skill chuyên đề (hiện Claude/subagent chạy theo `doi-chieu`); đưa `GEMINI.md` vào đầu prompt
   (đổi prompt làm mất cache — làm cùng lần đổi prompt kế tiếp).
6. ✅ Skill `xu-ly-va-cham` + lệnh `va-cham`: gộp mâu thuẫn (nghi_ngo.json, trường conflict, kiểm tra logic) → định vị
   từng giá trị (lớp chữ / bảng ảnh / Claude chỉ ô trong ảnh cắt) → `va_cham.json` + `*_va_cham.pdf`. Claude không hỏi
   người dùng, không chọn giá trị (yêu cầu 14/10/2026). ⏳ Chốt giá trị khi va chạm: chưa làm (người dùng quyết định sau).
7. ✅ Mọi hạng mục đều là hạng mục chính: `hm-pages` chia trang theo tên hạng mục trong chữ trang → `hm_pages.json`
   (sửa tay được); `check` chạy rule engine riêng từng hạng mục trên trang của nó, ngưỡng theo thông số của nó
   (`ProjectInfo.for_hang_muc`); finding có `hang_muc` → `findings.jsonl` cột `hm` = HM01… Trang tổng thể → "chung".

## Mở rộng
| Muốn | Làm ở đâu |
|---|---|
| Luật chạy bằng số | `rules/qcvn06_2022_sd01_2023.yaml` (hoặc `/add-rule`); check mới: `rules/checks.py` `@register` |
| Loại hình mới | `rules/checklists/<loại>/` + `rules/_index.md` + `pipeline/rule_keys.py` |
| Mục bảng mới | 1 dòng `MUC` trong `pipeline/chuyen_de.py` + `skills/chuyen-de/<slug>/SKILL.md` theo khung + chạy lại `split_rules.py` |
| Extractor mới | `extractors/base.py::Extractor` |
| Xuất định dạng mới | `src/pccc_checker/output/` + lệnh trong `cli.py` |
