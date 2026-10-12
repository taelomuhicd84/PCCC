"""Chuyển chữ Việt mã cũ VNI (font VNI-*) sang Unicode.

Bản vẽ CAD Việt Nam thường dùng font VNI: PDF lưu "MAËT BAÈNG" thay vì "MẶT BẰNG". Không chuyển thì regex và
ngữ cảnh gửi Gemini đều sai. Quy tắc VNI: nguyên âm + ký tự dấu đứng sau, vd a+ù=á, a+â=â, a+ä=ậ, a+ê=ă, a+ë=ặ;
ô=ơ, ö=ư, ñ=đ; i có ký tự riêng (í ì æ ó ò), ỵ=î.
"""
from __future__ import annotations

import re
import unicodedata

ACUTE, GRAVE, HOOK, TILDE, DOT = "́", "̀", "̉", "̃", "̣"
CIRC, BREVE, HORN = "̂", "̆", "̛"

_TONES = {"ù": ACUTE, "ø": GRAVE, "û": HOOK, "õ": TILDE, "ï": DOT}
_CIRC = {"â": "", "á": ACUTE, "à": GRAVE, "å": HOOK, "ã": TILDE, "ä": DOT}
_BREVE = {"ê": "", "é": ACUTE, "è": GRAVE, "ú": HOOK, "ü": TILDE, "ë": DOT}


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def _build() -> dict[str, str]:
    m: dict[str, str] = {}

    def add(key: str, val: str) -> None:
        m[key] = _nfc(val)
        m[key.upper()] = _nfc(val).upper()

    for v in "aeiouy":
        for code, mark in _TONES.items():
            add(v + code, v + mark)
    for v in "aeo":
        for code, mark in _CIRC.items():
            add(v + code, v + CIRC + mark)
    for code, mark in _BREVE.items():
        add("a" + code, "a" + BREVE + mark)
    for code, mark in _TONES.items():          # ơ, ư có dấu thanh
        add("ô" + code, "o" + HORN + mark)
        add("ö" + code, "u" + HORN + mark)
    # ký tự đơn
    for k, v in {"ô": "o" + HORN, "ö": "u" + HORN, "ñ": "d̶", "í": "i" + ACUTE, "ì": "i" + GRAVE,
                 "æ": "i" + HOOK, "ó": "i" + TILDE, "ò": "i" + DOT, "î": "y" + DOT}.items():
        add(k, v)
    m["ñ"], m["Ñ"] = "đ", "Đ"
    return m


_MAP = _build()
_PATTERN = re.compile("|".join(sorted(map(re.escape, _MAP), key=len, reverse=True)))


def vni_to_unicode(text: str) -> str:
    return _PATTERN.sub(lambda m: _MAP[m.group(0)], text)


def is_vni_font(font: str) -> bool:
    return font.upper().startswith("VNI")


def fix_span(text: str, font: str) -> str:
    return vni_to_unicode(text) if is_vni_font(font) else text


# --- Font Arial nhúng kiểu Identity-H thiếu /ToUnicode (vd bản vẽ ICIC): PDF chỉ lưu số glyph (GID), text đọc ra
# thành rác "3+Ҫ1&+81*" (= "PHẦN CHUNG"). Thứ tự glyph Arial cố định nên tra bảng GID -> Unicode (tạo từ cmap
# C:/Windows/Fonts/arial.ttf bằng fontTools) rồi gắn /ToUnicode cho font trước khi lấy text.
# shortcut: Arial nghiêng lệch thứ tự từ GID 748 (chữ Việt nghiêng có thể sai), cần bảng riêng nếu gặp nhiều.
_ARIAL_GID: dict[int, int] | None = None


def _arial_tounicode() -> bytes:
    global _ARIAL_GID
    if _ARIAL_GID is None:
        import json
        from pathlib import Path
        _ARIAL_GID = {int(k): v for k, v in json.loads((Path(__file__).with_name("arial_gid.json")).read_text()).items()}
    pairs = [f"<{g:04X}> <{u:04X}>" for g, u in _ARIAL_GID.items() if g <= 0xFFFF and u <= 0xFFFF]
    body = "".join(f"{len(c)} beginbfchar\n" + "\n".join(c) + "\nendbfchar\n"
                   for c in (pairs[i:i + 100] for i in range(0, len(pairs), 100)))
    return ("/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
            "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
            "/CMapName /Adobe-Identity-UCS def /CMapType 2 def\n"
            "1 begincodespacerange <0000> <FFFF> endcodespacerange\n" + body +
            "endcmap CMapName currentdict /CMap defineresource pop end end").encode()


def fix_identity_fonts(doc, page) -> int:
    """Gắn /ToUnicode cho font Arial Identity-H thiếu nó trên trang (sửa trong bộ nhớ, không ghi file). Trả về số font đã sửa."""
    n = 0
    for xref, _, typ, name, _, enc, *_ in page.get_fonts(full=True):
        if typ == "Type0" and enc == "Identity-H" and name.split("+")[-1].startswith("Arial") \
                and doc.xref_get_key(xref, "ToUnicode")[0] == "null":
            cmap = doc.get_new_xref()
            doc.update_object(cmap, "<<>>")
            doc.update_stream(cmap, _arial_tounicode())
            doc.xref_set_key(xref, "ToUnicode", f"{cmap} 0 R")
            n += 1
    return n
