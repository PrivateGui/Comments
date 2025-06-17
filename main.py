import requests
import random
import string
import time
import os
import mysql.connector

# --- CONFIG ---
BOT_TOKEN = '812616487:PcCYPrqiWmEmfVpPWaWWzxNtvIhjoOSNrK7yFLAX'  # Replace with your bot token
API_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"
ADMIN_USERNAMES = ['zonercm']  # Add more if needed
DB = mysql.connector.connect(
    host="cests",
    user="root",
    password="flTurEdlcHlTcvZ9xYVsGdBY",
    database="gallant_yonath"
)
CURSOR = DB.cursor(dictionary=True)

# --- INIT TABLES ---
CURSOR.execute("""
CREATE TABLE IF NOT EXISTS posts (
    id VARCHAR(64) PRIMARY KEY,
    type VARCHAR(10),
    content TEXT,
    views INT DEFAULT 0,
    likes INT DEFAULT 0
)""")
CURSOR.execute("""
CREATE TABLE IF NOT EXISTS likes (
    post_id VARCHAR(64),
    user_id BIGINT,
    UNIQUE(post_id, user_id)
)""")
DB.commit()

# --- UTILS ---
def get_updates(offset=None):
    params = {'timeout': 30, 'offset': offset}
    return requests.get(API_URL + '/getUpdates', params=params).json()

def send_message(chat_id, text, reply_markup=None):
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    requests.post(API_URL + '/sendMessage', json=payload)

def send_document(chat_id, file_path, caption='', reply_markup=None):
    with open(file_path, 'rb') as f:
        files = {'document': f}
        data = {'chat_id': chat_id, 'caption': caption}
        if reply_markup:
            data['reply_markup'] = reply_markup
        requests.post(API_URL + '/sendDocument', data=data, files=files)

def generate_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

def is_admin(username):
    return username in ADMIN_USERNAMES

def build_inline(post_id, views, likes):
    return {
        'inline_keyboard': [[
            {'text': f'👁 {views}', 'callback_data': f'views_{post_id}'},
            {'text': f'❤️ {likes}', 'callback_data': f'like_{post_id}'}
        ]]
    }

def build_admin_keyboard():
    return {
        'keyboard': [[
            {'text': '📤 ارسال فایل'}, {'text': '📝 ارسال متن'},
        ],[
            {'text': '📣 ارسال پیام همگانی'},
        ]],
        'resize_keyboard': True
    }

# --- STATE MGMT ---
user_states = {}

# --- MAIN LOOP ---
print("Bot is running...")
last_update = None

