"""Gọi Gemini qua giao diện web gemini.google.com (Playwright + Chrome) thay cho API key.

Đăng nhập lưu trong profile Chrome riêng `data/chrome_gemini` (cookie giữ giữa các lần chạy). Lần đầu chạy
`python -m pccc_checker gemini-login` rồi đăng nhập trong cửa sổ Chrome. Có thể nạp thêm cookie xuất từ tiện ích
Cookie-Editor: lưu một dòng `GEMINI_COOKIES=<json>` trong .env (không commit, không in ra).
Mỗi lần gọi mở một cuộc trò chuyện mới, chọn model theo tên hiển thị ("Pro", "Flash"...), tải ảnh, gửi prompt, chờ
câu trả lời đứng yên rồi trả về text. Playwright sync chỉ chạy trên 1 luồng -> extractor phải dùng workers=1.
shortcut: dựa vào cấu trúc trang Gemini (data-test-id, class) tháng 10/2026 — Google đổi giao diện thì sửa selector ở đây.
"""
from __future__ import annotations

import atexit
import json
import os
import re
import time
from pathlib import Path

from ..config import PROJECT_ROOT

URL = "https://gemini.google.com/app"
EDITOR = "rich-textarea [contenteditable='true']"
SIGN_IN = "a[href*='accounts.google.com/ServiceLogin'], a[href*='accounts.google.com/v3/signin']"
RESPONSE = "model-response message-content"
SEND = "button[aria-label='Gửi tin nhắn'], button[aria-label='Send message']"
STOP = "button[aria-label*='Dừng'], button[aria-label*='Stop']"


class GeminiWeb:
    def __init__(self, profile: str = "data/chrome_gemini", headless: bool = False,
                 timeout_s: int = 300):
        self.profile = PROJECT_ROOT / profile
        self.headless, self.timeout_s = headless, timeout_s
        self._pw = self._ctx = self.page = None

    # ------------------------------------------------------------ trình duyệt
    def _open(self):
        if self.page:
            return self.page
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._ctx = self._pw.chromium.launch_persistent_context(
            str(self.profile), channel="chrome", headless=self.headless, viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"])
        cookies = os.environ.get("GEMINI_COOKIES")              # nạp từ .env bởi load_settings()
        if cookies:
            self._ctx.add_cookies(_cookie_editor(json.loads(cookies)))
        self.page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        atexit.register(self.close)
        return self.page

    def close(self):
        try:
            if self._ctx:
                self._ctx.close()
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._pw = self._ctx = self.page = None

    def signed_in(self) -> bool:
        return self.page.locator(SIGN_IN).count() == 0

    def login(self, wait_s: int = 600) -> bool:
        """Mở Gemini, chờ người dùng đăng nhập trong cửa sổ Chrome (tối đa wait_s giây)."""
        pg = self._open()
        pg.goto(URL, wait_until="domcontentloaded")
        pg.wait_for_timeout(4000)
        end = time.time() + wait_s
        while not self.signed_in() and time.time() < end:
            pg.wait_for_timeout(2000)
        return self.signed_in()

    # ---------------------------------------------------------------- gọi model
    def generate(self, model: str, data: bytes, prompt: str, name: str = "tile.png", mime: str = "image/png") -> str:
        pg = self._open()
        pg.goto(URL, wait_until="domcontentloaded")                 # cuộc trò chuyện mới mỗi lần
        pg.locator(EDITOR).first.wait_for(timeout=30000)
        if not self.signed_in():
            raise PermissionError("Chưa đăng nhập Gemini web — chạy: python -m pccc_checker gemini-login")
        self._pick_model(model)
        with pg.expect_file_chooser() as fc:
            pg.locator("button[aria-label*='Upload'], button[aria-label*='tải lên']").first.click()
            pg.locator("[data-test-id='local-images-files-uploader-button']").click()
        fc.value.set_files({"name": name, "mimeType": mime, "buffer": data})
        pg.locator(EDITOR).first.click()
        pg.keyboard.insert_text(prompt)
        send = pg.locator(SEND).first
        end = time.time() + 120                                     # chờ ảnh tải lên xong (nút gửi bật lại)
        while time.time() < end and not (send.count() and send.is_enabled()
                                         and send.get_attribute("aria-disabled") != "true"):
            pg.wait_for_timeout(500)
        before = pg.locator(RESPONSE).count()
        send.click()
        text = self._wait_answer(before)
        if "{" not in text and re.search(r"limit|giới hạn|hạn mức", text, re.I):
            # hết lượt model này trong ngày -> báo như quota API để _call chuyển ngay sang model dự phòng
            raise RuntimeError(f"RESOURCE_EXHAUSTED PerDay (Gemini web {model}): {text[:150]}")
        return text

    def _pick_model(self, model: str):
        pg = self.page
        btn = pg.locator("[data-test-id='bard-mode-menu-button']")
        if (btn.inner_text() or "").strip().lower() == model.lower():
            return
        btn.click()
        # "3.1 Pro", "3.8 Flash" — khớp đúng tên, để "Flash" không trúng "Flash-Lite"
        item = pg.locator("[role=menuitem]").filter(has_text=re.compile(rf"\d[\d.]*\s+{re.escape(model)}(\s|$)", re.I)).first
        if item.count() == 0:
            pg.keyboard.press("Escape")
            raise RuntimeError(f"Gemini web không có model '{model}'")
        item.click()
        pg.wait_for_timeout(800)

    def _wait_answer(self, before: int) -> str:
        pg = self.page
        end = time.time() + self.timeout_s
        last, stable = "", 0
        while time.time() < end:
            pg.wait_for_timeout(1500)
            if pg.locator(RESPONSE).count() <= before:
                continue
            text = pg.locator(RESPONSE).last.inner_text()
            busy = pg.locator(STOP).count()
            stable = stable + 1 if text == last and text and not busy else 0
            last = text
            if stable >= 3:                                         # ~4,5 s không đổi -> trả lời xong
                return text
        raise TimeoutError(f"Gemini web không trả lời trong {self.timeout_s}s")


def _cookie_editor(items: list[dict] | dict) -> list[dict]:
    """Cookie JSON của tiện ích Cookie-Editor ([...] hoặc {"url":..., "cookies": [...]}) -> định dạng Playwright."""
    if isinstance(items, dict):
        items = items.get("cookies", [])
    same = {"no_restriction": "None", "lax": "Lax", "strict": "Strict"}
    out = []
    for c in items:
        ck = {"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path", "/"),
              "secure": c.get("secure", True), "httpOnly": c.get("httpOnly", False),
              "sameSite": same.get(str(c.get("sameSite")).lower(), "Lax")}
        if c.get("expirationDate"):
            ck["expires"] = int(c["expirationDate"])
        out.append(ck)
    return out
