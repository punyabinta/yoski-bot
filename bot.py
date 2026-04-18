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


# ── Health check ──────────────────────────────────────────────────────────────
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


# ── Helpers ───────────────────────────────────────────────────────────────────
def format_time(dt):
    return dt.strftime("%A | %B %d, %Y at %H:%M:%S")


def get_font(path: str, size: int):
    is_bold = "bd" in path.lower() or "bold" in path.lower()
    is_mono = "cour" in path.lower() or "mono" in path.lower()

    candidates = [path]
    if is_mono:
        candidates += [
            f"/usr/share/fonts/truetype/dejavu/DejaVuSansMono{'-Bold' if is_bold else ''}.ttf",
            f"/usr/share/fonts/truetype/liberation/LiberationMono-{'Bold' if is_bold else 'Regular'}.ttf",
            f"/usr/share/fonts/truetype/msttcorefonts/{'courbd' if is_bold else 'cour'}.ttf",
            f"/usr/share/fonts/truetype/freefont/FreeMono{'Bold' if is_bold else ''}.ttf",
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


# ── Core watermark ────────────────────────────────────────────────────────────
def add_watermark(input_path: str, output_path: str) -> None:
    img = Image.open(input_path).convert("RGBA")
    W, H = img.size
    is_portrait = H >= W   # square dianggap portrait

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    utc   = datetime.now(timezone.utc)
    local = utc + timedelta(hours=7)
    line_utc   = format_time(utc)
    line_local = format_time(local)

    # ── SKALA TERPISAH ────────────────────────────────────────────────────
    # BOX_W : hanya mengontrol LEBAR kontainer (52% / 42% dari W)
    # u()   : mengontrol TINGGI, FONT, PADDING — berdasarkan tinggi gambar H
    #         mengecilkan BOX_W tidak mempengaruhi font/tinggi sama sekali

    if is_portrait:
        BOX_W = max(300, min(900,  int(W * 0.52)))
    else:
        BOX_W = max(420, min(1100, int(W * 0.42)))

    # Referensi tinggi desain = 1920px
    REF_H  = 1920.0
    unit_h = H / REF_H

    def u(v):
        """Scale berdasarkan TINGGI gambar — font & padding tidak ikut mengecil saat lebar dikurangi."""
        return max(1, int(v * unit_h))

    # ── TINGGI BOX: dihitung dari komponen ──────────────────────────────
    TITLE_H    = u(52)
    LABEL_H    = u(28)
    TIMEBOX_H  = u(58)
    GAP_INNER  = u(18)
    BODY_PAD_T = u(18)
    BODY_PAD_B = u(14)
    FOOTER_H   = u(44)

    BODY_H = BODY_PAD_T + LABEL_H + TIMEBOX_H + GAP_INNER + LABEL_H + TIMEBOX_H + BODY_PAD_B
    BOX_H  = TITLE_H + BODY_H + FOOTER_H

    RADIUS = u(16)

    # ── POSISI: pojok kanan bawah dengan margin ──────────────────────────
    MARGIN_X = u(28)
    MARGIN_Y = u(40) if is_portrait else u(28)

    bx = max(8, W - BOX_W - MARGIN_X)
    by = max(8, H - BOX_H - MARGIN_Y)

    # ── WARNA ────────────────────────────────────────────────────────────
    C_WIN_BG    = (28,  28,  28,  240)
    C_TITLE_BG  = (40,  40,  40,  255)
    C_BODY_BG   = (255, 255, 255, 255)   # putih solid
    C_FOOTER_BG = (255, 255, 255, 255)   # putih solid
    C_TIMEBOX   = (18,  18,  18,  255)   # kotak waktu gelap
    C_BTN_SYNC  = (26,  111, 212, 255)
    C_BTN_AUTO  = (50,  50,  50,  255)
    C_BTN_SET   = (42,  42,  42,  255)
    C_DIVIDER   = (55,  55,  55,  255)
    C_DIV_LIGHT = (210, 210, 210, 255)
    C_GRAY_LBL  = (90,  90,  90,  255)
    C_GRAY_TITL = (150, 150, 150, 255)
    C_WHITE     = (255, 255, 255, 255)
    C_TEAL      = (30,  185, 172, 255)
    C_YELLOW    = (195, 148, 28,  255)
    C_GREEN     = (28,  155, 48,  255)
    C_SILVER    = (195, 195, 195, 255)

    # ── FONT: semua proporsional ─────────────────────────────────────────
    sz_title    = u(22)
    sz_label    = u(18)
    sz_time     = u(24)
    sz_btn      = u(20)
    sz_status   = u(20)
    sz_diff     = u(18)

    f_appname = get_font("arial.ttf",   sz_title)
    f_label   = get_font("arialbd.ttf", sz_label)
    f_time    = get_font("cour.ttf",    sz_time)
    f_btn     = get_font("arial.ttf",   sz_btn)
    f_status  = get_font("arialbd.ttf", sz_status)
    f_diff    = get_font("cour.ttf",    sz_diff)

    # ═══════════════════════════════════════════════════
    # 1. WINDOW BACKGROUND
    # ═══════════════════════════════════════════════════
    draw.rounded_rectangle([bx, by, bx+BOX_W, by+BOX_H], radius=RADIUS, fill=C_WIN_BG)

    # ═══════════════════════════════════════════════════
    # 2. TITLEBAR
    # ═══════════════════════════════════════════════════
    draw.rounded_rectangle(
        [bx, by, bx+BOX_W, by+TITLE_H+RADIUS],
        radius=RADIUS, fill=C_TITLE_BG
    )
    draw.rectangle([bx, by+TITLE_H, bx+BOX_W, by+TITLE_H+1], fill=C_DIVIDER)

    # Traffic light dots
    dot_sz = u(16)
    dot_gap = u(26)
    for i, col in enumerate([(255,95,86,255),(255,189,46,255),(40,200,64,255)]):
        cx = bx + u(20) + i * dot_gap
        cy = by + (TITLE_H - dot_sz) // 2
        draw.ellipse([cx, cy, cx+dot_sz, cy+dot_sz], fill=col)

    # App name center
    app_text = "Bob's Time"
    tb = draw.textbbox((0,0), app_text, font=f_appname)
    tw = tb[2] - tb[0]
    th = tb[3] - tb[1]
    safe_text(draw,
        (bx + (BOX_W - tw) // 2, by + (TITLE_H - th) // 2),
        app_text, C_GRAY_TITL, f_appname
    )

    # ═══════════════════════════════════════════════════
    # 3. BODY (putih solid)
    # ═══════════════════════════════════════════════════
    BODY_TOP    = by + TITLE_H + 1
    FOOTER_TOP  = by + BOX_H - FOOTER_H

    draw.rectangle([bx, BODY_TOP, bx+BOX_W, FOOTER_TOP], fill=C_BODY_BG)
    draw.rectangle([bx, BODY_TOP, bx+BOX_W, BODY_TOP+1], fill=C_DIVIDER)

    # Layout: panel kiri + tombol kanan
    # Lebar tombol & padding pakai proporsi BOX_W agar tidak overflow
    BTN_W   = int(BOX_W * 0.30)   # 30% dari lebar box
    PAD_L   = int(BOX_W * 0.035)  # padding kiri panel
    PAD_R   = int(BOX_W * 0.025)  # padding kanan tombol
    GAP_BTN = int(BOX_W * 0.025)  # gap antara panel dan tombol
    PANEL_X = bx + PAD_L
    PANEL_W = BOX_W - BTN_W - PAD_L - GAP_BTN - PAD_R
    BTN_X   = bx + BOX_W - BTN_W - PAD_R

    # Cursor y untuk panel kiri
    cur_y = BODY_TOP + BODY_PAD_T

    # Label UTC
    safe_text(draw, (PANEL_X, cur_y), "SERVER TIME (UTC)", C_GRAY_LBL, f_label)
    cur_y += LABEL_H

    # Kotak UTC
    draw.rounded_rectangle(
        [PANEL_X, cur_y, PANEL_X+PANEL_W, cur_y+TIMEBOX_H],
        radius=u(10), fill=C_TIMEBOX
    )
    tb_u = draw.textbbox((0,0), line_utc, font=f_time)
    th_u = tb_u[3] - tb_u[1]
    safe_text(draw,
        (PANEL_X + u(16), cur_y + (TIMEBOX_H - th_u) // 2),
        line_utc, C_TEAL, f_time
    )
    cur_y += TIMEBOX_H + GAP_INNER

    # Label Local
    safe_text(draw, (PANEL_X, cur_y), "LOCAL PC TIME", C_GRAY_LBL, f_label)
    cur_y += LABEL_H

    # Kotak Local
    draw.rounded_rectangle(
        [PANEL_X, cur_y, PANEL_X+PANEL_W, cur_y+TIMEBOX_H],
        radius=u(10), fill=C_TIMEBOX
    )
    tb_l = draw.textbbox((0,0), line_local, font=f_time)
    th_l = tb_l[3] - tb_l[1]
    safe_text(draw,
        (PANEL_X + u(16), cur_y + (TIMEBOX_H - th_l) // 2),
        line_local, C_YELLOW, f_time
    )

    # Tombol kanan — vertikal centered dalam body
    B_H   = u(52)
    B_GAP = u(14)
    total_btn_h = B_H * 3 + B_GAP * 2
    b_start_y = BODY_TOP + (BODY_H - total_btn_h) // 2

    # Sync Now
    draw.rounded_rectangle(
        [BTN_X, b_start_y, BTN_X+BTN_W, b_start_y+B_H],
        radius=u(10), fill=C_BTN_SYNC
    )
    tb_b = draw.textbbox((0,0), "Sync Now", font=f_btn)
    bw = tb_b[2] - tb_b[0]
    bh = tb_b[3] - tb_b[1]
    safe_text(draw,
        (BTN_X + (BTN_W - bw) // 2, b_start_y + (B_H - bh) // 2),
        "Sync Now", C_WHITE, f_btn
    )

    # Auto Sync
    b2y = b_start_y + B_H + B_GAP
    draw.rounded_rectangle(
        [BTN_X, b2y, BTN_X+BTN_W, b2y+B_H],
        radius=u(10), fill=C_BTN_AUTO
    )
    tb_b2 = draw.textbbox((0,0), "Auto Sync", font=f_btn)
    bw2 = tb_b2[2] - tb_b2[0]
    bh2 = tb_b2[3] - tb_b2[1]
    safe_text(draw,
        (BTN_X + (BTN_W - bw2) // 2, b2y + (B_H - bh2) // 2),
        "Auto Sync", C_SILVER, f_btn
    )

    # Settings
    b3y = b2y + B_H + B_GAP
    draw.rounded_rectangle(
        [BTN_X, b3y, BTN_X+BTN_W, b3y+B_H],
        radius=u(10), fill=C_BTN_SET
    )
    tb_b3 = draw.textbbox((0,0), "Settings", font=f_btn)
    bw3 = tb_b3[2] - tb_b3[0]
    bh3 = tb_b3[3] - tb_b3[1]
    safe_text(draw,
        (BTN_X + (BTN_W - bw3) // 2, b3y + (B_H - bh3) // 2),
        "Settings", C_SILVER, f_btn
    )

    # ═══════════════════════════════════════════════════
    # 4. FOOTER (putih solid)
    # ═══════════════════════════════════════════════════
    draw.rectangle([bx, FOOTER_TOP, bx+BOX_W, by+BOX_H], fill=C_FOOTER_BG)
    draw.rectangle([bx, FOOTER_TOP, bx+BOX_W, FOOTER_TOP+1], fill=C_DIV_LIGHT)

    dot_f = u(14)
    dot_fy = FOOTER_TOP + (FOOTER_H - dot_f) // 2
    draw.ellipse([bx+u(22), dot_fy, bx+u(22)+dot_f, dot_fy+dot_f], fill=C_GREEN)

    tb_s = draw.textbbox((0,0), "Synced Perfectly", font=f_status)
    sh = tb_s[3] - tb_s[1]
    safe_text(draw,
        (bx + u(22) + dot_f + u(10), FOOTER_TOP + (FOOTER_H - sh) // 2),
        "Synced Perfectly", C_GREEN, f_status
    )

    diff_text = "diff: 0.0s via NIST"
    tb_d = draw.textbbox((0,0), diff_text, font=f_diff)
    dw = tb_d[2] - tb_d[0]
    dh = tb_d[3] - tb_d[1]
    safe_text(draw,
        (bx + BOX_W - dw - u(18), FOOTER_TOP + (FOOTER_H - dh) // 2),
        diff_text, C_GRAY_LBL, f_diff
    )

    # ═══════════════════════════════════════════════════
    # 5. RENDER
    # ═══════════════════════════════════════════════════
    result = Image.alpha_composite(img, overlay)
    result.convert("RGB").save(output_path, quality=95)


# ── Bot handlers ──────────────────────────────────────────────────────────────
def send_message(chat_id: int, text: str) -> None:
    try:
        requests.post(f"{URL}/sendMessage",
                      data={"chat_id": chat_id, "text": text}, timeout=20)
    except Exception as e:
        print(f"[send_message] Error: {e}")


def send_photo(chat_id: int, photo_path: str, caption: str = "") -> None:
    try:
        with open(photo_path, "rb") as f:
            requests.post(f"{URL}/sendPhoto",
                          data={"chat_id": chat_id, "caption": caption},
                          files={"photo": f}, timeout=60)
    except Exception as e:
        print(f"[send_photo] Error: {e}")


def download_file(file_id: str, path: str) -> bool:
    try:
        info = requests.get(f"{URL}/getFile",
                            params={"file_id": file_id}, timeout=20).json()
        if not info.get("ok"):
            print(f"[download_file] gagal: {info}")
            return False
        fp = info["result"]["file_path"]
        content = requests.get(
            f"https://api.telegram.org/file/bot{TOKEN}/{fp}", timeout=60
        ).content
        with open(path, "wb") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[download_file] Error: {e}")
        return False


def get_updates(offset=None):
    try:
        res = requests.get(f"{URL}/getUpdates",
                           params={"timeout": 30, "offset": offset}, timeout=35)
        return res.json()
    except Exception as e:
        print(f"[get_updates] Error: {e}")
        return {"result": []}


def cleanup_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def handle_photo_message(msg: dict):
    chat_id = msg.get("chat", {}).get("id")
    if not chat_id:
        return

    photo_list = msg.get("photo", [])
    if not photo_list:
        send_message(chat_id, "Foto tidak ditemukan.")
        return

    file_id     = photo_list[-1]["file_id"]
    unique_id   = uuid.uuid4().hex
    input_path  = f"/tmp/input_{chat_id}_{unique_id}.jpg"
    output_path = f"/tmp/output_{chat_id}_{unique_id}.jpg"

    send_message(chat_id, "Memproses watermark...")

    try:
        if not download_file(file_id, input_path):
            send_message(chat_id, "Gagal mengunduh foto.")
            return
        add_watermark(input_path, output_path)
        send_photo(chat_id, output_path, caption="Watermark berhasil ditambahkan.")
    except Exception as e:
        print(f"[handle_photo] Error: {e}")
        send_message(chat_id, "Gagal memproses gambar.")
    finally:
        cleanup_file(input_path)
        cleanup_file(output_path)


def main():
    if not TOKEN:
        print("ERROR: BOT_TOKEN belum di-set.")
        return

    threading.Thread(target=run_health_server, daemon=True).start()
    print("Bot berjalan...")
    offset = None

    while True:
        data = get_updates(offset)

        for update in data.get("result", []):
            offset = update["update_id"] + 1
            msg    = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            if not chat_id:
                continue

            text = msg.get("text", "").strip().lower()

            if text == "/start":
                send_message(chat_id,
                    "Halo! Kirimkan foto dan saya akan menambahkan watermark Bob's Time.\n\n"
                    "Watermark otomatis menyesuaikan ukuran gambar (portrait maupun landscape).\n\n"
                    "/help untuk bantuan.")
                continue

            if text == "/help":
                send_message(chat_id,
                    "Cara penggunaan:\n\n"
                    "Cukup kirim foto — watermark akan otomatis menyesuaikan ukuran dan orientasi gambar.\n\n"
                    "Tidak perlu pilih ukuran manual.")
                continue

            if "photo" in msg:
                handle_photo_message(msg)
                continue

            if msg:
                send_message(chat_id,
                    "Kirim foto untuk mendapatkan watermark waktu otomatis.")

        time.sleep(1)


if __name__ == "__main__":
    main()
