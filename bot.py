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
        font_title = ImageFont.truetype("arial.ttf", 18)
        font_text = ImageFont.truetype("arial.ttf", 14)
    except:
        font_title = font_text = ImageFont.load_default()

    # ===== TIME =====
    utc = datetime.now(timezone.utc)
    wib = utc + timedelta(hours=7)

    line1 = format_time(utc)
    line2 = format_time(wib)

    # ===== HITUNG LEBAR DINAMIS =====
    padding = 20
    text_width = max(
        draw.textlength(line1, font=font_text),
        draw.textlength(line2, font=font_text)
    )

    box_w = int(text_width + padding*2 + 80)  # tambah ruang tombol kanan
    box_h = 170

    x = width - box_w - 20
    y = height - box_h - 20

    # ===== WINDOW BACKGROUND =====
    draw.rounded_rectangle(
        [x, y, x+box_w, y+box_h],
        radius=18,
        fill=(22, 22, 26, 235)
    )

    # ===== TITLE BAR =====
    draw.rectangle([x, y, x+box_w, y+35], fill=(30,30,35,255))

    # ===== TRAFFIC LIGHT BUTTON =====
    r = 6
    draw.ellipse([x+12, y+12, x+12+r*2, y+12+r*2], fill=(255,95,86))   # merah
    draw.ellipse([x+30, y+12, x+30+r*2, y+12+r*2], fill=(255,189,46))  # kuning
    draw.ellipse([x+48, y+12, x+48+r*2, y+12+r*2], fill=(39,201,63))   # hijau

    # ===== TITLE =====
    draw.text((x+80, y+10), "Yoski Time", fill=(200,200,220), font=font_title)

    # ===== CONTENT =====
    draw.text((x+20, y+50), "SERVER TIME (UTC)", fill=(120,180,255), font=font_text)
    draw.text((x+20, y+70), line1, fill=(120,255,255), font=font_text)

    draw.text((x+20, y+100), "LOCAL TIME (WIB)", fill=(200,200,200), font=font_text)
    draw.text((x+20, y+120), line2, fill=(255,200,100), font=font_text)

    # ===== STATUS BAR =====
    draw.rectangle([x, y+box_h-30, x+box_w, y+box_h], fill=(28,28,32))
    draw.text((x+20, y+box_h-25), "● LIVE SYNCED", fill=(100,255,120), font=font_text)

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
