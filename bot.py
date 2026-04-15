import os
import imghdr2 as imghdr
from telegram.ext import Updater, MessageHandler, Filters
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone

TOKEN = os.getenv("BOT_TOKEN")

def format_time(dt):
    return dt.strftime("%A | %B %d, %Y at %H:%M:%S")

def add_watermark(image_path, output_path):
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    box_width = int(width * 0.55)
    box_height = int(height * 0.4)

    x = width - box_width - 20
    y = height - box_height - 20

    draw.rectangle([x, y, x + box_width, y + box_height], fill=(25, 25, 30, 230))

    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()

    utc_time = datetime.now(timezone.utc)
    local_time = datetime.now()

    draw.text((x + 15, y + 15), "Yoski Time", fill=(180, 180, 200), font=font)
    draw.text((x + 15, y + 45), "Server: " + format_time(utc_time), fill=(120, 255, 255), font=font)
    draw.text((x + 15, y + 75), "Local: " + format_time(local_time), fill=(255, 200, 100), font=font)
    draw.text((x + 15, y + 110), "● Synced Perfectly", fill=(100, 255, 120), font=font)

    result = Image.alpha_composite(img, overlay)
    result.convert("RGB").save(output_path)

def handle_photo(update, context):
    photo = update.message.photo[-1].get_file()

    input_path = "input.jpg"
    output_path = "output.jpg"

    photo.download(input_path)

    add_watermark(input_path, output_path)

    update.message.reply_photo(photo=open(output_path, "rb"))

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.photo, handle_photo))

    print("Bot jalan...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
