import os
import json
import time
import random
import string
import sqlite3
import requests

TOKEN = "812616487:PcCYPrqiWmEmfVpPWaWWzxNtvIhjoOSNrK7yFLAX"
API = f"https://tapi.bale.ai/bot{TOKEN}"
FILE_API = f"https://tapi.bale.ai/file/bot{TOKEN}"
DB_PATH = "/tmp/uploader.db"
UPLOAD_DIR = "/tmp"
ADMINS = ["zonercm"]  # allowed usernames

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY,
    type TEXT,
    content TEXT,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS likes (
    upload_id TEXT,
    user_id INTEGER,
    PRIMARY KEY (upload_id, user_id)
)""")
conn.commit()


def gen_id(n=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


def is_admin(username):
    return username in ADMINS


def send(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{API}/sendMessage", data=payload)


def send_typing(chat_id):
    requests.post(f"{API}/sendChatAction", data={"chat_id": chat_id, "action": "typing"})


def send_file(chat_id, filepath, inline_markup=None):
    with open(filepath, "rb") as f:
        data = {"chat_id": chat_id}
        files = {"document": f}
        if inline_markup:
            data["reply_markup"] = json.dumps(inline_markup)
        requests.post(f"{API}/sendDocument", data=data, files=files)


def edit_inline_markup(chat_id, msg_id, markup):
    requests.post(f"{API}/editMessageReplyMarkup", data={
        "chat_id": chat_id,
        "message_id": msg_id,
        "reply_markup": json.dumps(markup)
    })


def get_file_path(file_id):
    res = requests.get(f"{API}/getFile?file_id={file_id}").json()
    return res["result"]["file_path"]


def save_file_from_url(file_url, filename):
    content = requests.get(file_url).content
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)
    return path


def save_upload(upload_type, content):
    upload_id = gen_id()
    cur.execute("INSERT INTO uploads (id, type, content) VALUES (?, ?, ?)", (upload_id, upload_type, content))
    conn.commit()
    return upload_id


def handle_like(user_id, upload_id):
    cur.execute("SELECT 1 FROM likes WHERE upload_id = ? AND user_id = ?", (upload_id, user_id))
    if cur.fetchone():
        return False
    cur.execute("INSERT INTO likes (upload_id, user_id) VALUES (?, ?)", (upload_id, user_id))
    cur.execute("UPDATE uploads SET likes = likes + 1 WHERE id = ?", (upload_id,))
    conn.commit()
    return True


def increment_view(upload_id):
    cur.execute("UPDATE uploads SET views = views + 1 WHERE id = ?", (upload_id,))
    conn.commit()


def get_upload(upload_id):
    cur.execute("SELECT * FROM uploads WHERE id = ?", (upload_id,))
    return cur.fetchone()


def get_updates(offset=None):
    params = {"timeout": 0}
    if offset:
        params["offset"] = offset
    res = requests.get(f"{API}/getUpdates", params=params)
    return res.json().get("result", [])


def main():
    offset = None
    print("ربات فعال شد ✅")

    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message")
            if not msg:
                continue

            chat_id = msg["chat"]["id"]
            user_id = msg["from"]["id"]
            username = msg["from"].get("username", "")
            text = msg.get("text", "")
            doc = msg.get("document")

            send_typing(chat_id)

            # handle /start <id>
            if text.startswith("/start "):
                upload_id = text.split(" ")[1]
                data = get_upload(upload_id)
                if not data:
                    send(chat_id, "⛔️ محتوایی یافت نشد.")
                    continue

                _id, typ, content, views, likes = data
                increment_view(_id)
                markup = {
                    "inline_keyboard": [[
                        {"text": f"👁 {views+1}", "callback_data": "noop"},
                        {"text": f"❤️ {likes}", "callback_data": f"like_{_id}"}
                    ]]
                }

                if typ == "text":
                    send(chat_id, f"<b>📝 متن:</b>\n{content}", reply_markup=markup)
                elif typ == "file":
                    send_file(chat_id, content, inline_markup=markup)
                continue

            # Like callback
            if "callback_query" in update:
                cq = update["callback_query"]
                data = cq["data"]
                msg_id = cq["message"]["message_id"]
                chat_id = cq["message"]["chat"]["id"]
                if data.startswith("like_"):
                    upload_id = data.split("_")[1]
                    if handle_like(cq["from"]["id"], upload_id):
                        up = get_upload(upload_id)
                        markup = {
                            "inline_keyboard": [[
                                {"text": f"👁 {up[3]}", "callback_data": "noop"},
                                {"text": f"❤️ {up[4]}", "callback_data": f"like_{upload_id}"}
                            ]]
                        }
                        edit_inline_markup(chat_id, msg_id, markup)
                continue

            # Admin Uploads
            if is_admin(username):
                if doc:
                    file_id = doc["file_id"]
                    filename = doc.get("file_name", gen_id() + ".bin")
                    path = get_file_path(file_id)
                    file_url = f"{FILE_API}/{path}"
                    saved = save_file_from_url(file_url, filename)
                    upload_id = save_upload("file", saved)
                    send(chat_id, f"✅ فایل ذخیره شد!\nلینک: <code>/start {upload_id}</code>")
                elif text and not text.startswith("/"):
                    upload_id = save_upload("text", text)
                    send(chat_id, f"✅ متن ذخیره شد!\nلینک: <code>/start {upload_id}</code>")
                elif text == "/broadcast":
                    send(chat_id, "لطفاً پیامی که می‌خواهید ارسال کنید را فوروارد یا ارسال کنید.")
                continue

            # Default
            send(chat_id, "👋 برای دریافت محتوا، لینک /start را ارسال کنید.")


if __name__ == "__main__":
    main()
