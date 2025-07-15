import random
import requests
from PIL import Image
from io import BytesIO
import os
import time

# Your Bale bot token
BOT_TOKEN = "889732515:Q588DCcltyOVu9rPIJXMKGu4SZjuI7sHbCEEKFlH"

# Watermark image URL
WATERMARK_URL = "https://s6.uupload.ir/files/watermark_z744.png"

# Bale API base URL
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

# Temp directory for images
TMP_DIR = "/tmp/"
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

def get_updates(offset=None):
    """Fetch updates using long polling"""
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 100, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=120)
        response.raise_for_status()
        return response.json().get("result", [])
    except requests.RequestException as e:
        print(f"[ERROR] Fetching updates: {e}")
        return []

def send_photo(chat_id, photo_path):
    """Send photo to user"""
    url = f"{BASE_URL}/sendPhoto"
    with open(photo_path, "rb") as photo:
        files = {"photo": photo}
        data = {"chat_id": chat_id}
        try:
            response = requests.post(url, data=data, files=files)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"[ERROR] Sending photo: {e}")
            return None

def send_message(chat_id, text):
    """Send text message to user"""
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"[ERROR] Sending message: {e}")
        return None

def add_watermark(image_url, watermark_url):
    """Download image, add watermark, and save"""
    try:
        # Download main image
        response = requests.get(image_url)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGBA")

        # Download watermark
        wm_response = requests.get(watermark_url)
        wm_response.raise_for_status()
        watermark = Image.open(BytesIO(wm_response.content)).convert("RGBA")

        # Resize watermark
        wm_width = image.width // 4
        wm_height = int(watermark.height * (wm_width / watermark.width))
        watermark = watermark.resize((wm_width, wm_height), Image.Resampling.LANCZOS)

        # Position watermark (bottom-right)
        padding = 20
        position = (image.width - wm_width - padding, image.height - wm_height - padding)

        # Combine image + watermark
        result = Image.new("RGBA", image.size)
        result.paste(image, (0, 0))
        result.paste(watermark, position, watermark)

        # Save to /tmp with unique name
        filename = f"watermarked_{int(time.time() * 1000)}.jpg"
        path = os.path.join(TMP_DIR, filename)
        result.convert("RGB").save(path, "JPEG", quality=95)
        return path
    except Exception as e:
        print(f"[ERROR] Processing image: {e}")
        return None

def cleanup_old_files():
    """Remove old files from /tmp (older than 10 mins)"""
    now = time.time()
    for file in os.listdir(TMP_DIR):
        path = os.path.join(TMP_DIR, file)
        if os.path.isfile(path) and (now - os.path.getmtime(path)) > 600:
            os.remove(path)
            print(f"[INFO] Deleted old file: {file}")

def main():
    offset = None
    print("[INFO] Bot is running...")
    while True:
        updates = get_updates(offset)
        for update in updates:
            if "message" not in update:
                continue

            message = update["message"]
            chat_id = message["chat"]["id"]
            if "text" not in message:
                continue

            text = message["text"].strip()

            if text == "/start":
                send_message(chat_id, "سلام! 👋 برای ساخت تصویر از دستور زیر استفاده کنید:\n/gen <متن>")
            
            elif text.startswith("/gen"):
                prompt = text[4:].strip()
                if not prompt:
                    send_message(chat_id, "لطفاً متن بعد از /gen وارد کنید. مثال:\n/gen گربه روی صندلی")
                else:
                    send_message(chat_id, "در حال ساخت تصویر... ⏳")
                    r_seed = random.randint(1, 10**12)
                    image_url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&seed={r_seed}&model=flux&nologo=true"
                    
                    output_path = add_watermark(image_url, WATERMARK_URL)
                    if output_path:
                        send_photo(chat_id, output_path)
                    else:
                        send_message(chat_id, "❌ مشکلی در ساخت تصویر پیش آمد. دوباره تلاش کنید.")
            
            # Update offset after processing each update
            offset = update["update_id"] + 1
        
        cleanup_old_files()  # Delete old files every cycle
        time.sleep(1)  # Prevent API hammering

if __name__ == "__main__":
    main()
