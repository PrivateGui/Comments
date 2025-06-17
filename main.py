import requests
import json
import random
import string
import os
import mysql.connector
from urllib.parse import quote
from datetime import datetime

# Telegram Bot Token (replace with your bot token)
TOKEN = "812616487:PcCYPrqiWmEmfVpPWaWWzxNtvIhjoOSNrK7yFLAX"
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}/"

# MySQL Database Configuration
DB_CONFIG = {
    'host': 'cests',
    'user': 'root',
    'password': 'flTurEdlcHlTcvZ9xYVsGdBY',
    'database': 'gallant_yonath'
}

# Admin IDs (replace with actual admin Telegram IDs)
ADMIN_IDS = [844843541]  # Example admin ID

# Temporary directory for file storage
TMP_DIR = "/tmp/telegram_bot_files"
if not os.path.exists(TMP_DIR):
    os.makedirs(TMP_DIR)

# Connect to MySQL database
def init_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INT AUTO_INCREMENT PRIMARY KEY,
            upload_type VARCHAR(10),
            file_path TEXT,
            content TEXT,
            random_string VARCHAR(20) UNIQUE,
            view_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            upload_id INT,
            user_id BIGINT,
            PRIMARY KEY (upload_id, user_id),
            FOREIGN KEY (upload_id) REFERENCES uploads(id)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

# Generate random string for /start links
def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Save file to /tmp
def save_file(file_id, file_name):
    file_info = requests.get(f"{BASE_URL}getFile?file_id={file_id}").json()
    if file_info["ok"]:
        file_path = file_info["result"]["file_path"]
        file_url = f"https://tapi.bale.ai/file/bot{TOKEN}/{file_path}"
        response = requests.get(file_url)
        save_path = os.path.join(TMP_DIR, file_name)
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return save_path
    return None

# Send message with requests
def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup
    }
    requests.post(f"{BASE_URL}sendMessage", json=payload)

# Send file with requests
def send_file(chat_id, file_path, caption="", reply_markup=None):
    with open(file_path, 'rb') as f:
        files = {'document': f}
        payload = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        requests.post(f"{BASE_URL}sendDocument", data=payload, files=files)

# Get inline keyboard for views and likes
def get_inline_keyboard(upload_id, view_count, user_id):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM likes WHERE upload_id = %s AND user_id = %s", (upload_id, user_id))
    has_liked = cursor.fetchone()[0] > 0
    cursor.close()
    conn.close()
    
    like_text = "👍 لایک کرده‌اید" if has_liked else "👍 لایک"
    return {
        "inline_keyboard": [
            [
                {"text": like_text, "callback_data": f"like_{upload_id}"},
                {"text": f"👀 بازدید: {view_count}", "callback_data": f"view_{upload_id}"}
            ]
        ]
    }

