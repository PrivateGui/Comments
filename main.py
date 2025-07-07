import requests
import time
import os
import re
import random
from urllib.parse import quote

# Telegram Bot Token (replace with your own from BotFather)
TELEGRAM_TOKEN = "889732515:Q588DCcltyOVu9rPIJXMKGu4SZjuI7sHbCEEKFlH"
TELEGRAM_API_URL = f"https://tapi.bale.ai/bot{TELEGRAM_TOKEN}"

# Google Translate API endpoint (public, no API key required)
GOOGLE_TRANSLATE_URL = "https://translate.google.com/translate_a/single"

# Offset for long polling
update_offset = None

def is_persian(text):
    """Detect if text contains Persian characters (Unicode range U+0600 to U+06FF)."""
    return bool(re.search(r'[\u0600-\u06FF]', text))

def translate_to_english(text):
    """Translate Persian text to English using Google Translate API."""
    try:
        params = {
            "client": "gtx",
            "sl": "fa",  # Source language: Persian
            "tl": "en",  # Target language: English
            "dt": "t",
            "q": text,
        }
        response = requests.get(GOOGLE_TRANSLATE_URL, params=params)
        if response.status_code == 200:
            # Parse the nested response structure
            data = response.json()
            translated_text = data[0][0][0]  # Extract translated text
            return True, translated_text
        else:
            return False, "خطای API ترجمه"
    except Exception as e:
        return False, f"خطا در ترجمه: {str(e)}"

def send_message(chat_id, text, reply_to_message_id=None):
    """Send a message to the user."""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
    response = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
    return response.json()

def send_typing(chat_id):
    """Send 'typing' action to indicate bot is working."""
    requests.post(f"{TELEGRAM_API_URL}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})

def edit_message(chat_id, message_id, text):
    """Edit an existing message."""
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    response = requests.post(f"{TELEGRAM_API_URL}/editMessageText", json=payload)
    return response.json()

def delete_message(chat_id, message_id):
    """Delete a message."""
    payload = {"chat_id": chat_id, "message_id": message_id}
    response = requests.post(f"{TELEGRAM_API_URL}/deleteMessage", json=payload)
    return response.json()

def send_photo(chat_id, photo_path, caption=None, reply_to_message_id=None):
    """Send a photo to the user."""
    with open(photo_path, "rb") as photo:
        payload = {"chat_id": chat_id}
        if caption:
            payload["caption"] = caption
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        response = requests.post(f"{TELEGRAM_API_URL}/sendPhoto", data=payload, files={"photo": photo})
    return response.json()

def generate_image(prompt, output_path="/tmp/image.webp"):
    """Generate an image using Pollinations AI API."""
    try:
        r_seed = random.randint(1, 1000000000000)
        url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width=1024&height=1024&seed={r_seed}&model=flux&nologo=true&private=false&enhance=false&safe=false"
        response = requests.get(url)
        if response.status_code == 200:
            with open(output_path, 'wb') as file:
                file.write(response.content)
            return True, output_path
        else:
            return False, f"خطای API Pollinations AI: {response.status_code}"
    except Exception as e:
        return False, f"خطا در تولید تصویر: {str(e)}"

def handle_message(update):
    """Process incoming messages and respond accordingly."""
    message = update.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")
    text = message.get("text", "").strip()
    user = message.get("from", {}).get("first_name", "کاربر")

    if not chat_id or not text:
        return

    # Send typing indicator
    send_typing(chat_id)

    # Handle commands
    if text.startswith("/start"):
        send_message(
            chat_id,
            f"خوش آمدید، {user}!",
            reply_to_message_id=message_id,
        )
        return

    if text.startswith("/help"):
        send_message(
            chat_id,
            "این یک راهنما است.",
            reply_to_message_id=message_id,
        )
        return

    # Check if the prompt is in Persian
    prompt = text
    is_persian_prompt = is_persian(text)
    if is_persian_prompt:
        success, translated_prompt = translate_to_english(text)
        if success:
            prompt = translated_prompt
            send_message(
                chat_id,
                f"🌍 **ترجمه درخواست**: {text} → {prompt}",
                reply_to_message_id=message_id,
            )
        else:
            send_message(
                chat_id,
                f"❌ **خطا در ترجمه درخواست**: {translated_prompt}\nلطفاً دوباره امتحان کنید یا از `/help` استفاده کنید.",
                reply_to_message_id=message_id,
            )
            return

    # Send initial response and store message ID for editing
    response = send_message(
        chat_id,
        f"🎨 **در حال تولید تصویر برای '{text}'...** لطفاً کمی صبر کنید!",
        reply_to_message_id=message_id,
    )
    response_message_id = response.get("result", {}).get("message_id")

    # Generate the image
    output_path = f"image_{chat_id}_{message_id}.webp"
    success, result = generate_image(prompt, output_path)

    if success:
        # Edit message to indicate completion
        edit_message(
            chat_id,
            response_message_id,
            f"✅ **تصویر برای '{text}' تولید شد!** در حال ارسال...",
        )
        # Send the image
        send_photo(
            chat_id,
            output_path,
            caption=f"🖼️ **تصویر تولید شده**: {text}",
            reply_to_message_id=message_id,
        )
        # Delete the "Image uploaded" message after 2 seconds
        time.sleep(2)
        delete_message(chat_id, response_message_id)
        # Clean up the file
        try:
            os.remove(output_path)
        except:
            pass
    else:
        # Edit message to show error
        edit_message(
            chat_id,
            response_message_id,
            f"❌ **خطا در تولید تصویر برای '{text}'**.\nعلت: {result}\nلطفاً دوباره امتحان کنید یا از `/help` استفاده کنید.",
        )

def main():
    """Run the bot with long polling."""
    global update_offset
    print("Bot is running...")

    while True:
        try:
            # Fetch updates
            params = {"timeout": 60, "allowed_updates": ["message"]}
            if update_offset:
                params["offset"] = update_offset
            response = requests.get(f"{TELEGRAM_API_URL}/getUpdates", params=params)
            data = response.json()

            if not data.get("ok"):
                print(f"Error fetching updates: {data}")
                time.sleep(5)
                continue

            updates = data.get("result", [])
            for update in updates:
                update_offset = update["update_id"] + 1
                handle_message(update)

        except KeyboardInterrupt:
            print("Bot stopped by user.")
            break
        except Exception as e:
            print(f"Error in polling loop: {e}")
            time.sleep(5)  # Wait before retrying to avoid spamming

if __name__ == "__main__":
    main()
