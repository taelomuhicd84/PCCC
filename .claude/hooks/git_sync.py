"""Đồng bộ dự án lên GitHub: commit mọi thay đổi rồi push.

Được dùng bởi:
- run_tests_on_stop.py (Stop hook): tự sync sau mỗi lượt Claude làm việc, CHỈ khi test pass.
- sync.bat: khi bạn tự sửa code bằng tay. Có thể kèm message: sync.bat "fix: sua nut Luu"
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GIT = shutil.which("git") or r"C:\Program Files\Git\cmd\git.exe"
PUSH_TIMEOUT = 120


def _git(*args: str, interactive: bool = True, timeout: float | None = None):
    env = dict(os.environ)
    if not interactive:
        # Hook chạy ngầm: không được treo chờ cửa sổ đăng nhập.
        env.update(GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    return subprocess.run(
        [GIT, *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=timeout,
    )


def sync(message: str | None = None, interactive: bool = True) -> int:
    """Trả về 0 nếu OK (hoặc không có gì để sync), 1 nếu lỗi."""
    if not (PROJECT_ROOT / ".git").exists():
        return 0

    _git("add", "-A")
    if _git("diff", "--cached", "--quiet").returncode != 0:
        msg = message or f"auto: sync {datetime.now():%Y-%m-%d %H:%M}"
        commit = _git("commit", "-m", msg)
        if commit.returncode != 0:
            print("Commit thất bại:\n" + commit.stderr, file=sys.stderr)
            return 1

    ahead = _git("rev-list", "--count", "@{u}..HEAD")
    if ahead.returncode == 0 and ahead.stdout.strip() == "0":
        return 0  # đã đồng bộ, không cần push

    try:
        push = _git("push", "-u", "origin", "HEAD", interactive=interactive, timeout=PUSH_TIMEOUT)
    except subprocess.TimeoutExpired:
        print("Push quá lâu, bỏ qua. Chạy sync.bat để thử lại.", file=sys.stderr)
        return 1
    if push.returncode != 0:
        print("Push lên GitHub thất bại (đã commit ở máy):\n" + push.stderr, file=sys.stderr)
        return 1
    print("Đã đồng bộ lên GitHub.")
    return 0


if __name__ == "__main__":
    sys.exit(sync(" ".join(sys.argv[1:]) or None))
