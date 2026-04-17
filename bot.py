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
    is_bold = "bd" in path.lower() or "bold" in path.lower()
    is_mono = "cour" in path.lower() or "mono" in path.lower()

    candidates = [path]

    if is_mono:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
            "/usr/share/fonts/truetype/msttcorefonts/cour.ttf",
            "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
        ]
    else:
        candidates += [
            f"/usr/share/fonts/truetype/msttcorefonts/{path}",
            f"/usr/share/fonts/truetype/liberation/{path.replace('arial', 'LiberationSans').replace('arialbd', 'LiberationSans-Bold')}",
            f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if is_bold else ''}.ttf",
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
        draw.text(xy, str(text).encode("ascii", "ignore").decode(), fill=fill, font=font)


def add_watermark(input_path: str, output_path: str, size_mode: str = "medium") -> None:
    img = Image.open(input_path).convert("RGBA")
    W, H = img.size
    is_portrait = H > W
    is_landscape = W > H

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    utc = datetime.now(timezone.utc)
    local = utc + timedelta(hours=7)

    line_utc = format_time(utc)
    line_local = format_time(local)

    # ── AUTO RESIZE BERDASARKAN PORTRAIT / LANDSCAPE ──────────────────────
    if size_mode == "small":
        if is_portrait:
            box_ratio = 0.43
            min_box_w = 300
            max_box_w = 440
            base_box_h = 132
        else:
            box_ratio = 0.35
            min_box_w = 300
            max_box_w = 470
            base_box_h = 132
    else:  # medium
        if is_portrait:
            box_ratio = 0.68
            min_box_w = 470
            max_box_w = 760
            base_box_h = 205
        else:
            box_ratio = 0.58
            min_box_w = 520
            max_box_w = 860
            base_box_h = 205

    BOX_W = max(min_box_w, min(max_box_w, int(W * box_ratio)))
    BOX_H = base_box_h

    scale = BOX_W / 620.0

    def s(v):
        return max(1, int(v * scale))

    RADIUS = s(14)

    bx = max(10, W - BOX_W - s(20))
    by = max(10, H - BOX_H - s(20))

    # ── WARNA ──────────────────────────────────────────────────────────────
    # Background utama tetap gelap, tapi body/footer akan ditimpa hitam solid
    C_WIN_BG   = (30, 30, 30, 245)
    C_TITLE_BG = (42, 42, 42, 255)

    # Full hitam solid
    C_TIME_BG  = (0, 0, 0, 255)
    C_FOOTER   = (0, 0, 0, 255)

    C_BTN_SYNC = (26, 111, 212, 255)
    C_BTN_AUTO = (46, 46, 46, 255)
    C_BTN_SET  = (39, 39, 39, 255)

    C_DIVIDER  = (58, 58, 58, 255)
    C_GRAY     = (136, 136, 136, 255)
    C_WHITE    = (255, 255, 255, 255)
    C_TEAL     = (46, 207, 192, 255)
    C_YELLOW   = (232, 184, 75, 255)
    C_GREEN    = (40, 200, 64, 255)
    C_SILVER   = (200, 200, 200, 255)

    # ── FONT ───────────────────────────────────────────────────────────────
    # khusus medium landscape: font diperkecil agar horizontal rapi
    if size_mode == "medium":
        if is_landscape:
            app_font_size = s(12)
            label_font_size = s(10)
            time_font_size = s(14)
            btn_font_size = s(12)
            status_font_size = s(12)
            diff_font_size = s(11)
        else:
            app_font_size = s(13)
            label_font_size = s(11)
            time_font_size = s(17)
            btn_font_size = s(13)
            status_font_size = s(13)
            diff_font_size = s(12)
    else:
        app_font_size = s(13)
        label_font_size = s(11)
        time_font_size = s(12)
        btn_font_size = s(10)
        status_font_size = s(10)
        diff_font_size = s(10)

    f_appname = get_font("arial.ttf", app_font_size)
    f_label   = get_font("arialbd.ttf", label_font_size)
    f_time    = get_font("cour.ttf", time_font_size)
    f_btn     = get_font("arial.ttf", btn_font_size)
    f_status  = get_font("arial.ttf", status_font_size)
    f_diff    = get_font("cour.ttf", diff_font_size)

    if getattr(f_time, "getname", lambda: ("", ""))()[0] == "Default":
        f_time = get_font("mono.ttf", time_font_size)
        f_diff = get_font("mono.ttf", diff_font_size)

    # ── BACKGROUND UTAMA ───────────────────────────────────────────────────
    draw.rounded_rectangle(
        [bx, by, bx + BOX_W, by + BOX_H],
        radius=RADIUS,
        fill=C_WIN_BG
    )

    # Header
    TITLE_H = s(38 if size_mode == "medium" else 30)
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
    title_bbox = draw.textbbox((0, 0), title, font=f_appname)
    tw = title_bbox[2] - title_bbox[0]
    safe_text(draw, (bx + (BOX_W - tw) // 2, by + s(12)), title, C_GRAY, f_appname)

    # ── LAYOUT BODY ────────────────────────────────────────────────────────
    BODY_Y = by + TITLE_H + s(12)

    if size_mode == "small":
        BTN_W = s(98)
        PANEL_X = bx + s(18)
        PANEL_W = BOX_W - BTN_W - s(46)
        BTN_X = bx + BOX_W - BTN_W - s(14)

        B_H = s(24)
        B_GAP = s(7)
        TIME_H = s(24)
        LABEL_GAP = s(12)
        TIME_TEXT_DY = s(5)
        FOOT_H = s(24)
    else:
        if is_landscape:
            BTN_W = s(118)
            PANEL_X = bx + s(18)
            PANEL_W = BOX_W - BTN_W - s(48)
            BTN_X = bx + BOX_W - BTN_W - s(14)

            B_H = s(30)
            B_GAP = s(8)
            TIME_H = s(30)
            LABEL_GAP = s(15)
            TIME_TEXT_DY = s(6)
            FOOT_H = s(30)
        else:
            BTN_W = s(132)
            PANEL_X = bx + s(20)
            PANEL_W = BOX_W - BTN_W - s(56)
            BTN_X = bx + BOX_W - BTN_W - s(16)

            B_H = s(34)
            B_GAP = s(10)
            TIME_H = s(36)
            LABEL_GAP = s(17)
            TIME_TEXT_DY = s(8)
            FOOT_H = s(34)

    # ── BODY AREA FULL HITAM SOLID ────────────────────────────────────────
    FOOT_Y = by + BOX_H - FOOT_H
    BODY_BLACK_TOP = by + TITLE_H + 1
    BODY_BLACK_BOTTOM = FOOT_Y

    draw.rectangle(
        [bx, BODY_BLACK_TOP, bx + BOX_W, BODY_BLACK_BOTTOM],
        fill=C_TIME_BG
    )

    # Divider header/body
    draw.rectangle([bx, BODY_BLACK_TOP, bx + BOX_W, BODY_BLACK_TOP + 1], fill=C_DIVIDER)

    # Panel UTC
    safe_text(draw, (PANEL_X, BODY_Y), "SERVER TIME (UTC)", C_GRAY, f_label)
    U_Y = BODY_Y + LABEL_GAP
    draw.rounded_rectangle(
        [PANEL_X, U_Y, PANEL_X + PANEL_W, U_Y + TIME_H],
        radius=s(8),
        fill=C_TIME_BG
    )
    safe_text(draw, (PANEL_X + s(14), U_Y + TIME_TEXT_DY), line_utc, C_TEAL, f_time)

    # Panel LOCAL
    L_LBL_Y = U_Y + TIME_H + s(8 if size_mode == "small" else 10)
    safe_text(draw, (PANEL_X, L_LBL_Y), "LOCAL PC TIME", C_GRAY, f_label)
    L_Y = L_LBL_Y + LABEL_GAP
    draw.rounded_rectangle(
        [PANEL_X, L_Y, PANEL_X + PANEL_W, L_Y + TIME_H],
        radius=s(8),
        fill=C_TIME_BG
    )
    safe_text(draw, (PANEL_X + s(14), L_Y + TIME_TEXT_DY), line_local, C_YELLOW, f_time)

    # Tombol kanan
    B1Y = BODY_Y + s(2)
    draw.rounded_rectangle(
        [BTN_X, B1Y, BTN_X + BTN_W, B1Y + B_H],
        radius=s(8),
        fill=C_BTN_SYNC
    )
    safe_text(draw, (BTN_X + s(14), B1Y + s(7)), "Sync Now", C_WHITE, f_btn)

    B2Y = B1Y + B_H + B_GAP
    draw.rounded_rectangle(
        [BTN_X, B2Y, BTN_X + BTN_W, B2Y + B_H],
        radius=s(8),
        fill=C_BTN_AUTO
    )
    safe_text(draw, (BTN_X + s(12), B2Y + s(7)), "Auto Sync", C_SILVER, f_btn)

    B3Y = B2Y + B_H + B_GAP
    draw.rounded_rectangle(
        [BTN_X, B3Y, BTN_X + BTN_W, B3Y + B_H],
        radius=s(8),
        fill=C_BTN_SET
    )
    safe_text(draw, (BTN_X + s(14), B3Y + s(7)), "Settings", C_GRAY, f_btn)

    # ── FOOTER FULL HITAM SOLID ────────────────────────────────────────────
    draw.rectangle([bx, FOOT_Y, bx + BOX_W, by + BOX_H], fill=C_FOOTER)
    draw.rectangle([bx, FOOT_Y, bx + BOX_W, FOOT_Y + 1], fill=C_DIVIDER)

    draw.ellipse([bx + s(20), FOOT_Y + s(8), bx + s(30), FOOT_Y + s(18)], fill=C_GREEN)
    safe_text(draw, (bx + s(38), FOOT_Y + s(5)), "Synced Perfectly", C_GREEN, f_status)

    diff = "diff: 0.0s via NIST"
    diff_bbox = draw.textbbox((0, 0), diff, font=f_diff)
    dw = diff_bbox[2] - diff_bbox[0]
    safe_text(draw, (bx + BOX_W - dw - s(16), FOOT_Y + s(6)), diff, C_GRAY, f_diff)

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
