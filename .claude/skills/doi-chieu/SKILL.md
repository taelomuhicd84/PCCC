---
name: doi-chieu
description: Đối chiếu hạng mục × chuyên đề với bảng tra .md (skill 04) — đọc rule_keys.json, nạp đúng 1 file bảng tra + khung skill chuyên đề trong skills/chuyen-de/, ghi findings.jsonl 4 trạng thái D/KD/XM/NA rồi chạy script chặn. Dùng sau Cổng 1 khi cần kết luận theo bảng đối chiếu (khách sạn k1/k2/k3), hoặc khi người dùng hỏi "đối chiếu", "kiểm chuyên đề thoát nạn/quy mô…".
---

# Đối chiếu theo chuyên đề (skill 04)

Điều kiện: đã qua Cổng 1 (`cong-claude`), có `project_facts.json` và `rule_keys.json` (`keys`).
Nguyên tắc: không mở lại bản vẽ; mỗi lượt chỉ nạp `rules/_index.md` + 1 khung chuyên đề + file bảng tra của nó.

```powershell
$env:PYTHONPATH="src"
python -m pccc_checker keys data/output/<hồ sơ>              # rule_keys.json: loại hình, bộ k1/k2/k3, file từng chuyên đề
python -m pccc_checker check data/output/<hồ sơ>/extraction.json   # luật YAML bằng số (0 token), nếu đã extract
python -m pccc_checker findings data/output/<hồ sơ>          # engine -> findings.jsonl (dòng nguồn "engine")
python -m pccc_checker findings --check data/output/<hồ sơ>/findings.jsonl   # sau khi ghi thêm dòng
```

## Thứ tự
1. Đọc `rule_keys.json`. Hạng mục `thieu` khóa quyết định → mọi chuyên đề cần khóa đó ghi 1 dòng XM, không đoán.
   `loai_hinh` chưa có bảng (nhà xưởng, kho, văn phòng…) → chỉ dùng kết quả luật YAML; báo người dùng là chưa có bộ bảng.
2. Chuyên đề = MỤC LỚN của bảng đối chiếu (18 mục, `pipeline/chuyen_de.py`; bảng ≤ 50 m có 17 vì không có gian lánh nạn).
   Với từng hạng mục × mục có file trong `rule_keys.file`: mở `skills/chuyen-de/<slug>/SKILL.md`, làm theo khung 6 bước;
   mục nhiều phần (`07-thoat-nan.1.md`, `.2`, `.3`) → mỗi phần một lượt.
   Trang cần đọc của chuyên đề: `rule_keys.trang_theo_chuyen_de[<chuyên đề>]` (từ danh mục bản vẽ `danh_muc_ban_ve.json`,
   lệnh `trang <thư mục> --cd <chuyên đề>`) — chỉ xem ảnh cắt / gửi Gemini đúng các trang này, không cả hồ sơ.
   Thứ tự: `quy-mo` (mục 1) LUÔN trước — nó chốt bộ bảng và khóa tra; sau đó theo số NN (= thứ tự bảng Word đầu ra).
   Mục chỉ dẫn "Thực hiện theo mẫu B34/B35/B36–B44/B45/B46/B48/B49/B50" → XM tới khi mẫu đó được chuẩn hoá.
   Nhiều hạng mục / chuyên đề độc lập → có thể giao subagent song song, mỗi subagent 1 cặp (HM, chuyên đề),
   chỉ trả về số dòng D/KD/XM/NA + đường dẫn file.
3. Cột "Quy định" của bảng là căn cứ duy nhất. Dòng dẫn tới bảng số chưa chuẩn hoá (Bảng 1–5, E.1, G.9, H.2…, xem
   "Còn thiếu" trong `rules/_index.md`) → XM, ghi tên bảng thiếu.
4. Ghi thêm vào `findings.jsonl` (append, mỗi dòng 1 JSON, `nguon: "<chuyên đề>"`), rồi `findings --check`.
5. Chuyển sang Cổng 2 (`cong-claude`).

## Lỗi hay gặp
`memory/lessons.md` mục `chung` + mục chuyên đề. Quyết định người dùng đã chốt: `memory/overrides.json`.
