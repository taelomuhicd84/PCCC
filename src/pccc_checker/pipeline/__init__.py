"""Pipeline 8 bước · 2 cổng Claude (docs/ARCHITECTURE.md).

  intake      : PDF -> page_index.json   (loại trang, luồng LAYER/HON-HOP/SCAN, vùng ảnh, mã băm từng trang)
  facts       : project_info.json -> project_facts.json + cong1.md   (ô dữ liệu [giá trị, trang, bbox, H/M/L])
  rule_keys   : project_facts.json -> rule_keys.json                 (loại hình, bộ bảng tra, file cần nạp)
  consistency : findings.jsonl  (4 trạng thái D/KD/XM/NA; KD thiếu bằng chứng -> XM)
"""
