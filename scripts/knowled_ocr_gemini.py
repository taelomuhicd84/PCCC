"""OCR bản scan (PDF không có lớp chữ) bằng Gemini web: chia chunk trang -> chép nguyên văn -> ghép 1 file .txt để nạp kho.

    python scripts/knowled_ocr_gemini.py "<scan.pdf>" --ma qcvn10 [--trang-moi-chunk 6] [--tabs 4]
    python scripts/knowled_import_pdf.py data/ocr/qcvn10.txt --ma qcvn10 --ten "QCVN 10:2025" --tach 3

- Chỉ gửi FILE PDF (theo skill gemini-web), mỗi chunk một tab, tối đa --tabs tab song song, giãn cách như người thật.
- Có thể chạy lại: chunk đã có trong data/ocr/<ma>/ được bỏ qua. Kết quả OCR luôn là cho_duyet cho tới khi người dùng đối chiếu.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

PROMPT = (
    "Đây là các trang SCAN của một văn bản quy phạm tiếng Việt (file có {n} trang, tương ứng trang {a}–{b} của hồ sơ gốc). "
    "Hãy CHÉP LẠI NGUYÊN VĂN toàn bộ chữ trên mọi trang, đúng dấu tiếng Việt, đúng thứ tự đọc. "
    "Giữ nguyên số hiệu Điều/Khoản/Mục/điểm (ví dụ 'Điều 3.', '3.1.2', 'a)'), giữ nguyên đơn vị và con số. "
    "Bảng chép thành bảng markdown (| cột | cột |), dòng tiêu đề bảng ghi riêng một dòng dạng 'Bảng X. Tên bảng' ngay trên bảng. "
    "Không tóm tắt, không giải thích, không bỏ sót, không thêm lời dẫn. Chỗ không đọc rõ ghi [không rõ]. "
    "Bắt đầu mỗi trang bằng một dòng '=== TRANG k ===' với k là số trang gốc ({a}–{b}). Bỏ số trang và đầu trang/chân trang lặp lại."
)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--ma", required=True)
    ap.add_argument("--trang-moi-chunk", type=int, default=6, dest="per")
    ap.add_argument("--tabs", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    import fitz
    from pccc_checker.config import load_settings
    from pccc_checker.extractors import gemini_web
    from pccc_checker.extractors.gemini_extractor import backend_kwargs

    src = fitz.open(a.pdf)
    out_dir = ROOT / "data" / "ocr" / a.ma
    out_dir.mkdir(parents=True, exist_ok=True)
    chunks = [(i + 1, min(i + a.per, len(src))) for i in range(0, len(src), a.per)]
    todo = [(s, e) for s, e in chunks if not (out_dir / f"{s:03d}-{e:03d}.txt").exists()]
    print(f"{a.ma}: {len(src)} trang -> {len(chunks)} chunk, còn {len(todo)} chunk cần OCR")
    if todo:
        st = load_settings(None)
        kw = backend_kwargs(dict(st["gemini"], backend="web"))["web"]
        gemini_web.MAX_TABS = a.tabs
        web = gemini_web.GeminiWeb(**{**kw, "timeout_s": a.timeout})
        try:
            jobs = []
            for s, e in todo:
                part = fitz.open()
                part.insert_pdf(src, from_page=s - 1, to_page=e - 1)
                jobs.append((part.tobytes(deflate=True, garbage=3), PROMPT.format(n=e - s + 1, a=s, b=e), f"{a.ma}_{s}-{e}.pdf", "application/pdf"))

            def save(i, text):
                if isinstance(text, str):
                    s, e = todo[i]
                    (out_dir / f"{s:03d}-{e:03d}.txt").write_text(text, encoding="utf-8")
                    print(f"  chunk {s}-{e}: {len(text)} ký tự", flush=True)

            res = web.generate_many(kw.get("model") or st["gemini"]["web"]["model"], jobs, on_result=save, log=lambda m: print(m, flush=True))
            bad = [todo[i] for i, r in enumerate(res) if not isinstance(r, str)]
            if bad:
                print("chunk lỗi (chạy lại lệnh để thử tiếp):", bad)
        finally:
            web.close()
    parts = sorted(out_dir.glob("*.txt"))
    full = "\n".join(p.read_text(encoding="utf-8") for p in parts)
    (ROOT / "data" / "ocr" / f"{a.ma}.txt").write_text(full, encoding="utf-8")
    print(f"đã ghép {len(parts)}/{len(chunks)} chunk -> data/ocr/{a.ma}.txt ({len(full)} ký tự)")


if __name__ == "__main__":
    main()
