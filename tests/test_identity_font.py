"""Font Arial Identity-H thiếu /ToUnicode (bản vẽ ICIC) phải đọc lại được tiếng Việt."""
from pathlib import Path

import pymupdf
import pytest

from pccc_checker.pdf.classify import classify_page
from pccc_checker.pdf.render import vector_text

ARIAL = Path("C:/Windows/Fonts/arial.ttf")


@pytest.mark.skipif(not ARIAL.exists(), reason="cần arial.ttf để dựng PDF mẫu")
def test_arial_identity_without_tounicode(tmp_path):
    pdf = tmp_path / "gid.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=800, height=400)
    page.insert_text((50, 100), "MẶT CĂT S2, S5", fontname="F0", fontfile=str(ARIAL), fontsize=20)
    page.insert_text((50, 200), "Tường ngăn cháy REI 150, dày 200mm, gạch đất sét nung", fontname="F0", fontfile=str(ARIAL), fontsize=20)
    for xref, *_, enc, _ in page.get_fonts(full=True):
        if enc == "Identity-H":
            doc.xref_set_key(xref, "BaseFont", "/ABCDEF+ArialMT")
            doc.xref_set_key(xref, "ToUnicode", "null")    # giả lập PDF xuất từ CAD: chỉ còn GID
    doc.save(pdf)

    with pymupdf.open(pdf) as d:
        assert "MẶT" not in d[0].get_text()                 # chưa sửa thì text là rác
    texts = [t["text"] for t in vector_text(pdf, 1)]
    assert texts == ["MẶT CĂT S2, S5", "Tường ngăn cháy REI 150, dày 200mm, gạch đất sét nung"]
    assert classify_page(pdf, 1)[0] == "section"
