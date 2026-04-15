import os
import time
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone
from datetime import timedelta

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

def format_time(dt):
    return dt.strftime("%A | %B %d, %Y at %H:%M:%S")

def add_watermark(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    width, height = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # ===== FONT =====
    try:
        font_title = ImageFont.truetype("arial.ttf", 18)
        font_label = ImageFont.truetype("arial.ttf", 11)
        font_time = ImageFont.truetype("arialbd.ttf", 14)  # Bold untuk waktu
        font_status = ImageFont.truetype("arial.ttf", 12)
        font_small = ImageFont.truetype("arial.ttf", 10)
    except:
        font_title = font_label = font_time = font_status = font_small = ImageFont.load_default()

    # ===== TIME =====
    utc = datetime.now(timezone.utc)
    local = utc + timedelta(hours=7)  # Sesuaikan dengan timezone lokal

    line_utc = format_time(utc)
    line_local = format_time(local)

    # ===== UKURAN BOX =====
    box_w = 420
    box_h = 200

    x = width - box_w - 20
    y = height - box_h - 20

    # ===== WARNA =====
    bg_dark = (30, 30, 30)
    bg_time_block = (40, 40, 40)
    text_gray = (120, 120, 120)
    text_white = (255, 255, 255)
    accent_yellow = (255, 200, 60)
    accent_green = (80, 200, 120)
    btn_cyan = (0, 180, 180)
    btn_cyan_dark = (0, 150, 150)

    # =========================
    # BACKGROUND UTAMA (DARK)
    # =========================
    draw.rounded_rectangle(
        [x, y, x + box_w, y + box_h],
        radius=16,
        fill=bg_dark
    )

    # =========================
    # HEADER
    # =========================
    # Traffic light
    r = 6
    draw.ellipse([x + 15, y + 15, x + 15 + r*2, y + 15 + r*2], fill=(255, 95, 86))
    draw.ellipse([x + 35, y + 15, x + 35 + r*2, y + 15 + r*2], fill=(255, 189, 46))
    draw.ellipse([x + 55, y + 15, x + 55 + r*2, y + 15 + r*2], fill=(39, 201, 63))

    # Title (center)
    title = "Pozko Time"
    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text((x + (box_w - title_w) // 2, y + 12), title, fill=text_gray, font=font_title)

    # =========================
    # SERVER TIME (UTC)
    # =========================
    draw.text((x + 20, y + 45), "SERVER TIME (UTC)", fill=text_gray, font=font_label)

    # Blok waktu UTC
    draw.rounded_rectangle(
        [x + 20, y + 60, x + 280, y + 90],
        radius=6,
        fill=bg_time_block
    )
    draw.text((x + 35, y + 68), line_utc, fill=accent_yellow, font=font_time)

    # =========================
    # LOCAL PC TIME
    # =========================
    draw.text((x + 20, y + 100), "LOCAL PC TIME", fill=text_gray, font=font_label)

    # Blok waktu Local
    draw.rounded_rectangle(
        [x + 20, y + 115, x + 280, y + 145],
        radius=6,
        fill=bg_time_block
    )
    draw.text((x + 35, y + 123), line_local, fill=accent_yellow, font=font_time)

    # =========================
    # TOMBOL KANAN
    # =========================
    btn_x = x + 295
    btn_w = 105
    btn_h = 32

    # Sync Now button
    draw.rounded_rectangle(
        [btn_x, y + 55, btn_x + btn_w, y + 55 + btn_h],
        radius=8,
        fill=btn_cyan
    )
    draw.text((btn_x + 20, y + 62), "↻ Sync Now", fill=text_white, font=font_status)

    # Auto (2s) button
    draw.rounded_rectangle(
        [btn_x, y + 95, btn_x + btn_w, y + 95 + btn_h],
        radius=8,
        fill=btn_cyan_dark
    )
    draw.text((btn_x + 18, y + 102), "⏱ Auto Sync", fill=text_white, font=font_status)

    # Settings button
    draw.rounded_rectangle(
        [btn_x, y + 135, btn_x + btn_w, y + 135 + btn_h],
        radius=8,
        fill=(50, 50, 50)
    )
    draw.text((btn_x + 18, y + 142), "⚙ Settings", fill=text_gray, font=font_status)

    # =========================
    # FOOTER
    # =========================
    draw.text((x + 20, y + 170), "●", fill=accent_green, font=font_status)
    draw.text((x + 35, y + 170), "Synced Perfectly", fill=accent_green, font=font_status)

    # Diff info (kanan bawah)
    diff_text = "diff: 0.0s via NIST"
    diff_bbox = draw.textbbox((0, 0), diff_text, font=font_small)
    diff_w = diff_bbox[2] - diff_bbox[0]
    draw.text((x + box_w - diff_w - 20, y + 172), diff_text, fill=text_gray, font=font_small)

    # ===== FINAL =====
    result = Image.alpha_composite(img, overlay)
    result.convert("RGB").save(output_path)

# Contoh penggunaan
# add_watermark("input.png", "output.png")
    
def get_updates(offset=None):
    url = f"{URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    res = requests.get(url, params=params)
    return res.json()

def send_photo(chat_id, photo_path):
    url = f"{URL}/sendPhoto"
    with open(photo_path, "rb") as f:
        requests.post(url, data={"chat_id": chat_id}, files={"photo": f})

def download_file(file_id, path):
    file_info = requests.get(f"{URL}/getFile", params={"file_id": file_id}).json()
    file_path = file_info["result"]["file_path"]

    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    content = requests.get(file_url).content

    with open(path, "wb") as f:
        f.write(content)

def main():
    print("Bot jalan...")
    offset = None

    while True:
        data = get_updates(offset)

        for update in data["result"]:
            offset = update["update_id"] + 1

            if "message" in update and "photo" in update["message"]:
                chat_id = update["message"]["chat"]["id"]
                file_id = update["message"]["photo"][-1]["file_id"]

                download_file(file_id, "input.jpg")
                add_watermark("input.jpg", "output.jpg")
                send_photo(chat_id, "output.jpg")

        time.sleep(2)

if __name__ == "__main__":
    main()
