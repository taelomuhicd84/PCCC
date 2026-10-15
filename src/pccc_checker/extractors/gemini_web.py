"""Gọi Gemini qua giao diện web gemini.google.com (Playwright + Chrome) thay cho API key.

Cách đăng nhập (ưu tiên từ 14/10/2026 — người dùng: "dùng 1 file json cookie mà đăng nhập riết"):
0. NẠP COOKIE VÀO PROFILE: `gemini-cookie <file>` thêm cookie vào profile Chrome của tool (`data/chrome_gemini`) rồi XOÁ
   cookie khỏi .env. Từ đó profile là nơi DUY NHẤT giữ phiên: Chrome tự nhận 1PSIDTS mới và ghi xuống ổ đĩa mỗi lần chạy
   -> 1 file JSON dùng lâu dài (tới khi Google thu hồi phiên / đăng xuất). Xuất cookie từ cửa sổ ẩn danh rồi ĐÓNG cửa sổ đó
   (không bấm đăng xuất) để trình duyệt của người dùng không xoay cookie song song với tool.
1. COOKIE (mặc định khi .env có GEMINI_COOKIES / GEMINI_1PSID) — theo docs của người dùng
   (D:/Nhap-Claude/gemini-web-automation-prompts.md): mỗi lượt mở trình duyệt SẠCH (không profile), nạp cookie TRƯỚC khi
   vào trang, và trước khi đóng LƯU LẠI cookie Google vừa cấp mới (nhất là __Secure-1PSIDTS) vào .env -> cookie không chết.
   Nạp lần đầu: `python -m pccc_checker gemini-cookie <file>` (JSON Cookie-Editor, chuỗi "a=b; c=d" hoặc giá trị 1PSID).
2. PROFILE (khi .env không có cookie): profile Chrome của tool, đăng nhập tay 1 lần bằng `gemini-login`.
Kiểm tra đăng nhập: chờ tối đa 30 s xem cái gì hiện ra (ô nhập đứng yên = sống; nút đúng chữ "Đăng nhập"/"Sign in" hoặc
chuyển sang accounts.google.com = chết) — không kiểm tra tức thời (DOM chưa render cho kết quả sai).
Cả lượt chạy dùng MỘT cuộc trò chuyện (yêu cầu người dùng), nghỉ ngẫu nhiên 5–15 s giữa các tin nhắn. Chọn model theo tên
hiển thị ("Argon", "Pro", "Flash"...), tải file, gửi prompt, chờ câu trả lời đứng yên rồi trả về text. Playwright sync chỉ chạy
trên 1 luồng -> extractor phải dùng workers=1.
shortcut: dựa vào cấu trúc trang Gemini (data-test-id, class) tháng 10/2026 — Google đổi giao diện thì sửa selector ở đây.
"""
from __future__ import annotations

import atexit
import json
import os
import random
import re
import sys
import time
from pathlib import Path

from ..config import PROJECT_ROOT

URL = "https://gemini.google.com/app"
EDITOR = "rich-textarea [contenteditable='true']"
SIGN_IN = ("a:text-is('Đăng nhập'):visible, a:text-is('Sign in'):visible, "
           "button:text-is('Đăng nhập'):visible, button:text-is('Sign in'):visible")
RESPONSE = "model-response message-content"
SEND = "button[aria-label='Gửi tin nhắn'], button[aria-label='Send message']"
STOP = "button[aria-label*='Dừng'], button[aria-label*='Stop']"
MAX_TABS = 10            # người dùng: tối đa 10 phiên cùng lúc, nhiều hơn Google coi là bot / spam
TAB_GAP = (8, 20)        # giây nghỉ ngẫu nhiên giữa 2 lần mở tab
STEP_GAP = (1, 3)        # giây nghỉ ngẫu nhiên giữa các thao tác trong 1 tab (như người thật)


def _human(gap=STEP_GAP):
    time.sleep(random.uniform(*gap))


ARGS = ["--disable-blink-features=AutomationControlled",          # tab nền (chunk song song) không bị Chrome hãm
        "--disable-background-timer-throttling", "--disable-renderer-backgrounding",
        "--disable-backgrounding-occluded-windows"]


