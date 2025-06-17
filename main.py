import requests
import random
import string
import os
import mysql.connector
from urllib.parse import quote_plus

# Bot token
TOKEN = "812616487:PcCYPrqiWmEmfVpPWaWWzxNtvIhjoOSNrK7yFLAX"
API_URL = f"https://tapi.bale.ai/bot{TOKEN}"

# Admin user IDs
ADMINS = {844843541}  # Fill with your Telegram user IDs

# MySQL database connection
db = mysql.connector.connect(
    host="cests",
    port=3306,
    user="root",
    password="flTurEdlcHlTcvZ9xYVsGdBY",
    database="gallant_yonath"
)
cursor = db.cursor(dictionary=True)

# Ensure tables exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS posts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_key VARCHAR(32) UNIQUE,
    kind ENUM('file', 'text') NOT NULL,
    file_id VARCHAR(255),
    text TEXT,
    views INT DEFAULT 0,
    likes INT DEFAULT 0
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS likes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    post_key VARCHAR(32),
    user_id BIGINT,
    UNIQUE KEY (post_key, user_id)
)
""")
db.commit()

def get_updates(offset=None):
    params = {'timeout': 60, 'offset': offset}
    resp = requests.get(API_URL + "/getUpdates", params=params)
    return resp.json()['result']

def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = reply_markup
    requests.post(API_URL + "/sendMessage", data=data)

def send_document(chat_id, file_id, reply_markup=None):
    data = {'chat_id': chat_id, 'document': file_id}
    if reply_markup:
        data['reply_markup'] = reply_markup
    requests.post(API_URL + "/sendDocument", data=data)

def send_text(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = reply_markup
    requests.post(API_URL + "/sendMessage", data=data)

def send_reply_keyboard(chat_id, buttons):
    keyboard = {"keyboard": [[{"text": btn} for btn in buttons]], "resize_keyboard": True}
    send_message(chat_id, "انتخاب کنید:", reply_markup=str(keyboard).replace("'", '"'))

def send_inline_keyboard(chat_id, text, post_key, views, likes, kind):
    inline = {
        "inline_keyboard": [
            [
                {"text": f"👁️ {views}", "callback_data": f"views_{post_key}"},
                {"text": f"❤️ {likes}", "callback_data": f"like_{post_key}"}
            ]
        ]
    }
    if kind == 'file':
        send_document(chat_id, get_file_id(post_key), reply_markup=str(inline).replace("'", '"'))
    else:
        send_text(chat_id, text, reply_markup=str(inline).replace("'", '"'))

def generate_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=12))

def is_admin(user_id):
    return user_id in ADMINS

def get_file_id(post_key):
    cursor.execute("SELECT file_id FROM posts WHERE post_key=%s", (post_key,))
    row = cursor.fetchone()
    return row["file_id"] if row else None

def get_post(post_key):
    cursor.execute("SELECT * FROM posts WHERE post_key=%s", (post_key,))
    return cursor.fetchone()

def increment_view(post_key):
    cursor.execute("UPDATE posts SET views=views+1 WHERE post_key=%s", (post_key,))
    db.commit()

def increment_like(post_key, user_id):
    try:
        cursor.execute("INSERT INTO likes (post_key, user_id) VALUES (%s, %s)", (post_key, user_id))
        cursor.execute("UPDATE posts SET likes=likes+1 WHERE post_key=%s", (post_key,))
        db.commit()
        return True
    except mysql.connector.Error:
        db.rollback()
        return False

def has_liked(post_key, user_id):
    cursor.execute("SELECT 1 FROM likes WHERE post_key=%s AND user_id=%s", (post_key, user_id))
    return cursor.fetchone() is not None

def handle_admin_command(chat_id, text, state):
    if text == "آپلود فایل 📁":
        send_message(chat_id, "لطفا فایل خود را ارسال کنید.")
        state['mode'] = 'awaiting_file'
    elif text == "آپلود متن 📝":
        send_message(chat_id, "لطفا متن خود را ارسال کنید.")
        state['mode'] = 'awaiting_text'
    elif text == "ارسال پیام همگانی 📢":
        send_message(chat_id, "لطفا پیام خود را وارد کنید.")
        state['mode'] = 'awaiting_broadcast'
    elif text == "لغو ❌":
        send_message(chat_id, "لغو شد.")
        state['mode'] = None

def handle_file_upload(chat_id, file_id):
    key = generate_key()
    cursor.execute("INSERT INTO posts (post_key, kind, file_id) VALUES (%s, 'file', %s)", (key, file_id))
    db.commit()
    link = f"https://t.me/{get_bot_username()}?start={key}"
    send_message(chat_id, f"✅ فایل بارگذاری شد!\n\n🔗 برای اشتراک‌گذاری:\n{link}")
    
def handle_text_upload(chat_id, text):
    key = generate_key()
    cursor.execute("INSERT INTO posts (post_key, kind, text) VALUES (%s, 'text', %s)", (key, text))
    db.commit()
    link = f"https://t.me/{get_bot_username()}?start={key}"
    send_message(chat_id, f"✅ متن ذخیره شد!\n\n🔗 برای اشتراک‌گذاری:\n{link}")

def handle_broadcast(text, kind, file_id=None):
    cursor.execute("SELECT DISTINCT user_id FROM likes")  # or maintain your own user table
    users = [u['user_id'] for u in cursor.fetchall()]
    for uid in users:
        try:
            if kind == 'file':
                send_document(uid, file_id)
            else:
                send_text(uid, text)
        except Exception:
            pass

def get_bot_username():
    if not hasattr(get_bot_username, "username"):
        resp = requests.get(API_URL + "/getMe").json()
        get_bot_username.username = resp["result"]["username"]
    return get_bot_username.username

def main():
    offset = None
    user_states = {}
    while True:
        updates = get_updates(offset)
        for upd in updates:
            offset = upd["update_id"] + 1
            message = upd.get("message")
            callback = upd.get("callback_query")
            
            if message:
                chat_id = message["chat"]["id"]
                user_id = message["from"]["id"]
                text = message.get("text", "")
                state = user_states.setdefault(user_id, {"mode": None})
                
                if is_admin(user_id):
                    if text == "/start":
                        send_reply_keyboard(chat_id, ["آپلود فایل 📁", "آپلود متن 📝", "ارسال پیام همگانی 📢", "لغو ❌"])
                        continue

                    # Admin command states
                    if state["mode"] is None:
                        handle_admin_command(chat_id, text, state)
                        continue
                    elif state["mode"] == "awaiting_file" and "document" in message:
                        file_id = message["document"]["file_id"]
                        handle_file_upload(chat_id, file_id)
                        state["mode"] = None
                        continue
                    elif state["mode"] == "awaiting_text" and text:
                        handle_text_upload(chat_id, text)
                        state["mode"] = None
                        continue
                    elif state["mode"] == "awaiting_broadcast":
                        # Optional: accept file or text
                        if "document" in message:
                            handle_broadcast(None, 'file', file_id=message["document"]["file_id"])
                        else:
                            handle_broadcast(text, 'text')
                        send_message(chat_id, "پیام برای همه ارسال شد! ✅")
                        state["mode"] = None
                        continue

                # Handle /start <key>
                if text.startswith("/start "):
                    key = text.split(" ", 1)[1].strip()
                    post = get_post(key)
                    if not post:
                        send_message(chat_id, "❌ لینک معتبر نیست.")
                        continue

                    increment_view(key)
                    views = post['views'] + 1
                    likes = post['likes']
                    if post["kind"] == "file":
                        send_inline_keyboard(chat_id, None, key, views, likes, "file")
                    else:
                        send_inline_keyboard(chat_id, post["text"], key, views, likes, "text")
                elif text == "/start":
                    if is_admin(user_id):
                        send_reply_keyboard(chat_id, ["آپلود فایل 📁", "آپلود متن 📝", "ارسال پیام همگانی 📢", "لغو ❌"])
                    else:
                        send_message(chat_id, "سلام! به بات آپلودر خوش آمدید. 😊\n\nبرای دریافت فایل یا متن، لینک مخصوص را ارسال کنید.")
                # Ignore other messages for non-admins to prevent accidental uploads

            elif callback:
                data = callback["data"]
                chat_id = callback["message"]["chat"]["id"]
                user_id = callback["from"]["id"]
                if data.startswith("like_"):
                    key = data[5:]
                    if has_liked(key, user_id):
                        requests.post(API_URL + "/answerCallbackQuery", data={
                            "callback_query_id": callback["id"],
                            "text": "شما قبلاً لایک کرده‌اید! ❤️"
                        })
                    else:
                        if increment_like(key, user_id):
                            post = get_post(key)
                            likes = post["likes"]
                            views = post["views"]
                            requests.post(API_URL + "/answerCallbackQuery", data={
                                "callback_query_id": callback["id"],
                                "text": "لایک شما ثبت شد! ❤️"
                            })
                            send_inline_keyboard(chat_id, post["text"] if post["kind"] == "text" else None, key, views, likes, post["kind"])
                elif data.startswith("views_"):
                    key = data[6:]
                    post = get_post(key)
                    if post:
                        requests.post(API_URL + "/answerCallbackQuery", data={
                            "callback_query_id": callback["id"],
                            "text": f"تعداد بازدید: {post['views']} 👁️"
                        })

if __name__ == "__main__":
    main()
