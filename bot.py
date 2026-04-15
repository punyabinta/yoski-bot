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

    # ===== FONT (LEBIH BESAR & TEBAL FEEL) =====
    try:
        font_title = ImageFont.truetype("arial.ttf", 20)
        font_text = ImageFont.truetype("arial.ttf", 16)
    except:
        font_title = font_text = ImageFont.load_default()

    # ===== TIME =====
    utc = datetime.now(timezone.utc)
    wib = utc + timedelta(hours=7)

    line1 = format_time(utc)
    line2 = format_time(wib)

    # ===== HITUNG LEBAR DINAMIS =====
    padding = 25
    text_width = max(
        draw.textlength(line1, font=font_text),
        draw.textlength(line2, font=font_text)
    )

    box_w = int(text_width + padding*2 + 100)
    box_h = 180

    x = width - box_w - 20
    y = height - box_h - 20

    # ===== BACKGROUND UTAMA (LEBIH SOFT / GLASS FEEL) =====
    draw.rounded_rectangle(
        [x, y, x+box_w, y+box_h],
        radius=22,
        fill=(28, 28, 32, 200)  # opacity diturunin (lebih transparan)
    )

    # ===== TITLE BAR =====
    draw.rounded_rectangle(
        [x, y, x+box_w, y+40],
        radius=22,
        fill=(35,35,40,230)
    )

    # ===== TRAFFIC LIGHT BUTTON (MACOS) =====
    r = 7
    draw.ellipse([x+14, y+14, x+14+r*2, y+14+r*2], fill=(255,95,86))   # merah
    draw.ellipse([x+36, y+14, x+36+r*2, y+14+r*2], fill=(255,189,46))  # kuning
    draw.ellipse([x+58, y+14, x+58+r*2, y+14+r*2], fill=(39,201,63))   # hijau

    # ===== TITLE (CENTER FEEL) =====
    draw.text((x+100, y+12), "Yoski Time", fill=(220,220,235), font=font_title)

    # ===== CONTENT =====
    draw.text((x+25, y+60), "SERVER TIME (UTC)", fill=(140,190,255), font=font_text)
    draw.text((x+25, y+82), line1, fill=(120,255,255), font=font_text)

    draw.text((x+25, y+112), "LOCAL TIME (WIB)", fill=(210,210,210), font=font_text)
    draw.text((x+25, y+134), line2, fill=(255,210,120), font=font_text)

    # ===== STATUS BAR =====
    draw.rounded_rectangle(
        [x, y+box_h-32, x+box_w, y+box_h],
        radius=22,
        fill=(30,30,35,220)
    )

    draw.text((x+25, y+box_h-26), "● LIVE SYNCED", fill=(120,255,150), font=font_text)

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
