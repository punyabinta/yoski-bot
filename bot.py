import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
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

    draw.rounded_rectangle(
        [x, y, x + box_width, y + box_height],
        radius=20,
        fill=(25, 25, 30, 230)
    )

    try:
        font_title = ImageFont.truetype("arial.ttf", 24)
        font_text = ImageFont.truetype("arial.ttf", 16)
    except:
        font_title = font_text = ImageFont.load_default()

    draw.text((x + 20, y + 15), "Yoski Time", fill=(180, 180, 200), font=font_title)

    utc_time = datetime.now(timezone.utc)
    local_time = datetime.now()

    draw.rounded_rectangle(
        [x + 20, y + 60, x + box_width - 140, y + 110],
        radius=10,
        fill=(15, 15, 20, 255)
    )
    draw.text((x + 25, y + 65), "SERVER TIME (UTC)", fill=(120, 180, 255), font=font_text)
    draw.text((x + 25, y + 85), format_time(utc_time), fill=(120, 255, 255), font=font_text)

    draw.rounded_rectangle(
        [x + 20, y + 120, x + box_width - 140, y + 170],
        radius=10,
        fill=(15, 15, 20, 255)
    )
    draw.text((x + 25, y + 125), "LOCAL PC TIME", fill=(200, 200, 200), font=font_text)
    draw.text((x + 25, y + 145), format_time(local_time), fill=(255, 200, 100), font=font_text)

    btn_x = x + box_width - 110

    draw.rounded_rectangle(
        [btn_x, y + 60, btn_x + 90, y + 95],
        radius=8,
        fill=(50, 120, 255)
    )
    draw.text((btn_x + 10, y + 68), "Sync Now", fill=(255, 255, 255), font=font_text)

    draw.rounded_rectangle(
        [btn_x, y + 105, btn_x + 90, y + 140],
        radius=8,
        fill=(60, 60, 70)
    )
    draw.text((btn_x + 8, y + 112), "Auto Sync", fill=(200, 200, 200), font=font_text)

    draw.rounded_rectangle(
        [btn_x, y + 150, btn_x + 90, y + 185],
        radius=8,
        fill=(60, 60, 70)
    )
    draw.text((btn_x + 12, y + 158), "Settings", fill=(200, 200, 200), font=font_text)

    draw.text((x + 25, y + box_height - 30), "● Synced Perfectly", fill=(100, 255, 120), font=font_text)

    result = Image.alpha_composite(img, overlay)
    result.convert("RGB").save(output_path)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()

    input_path = "input.jpg"
    output_path = "output.jpg"

    await file.download_to_drive(input_path)

    add_watermark(input_path, output_path)

    await update.message.reply_photo(photo=open(output_path, "rb"))

async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("Bot jalan...")
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
