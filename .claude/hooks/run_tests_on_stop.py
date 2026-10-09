"""Stop hook: trước khi Claude kết thúc lượt trả lời, chạy toàn bộ test (pytest, offline).

Test fail → exit 2: Claude bị yêu cầu làm tiếp để sửa.
Test pass → commit + push lên GitHub (git_sync.py). Code lỗi không bao giờ được tự đẩy lên.
stop_hook_active=True nghĩa là Claude đang làm tiếp do chính hook này → không chặn lần 2 (tránh vòng lặp).
"""

import json
import subprocess
import sys
from pathlib import Path

sys.stderr.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")

data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig") or "{}")
if data.get("stop_hook_active"):
    sys.exit(0)

project_root = Path(__file__).resolve().parents[2]
result = subprocess.run(
    [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
    cwd=project_root,
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace",
)
if result.returncode != 0:
    print("Test đang FAIL, hãy sửa trước khi kết thúc:\n" + (result.stdout + result.stderr)[-3000:], file=sys.stderr)
    sys.exit(2)

# Test pass → tự đồng bộ lên GitHub. Lỗi push chỉ báo cho người dùng, không bắt Claude làm tiếp.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from git_sync import sync  # noqa: E402

sys.exit(sync(interactive=False))
