import os
import time
import json
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, timedelta

TOKEN = os.getenv("BOT_TOKEN")
URL = f"[api.telegram.org](https://api.telegram.org/bot{TOKEN})"

user_size_pref = {}
pending_photos = {}


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


def format_time(dt):
    return dt.strftime("%A | %B %d, %Y at %H:%M:%S")


def get_font(path: str, size: int):
    candidates = [
        path,
        f"/usr/share/fonts/truetype/msttcorefonts/{path}",
        f"/usr/share/fonts/truetype/liberation/{path.replace('arial', 'LiberationSans').replace('arialbd', 'LiberationSans-Bold')}",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'Bold' if 'bd' in path else ''}.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def add_watermark(input_path: str, output_path: str, size: str = "medium") -> None:
    img = Image.open(input_path).convert("RGBA")
    W, H = img.size

    SCALE = 1.0 if size == "medium" else 1.5

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    f_appname = get_font("arial.ttf",   int(13 * SCALE))
    f_label   = get_font("arialbd.ttf", int(11 * SCALE))
    f_time    = get_font("cour.ttf",    int(17 * SCALE))
    f_btn     = get_font("arial.ttf",   int(13 * SCALE))
    f_status  = get_font("arial.ttf",   int(13 * SCALE))
    f_diff    = get_font("cour.ttf",    int(12 * SCALE))

    if not any(os.path.exists(p) for p in [
        "cour.ttf", "/usr/share/fonts/truetype/msttcorefonts/cour.ttf"
    ]):
        f_time = get_font("arialbd.ttf", int(16 * SCALE))
        f_diff = get_font("arial.ttf",   int(11 * SCALE))

    utc   = datetime.now(timezone.utc)
    local = utc + timedelta(hours=7)
    line_utc   = format_time(utc)
    line_local = format_time(local)

    BOX_W  = int(max(520, min(860, int(W * 0.70))) * SCALE)
    BOX_H  = int(222 * SCALE)
    RADIUS = int(14 * SCALE)

    BOX_W = min(BOX_W, W - 30)
    BOX_H = min(BOX_H, H - 30)

    bx = max(10, W - BOX_W - 20)
    by = max(10, H - BOX_H - 20)

    C_WIN_BG   = (30,  30,  30,  225)
    C_TITLE_BG = (42,  42,  42,  230)
    C_TIME_BG  = (17,  17,  17,  240)
    C_BTN_SYNC = (26, 111, 212,  255)
    C_BTN_AUTO = (46,  46,  46,  255)
    C_BTN_SET  = (39,  39,  39,  255)
    C_FOOTER   = (26,  26,  26,  230)
    C_DIVIDER  = (50,  50,  50,  200)
    C_GRAY     = (136, 136, 136, 255)
    C_WHITE    = (255, 255, 255, 255)
    C_TEAL     = (46,  207, 192, 255)
    C_YELLOW   = (232, 184,  75, 255)
    C_GREEN    = (40,  200,  64, 255)
    C_SILVER   = (200, 200, 200, 255)

    draw.rounded_rectangle([bx, by, bx+BOX_W, by+BOX_H], radius=RADIUS, fill=C_WIN_BG)

    TITLE_H = int(38 * SCALE)
    draw.rounded_rectangle([bx, by, bx+BOX_W, by+TITLE_H+RADIUS], radius=RADIUS, fill=C_TITLE_BG)
    draw.rectangle([bx, by+TITLE_H, bx+BOX_W, by+TITLE_H+1], fill=C_DIVIDER)

    dot_r = int(13 * SCALE)
    for i, col in enumerate([(255,95,86,255),(255,189,46,255),(40,200,64,255)]):
        cx = bx + int(18 * SCALE) + i * int(22 * SCALE)
        cy = by + int(13 * SCALE)
        draw.ellipse([cx, cy, cx+dot_r, cy+dot_r], fill=col)

    tw = draw.textbbox((0,0), "Bob's Time", font=f_appname)[2]
    draw.text((bx + (BOX_W-tw)//2, by + int(12 * SCALE)), "Bob's Time", fill=C_GRAY, font=f_appname)

    BODY_Y  = by + TITLE_H + int(14 * SCALE)
    BTN_W   = int(132 * SCALE)
    PANEL_X = bx + int(20 * SCALE)
    PANEL_W = BOX_W - BTN_W - int(56 * SCALE)
    BTN_X   = bx + BOX_W - BTN_W - int(16 * SCALE)
    B_H     = int(34 * SCALE)
    B_GAP   = int(10 * SCALE)

    draw.text((PANEL_X, BODY_Y), "SERVER TIME (UTC)", fill=C_GRAY, font=f_label)
    U_Y = BODY_Y + int(17 * SCALE)
    draw.rounded_rectangle([PANEL_X, U_Y, PANEL_X+PANEL_W, U_Y+int(43*SCALE)], radius=int(9*SCALE), fill=C_TIME_BG)
    draw.text((PANEL_X+int(14*SCALE), U_Y+int(11*SCALE)), line_utc, fill=C_TEAL, font=f_time)

    L_LBL_Y = U_Y + int(43*SCALE) + int(12*SCALE)
    draw.text((PANEL_X, L_LBL_Y), "LOCAL PC TIME", fill=C_GRAY, font=f_label)
    L_Y = L_LBL_Y + int(17 * SCALE)
    draw.rounded_rectangle([PANEL_X, L_Y, PANEL_X+PANEL_W, L_Y+int(43*SCALE)], radius=int(9*SCALE), fill=C_TIME_BG)
    draw.text((PANEL_X+int(14*SCALE), L_Y+int(11*SCALE)), line_local, fill=C_YELLOW, font=f_time)

    B1Y = BODY_Y + int(4 * SCALE)
    draw.rounded_rectangle([BTN_X, B1Y, BTN_X+BTN_W, B1Y+B_H], radius=int(9*SCALE), fill=C_BTN_SYNC)
    draw.text((BTN_X+int(24*SCALE), B1Y+int(9*SCALE)), "Sync Now", fill=C_WHITE, font=f_btn)

    B2Y = B1Y + B_H + B_GAP
    draw.rounded_rectangle([BTN_X, B2Y, BTN_X+BTN_W, B2Y+B_H], radius=int(9*SCALE), fill=C_BTN_AUTO)
    draw.text((BTN_X+int(20*SCALE), B2Y+int(9*SCALE)), "Auto Sync", fill=C_SILVER, font=f_btn)

    B3Y = B2Y + B_H + B_GAP
    draw.rounded_rectangle([BTN_X, B3Y, BTN_X+BTN_W, B3Y+B_H], radius=int(9*SCALE), fill=C_BTN_SET)
    draw.text((BTN_X+int(22*SCALE), B3Y+int(9*SCALE)), "Settings", fill=C_GRAY, font=f_btn)

    FOOT_Y = by + BOX_H - int(36 * SCALE)
    draw.rectangle([bx, FOOT_Y, bx+BOX_W, by+BOX_H], fill=C_FOOTER)
    draw.rectangle([bx, FOOT_Y, bx+BOX_W, FOOT_Y+1], fill=C_DIVIDER)
    dot_s = int(10 * SCALE)
    draw.ellipse([bx+int(20*SCALE), FOOT_Y+int(13*SCALE),
                  bx+int(20*SCALE)+dot_s, FOOT_Y+int(13*SCALE)+dot_s], fill=C_GREEN)
    draw.text((bx+int(38*SCALE), FOOT_Y+int(10*SCALE)), "Synced Perfectly", fill=C_GREEN, font=f_status)

    diff = "diff: 0.0s via NIST"
    dw = draw.textbbox((0,0), diff, font=f_diff)[2]
    draw.text((bx+BOX_W-dw-int(18*SCALE), FOOT_Y+int(11*SCALE)), diff, fill=C_GRAY, font=f_diff)

    result = Image.alpha_composite(img, overlay)
    result.convert("RGB").save(output_path, quality=95)


def kirim_pesan(chat_id: int, text: str, keyboard: dict = None) -> None:
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if keyboard:
        payload["reply_markup"] = json.dumps(keyboard)
    res = requests.post(f"{URL}/sendMessage", data=payload)
    if not res.json().get("ok"):
        print(f"[kirim_pesan] Error: {res.json()}")


def kirim_foto(chat_id: int, photo_path: str, caption: str = "") -> None:
    with open(photo_path, "rb") as f:
        requests.post(
            f"{URL}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": f},
        )


def jawab_callback(callback_query_id: str) -> None:
    requests.post(f"{URL}/answerCallbackQuery",
                  data={"callback_query_id": callback_query_id})


def download_file(file_id: str, path: str) -> bool:
    try:
        file_info = requests.get(
            f"{URL}/getFile", params={"file_id": file_id}, timeout=15
        ).json()
        file_path = file_info["result"]["file_path"]
        content = requests.get(
            f"[api.telegram.org](https://api.telegram.org/file/bot{TOKEN}/{file_path})", timeout=30
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


KEYBOARD_UKURAN = {
    "inline_keyboard": [[
        {"text": "Sedang", "callback_data": "size_medium"},
        {"text": "Besar",  "callback_data": "size_large"},
    ]]
}


def proses_foto(chat_id: int, file_id: str, size: str) -> None:
    if download_file(file_id, "input.jpg"):
        try:
            add_watermark("input.jpg", "output.jpg", size=size)
            label = "Sedang" if size == "medium" else "Besar"
            kirim_foto(chat_id, "output.jpg",
                       caption=f"Watermark ({label}) berhasil ditambahkan.")
        except Exception as e:
            print(f"[watermark] Error: {e}")
            kirim_pesan(chat_id, "Gagal memproses gambar.")
    else:
        kirim_pesan(chat_id, "Gagal mengunduh foto.")


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

            if "callback_query" in update:
                cb      = update["callback_query"]
                cb_id   = cb["id"]
                cb_data = cb["data"]
                chat_id = cb["message"]["chat"]["id"]

                jawab_callback(cb_id)

                if cb_data in ("size_medium", "size_large"):
                    size = "medium" if cb_data == "size_medium" else "large"
                    user_size_pref[chat_id] = size
                    label = "Sedang" if size == "medium" else "Besar"

                    if chat_id in pending_photos:
                        file_id = pending_photos.pop(chat_id)
                        kirim_pesan(chat_id, f"Ukuran dipilih: {label}. Sedang memproses foto...")
                        proses_foto(chat_id, file_id, size)
                    else:
                        kirim_pesan(chat_id, f"Ukuran watermark diset ke: {label}. Sekarang kirim foto kamu!")
                continue

            msg     = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            if not chat_id:
                continue

            text = msg.get("text", "")

            if text in ("/start", "/help"):
                kirim_pesan(chat_id,
                    "Halo! Saya akan menambahkan watermark Bob's Time ke foto kamu.\n\n"
                    "Caranya:\n"
                    "1. Ketik /ukuran untuk pilih ukuran watermark\n"
                    "2. Kirim foto kamu\n\n"
                    "Atau langsung kirim foto, nanti saya tanya ukurannya.")
                continue

            if text == "/ukuran":
                current = user_size_pref.get(chat_id, "medium")
                label   = "Sedang" if current == "medium" else "Besar"
                kirim_pesan(chat_id,
                    f"Pilih ukuran watermark (saat ini: {label}):",
                    keyboard=KEYBOARD_UKURAN)
                continue

            if "photo" in msg:
                file_id = msg["photo"][-1]["file_id"]

                if chat_id in user_size_pref:
                    proses_foto(chat_id, file_id, user_size_pref[chat_id])
                else:
                    pending_photos[chat_id] = file_id
                    kirim_pesan(chat_id,
                        "Pilih ukuran watermark dulu:",
                        keyboard=KEYBOARD_UKURAN)
                continue

            if msg:
                kirim_pesan(chat_id,
                    "Kirim foto untuk mendapatkan watermark.\n"
                    "Gunakan /ukuran untuk pilih ukuran.")

        time.sleep(1)


if __name__ == "__main__":
    main()
    