while True:
    updates = get_updates(last_update)
    if updates.get("ok"):
        for update in updates["result"]:
            last_update = update["update_id"] + 1

            msg = update.get("message")
            cbq = update.get("callback_query")

            # --- CALLBACKS ---
            if cbq:
                data = cbq["data"]
                user_id = cbq["from"]["id"]
                cid = cbq["message"]["chat"]["id"]

                if data.startswith("like_"):
                    post_id = data.split("_", 1)[1]
                    CURSOR.execute("SELECT * FROM likes WHERE post_id=%s AND user_id=%s", (post_id, user_id))
                    if not CURSOR.fetchone():
                        CURSOR.execute("INSERT INTO likes (post_id, user_id) VALUES (%s, %s)", (post_id, user_id))
                        CURSOR.execute("UPDATE posts SET likes = likes + 1 WHERE id=%s", (post_id,))
                        DB.commit()
                    CURSOR.execute("SELECT * FROM posts WHERE id=%s", (post_id,))
                    post = CURSOR.fetchone()
                    requests.post(API_URL + '/editMessageReplyMarkup', json={
                        'chat_id': cid,
                        'message_id': cbq["message"]["message_id"],
                        'reply_markup': build_inline(post_id, post['views'], post['likes'])
                    })
                continue

            if not msg: continue
            text = msg.get("text", "")
            username = msg["from"].get("username", "")
            user_id = msg["from"]["id"]
            cid = msg["chat"]["id"]

            # --- ADMIN MENU ---
            if is_admin(username):
                if text == "/start":
                    send_message(cid, "سلام ادمین عزیز 😎\nیکی از گزینه‌های زیر رو انتخاب کن:", reply_markup=build_admin_keyboard())
                    continue
                if text == "📤 ارسال فایل":
                    user_states[user_id] = 'awaiting_file'
                    send_message(cid, "فایل خود را ارسال کن 📂")
                    continue
                if text == "📝 ارسال متن":
                    user_states[user_id] = 'awaiting_text'
                    send_message(cid, "متن موردنظر را بفرست 📝")
                    continue
                if text == "📣 ارسال پیام همگانی":
                    user_states[user_id] = 'awaiting_broadcast'
                    send_message(cid, "پیام مورد نظر را بفرست (متن یا عکس یا فایل)")
                    continue

            # --- STATES ---
            state = user_states.get(user_id)
            if state == 'awaiting_text':
                key = generate_key()
                CURSOR.execute("INSERT INTO posts (id, type, content) VALUES (%s, %s, %s)", (key, 'text', text))
                DB.commit()
                send_message(cid, f"✅ ذخیره شد!\nلینک: /start {key}")
                user_states.pop(user_id)
                continue

            if state == 'awaiting_broadcast':
                if msg.get("document"):
                    file_id = msg["document"]["file_id"]
                    file_info = requests.get(f"{API_URL}/getFile?file_id={file_id}").json()
                    path = file_info["result"]["file_path"]
                    file_url = f"https://tapi.bale.ai/file/bot{BOT_TOKEN}/{path}"
                    file_data = requests.get(file_url).content
                    tmp_path = f"/tmp/{msg['document']['file_name']}"
                    with open(tmp_path, "wb") as f:
                        f.write(file_data)
                    # Send to all users
                    CURSOR.execute("SELECT DISTINCT user_id FROM likes")
                    for row in CURSOR.fetchall():
                        try:
                            send_document(row['user_id'], tmp_path, caption="📣 پیام جدید از ادمین")
                        except: pass
                elif text:
                    CURSOR.execute("SELECT DISTINCT user_id FROM likes")
                    for row in CURSOR.fetchall():
                        try:
                            send_message(row['user_id'], f"📣 پیام جدید:\n{text}")
                        except: pass
                send_message(cid, "📢 پیام همگانی ارسال شد")
                user_states.pop(user_id)
                continue

            if state == 'awaiting_file':
                if not msg.get("document"):
                    send_message(cid, "❌ لطفاً یک فایل بفرست")
                    continue
                file_id = msg["document"]["file_id"]
                file_info = requests.get(f"{API_URL}/getFile?file_id={file_id}").json()
                path = file_info["result"]["file_path"]
                file_url = f"https://tapi.bale.ai/file/bot{BOT_TOKEN}/{path}"
                file_data = requests.get(file_url).content
                file_path = f"/tmp/{msg['document']['file_name']}"
                with open(file_path, "wb") as f:
                    f.write(file_data)
                key = generate_key()
                CURSOR.execute("INSERT INTO posts (id, type, content) VALUES (%s, %s, %s)", (key, 'file', file_path))
                DB.commit()
                send_message(cid, f"✅ فایل ذخیره شد!\nلینک: /start {key}")
                user_states.pop(user_id)
                continue

            # --- /start <key> ---
            if text.startswith("/start "):
                key = text.split("/start ", 1)[1].strip()
                CURSOR.execute("SELECT * FROM posts WHERE id=%s", (key,))
                post = CURSOR.fetchone()
                if not post:
                    send_message(cid, "❌ چنین محتوایی وجود ندارد.")
                    continue
                CURSOR.execute("UPDATE posts SET views = views + 1 WHERE id=%s", (key,))
                DB.commit()
                CURSOR.execute("INSERT IGNORE INTO likes (post_id, user_id) VALUES (%s, %s)", (key, user_id))
                DB.commit()
                markup = build_inline(post['id'], post['views']+1, post['likes'])
                if post['type'] == 'text':
                    send_message(cid, post['content'], reply_markup=markup)
                else:
                    send_document(cid, post['content'], reply_markup=markup)
                continue

            # --- NORMAL USER /start ---
            if text == "/start":
                send_message(cid, "سلام 👋\nبه ربات خوش اومدی!", reply_markup=None)
                continue
