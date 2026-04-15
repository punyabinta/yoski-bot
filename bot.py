import os
import time
import requests
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}"

def format_time(dt):
    return dt.strftime("%A | %B %d, %Y at %H:%M:%S")

def add_watermark(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    width, height = img.size

    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)

    box_w = int(width * 0.5)
    box_h = int(height * 0.3)

    x = width - box_w - 20
    y = height - box_h - 20

    draw.rectangle([x, y, x+box_w, y+box_h], fill=(30,30,30,200))

    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()

    utc = datetime.now(timezone.utc)
    local = datetime.now()

    draw.text((x+10, y+10), "Yoski Time", fill=(200,200,255), font=font)
    draw.text((x+10, y+40), "Server: " + format_time(utc), fill=(255,255,255), font=font)
    draw.text((x+10, y+70), "Local: " + format_time(local), fill=(255,255,255), font=font)
    draw.text((x+10, y+100), "Synced Perfectly", fill=(150,255,150), font=font)

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