class GeminiWeb:
    def __init__(self, profile: str = "data/chrome_gemini", headless: bool = False,
                 timeout_s: int = 300, profile_directory: str | None = None, thinking: str | None = None):
        self.profile = PROJECT_ROOT / profile
        self.profile_directory = profile_directory          # vd "Profile 6": profile con trong thư mục `profile`
        self.headless, self.timeout_s = headless, timeout_s
        self.thinking = thinking                            # mức suy luận trong menu model: Thấp | Trung bình | Cao
        self._pw = self._browser = self._ctx = self.page = None
        self.in_chat = False
        self.cookie_mode = self.live = False

    # ------------------------------------------------------------ trình duyệt
    def _open(self, use_env: bool = True):
        if self.page:
            return self.page
        from playwright.sync_api import sync_playwright
        raw = _env_cookies() if use_env else None
        self._pw = sync_playwright().start()
        if raw:                                             # cách 1: trình duyệt sạch + cookie
            self.cookie_mode = True
            self._browser = self._pw.chromium.launch(channel="chrome", headless=self.headless, args=ARGS)
            self._ctx = self._browser.new_context(viewport={"width": 1366, "height": 900},
                                                  extra_http_headers={"accept-language": "en-US,en;q=0.9,vi;q=0.8"})
            _stealth(self._ctx)
            self._ctx.add_cookies(parse_cookies(raw))
            self.page = self._ctx.new_page()
        else:                                               # cách 2: profile đăng nhập tay
            self._ctx = self._pw.chromium.launch_persistent_context(
                str(self.profile), channel="chrome", headless=self.headless, viewport={"width": 1280, "height": 900},
                args=ARGS + ([f"--profile-directory={self.profile_directory}"] if self.profile_directory else []))
            _stealth(self._ctx)
            self.page = self._ctx.pages[0] if self._ctx.pages else self._ctx.new_page()
        atexit.register(self.close)
        return self.page

    def save_cookies(self):
        """Lưu cookie Google vừa cấp lại (1PSIDTS) vào .env. Gọi sau MỖI kết quả + định kỳ, không chỉ lúc đóng:
        dừng ngang lượt chạy (kill) mà chưa lưu -> .env giữ 1PSIDTS cũ đã bị Google thay -> cookie chết (13/10/2026)."""
        try:
            if self._ctx and self.cookie_mode and self.live:
                save_env_cookies([c for c in self._ctx.cookies() if "google.com" in c["domain"]])
                self._saved_at = time.time()
        except Exception as e:
            print(f"[gemini-web] ⚠ không lưu được cookie mới: {str(e)[:100]}", file=sys.stderr)

    def close(self):
        if self.page and self.in_chat and self.live:        # phiên đơn xong việc -> xoá cuộc trò chuyện trên Gemini
            self._delete_chat(self.page)
        self.save_cookies()
        for obj in (self._ctx, self._browser):
            try:
                if obj:
                    obj.close()
            except Exception:
                pass
        try:
            if self._pw:
                self._pw.stop()
        except Exception:
            pass
        self._pw = self._browser = self._ctx = self.page = None
        self.in_chat = False

    def state(self, pg=None, timeout_s: int = 30) -> str:
        """'live' | 'dead' — chờ tối đa timeout_s tới khi trang rõ ràng (không kiểm tra tức thời)."""
        pg = pg or self.page
        end, seen = time.time() + timeout_s, None
        while time.time() < end:
            if "accounts.google.com" in pg.url or pg.locator(SIGN_IN).count():
                return "dead"
            if pg.locator(EDITOR).count():
                seen = seen or time.time()
                if time.time() - seen >= 3:                 # ô nhập đứng 3 s mà không hiện nút "Đăng nhập"
                    self.live = True
                    return "live"
            pg.wait_for_timeout(500)
        return "dead"

    def signed_in(self) -> bool:
        return self.state() == "live"

    def login(self, wait_s: int = 600, manual: bool = False) -> bool:
        """Mở Gemini, chờ người dùng đăng nhập trong cửa sổ Chrome (tối đa wait_s giây).
        manual=True (lệnh gemini-login): dùng profile, KHÔNG nạp cookie .env."""
        pg = self._open(use_env=not manual)
        pg.goto(URL, wait_until="domcontentloaded")
        end = time.time() + wait_s
        try:
            ok = self.state() == "live"
            while not ok and time.time() < end:
                pg.wait_for_timeout(2000)
                ok = self.state(timeout_s=5) == "live"
            if ok and manual:
                pg.wait_for_timeout(5000)                       # cho Chrome ghi cookie phiên vào profile
            return ok
        except Exception:                                       # người dùng đóng cửa sổ trước khi đăng nhập xong
            return False

    def seed_profile(self, raw) -> bool:
        """Nạp cookie (JSON / chuỗi) vào profile Chrome của tool, mở Gemini kiểm tra. Sống -> chờ Chrome ghi cookie
        xuống profile. Từ đó chạy theo cách PROFILE (không cần .env)."""
        pg = self._open(use_env=False)
        self._ctx.add_cookies(parse_cookies(raw))
        pg.goto(URL, wait_until="domcontentloaded")
        ok = self.state() == "live"
        if ok:
            pg.wait_for_timeout(5000)
        return ok

    # ---------------------------------------------------------------- gọi model
    def generate(self, model: str, data: bytes | list, prompt: str, name: str = "tile.png",
                 mime: str = "image/png") -> str:
        """data: bytes 1 file, hoặc list [(name, mime, bytes), ...] (tối đa 10 file/tin nhắn của Gemini web).
        Người dùng yêu cầu: cả lượt chạy dùng MỘT cuộc trò chuyện -> chỉ mở chat mới ở lần gọi đầu hoặc sau lỗi."""
        pg = self._open()
        if not self.in_chat:
            self._new_chat_on(pg)
        else:
            time.sleep(random.uniform(5, 15))                     # nghỉ giữa các tin nhắn cùng cookie
        self.in_chat = False                                        # lỗi giữa chừng -> lần sau mở chat mới
        before = self._send(pg, model, data, prompt, name, mime)
        text = self._check_limit(self._wait_answer(before), model)
        self.in_chat = True
        self.save_cookies()
        return text

    def generate_many(self, model: str, jobs: list, on_result=None, log=None) -> list:
        """Nhiều chunk song song theo HÀNG ĐỢI: mỗi job (data, prompt, name, mime) một TAB = một cuộc trò chuyện riêng
        (người dùng cho phép khi bản vẽ quá nhiều trang). Luôn giữ tối đa MAX_TABS tab; tab nào xong -> lưu tạm
        (on_result(i, text)), XOÁ cuộc trò chuyện, đóng tab và mở ngay job kế tiếp (không chờ cả nhóm — 1 tab treo từng
        làm cả nhóm đợi 10 phút). Mở tab giãn cách TAB_GAP như người thật. Mỗi tab chờ tối đa timeout_s.
        -> list text | Exception theo thứ tự job."""
        self._open()
        out: list = [None] * len(jobs)
        pending = list(range(len(jobs)))
        active: list = []                                   # [i, page, before, state, t_gửi]
        opened = 0
        while pending or active:
            if pending and len(active) < MAX_TABS:
                if opened:
                    _human(TAB_GAP)
                i = pending.pop(0)
                opened += 1
                data, prompt, name, mime = jobs[i]
                pg = self._ctx.new_page()
                try:
                    self._new_chat_on(pg)
                    active.append([i, pg, self._send(pg, model, data, prompt, name, mime), ["", 0], time.time()])
                except PermissionError:
                    raise
                except Exception as e:
                    out[i] = e
                    self._close_tab(pg)
                continue                                    # mở đủ tab trước (vẫn giãn cách), rồi mới chờ
            time.sleep(2)
            if time.time() - getattr(self, "_saved_at", 0) > 60:
                self.save_cookies()                         # định kỳ: dừng ngang cũng không mất cookie mới
            for job in list(active):
                i, pg, before, st, t0 = job
                try:
                    text = self._poll(pg, before, st)
                    if text is None and time.time() - t0 > self.timeout_s:
                        raise TimeoutError(f"Gemini web không trả lời trong {self.timeout_s}s")
                    if text is None:
                        continue
                    out[i] = self._check_limit(text, model)
                    if on_result:
                        on_result(i, out[i])                # lưu tạm TRƯỚC khi xoá cuộc trò chuyện
                    self.save_cookies()
                except Exception as e:
                    out[i] = e
                self._delete_chat(pg)
                self._close_tab(pg)
                active.remove(job)
                if log:
                    log(f"[gemini-web] xong {len(jobs) - len(pending) - len(active)}/{len(jobs)} chunk"
                        + (f" (lỗi: {str(out[i])[:60]})" if isinstance(out[i], Exception) else ""))
        return out

    @staticmethod
    def _close_tab(pg):
        try:
            pg.close()
        except Exception:
            pass

    def new_chat(self):
        """Lần generate sau mở cuộc trò chuyện mới."""
        self.in_chat = False

    def _new_chat_on(self, pg):
        pg.goto(URL, wait_until="domcontentloaded")
        _human()
        if self.state(pg) != "live":
            raise PermissionError("Gemini web chưa đăng nhập / cookie đã chết — nạp cookie mới: "
                                  "python -m pccc_checker gemini-cookie <file>, hoặc gemini-login")

    def _send(self, pg, model: str, data: bytes | list, prompt: str, name: str, mime: str) -> int:
        """Chọn model, tải file, gõ prompt, bấm gửi. -> số câu trả lời trước khi gửi."""
        self._pick_model(model, pg)
        _human()
        files = data if isinstance(data, list) else [(name, mime, data)]
        with pg.expect_file_chooser() as fc:
            pg.locator("button[aria-label*='Upload'], button[aria-label*='tải lên']").first.click()
            _human((0.5, 1.5))
            pg.locator("[data-test-id='local-images-files-uploader-button']").click()
        fc.value.set_files([{"name": n, "mimeType": m, "buffer": b} for n, m, b in files])
        _human()
        pg.locator(EDITOR).first.click()
        _human((0.5, 1.5))
        pg.keyboard.insert_text(prompt)
        _human()
        send = pg.locator(SEND).first
        end = time.time() + 180                                     # chờ file tải lên xong (nút gửi bật lại)
        while time.time() < end and not (send.count() and send.is_enabled()
                                         and send.get_attribute("aria-disabled") != "true"):
            pg.wait_for_timeout(500)
        before = pg.locator(RESPONSE).count()
        send.click()
        return before

    def _delete_chat(self, pg) -> bool:
        """Xoá cuộc trò chuyện đang mở (người dùng: có kết quả rồi thì xoá phiên trên Gemini).
        Selector kiểm chứng 13/10/2026 (menu thao tác cuộc trò chuyện -> delete-button -> hộp xác nhận). Lỗi: chỉ cảnh báo."""
        try:
            _human()
            pg.locator("button[aria-label*='thao tác đối với cuộc trò chuyện' i], "
                       "button[aria-label*='conversation actions' i]").first.click(timeout=8000)
            _human((0.5, 1.5))
            pg.locator("[data-test-id='delete-button']").first.click(timeout=8000)
            _human((0.5, 1.5))
            pg.locator(".cdk-overlay-pane button, [role=dialog] button, mat-dialog-container button").filter(
                has_text=re.compile(r"^\s*(X[oó]|Delete)", re.I)).first.click(timeout=8000)   # "Xoá"/"Xóa" (dấu khác nhau)
            pg.wait_for_timeout(1500)
            return True
        except Exception as e:
            print(f"[gemini-web] ⚠ không xoá được cuộc trò chuyện: {str(e)[:100]}", file=sys.stderr)
            return False

    @staticmethod
    def _check_limit(text: str, model: str) -> str:
        # chỉ thông báo hết lượt (ngắn); câu trả lời dài nhắc "giới hạn chịu lửa" KHÔNG phải hết lượt (lỗi 15/10/2026)
        if "{" not in text and len(text) < 400 and re.search(r"limit|giới hạn|hạn mức", text, re.I):
            # hết lượt model này trong ngày -> báo như quota API để _call chuyển ngay sang model dự phòng
            raise RuntimeError(f"RESOURCE_EXHAUSTED PerDay (Gemini web {model}): {text[:150]}")
        return text

    def _pick_model(self, model: str, pg=None):
        pg = pg or self.page
        btn = pg.locator("[data-test-id='bard-mode-menu-button']")
        btn.wait_for(timeout=30000)
        label = (btn.inner_text() or "").lower().split()      # nút ghi "Argon Cao" = model + mức tư duy đang chọn
        if label[:1] != [model.lower()]:
            btn.click()
            # "4 Argon", "3.1 Pro", "3.8 Flash" — khớp đúng tên, để "Flash" không trúng "Flash-Lite"; textContent có thể
            # dính liền mô tả ("3.8 FlashTrợ giúp toàn diện") nên không đòi khoảng trắng sau tên
            item = pg.locator("[role=menuitem]").filter(has_text=re.compile(rf"\d[\d.]*\s*{re.escape(model)}(?!-)", re.I)).first
            if item.count() == 0:
                pg.keyboard.press("Escape")
                raise RuntimeError(f"Gemini web không có model '{model}'")
            item.click()
            pg.wait_for_timeout(800)
        # SAU khi đổi model (đổi model có thể đặt lại mức tư duy); nút đã ghi đúng mức -> khỏi mở menu
        if self.thinking and not " ".join((btn.inner_text() or "").lower().split()).endswith(self.thinking.lower()):
            self._pick_thinking(pg, btn)

    def _pick_thinking(self, pg, btn):
        """Chọn mức suy luận (mặc định Thấp — settings.yaml). Không có mục -> cảnh báo rồi bỏ qua."""
        btn.click()
        item = pg.locator("[role=menuitem]").filter(has_text=re.compile(rf"^\s*{re.escape(self.thinking)}", re.I)).first
        sub = pg.locator("[role=menuitem]").filter(has_text=re.compile(r"^\s*(Cấp độ tư duy|Thinking)", re.I)).first
        if item.count() and not item.is_visible() and sub.count():   # từ 13/10/2026 mức tư duy nằm trong menu con
            sub.click()
            pg.wait_for_timeout(800)
        if item.count() and item.is_visible():
            item.click()
            pg.wait_for_timeout(500)
        else:                                              # không im lặng: model này không có mức tư duy đã chọn
            print(f"[gemini-web] ⚠ không thấy mức tư duy '{self.thinking}' — chạy mức mặc định của model", file=sys.stderr)
        for _ in range(2):                                 # đóng menu con + menu chính nếu còn mở
            if pg.locator("[role=menuitem]:visible").count():
                pg.keyboard.press("Escape")
                pg.wait_for_timeout(300)

    @staticmethod
    def _poll(pg, before: int, st: list) -> str | None:
        """Một lần kiểm tra câu trả lời; st = [text lần trước, số lần đứng yên]. -> text khi ~4,5 s không đổi."""
        if pg.locator(RESPONSE).count() <= before:
            return None
        text = pg.locator(RESPONSE).last.inner_text()
        busy = pg.locator(STOP).count()
        st[1] = st[1] + 1 if text == st[0] and text and not busy else 0
        st[0] = text
        return text if st[1] >= 3 else None

    def _wait_answer(self, before: int) -> str:
        pg, st = self.page, ["", 0]
        end = time.time() + self.timeout_s
        while time.time() < end:
            pg.wait_for_timeout(1500)
            text = self._poll(pg, before, st)
            if text is not None:
                return text
        raise TimeoutError(f"Gemini web không trả lời trong {self.timeout_s}s")


