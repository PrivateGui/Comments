import requests
import sqlite3
import os
import random
import string
import time
from datetime import datetime

# Telegram Bot Token
TOKEN = "812616487:PcCYPrqiWmEmfVpPWaWWzxNtvIhjoOSNrK7yFLAX"  # Replace with your bot token
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}/"

# Admin user IDs (replace with actual admin Telegram IDs)
ADMINS = {844843541}  # Set of admin user IDs

# Database setup
DB_PATH = "/tmp/bot_database.db"
FILES_DIR = "/tmp/bot_files"
os.makedirs(FILES_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS uploads
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  type TEXT,
                  content TEXT,
                  file_path TEXT,
                  link_key TEXT UNIQUE,
                  view_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  message TEXT,
                  timestamp TEXT)''')
    conn.commit()
    conn.close()

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def save_file(file_url, file_id):
    file_path = f"{FILES_DIR}/{file_id}"
    response = requests.get(file_url)
    with open(file_path, 'wb') as f:
        f.write(response.content)
    return file_path

def get_file_url(file_id):
    response = requests.get(f"{BASE_URL}getFile", params={"file_id": file_id})
    file_info = response.json()
    if file_info["ok"]:
        file_path = file_info["result"]["file_path"]
        return f"https://tapi.bale.ai/file/bot{TOKEN}/{file_path}"
    return None

def save_upload(type, content, file_path, link_key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO uploads (type, content, file_path, link_key, view_count) VALUES (?, ?, ?, ?, ?)",
              (type, content, file_path, link_key, 0))
    conn.commit()
    conn.close()

def get_upload(link_key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT type, content, file_path, view_count FROM uploads WHERE link_key = ?", (link_key,))
    result = c.fetchone()
    conn.close()
    return result

def increment_view_count(link_key):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE uploads SET view_count = view_count + 1 WHERE link_key = ?", (link_key,))
    conn.commit()
    conn.close()

def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{BASE_URL}sendMessage", json=payload)

def send_file(chat_id, file_path, caption, reply_markup=None):
    with open(file_path, 'rb') as f:
        files = {"document": f}
        payload = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        requests.post(f"{BASE_URL}sendDocument", data=payload, files=files)

def broadcast_message(text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id FROM messages")
    users = c.fetchall()
    conn.close()
    for user in users:
        send_message(user[0], text)

def handle_update(update):
    if "message" not in update:
        return

    message = update["message"]
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]

    # Log user message
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO messages (user_id, message, timestamp) VALUES (?, ?, ?)",
              (user_id, str(message), datetime.now().isoformat()))
    conn.commit()
    conn.close()

    # Handle /start command
    if "text" in message and message["text"].startswith("/start"):
        link_key = message["text"].split()[-1] if len(message["text"].split()) > 1 else None
        if link_key:
            upload = get_upload(link_key)
            if upload:
                type, content, file_path, view_count = upload
                increment_view_count(link_key)
                reply_markup = {
                    "inline_keyboard": [[{"text": "Like", "callback_data": f"like_{link_key}"}]]
                }
                if type == "text":
                    send_message(chat_id, f"{content}\n\nViews: {view_count + 1}", reply_markup)
                else:
                    send_file(chat_id, file_path, f"Views: {view_count + 1}", reply_markup)
            else:
                send_message(chat_id, "Invalid or expired link.")
        else:
            send_message(chat_id, "Welcome! Send a file or text (if admin) or use a /start <code> link.")
        return

    # Admin commands
    if user_id in ADMINS:
        # Handle broadcast command
        if "text" in message and message["text"].startswith("/broadcast"):
            broadcast_text = message["text"][10:].strip()
            if broadcast_text:
                broadcast_message(broadcast_text)
                send_message(chat_id, "Broadcast sent!")
            else:
                send_message(chat_id, "Please provide a message to broadcast.")
            return

        # Handle file upload
        if "document" in message or "photo" in message or "video" in message:
            file_id = None
            if "document" in message:
                file_id = message["document"]["file_id"]
            elif "photo" in message:
                file_id = message["photo"][-1]["file_id"]
            elif "video" in message:
                file_id = message["video"]["file_id"]

            file_url = get_file_url(file_id)
            if file_url:
                file_path = save_file(file_url, file_id)
                link_key = generate_random_string()
                save_upload("file", "", file_path, link_key)
                send_message(chat_id, f"File uploaded! Share this link: /start {link_key}")
            else:
                send_message(chat_id, "Failed to upload file.")
            return

        # Handle text upload
        if "text" in message:
            text = message["text"]
            link_key = generate_random_string()
            save_upload("text", text, "", link_key)
            send_message(chat_id, f"Text uploaded! Share this link: /start {link_key}")
            return

    # Non-admin users
    send_message(chat_id, "Please use a /start <code> link to view content.")

def main():
    init_db()
    offset = None
    while True:
        try:
            params = {"timeout": 30, "offset": offset}
            response = requests.get(f"{BASE_URL}getUpdates", params=params, timeout=35)
            data = response.json()
            if not data["ok"]:
                continue
            for update in data["result"]:
                handle_update(update)
                offset = update["update_id"] + 1
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(0.3)  # Brief pause to prevent tight loop on errors

if __name__ == "__main__":
    main()
