"""Viết lại cột "Nội dung thiết kế" theo văn phong bảng đối chiếu mẫu (B17 BIBICO) + sửa chính tả — Gemini viết, script kiểm, Claude giám sát.

Gemini nhận file text nhỏ (không gửi PDF): mỗi dòng = ID | nội dung đối chiếu | quy định (tóm tắt) | dữ liệu đã đọc từ bản vẽ (trang, trích dẫn, nhận xét)
và 1 trang ví dụ văn phong. Trả `ID ||| thiết kế ||| ghi chú`. Script chấp nhận kết quả khi:
  • mọi SỐ trong thiết kế/ghi chú có trong dữ liệu đầu vào của dòng (không bịa số);
  • dòng chưa đạt (XM/KD) không được viết "Đảm bảo"; dòng NA chỉ được "Không thuộc diện…".
Không đạt kiểm -> giữ bản script (văn thô) và ghi `nguon: "script"` để Claude xem. Kết quả lưu `goi/tk_bang.json`.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

VI_DU = """VÍ DỤ VĂN PHONG (bảng đã được thẩm duyệt):
Nội dung đối chiếu: Chiều cao an toàn PCCC của các hạng mục -> Thiết kế: "- Xưởng sản xuất bao bì: chiều cao PCCC 6m"
Nội dung đối chiếu: Số tầng -> Thiết kế: "- Xưởng máy in: 1 tầng."
Nội dung đối chiếu: Bậc chịu lửa -> Thiết kế: "- Xưởng sản xuất bao bì: IV ; - Văn phòng: II"
Nội dung đối chiếu: Độ dốc của đường -> Thiết kế: "Không vượt quá 1:8,3"
Nội dung đối chiếu: Tải trọng nền đường -> Thiết kế: "Lớn hơn hoặc bằng 30 tấn"
Nội dung đối chiếu: Đoạn tránh xe -> Thiết kế: "Không yêu cầu thiết kế"
Nội dung đối chiếu: Ngăn cháy máy biến áp -> Thiết kế: "MBA đặt ngoài trời và cách xưởng sản xuất bao bì lớn hơn 3m"
Nội dung đối chiếu: Lối thoát nạn -> Thiết kế: "- Kho thành phẩm: thoát ra ngoài trực tiếp. - Văn phòng 2 tầng: thoát ra thang loại 2 và thoát ra ngoài trực tiếp."
Nội dung đối chiếu: Bố trí buồng thang bộ L2 -> Thiết kế: "Không bố trí"
Nội dung đối chiếu: Bố trí buồng thang thoát nạn không nhiễm khói -> Thiết kế: "Không thuộc diện"
Nội dung đối chiếu: (dòng đã đạt) -> Thiết kế: "Đảm bảo theo quy định"
Các cụm cố định: "Không thuộc diện", "Không thiết kế", "Không yêu cầu thiết kế", "Không bố trí", "Đảm bảo theo quy định".
"""

LENH = """Bạn là kỹ sư thiết kế PCCC viết cột "Nội dung thiết kế" của bảng đối chiếu thẩm duyệt. Văn phong NGẮN GỌN như ví dụ ở cuối.
Với MỖI dòng trong file đính kèm, viết lại phần thiết kế từ DỮ LIỆU ĐÃ ĐỌC (không đọc lại bản vẽ):
- Nêu số liệu / giải pháp thiết kế bằng tiếng Việt đúng chính tả, đủ dấu; có thể gạch đầu dòng "- " theo hạng mục.
- Chỉ dùng số và tên có trong dữ liệu của dòng. TUYỆT ĐỐI không bịa số.
- Dòng KẾT QUẢ=ĐẠT: nêu số liệu thiết kế rồi nếu phù hợp thêm "Đảm bảo theo quy định".
- Dòng KẾT QUẢ=KHÔNG ÁP DỤNG: viết "Không thuộc diện" (hoặc "Không thiết kế"/"Không bố trí" nếu hợp nghĩa).
- Dòng KẾT QUẢ=CẦN XÁC MINH hoặc KHÔNG ĐẠT: chỉ viết điều ĐÃ THỂ HIỆN trên bản vẽ theo dữ liệu, KHÔNG viết "Đảm bảo"; nếu bản vẽ chưa thể hiện thì viết "Chưa thể hiện trên bản vẽ" kèm điều đã thấy.
- Cột ghi chú (≤ 20 từ, chỉ cho dòng CẦN XÁC MINH/KHÔNG ĐẠT): nêu thiếu gì hoặc sai gì và ở trang nào; dòng khác để trống.
Trả về ĐÚNG mỗi dòng một kết quả, định dạng:  ID ||| thiết kế ||| ghi chú   (không thêm lời dẫn, không bảng, không markdown).
"""

NHAN = {"D": "ĐẠT", "KD": "KHÔNG ĐẠT", "XM": "CẦN XÁC MINH", "NA": "KHÔNG ÁP DỤNG"}


def _so(s: str) -> set[str]:
    return {x.replace(",", ".") for x in re.findall(r"\d+(?:[.,]\d+)?", s)}


def dong_dau_vao(rid: str, ten: str, quy_dinh: str, f: dict, facts: str) -> str:
    du_lieu = " ; ".join(x for x in (f"tr.{f['trang']}" if f.get("trang") else "", f"trích: {f['evid']}" if f.get("evid") else "",
                                      f"nhận xét: {f.get('ly_do') or ''}") if x)
    return f"{rid} | {ten[:90]} | QĐ: {quy_dinh[:160]} | KẾT QUẢ={NHAN[f['tt']]} | {du_lieu} | CHUNG: {facts}"


def kiem(rid: str, f: dict, tk: str, gc: str, dau_vao: str) -> str | None:
    """None = chấp nhận; chuỗi = lý do từ chối."""
    if not tk.strip():
        return "rỗng"
    if not _so(tk + " " + gc) <= _so(dau_vao):
        return "có số không có trong dữ liệu"
    if f["tt"] in ("XM", "KD") and re.search(r"đảm bảo|đạt", tk, re.I) and not re.search(r"không đảm bảo|chưa", tk, re.I):
        return "dòng chưa đạt mà viết đảm bảo"
    if f["tt"] == "NA" and not re.match(r"không", tk.strip(), re.I):
        return "dòng NA phải bắt đầu bằng Không"
    return None


def parse(text: str) -> dict[str, tuple[str, str]]:
    out = {}
    for ln in text.splitlines():
        p = [x.strip() for x in ln.split("|||")]
        if len(p) >= 2 and re.match(r"^[A-Z0-9]+-[A-Z0-9-]+$", p[0].strip(" -*`")):
            out[p[0].strip(" -*`")] = (p[1], p[2] if len(p) > 2 else "")
    return out


def tao_file(path: Path, dong: list[str]) -> None:
    path.write_text(VI_DU + "\nDỮ LIỆU (mỗi dòng 1 mục):\n" + "\n".join(dong) + "\n", encoding="utf-8")
