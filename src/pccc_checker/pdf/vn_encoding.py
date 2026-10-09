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
