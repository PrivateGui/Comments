import random
import requests
from PIL import Image
from io import BytesIO
import os
import time

# Telegram bot token (replace with your bot token)
BOT_TOKEN = "889732515:Q588DCcltyOVu9rPIJXMKGu4SZjuI7sHbCEEKFlH"

# Watermark image URL
WATERMARK_URL = "https://s6.uupload.ir/files/watermark_z744.png"  # Replace with your direct watermark image link

# Telegram API base URL
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

# Ensure /tmp directory exists
TMP_DIR = "/tmp/"
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

def get_updates(offset=None):
    """Fetch updates from Telegram using long polling"""
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 100, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=120)
        response.raise_for_status()
        return response.json().get("result", [])
    except requests.RequestException as e:
        print(f"Error fetching updates: {e}")
        return []

def send_photo(chat_id, photo_path):
    """Send photo to the user"""
    url = f"{BASE_URL}/sendPhoto"
    with open(photo_path, "rb") as photo:
        files = {"photo": photo}
        data = {"chat_id": chat_id}
        try:
            response = requests.post(url, data=data, files=files)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error sending photo: {e}")
            return None

def send_message(chat_id, text):
    """Send text message to the user"""
    url = f"{BASE_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error sending message: {e}")
        return None

def add_watermark(image_url, watermark_url):
    """Download image, add watermark, and save to /tmp"""
    try:
        # Download the generated image
        response = requests.get(image_url)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGBA")

        # Download the watermark
        watermark_response = requests.get(watermark_url)
        watermark_response.raise_for_status()
        watermark = Image.open(BytesIO(watermark_response.content)).convert("RGBA")

        # Resize watermark to 1/4 of image width
        watermark_width = image.width // 4
        watermark_height = int(watermark.height * (watermark_width / watermark.width))
        watermark = watermark.resize((watermark_width, watermark_height), Image.Resampling.LANCZOS)

        # Position watermark (bottom-right with padding)
        padding = 20
        position = (image.width - watermark_width - padding, image.height - watermark_height - padding)

        # Create new image and overlay watermark
        result = Image.new("RGBA", image.size)
        result.paste(image, (0, 0))
        result.paste(watermark, position, watermark)

        # Save to /tmp with unique filename
        timestamp = int(time.time() * 1000)  # Milliseconds for uniqueness
        output_path = os.path.join(TMP_DIR, f"watermarked_image_{timestamp}.jpg")
        result = result.convert("RGB")
        result.save(output_path, "JPEG", quality=95)
        return output_path
    except Exception as e:
        print(f"Error processing image: {e}")
        return None

def main():
    offset = None
    print("Bot is running...")
    while True:
        updates = get_updates(offset)
        for update in updates:
            if "message" not in update:
                continue

            message = update["message"]
            chat_id = message["chat"]["id"]
            if "text" not in message:
                continue

            text = message["text"]
            if text.startswith("/gen"):
                # Extract prompt
                prompt = text[4:].strip()
                if not prompt:
                    send_message(chat_id, "Please provide a prompt. Usage: /gen <prompt>")
                    continue

                # Generate image URL
                r_seed = random.randint(1, 1000000000000)
                image_url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&seed={r_seed}&model=flux&nologo=true&private=false&enhance=false&safe=false"
                # Add watermark
                output_path = add_watermark(image_url, WATERMARK_URL)
                if output_path:
                    send_photo(chat_id, output_path)
                else:
                    send_message(chat_id, "Failed to generate or process the image.")

            offset = update["update_id"] + 1

if __name__ == "__main__":
    main()
