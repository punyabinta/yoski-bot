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

    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)

    # ===== FONT =====
    try:
        font_title = ImageFont.truetype("arial.ttf", 20)
        font_text = ImageFont.truetype("arial.ttf", 15)
        font_small = ImageFont.truetype("arial.ttf", 13)
    except:
        font_title = font_text = font_small = ImageFont.load_default()

    # ===== TIME =====
    utc = datetime.now(timezone.utc)
    wib = utc + timedelta(hours=7)

    line1 = format_time(utc)
    line2 = format_time(wib)

    # ===== SIZE DINAMIS =====
    padding = 25
    text_width = max(
        draw.textlength(line1, font=font_text),
        draw.textlength(line2, font=font_text)
    )

    box_w = int(text_width + 160)
    box_h = 190

    x = width - box_w - 20
    y = height - box_h - 20

    # ===== BACKGROUND UTAMA (PUTIH) =====
    draw.rounded_rectangle(
        [x, y, x+box_w, y+box_h],
        radius=22,
        fill=(255,255,255)
    )

    # =========================
    # 🔳 BAGIAN 1: HEADER (HITAM)
    # =========================
    draw.rounded_rectangle(
        [x, y, x+box_w, y+45],
        radius=22,
        fill=(20,20,20)
    )

    # Traffic light
    r = 6
    draw.ellipse([x+14, y+15, x+14+r*2, y+15+r*2], fill=(255,95,86))
    draw.ellipse([x+32, y+15, x+32+r*2, y+15+r*2], fill=(255,189,46))
    draw.ellipse([x+50, y+15, x+50+r*2, y+15+r*2], fill=(39,201,63))

    # Title
    draw.text((x+80, y+12), "Yoski Time", fill=(255,255,255), font=font_title)

    # =========================
    # ⚪ BAGIAN 2: MAIN (PUTIH + BLOK HITAM)
    # =========================

    # Label
    draw.text((x+20, y+60), "SERVER TIME (UTC)", fill=(80,80,80), font=font_small)

    # Blok hitam untuk waktu
    draw.rounded_rectangle(
        [x+20, y+80, x+box_w-20, y+110],
        radius=10,
        fill=(20,20,20)
    )
    draw.text((x+30, y+88), line1, fill=(255,255,255), font=font_text)

    # Label 2
    draw.text((x+20, y+120), "LOCAL TIME (WIB)", fill=(80,80,80), font=font_small)

    # Blok hitam untuk waktu 2
    draw.rounded_rectangle(
        [x+20, y+140, x+box_w-20, y+170],
        radius=10,
        fill=(20,20,20)
    )
    draw.text((x+30, y+148), line2, fill=(255,255,255), font=font_text)

    # =========================
    # ⚪ BAGIAN 3: FOOTER (PUTIH)
    # =========================
    draw.text((x+20, y+box_h-25), "● LIVE SYNCED", fill=(0,150,80), font=font_small)

    # ===== FINAL =====
    result = Image.alpha_composite(img, overlay)
    result.convert("RGB").save(output_path)    
    
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
