import requests
import sqlite3
import os
import random
import string
import json
from datetime import datetime
import tempfile

# Bot configuration
BOT_TOKEN = "812616487:PcCYPrqiWmEmfVpPWaWWzxNtvIhjoOSNrK7yFLAX"  # Replace with your Telegram bot token
API_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"
TMP_DIR = "/tmp/telegram_bot_files"
DB_PATH = "/tmp/telegram_bot.db"

# Ensure tmp directory exists
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_path TEXT,
        content_type TEXT,
        random_string TEXT UNIQUE,
        view_count INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS texts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text_content TEXT,
        random_string TEXT UNIQUE,
        view_count INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS likes (
        random_string TEXT,
        user_id INTEGER,
        UNIQUE(random_string, user_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY
    )''')
    conn.commit()
    conn.close()

init_db()

# Admin user IDs (replace with actual admin user IDs)
ADMINS = {844843541}  # Add your admin user IDs here

# Generate random string for start links
def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Send message with requests
def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{API_URL}sendMessage", json=payload)

# Send file with requests
def send_file(chat_id, file_path, content_type, caption=None, reply_markup=None):
    if content_type == "photo":
        with open(file_path, "rb") as file:
            files = {"photo": file}
            payload = {"chat_id": chat_id, "caption": caption or "", "parse_mode": "Markdown"}
            if reply_markup:
                payload["reply_markup"] = json.dumps(reply_markup)
            requests.post(f"{API_URL}sendPhoto", data=payload, files=files)
    elif content_type == "video":
        with open(file_path, "rb") as file:
            files = {"video": file}
            payload = {"chat_id": chat_id, "caption": caption or "", "parse_mode": "Markdown"}
            if reply_markup:
                payload["reply_markup"] = json.dumps(reply_markup)
            requests.post(f"{API_URL}sendVideo", data=payload, files=files)
    elif content_type == "document":
        with open(file_path, "rb") as file:
            files = {"document": file}
            payload = {"chat_id": chat_id, "caption": caption or "", "parse_mode": "Markdown"}
            if reply_markup:
                payload["reply_markup"] = json.dumps(reply_markup)
            requests.post(f"{API_URL}sendDocument", data=payload, files=files)

# Download file from Telegram
def download_file(file_id):
    response = requests.get(f"{API_URL}getFile", params={"file_id": file_id})
    file_info = response.json()["result"]
    file_path = file_info["file_path"]
    file_url = f"https://tapi.bale.ai/file/bot{BOT_TOKEN}/{file_path}"
    file_response = requests.get(file_url)
    temp_file = os.path.join(TMP_DIR, f"{file_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    with open(temp_file, "wb") as f:
        f.write(file_response.content)
    return temp_file

# Check if user is admin
def is_admin(user_id):
    return user_id in ADMINS

# Add admin to database
def add_admin(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# Get admin reply keyboard
def get_admin_keyboard():
    return {
        "keyboard": [
            [{"text": "📤 آپلود فایل"}],
            [{"text": "📝 آپلود متن"}],
            [{"text": "📢 ارسال پیام همگانی"}]
        ],
        "resize_keyboard": True
    }

# Get inline keyboard for view count and like
def get_inline_keyboard(random_string, view_count):
    return {
        "inline_keyboard": [
            [{"text": f"👀 تعداد بازدید: {view_count}", "callback_data": f"view_{random_string}"}],
            [{"text": "👍 لایک", "callback_data": f"like_{random_string}"}]
        ]
    }

# Save file to database
def save_file(file_path, content_type, random_string):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO files (file_path, content_type, random_string) VALUES (?, ?, ?)",
              (file_path, content_type, random_string))
    conn.commit()
    conn.close()

# Save text to database
def save_text(text_content, random_string):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO texts (text_content, random_string) VALUES (?, ?)",
              (text_content, random_string))
    conn.commit()
    conn.close()

# Increment view count
def increment_view_count(random_string, table):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"UPDATE {table} SET view_count = view_count + 1 WHERE random_string = ?", (random_string,))
    conn.commit()
    conn.close()

# Get file info
def get_file_info(random_string):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT file_path, content_type, view_count FROM files WHERE random_string = ?", (random_string,))
    result = c.fetchone()
    conn.close()
    return result

# Get text info
def get_text_info(random_string):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT text_content, view_count FROM texts WHERE random_string = ?", (random_string,))
    result = c.fetchone()
    conn.close()
    return result

# Check if user has liked
def has_liked(user_id, random_string):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM likes WHERE user_id = ? AND random_string = ?", (user_id, random_string))
    result = c.fetchone()
    conn.close()
    return bool(result)

# Add like
def add_like(user_id, random_string):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO likes (user_id, random_string) VALUES (?, ?)", (user_id, random_string))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # User already liked
    conn.close()

# Get all chat IDs (for broadcasting)
def get_all_chat_ids():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id FROM likes")  # Assuming likes table tracks users
    chat_ids = [row[0] for row in c.fetchall()]
    conn.close()
    return chat_ids

# Main bot logic
def handle_update(update):
    if "message" in update:
        message = update["message"]
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        text = message.get("text", "")

        # Check if user is admin
        if is_admin(user_id):
            # Show admin keyboard
            if text == "/start":
                send_message(chat_id, "👋 خوش آمدید، مدیر گرامی! لطفاً از منو انتخاب کنید:", get_admin_keyboard())
            elif text == "📤 آپلود فایل":
                send_message(chat_id, "📎 لطفاً فایل خود (عکس، ویدیو یا سند) را ارسال کنید:")
            elif text == "📝 آپلود متن":
                send_message(chat_id, "📜 لطفاً متن خود را ارسال کنید:")
            elif text == "📢 ارسال پیام همگانی":
                send_message(chat_id, "📣 پیام خود را برای ارسال همگانی وارد کنید:")
            elif "photo" in message:
                file_id = message["photo"][-1]["file_id"]
                file_path = download_file(file_id)
                random_string = generate_random_string()
                save_file(file_path, "photo", random_string)
                send_message(chat_id, f"✅ فایل آپلود شد!\nلینک: `/start {random_string}`")
            elif "video" in message:
                file_id = message["video"]["file_id"]
                file_path = download_file(file_id)
                random_string = generate_random_string()
                save_file(file_path, "video", random_string)
                send_message(chat_id, f"✅ فایل آپلود شد!\nلینک: `/start {random_string}`")
            elif "document" in message:
                file_id = message["document"]["file_id"]
                file_path = download_file(file_id)
                random_string = generate_random_string()
                save_file(file_path, "document", random_string)
                send_message(chat_id, f"✅ فایل آپلود شد!\nلینک: `/start {random_string}`")
            elif text and not text.startswith("/"):
                # Handle text upload or broadcast
                if update["message"]["reply_to_message"] and update["message"]["reply_to_message"]["text"] == "📜 لطفاً متن خود را ارسال کنید:":
                    random_string = generate_random_string()
                    save_text(text, random_string)
                    send_message(chat_id, f"✅ متن ذخیره شد!\nلینک: `/start {random_string}`")
                elif update["message"]["reply_to_message"] and update["message"]["reply_to_message"]["text"] == "📣 پیام خود را برای ارسال همگانی وارد کنید:":
                    chat_ids = get_all_chat_ids()
                    for cid in chat_ids:
                        send_message(cid, text)
                    send_message(chat_id, "✅ پیام همگانی ارسال شد!")
                else:
                    send_message(chat_id, "❓ لطفاً از منو انتخاب کنید:", get_admin_keyboard())
        else:
            # Non-admin user
            if text.startswith("/start"):
                if text == "/start":
                    send_message(chat_id, "👋 سلام! به ربات خوش آمدید!")
                else:
                    random_string = text.split(" ")[1] if len(text.split(" ")) > 1 else None
                    if random_string:
                        # Check if it's a file
                        file_info = get_file_info(random_string)
                        if file_info:
                            file_path, content_type, view_count = file_info
                            increment_view_count(random_string, "files")
                            view_count += 1
                            send_file(chat_id, file_path, content_type, caption=f"📄 فایل دریافت شد!", reply_markup=get_inline_keyboard(random_string, view_count))
                        # Check if it's a text
                        text_info = get_text_info(random_string)
                        if text_info:
                            text_content, view_count = text_info
                            increment_view_count(random_string, "texts")
                            view_count += 1
                            send_message(chat_id, f"📜 {text_content}", get_inline_keyboard(random_string, view_count))
                        else:
                            send_message(chat_id, "❌ لینک نامعتبر است!")
            else:
                send_message(chat_id, "👋 سلام! لطفاً از دستور /start استفاده کنید.")

    elif "callback_query" in update:
        callback = update["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        user_id = callback["from"]["id"]
        data = callback["data"]
        random_string = data.split("_")[1]

        if data.startswith("like_"):
            if not has_liked(user_id, random_string):
                add_like(user_id, random_string)
                send_message(chat_id, "👍 لایک شما ثبت شد!")
            else:
                send_message(chat_id, "⚠️ شما قبلاً این پست را لایک کرده‌اید!")
        elif data.startswith("view_"):
            file_info = get_file_info(random_string)
            if file_info:
                _, _, view_count = file_info
                send_message(chat_id, f"👀 تعداد بازدید: {view_count}")
            text_info = get_text_info(random_string)
            if text_info:
                _, view_count = text_info
                send_message(chat_id, f"👀 تعداد بازدید: {view_count}")

# Long polling
def poll_updates():
    offset = None
    while True:
        try:
            params = {"timeout": 60, "offset": offset}
            response = requests.get(f"{API_URL}getUpdates", params=params, timeout=65)
            updates = response.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                handle_update(update)
        except requests.RequestException as e:
            print(f"Error: {e}")
            continue

if __name__ == "__main__":
    print("Bot started...")
    poll_updates()