def _env_cookies() -> str | None:
    """Cookie trong .env (nạp bởi load_settings()): GEMINI_COOKIES=<json|chuỗi>, hoặc GEMINI_1PSID (+ GEMINI_1PSIDTS)."""
    if os.environ.get("GEMINI_COOKIES"):
        return os.environ["GEMINI_COOKIES"]
    if not os.environ.get("GEMINI_1PSID"):
        return None
    pairs = {"__Secure-1PSID": os.environ.get("GEMINI_1PSID"), "__Secure-1PSIDTS": os.environ.get("GEMINI_1PSIDTS")}
    return "; ".join(f"{k}={v}" for k, v in pairs.items() if v)


SAME_SITE = {"no_restriction": "None", "none": "None", "lax": "Lax", "strict": "Strict"}


def parse_cookies(raw, log=lambda m: print(m, file=sys.stderr)) -> list[dict]:
    """-> cookie định dạng Playwright add_cookies(). Nhận: JSON (Cookie-Editor [...] / {"cookies": [...]} / context.cookies()),
    chuỗi header "a=b; c=d", hoặc giá trị trần (= __Secure-1PSID). sameSite lạ -> None; expirationDate -> expires (int);
    bỏ trường lạ và cookie rỗng. Thiếu __Secure-1PSID -> ValueError; thiếu __Secure-1PSIDTS -> cảnh báo."""
    items = raw
    if isinstance(raw, str):
        t = raw.strip()
        if t[:1] in "[{":
            items = json.loads(t)
        elif "=" in t:
            items = [dict(zip(("name", "value"), (p.strip() for p in kv.split("=", 1))))
                     for kv in t.split(";") if "=" in kv]
        else:
            items = [{"name": "__Secure-1PSID", "value": t}]
    if isinstance(items, dict):
        items = items.get("cookies", [])
    out = []
    for c in items:
        if not c.get("value"):
            continue
        ck = {"name": c["name"], "value": c["value"], "domain": c.get("domain") or ".google.com",
              "path": c.get("path") or "/", "secure": c.get("secure", True), "httpOnly": c.get("httpOnly", True),
              "sameSite": SAME_SITE.get(str(c.get("sameSite")).lower(), "None")}
        exp = c.get("expirationDate", c.get("expires"))
        if exp and float(exp) > 0:
            ck["expires"] = int(float(exp))
        out.append(ck)
    names = {c["name"] for c in out}
    if "__Secure-1PSID" not in names:
        raise ValueError("Thiếu cookie __Secure-1PSID")
    if "__Secure-1PSIDTS" not in names:
        log("[gemini-web] ⚠ thiếu cookie __Secure-1PSIDTS — vẫn chạy nhưng cookie dễ chết")
    return out


