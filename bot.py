import os
import time
import uuid
import threading
import requests

from http.server import HTTPServer, BaseHTTPRequestHandler
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, timedelta

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

# Simpan preferensi ukuran per chat
USER_SIZE_MODE = {}


# ── Health check server (wajib untuk Render Web Service) ─────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass


def run_health_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"Health server berjalan di port {port}")
    server.serve_forever()
# ─────────────────────────────────────────────────────────────────────────────


def format_time(dt):
    return dt.strftime("%A | %B %d, %Y at %H:%M:%S")


def get_font(path: str, size: int):
    candidates = [
        path,
        f"/usr/share/fonts/truetype/msttcorefonts/{path}",
        f"/usr/share/fonts/truetype/liberation/{path.replace('arial', 'LiberationSans').replace('arialbd', 'LiberationSans-Bold')}",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if 'bd' in path else ''}.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def safe_text(draw, xy, text, fill, font):
    try:
        draw.text(xy, text, fill=fill, font=font)
    except Exception:
        # fallback sederhana kalau ada karakter/font issue
        draw.text(xy, str(text).encode("ascii", "ignore").decode(), fill=fill, font=font)


def add_watermark(input_path: str, output_path: str, size_mode: str = "medium") -> None:
    img = Image.open(input_path).convert("RGBA")
    W, H = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    scales = {
        "medium": 1.0,
        "small": 0.74,
    }
    scale = scales.get(size_mode, 1.0)

    def s(v):
        return max(1, int(v * scale))

    # Font dinamis
    f_appname = get_font("arial.ttf", s(13))
    f_label   = get_font("arialbd.ttf", s(11))
    f_time    = get_font("cour.ttf", s(17))
    f_btn     = get_font("arial.ttf", s(13))
    f_status  = get_font("arial.ttf", s(13))
    f_diff    = get_font("cour.ttf", s(12))

    if not any(os.path.exists(p) for p in [
        "cour.ttf",
        "/usr/share/fonts/truetype/msttcorefonts/cour.ttf"
    ]):
        f_time = get_font("arialbd.ttf", s(16))
        f_diff = get_font("arial.ttf", s(11))

    utc = datetime.now(timezone.utc)
    local = utc + timedelta(hours=7)

    line_utc = format_time(utc)
    line_local = format_time(local)

    # Ukuran box berdasarkan mode
    if size_mode == "small":
        box_ratio = 0.56
        min_box_w = 360
        max_box_w = 620
        base_box_h = 170
    else:
        box_ratio = 0.70
        min_box_w = 520
        max_box_w = 860
        base_box_h = 222

    BOX_W = max(min_box_w, min(max_box_w, int(W * box_ratio)))
    BOX_H = s(base_box_h)
    RADIUS = s(14)

    bx = max(10, W - BOX_W - 20)
    by = max(10, H - BOX_H - 20)

    C_WIN_BG   = (30, 30, 30, 225)
    C_TITLE_BG = (42, 42, 42, 230)
    C_TIME_BG  = (17, 17, 17, 240)
    C_BTN_SYNC = (26, 111, 212, 255)
    C_BTN_AUTO = (46, 46, 46, 255)
    C_BTN_SET  = (39, 39, 39, 255)
    C_FOOTER   = (26, 26, 26, 230)
    C_DIVIDER  = (50, 50, 50, 200)
    C_GRAY     = (136, 136, 136, 255)
    C_WHITE    = (255, 255, 255, 255)
    C_TEAL     = (46, 207, 192, 255)
    C_YELLOW   = (232, 184, 75, 255)
    C_GREEN    = (40, 200, 64, 255)
    C_SILVER   = (200, 200, 200, 255)

    # Background utama
    draw.rounded_rectangle(
        [bx, by, bx + BOX_W, by + BOX_H],
        radius=RADIUS,
        fill=C_WIN_BG
    )

    # Header
    TITLE_H = s(38)
    draw.rounded_rectangle(
        [bx, by, bx + BOX_W, by + TITLE_H + RADIUS],
        radius=RADIUS,
        fill=C_TITLE_BG
    )
    draw.rectangle([bx, by + TITLE_H, bx + BOX_W, by + TITLE_H + 1], fill=C_DIVIDER)

    # Tombol window kiri atas
    for i, col in enumerate([
        (255, 95, 86, 255),
        (255, 189, 46, 255),
        (40, 200, 64, 255)
    ]):
        cx = bx + s(18) + i * s(22)
        draw.ellipse([cx, by + s(13), cx + s(13), by + s(26)], fill=col)

    title = "Bob's Time"
    tw = draw.textbbox((0, 0), title, font=f_appname)[2]
    safe_text(draw, (bx + (BOX_W - tw) // 2, by + s(12)), title, C_GRAY, f_appname)

    # Layout body
    BODY_Y = by + TITLE_H + s(14)
    BTN_W = s(132 if size_mode == "medium" else 110)
    PANEL_X = bx + s(20)
    PANEL_W = BOX_W - BTN_W - s(56)
    BTN_X = bx + BOX_W - BTN_W - s(16)
    B_H = s(34 if size_mode == "medium" else 28)
    B_GAP = s(10)
    TIME_H = s(43 if size_mode == "medium" else 34)

    # Panel UTC
    safe_text(draw, (PANEL_X, BODY_Y), "SERVER TIME (UTC)", C_GRAY, f_label)
    U_Y = BODY_Y + s(17)
    draw.rounded_rectangle(
        [PANEL_X, U_Y, PANEL_X + PANEL_W, U_Y + TIME_H],
        radius=s(9),
        fill=C_TIME_BG
    )
    safe_text(draw, (PANEL_X + s(14), U_Y + s(11)), line_utc, C_TEAL, f_time)

    # Panel WIB
    L_LBL_Y = U_Y + TIME_H + s(12)
    safe_text(draw, (PANEL_X, L_LBL_Y), "LOCAL PC TIME", C_GRAY, f_label)
    L_Y = L_LBL_Y + s(17)
    draw.rounded_rectangle(
        [PANEL_X, L_Y, PANEL_X + PANEL_W, L_Y + TIME_H],
        radius=s(9),
        fill=C_TIME_BG
    )
    safe_text(draw, (PANEL_X + s(14), L_Y + s(11)), line_local, C_YELLOW, f_time)

    # Tombol kanan
    B1Y = BODY_Y + s(4)
    draw.rounded_rectangle(
        [BTN_X, B1Y, BTN_X + BTN_W, B1Y + B_H],
        radius=s(9),
        fill=C_BTN_SYNC
    )
    safe_text(draw, (BTN_X + s(18), B1Y + s(9)), "Sync Now", C_WHITE, f_btn)

    B2Y = B1Y + B_H + B_GAP
    draw.rounded_rectangle(
        [BTN_X, B2Y, BTN_X + BTN_W, B2Y + B_H],
        radius=s(9),
        fill=C_BTN_AUTO
    )
    safe_text(draw, (BTN_X + s(15), B2Y + s(9)), "Auto Sync", C_SILVER, f_btn)

    B3Y = B2Y + B_H + B_GAP
    draw.rounded_rectangle(
        [BTN_X, B3Y, BTN_X + BTN_W, B3Y + B_H],
        radius=s(9),
        fill=C_BTN_SET
    )
    safe_text(draw, (BTN_X + s(18), B3Y + s(9)), "Settings", C_GRAY, f_btn)

    # Footer
    FOOT_H = s(36 if size_mode == "medium" else 30)
    FOOT_Y = by + BOX_H - FOOT_H
    draw.rectangle([bx, FOOT_Y, bx + BOX_W, by + BOX_H], fill=C_FOOTER)
    draw.rectangle([bx, FOOT_Y, bx + BOX_W, FOOT_Y + 1], fill=C_DIVIDER)

    draw.ellipse([bx + s(20), FOOT_Y + s(10), bx + s(30), FOOT_Y + s(20)], fill=C_GREEN)
    safe_text(draw, (bx + s(38), FOOT_Y + s(8)), "Synced Perfectly", C_GREEN, f_status)

    diff = "diff: 0.0s via NIST"
    dw = draw.textbbox((0, 0), diff, font=f_diff)[2]
    safe_text(draw, (bx + BOX_W - dw - s(18), FOOT_Y + s(9)), diff, C_GRAY, f_diff)

    result = Image.alpha_composite(img, overlay)
    result.convert("RGB").save(output_path, quality=95)


def send_message(chat_id: int, text: str) -> None:
    try:
        requests.post(
            f"{URL}/sendMessage",
            data={"chat_id": chat_id, "text": text},
            timeout=20
        )
    except Exception as e:
        print(f"[send_message] Error: {e}")


def send_photo(chat_id: int, photo_path: str, caption: str = "") -> None:
    try:
        with open(photo_path, "rb") as f:
            requests.post(
                f"{URL}/sendPhoto",
                data={"chat_id": chat_id, "caption": caption},
                files={"photo": f},
                timeout=60
            )
    except Exception as e:
        print(f"[send_photo] Error: {e}")


def download_file(file_id: str, path: str) -> bool:
    try:
        file_info = requests.get(
            f"{URL}/getFile",
            params={"file_id": file_id},
            timeout=20
        ).json()

        if not file_info.get("ok"):
            print(f"[download_file] getFile gagal: {file_info}")
            return False

        file_path = file_info["result"]["file_path"]

        content = requests.get(
            f"https://api.telegram.org/file/bot{TOKEN}/{file_path}",
            timeout=60
        ).content

        with open(path, "wb") as f:
            f.write(content)

        return True
    except Exception as e:
        print(f"[download_file] Error: {e}")
        return False


def get_updates(offset=None):
    try:
        res = requests.get(
            f"{URL}/getUpdates",
            params={"timeout": 30, "offset": offset},
            timeout=35,
        )
        return res.json()
    except Exception as e:
        print(f"[get_updates] Error: {e}")
        return {"result": []}


def detect_size_mode_from_text(text: str, default_mode: str = "medium") -> str:
    if not text:
        return default_mode

    t = text.lower().strip()

    if "small" in t or "kecil" in t:
        return "small"
    if "medium" in t or "sedang" in t:
        return "medium"

    return default_mode


def cleanup_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        print(f"[cleanup_file] Error: {e}")


def handle_photo_message(msg: dict):
    chat_id = msg.get("chat", {}).get("id")
    if not chat_id:
        return

    caption = msg.get("caption", "")
    default_mode = USER_SIZE_MODE.get(chat_id, "medium")
    size_mode = detect_size_mode_from_text(caption, default_mode)

    photo_list = msg.get("photo", [])
    if not photo_list:
        send_message(chat_id, "Foto tidak ditemukan.")
        return

    file_id = photo_list[-1]["file_id"]

    unique_id = uuid.uuid4().hex
    input_path = f"/tmp/input_{chat_id}_{unique_id}.jpg"
    output_path = f"/tmp/output_{chat_id}_{unique_id}.jpg"

    send_message(chat_id, f"Foto diterima. Memproses watermark mode: {size_mode}...")

    try:
        if not download_file(file_id, input_path):
            send_message(chat_id, "Gagal mengunduh foto.")
            return

        add_watermark(input_path, output_path, size_mode=size_mode)
        send_photo(chat_id, output_path, caption=f"Watermark {size_mode} berhasil ditambahkan.")
    except Exception as e:
        print(f"[handle_photo_message] Error: {e}")
        send_message(chat_id, "Gagal memproses gambar.")
    finally:
        cleanup_file(input_path)
        cleanup_file(output_path)


def main():
    if not TOKEN:
        print("ERROR: BOT_TOKEN belum di-set.")
        return

    # Jalankan health server di thread terpisah
    t = threading.Thread(target=run_health_server, daemon=True)
    t.start()

    print("Bot berjalan...")
    offset = None

    while True:
        data = get_updates(offset)

        for update in data.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")

            if not chat_id:
                continue

            text = msg.get("text", "").strip().lower()

            if text == "/start":
                USER_SIZE_MODE[chat_id] = "medium"
                send_message(
                    chat_id,
                    "Halo! Kirimkan foto dan saya akan menambahkan watermark Bob's Time.\n\n"
                    "Perintah yang tersedia:\n"
                    "/small  -> set mode default ke small\n"
                    "/medium -> set mode default ke medium\n"
                    "/help   -> bantuan\n\n"
                    "Anda juga bisa kirim foto dengan caption: small atau medium"
                )
                continue

            if text == "/help":
                send_message(
                    chat_id,
                    "Cara penggunaan:\n\n"
                    "1. Kirim perintah /small untuk set watermark kecil\n"
                    "2. Kirim perintah /medium untuk set watermark sedang\n"
                    "3. Kirim foto\n\n"
                    "Atau kirim foto dengan caption:\n"
                    "- small\n"
                    "- medium\n\n"
                    "Contoh:\n"
                    "Kirim foto + caption: small"
                )
                continue

            if text == "/small":
                USER_SIZE_MODE[chat_id] = "small"
                send_message(chat_id, "Mode default watermark diubah ke: small")
                continue

            if text == "/medium":
                USER_SIZE_MODE[chat_id] = "medium"
                send_message(chat_id, "Mode default watermark diubah ke: medium")
                continue

            if "photo" in msg:
                handle_photo_message(msg)
                continue

            if msg:
                current_mode = USER_SIZE_MODE.get(chat_id, "medium")
                send_message(
                    chat_id,
                    f"Mode saat ini: {current_mode}\n"
                    "Kirim foto untuk mendapatkan watermark waktu.\n"
                    "Gunakan /small atau /medium untuk mengganti ukuran."
                )

        time.sleep(1)


if __name__ == "__main__":
    main()
