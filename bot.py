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

USER_SIZE_MODE = {}


# ───────────────── HEALTH SERVER (Render wajib) ─────────────────
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


# ───────────────── FORMAT TIME ─────────────────
def format_time(dt):
    return dt.strftime("%A | %B %d, %Y at %H:%M:%S")


# ───────────────── FONT LOADER ─────────────────
def get_font(path, size):
    mono = "cour" in path.lower()

    candidates = [path]

    if mono:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        ]
    else:
        candidates += [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]

    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except:
                pass

    return ImageFont.load_default()


def safe_text(draw, xy, text, fill, font):
    try:
        draw.text(xy, text, fill=fill, font=font)
    except:
        draw.text(xy, text.encode("ascii", "ignore").decode(), fill=fill, font=font)


# ───────────────── WATERMARK ENGINE ─────────────────
def add_watermark(input_path, output_path, size_mode="medium"):

    img = Image.open(input_path).convert("RGBA")
    W, H = img.size
    portrait = H > W

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    utc = datetime.now(timezone.utc)
    local = utc + timedelta(hours=7)

    utc_text = format_time(utc)
    local_text = format_time(local)

    # ───── SIZE CONTROL ─────
    if size_mode == "small":

        if portrait:
            ratio = 0.43
        else:
            ratio = 0.35

        BOX_H = 130  # 🔥 dipendekkan agar space kosong hilang

    else:  # MEDIUM

        if portrait:
            ratio = 0.68
        else:
            ratio = 0.54

        BOX_H = 205

    BOX_W = int(W * ratio)

    scale = BOX_W / 620

    def s(x):
        return max(1, int(x * scale))

    bx = W - BOX_W - s(18)
    by = H - BOX_H - s(18)

    RADIUS = s(14)

    # ───── COLORS ─────
    C_BG = (30, 30, 30, 238)
    C_TITLE = (42, 42, 42, 242)
    C_BODY = (0, 0, 0, 255)
    C_FOOTER = (0, 0, 0, 255)

    C_SYNC = (26, 111, 212, 255)
    C_AUTO = (46, 46, 46, 255)
    C_SET = (39, 39, 39, 255)

    C_GRAY = (136, 136, 136, 255)
    C_WHITE = (255, 255, 255, 255)
    C_TEAL = (46, 207, 192, 255)
    C_YELLOW = (232, 184, 75, 255)
    C_GREEN = (40, 200, 64, 255)

    # ───── FONT ─────
    f_title = get_font("arial.ttf", s(13))
    f_label = get_font("arialbd.ttf", s(11))

    f_time = get_font("cour.ttf", s(17 if size_mode == "medium" else 12))

    f_btn = get_font("arial.ttf", s(13 if size_mode == "medium" else 10))
    f_status = get_font("arial.ttf", s(13 if size_mode == "medium" else 10))
    f_diff = get_font("cour.ttf", s(12 if size_mode == "medium" else 10))

    # ───── MAIN WINDOW ─────
    draw.rounded_rectangle(
        [bx, by, bx + BOX_W, by + BOX_H],
        radius=RADIUS,
        fill=C_BG
    )

    TITLE_H = s(36 if size_mode == "medium" else 30)

    draw.rounded_rectangle(
        [bx, by, bx + BOX_W, by + TITLE_H + RADIUS],
        radius=RADIUS,
        fill=C_TITLE
    )

    title = "Bob's Time"

    tw = draw.textbbox((0, 0), title, font=f_title)[2]

    safe_text(draw, (bx + (BOX_W - tw)//2, by + s(10)), title, C_GRAY, f_title)

    BODY_Y = by + TITLE_H + s(10)

    BTN_W = s(120 if size_mode == "medium" else 95)
    PANEL_X = bx + s(18)
    PANEL_W = BOX_W - BTN_W - s(48)
    BTN_X = bx + BOX_W - BTN_W - s(15)

    if size_mode == "small":

        TIME_H = s(26)
        GAP = s(7)
        TEXT_Y = s(7)
        FOOT_H = s(26)

    else:

        TIME_H = s(36)
        GAP = s(10)
        TEXT_Y = s(8)
        FOOT_H = s(34)

    # ───── UTC PANEL ─────
    safe_text(draw, (PANEL_X, BODY_Y), "SERVER TIME (UTC)", C_GRAY, f_label)

    UY = BODY_Y + s(14)

    draw.rounded_rectangle(
        [PANEL_X, UY, PANEL_X + PANEL_W, UY + TIME_H],
        radius=s(8),
        fill=C_BODY
    )

    safe_text(draw, (PANEL_X + s(12), UY + TEXT_Y), utc_text, C_TEAL, f_time)

    # ───── LOCAL PANEL ─────
    LY_LABEL = UY + TIME_H + GAP

    safe_text(draw, (PANEL_X, LY_LABEL), "LOCAL PC TIME", C_GRAY, f_label)

    LY = LY_LABEL + s(14)

    draw.rounded_rectangle(
        [PANEL_X, LY, PANEL_X + PANEL_W, LY + TIME_H],
        radius=s(8),
        fill=C_BODY
    )

    safe_text(draw, (PANEL_X + s(12), LY + TEXT_Y), local_text, C_YELLOW, f_time)

    # ───── BUTTONS ─────
    BY = BODY_Y

    draw.rounded_rectangle(
        [BTN_X, BY, BTN_X + BTN_W, BY + TIME_H],
        radius=s(8),
        fill=C_SYNC
    )

    safe_text(draw, (BTN_X + s(14), BY + TEXT_Y), "Sync Now", C_WHITE, f_btn)

    # ───── FOOTER ─────
    FOOT_Y = by + BOX_H - FOOT_H

    draw.rectangle([bx, FOOT_Y, bx + BOX_W, by + BOX_H], fill=C_FOOTER)

    draw.ellipse(
        [bx + s(16), FOOT_Y + s(8), bx + s(26), FOOT_Y + s(18)],
        fill=C_GREEN
    )

    safe_text(
        draw,
        (bx + s(32), FOOT_Y + s(6)),
        "Synced Perfectly",
        C_GREEN,
        f_status
    )

    diff = "diff: 0.0s via NIST"

    dw = draw.textbbox((0, 0), diff, font=f_diff)[2]

    safe_text(
        draw,
        (bx + BOX_W - dw - s(14), FOOT_Y + s(6)),
        diff,
        C_GRAY,
        f_diff
    )

    result = Image.alpha_composite(img, overlay)

    result.convert("RGB").save(output_path, quality=95)


# ───────────────── TELEGRAM FUNCTIONS ─────────────────
def send_message(chat_id, text):

    requests.post(
        f"{URL}/sendMessage",
        data={"chat_id": chat_id, "text": text}
    )


def send_photo(chat_id, photo_path, caption=""):

    with open(photo_path, "rb") as f:

        requests.post(
            f"{URL}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": f}
        )


def download_file(file_id, path):

    file_info = requests.get(
        f"{URL}/getFile",
        params={"file_id": file_id}
    ).json()

    file_path = file_info["result"]["file_path"]

    content = requests.get(
        f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    ).content

    with open(path, "wb") as f:
        f.write(content)

    return True


def detect_size_mode_from_text(text, default="medium"):

    if not text:
        return default

    t = text.lower()

    if "small" in t:
        return "small"

    if "medium" in t:
        return "medium"

    return default


def cleanup(path):

    if os.path.exists(path):
        os.remove(path)


def handle_photo_message(msg):

    chat_id = msg["chat"]["id"]

    caption = msg.get("caption", "")

    mode = detect_size_mode_from_text(
        caption,
        USER_SIZE_MODE.get(chat_id, "medium")
    )

    file_id = msg["photo"][-1]["file_id"]

    uid = uuid.uuid4().hex

    inp = f"/tmp/in_{uid}.jpg"
    out = f"/tmp/out_{uid}.jpg"

    send_message(chat_id, f"Processing watermark mode: {mode}...")

    download_file(file_id, inp)

    add_watermark(inp, out, mode)

    send_photo(chat_id, out, f"Watermark {mode} selesai ✅")

    cleanup(inp)
    cleanup(out)


# ───────────────── MAIN LOOP ─────────────────
def main():

    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start()

    offset = None

    print("Bot running...")

    while True:

        updates = requests.get(
            f"{URL}/getUpdates",
            params={"timeout": 30, "offset": offset}
        ).json()

        for u in updates.get("result", []):

            offset = u["update_id"] + 1

            msg = u.get("message", {})

            if not msg:
                continue

            chat_id = msg["chat"]["id"]

            text = msg.get("text", "").lower()

            if text == "/small":

                USER_SIZE_MODE[chat_id] = "small"

                send_message(chat_id, "Mode small aktif")

                continue

            if text == "/medium":

                USER_SIZE_MODE[chat_id] = "medium"

                send_message(chat_id, "Mode medium aktif")

                continue

            if "photo" in msg:

                handle_photo_message(msg)

        time.sleep(1)


if __name__ == "__main__":
    main()