# Get reply keyboard for admins
def get_admin_keyboard():
    return {
        "keyboard": [
            [{"text": "📤 آپلود فایل"}],
            [{"text": "📝 آپلود متن"}],
            [{"text": "📢 ارسال پیام همگانی"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }

# Handle updates
def handle_update(update):
    if "message" not in update:
        return

    message = update["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    is_admin = user_id in ADMIN_IDS

    # Handle commands
    if "text" in message and message["text"].startswith("/start"):
        random_string = message["text"].replace("/start ", "").strip() if message["text"] != "/start" else None
        if random_string:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT id, upload_type, file_path, content, view_count FROM uploads WHERE random_string = %s", (random_string,))
            upload = cursor.fetchone()
            if upload:
                upload_id, upload_type, file_path, content, view_count = upload
                # Increment view count
                cursor.execute("UPDATE uploads SET view_count = view_count + 1 WHERE id = %s", (upload_id,))
                conn.commit()
                
                reply_markup = get_inline_keyboard(upload_id, view_count + 1, user_id)
                if upload_type == "file" and os.path.exists(file_path):
                    send_file(chat_id, file_path, caption="📎 فایل دریافت شده:", reply_markup=reply_markup)
                elif upload_type == "text":
                    send_message(chat_id, content, reply_markup=reply_markup)
            else:
                send_message(chat_id, "❌ لینک نامعتبر است.")
            cursor.close()
            conn.close()
        else:
            if is_admin:
                send_message(chat_id, "👋 سلام ادمین! از کیبورد زیر برای مدیریت استفاده کنید:", get_admin_keyboard())
            else:
                send_message(chat_id, "👋 سلام! خوش آمدید به ربات آپلودر.")
        return

    # Admin-specific handling
    if is_admin:
        if "text" in message:
            text = message["text"]
            if text == "📤 آپلود فایل":
                send_message(chat_id, "📎 لطفاً فایل خود را ارسال کنید:")
            elif text == "📝 آپلود متن":
                send_message(chat_id, "📝 لطفاً متن خود را ارسال کنید:")
            elif text == "📢 ارسال پیام همگانی":
                send_message(chat_id, "📢 پیام خود را برای پخش همگانی ارسال کنید:")
            elif not text.startswith("/"):
                # Handle text uploads or broadcasts
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                cursor.execute("SELECT message_id FROM uploads WHERE upload_type = 'awaiting'")
                if cursor.fetchone():
                    random_string = generate_random_string()
                    cursor.execute("""
                        UPDATE uploads SET upload_type = 'text', content = %s, random_string = %s
                        WHERE upload_type = 'awaiting'
                    """, (text, random_string))
                    conn.commit()
                    start_link = f"/start {random_string}"
                    send_message(chat_id, f"✅ متن ذخیره شد!\nلینک: <code>{start_link}</code>")
                    cursor.execute("DELETE FROM uploads WHERE upload_type = 'awaiting'")
                else:
                    # Assume broadcast
                    cursor.execute("SELECT DISTINCT chat_id FROM uploads")
                    users = cursor.fetchall()
                    for user in users:
                        send_message(user[0], text)
                    send_message(chat_id, "✅ پیام همگانی ارسال شد!")
                cursor.close()
                conn.close()

        elif "document" in message or "photo" in message:
            # Handle file uploads
            file_id = message.get("document", {}).get("file_id") or message.get("photo", [{}])[-1].get("file_id")
            file_name = message.get("document", {}).get("file_name", f"file_{datetime.now().timestamp()}.dat")
            file_path = save_file(file_id, file_name)
            if file_path:
                conn = mysql.connector.connect(**DB_CONFIG)
                cursor = conn.cursor()
                random_string = generate_random_string()
                cursor.execute("""
                    INSERT INTO uploads (upload_type, file_path, random_string)
                    VALUES (%s, %s, %s)
                """, ("file", file_path, random_string))
                conn.commit()
                start_link = f"/start {random_string}"
                send_message(chat_id, f"✅ فایل ذخیره شد!\nلینک: <code>{start_link}</code>")
                cursor.close()
                conn.close()
            else:
                send_message(chat_id, "❌ خطا در ذخیره فایل!")

    # Handle callback queries (likes)
    if "callback_query" in update:
        callback = update["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        user_id = callback["from"]["id"]
        data = callback["data"]
        upload_id = int(data.split("_")[1])

        if data.startswith("like_"):
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM likes WHERE upload_id = %s AND user_id = %s", (upload_id, user_id))
            if cursor.fetchone()[0] == 0:
                cursor.execute("INSERT INTO likes (upload_id, user_id) VALUES (%s, %s)", (upload_id, user_id))
                conn.commit()
                cursor.execute("SELECT view_count FROM uploads WHERE id = %s", (upload_id,))
                view_count = cursor.fetchone()[0]
                reply_markup = get_inline_keyboard(upload_id, view_count, user_id)
                requests.post(f"{BASE_URL}editMessageReplyMarkup", json={
                    "chat_id": chat_id,
                    "message_id": callback["message"]["message_id"],
                    "reply_markup": reply_markup
                })
            cursor.close()
            conn.close()

# Main long polling loop
def main():
    init_db()
    offset = None
    while True:
        try:
            params = {"timeout": 60, "offset": offset}
            response = requests.get(f"{BASE_URL}getUpdates", params=params)
            data = response.json()
            if data["ok"]:
                for update in data["result"]:
                    handle_update(update)
                    offset = update["update_id"] + 1
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
