import os
import time
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, timedelta

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"


def format_time(dt):
    return dt.strftime("%A | %B %d, %Y at %H:%M:%S")


def get_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Coba load font dari beberapa lokasi umum, fallback ke default."""
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


def add_watermark(input_path: str, output_path: str) -> None:
    img = Image.open(input_path).convert("RGBA")
    width, height = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_title  = get_font("arial.ttf",   18)
    font_label  = get_font("arial.ttf",   11)
    font_time   = get_font("arialbd.ttf", 14)
    font_status = get_font("arial.ttf",   12)
    font_small  = get_font("arial.ttf",   10)

    utc   = datetime.now(timezone.utc)
    local = utc + timedelta(hours=7)

    line_utc   = format_time(utc)
    line_local = format_time(local)

    box_w = 430
    box_h = 200

    # Pastikan box tidak keluar dari gambar
    x = max(10, width  - box_w - 20)
    y = max(10, height - box_h - 20)

    bg_dark       = (30,  30,  30,  210)
    bg_time_block = (40,  40,  40,  230)
    text_gray     = (120, 120, 120, 255)
    text_white    = (255, 255, 255, 255)
    accent_yellow = (255, 200, 60,  255)
    accent_green  = (80,  200, 120, 255)
    btn_blue      = (26,  111, 212, 255)
    btn_blue_dark = (15,  80,  160, 255)
    btn_gray      = (50,  50,  50,  255)

    # Background utama
    draw.rounded_rectangle(
        [x, y, x + box_w, y + box_h],
        radius=16,
        fill=bg_dark,
    )

    # Traffic light dots
    for i, color in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        cx = x + 15 + i * 20
        draw.ellipse([cx, y + 15, cx + 12, y + 27], fill=color)

    # Judul tengah
    title = "Bob's Time"
    tw = draw.textbbox((0, 0), title, font=font_title)[2]
    draw.text((x + (box_w - tw) // 2, y + 12), title, fill=text_gray, font=font_title)

    # Label Server Time
    draw.text((x + 20, y + 45), "SERVER TIME (UTC)", fill=text_gray, font=font_label)

    # Kotak UTC
    draw.rounded_rectangle([x + 20, y + 60, x + 285, y + 92], radius=6, fill=bg_time_block)
    draw.text((x + 30, y + 68), line_utc, fill=accent_yellow, font=font_time)

    # Label Local PC Time
    draw.text((x + 20, y + 100), "LOCAL PC TIME", fill=text_gray, font=font_label)

    # Kotak Local
    draw.rounded_rectangle([x + 20, y + 115, x + 285, y + 147], radius=6, fill=bg_time_block)
    draw.text((x + 30, y + 123), line_local, fill=accent_yellow, font=font_time)

    # Tombol kanan
    btn_x = x + 300
    btn_w = 110
    btn_h = 30

    # Sync Now
    draw.rounded_rectangle([btn_x, y + 55, btn_x + btn_w, y + 55 + btn_h], radius=8, fill=btn_blue)
    draw.text((btn_x + 14, y + 61), "Sync Now", fill=text_white, font=font_status)

    # Auto Sync
    draw.rounded_rectangle([btn_x, y + 93, btn_x + btn_w, y + 93 + btn_h], radius=8, fill=btn_blue_dark)
    draw.text((btn_x + 14, y + 99), "Auto Sync", fill=text_white, font=font_status)

    # Settings
    draw.rounded_rectangle([btn_x, y + 131, btn_x + btn_w, y + 131 + btn_h], radius=8, fill=btn_gray)
    draw.text((btn_x + 22, y + 137), "Settings", fill=text_gray, font=font_status)

    # Footer status
    draw.ellipse([x + 20, y + 174, x + 28, y + 182], fill=accent_green)
    draw.text((x + 35, y + 171), "Synced Perfectly", fill=accent_green, font=font_status)

    diff_text = "diff: 0.0s via NIST"
    dw = draw.textbbox((0, 0), diff_text, font=font_small)[2]
    draw.text((x + box_w - dw - 15, y + 173), diff_text, fill=text_gray, font=font_small)

    result = Image.alpha_composite(img, overlay)
    result.convert("RGB").save(output_path, quality=95)


def send_message(chat_id: int, text: str) -> None:
    requests.post(f"{URL}/sendMessage", data={"chat_id": chat_id, "text": text})


def send_photo(chat_id: int, photo_path: str, caption: str = "") -> None:
    with open(photo_path, "rb") as f:
        requests.post(
            f"{URL}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption},
            files={"photo": f},
        )


def download_file(file_id: str, path: str) -> bool:
    try:
        file_info = requests.get(
            f"{URL}/getFile", params={"file_id": file_id}, timeout=15
        ).json()
        file_path = file_info["result"]["file_path"]
        content = requests.get(
            f"https://api.telegram.org/file/bot{TOKEN}/{file_path}", timeout=30
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


def main():
    if not TOKEN:
        print("ERROR: BOT_TOKEN belum di-set. Jalankan: export BOT_TOKEN=xxx")
        return

    print("Bot berjalan... Kirim foto ke bot untuk ditambahkan watermark.")
    offset = None

    while True:
        data = get_updates(offset)

        for update in data.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")

            if not chat_id:
                continue

            # Handle /start dan /help
            text = msg.get("text", "")
            if text in ("/start", "/help"):
                send_message(
                    chat_id,
                    "Halo! Kirimkan foto dan saya akan menambahkan watermark waktu (UTC & WIB) otomatis.",
                )
                continue

            # Handle foto
            if "photo" in msg:
                file_id = msg["photo"][-1]["file_id"]
                if download_file(file_id, "input.jpg"):
                    try:
                        add_watermark("input.jpg", "output.jpg")
                        send_photo(chat_id, "output.jpg", caption="Watermark berhasil ditambahkan.")
                    except Exception as e:
                        print(f"[watermark] Error: {e}")
                        send_message(chat_id, "Gagal memproses gambar.")
                else:
                    send_message(chat_id, "Gagal mengunduh foto.")
                continue

            # Pesan lain selain foto
            if msg:
                send_message(chat_id, "Kirim foto untuk mendapatkan watermark waktu.")

        time.sleep(1)


if __name__ == "__main__":
    main()