def save_env_cookies(cookies: list[dict], env: Path | None = None) -> None:
    """Ghi cookie (định dạng Playwright) vào .env thành dòng GEMINI_COOKIES (thay dòng cookie cũ). Không in giá trị."""
    env = env or PROJECT_ROOT / ".env"
    line = "GEMINI_COOKIES=" + json.dumps(cookies, separators=(",", ":"), ensure_ascii=False)
    old = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
    keep = [ln for ln in old if not ln.startswith(("GEMINI_COOKIES=", "GEMINI_1PSID=", "GEMINI_1PSIDTS="))]
    env.write_text("\n".join(keep + [line]) + "\n", encoding="utf-8")
    os.environ["GEMINI_COOKIES"] = line.split("=", 1)[1]
    for k in ("GEMINI_1PSID", "GEMINI_1PSIDTS"):
        os.environ.pop(k, None)


def clear_env_cookies(env: Path | None = None) -> None:
    """Bỏ dòng cookie khỏi .env (phiên đã nằm trong profile) -> lần chạy sau dùng profile, không ghi đè cookie cũ."""
    env = env or PROJECT_ROOT / ".env"
    if env.exists():
        keep = [ln for ln in env.read_text(encoding="utf-8").splitlines()
                if not ln.startswith(("GEMINI_COOKIES=", "GEMINI_1PSID=", "GEMINI_1PSIDTS="))]
        env.write_text("\n".join(keep) + "\n", encoding="utf-8")
    for k in ("GEMINI_COOKIES", "GEMINI_1PSID", "GEMINI_1PSIDTS"):
        os.environ.pop(k, None)


def import_cookie_file(src: Path, env: Path) -> int:
    """Nạp file cookie (JSON Cookie-Editor / chuỗi / giá trị 1PSID) vào .env. -> số cookie. Không in giá trị."""
    cookies = parse_cookies(Path(src).read_text(encoding="utf-8"))
    save_env_cookies(cookies, env)
    return len(cookies)


def _stealth(ctx) -> None:
    """Che dấu hiệu trình duyệt tự động (navigator.webdriver, plugin, WebGL...) — giảm rủi ro Google coi là bot."""
    try:
        from playwright_stealth import Stealth
    except ImportError:
        print("[gemini-web] ⚠ chưa cài playwright-stealth (pip install playwright-stealth) — dễ bị coi là bot", file=sys.stderr)
        return
    Stealth().apply_stealth_sync(ctx)
