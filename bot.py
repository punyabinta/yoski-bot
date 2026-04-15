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

    box_width = int(width * 0.5)
    box_height = int(height * 0.3)

    x = width - box_width - 20
    y = height - box_height - 20

    draw.rectangle([x, y, x + box_width, y + box_height], fill=(30, 30, 30, 200))

    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()

    utc_time = datetime.now(timezone.utc)
    local_time = datetime.now()

    draw.text((x+10, y+10), "Yoski Time", fill=(200,200,255), font=font)
    draw.text((x+10, y+40), "Server: " + format_time(utc_time), fill=(255,255,255), font=font)
    draw.text((x+10, y+70), "Local: " + format_time(local_time), fill=(255,255,255), font=font)
    draw.text((x+10, y+100), "Synced Perfectly", fill=(150,255,150), font=font)

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
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
