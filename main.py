import requests
import sqlite3
import os
import time
import uuid

TOKEN = '812616487:PcCYPrqiWmEmfVpPWaWWzxNtvIhjoOSNrK7yFLAX'
URL = f"https://tapi.bale.ai/bot{TOKEN}"
DB_PATH = "/tmp/uploader.db"
UPLOAD_PATH = "/tmp"
ADMINS = ["zonercm"]  # change usernames

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

# --- Create tables
cur.execute('''
CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY,
    uploader_id INTEGER,
    type TEXT,
    content TEXT,
    file_id TEXT,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS likes (
    upload_id TEXT,
    user_id INTEGER,
    PRIMARY KEY(upload_id, user_id)
)
''')

conn.commit()

def get_updates(offset=None):
    params = {'timeout': 100, 'offset': offset}
    r = requests.get(URL + "/getUpdates", params=params)
    return r.json()['result']

def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = reply_markup
    requests.post(URL + "/sendMessage", json=data)

def send_file(chat_id, file_type, file_id, caption=None, reply_markup=None):
    method = "sendDocument" if file_type == "document" else "sendPhoto"
    data = {'chat_id': chat_id, file_type: file_id}
    if caption:
        data['caption'] = caption
        data['parse_mode'] = 'HTML'
    if reply_markup:
        data['reply_markup'] = reply_markup
    requests.post(URL + f"/{method}", json=data)

def edit_buttons(chat_id, msg_id, reply_markup):
    requests.post(URL + "/editMessageReplyMarkup", json={
        'chat_id': chat_id,
        'message_id': msg_id,
        'reply_markup': reply_markup
    })

def build_buttons(upload_id, likes, views):
    return {
        "inline_keyboard": [[
            {"text": f"❤️ {likes}", "callback_data": f"like:{upload_id}"},
            {"text": f"👁 {views}", "callback_data": "noop"}
        ]]
    }

def handle_start(chat_id, text, username):
    if text.startswith('/start_'):
        uid = text.split('_', 1)[1]
        cur.execute("SELECT type, content, file_id, views, likes FROM uploads WHERE id=?", (uid,))
        row = cur.fetchone()
        if not row:
            send_message(chat_id, "❌ این محتوا پیدا نشد.")
            return
        utype, content, file_id, views, likes = row
        cur.execute("UPDATE uploads SET views = views + 1 WHERE id=?", (uid,))
        conn.commit()
        markup = build_buttons(uid, likes, views + 1)
        if utype == "text":
            send_message(chat_id, content, reply_markup=markup)
        else:
            send_file(chat_id, utype, file_id, content, reply_markup=markup)
    else:
        send_message(chat_id, "سلام! برای دریافت محتوا از لینک /start_ استفاده کنید.")

def handle_like(chat_id, user_id, data, msg_id):
    _, uid = data.split(':')
    cur.execute("SELECT 1 FROM likes WHERE upload_id=? AND user_id=?", (uid, user_id))
    if cur.fetchone():
        return
    cur.execute("INSERT INTO likes (upload_id, user_id) VALUES (?, ?)", (uid, user_id))
    cur.execute("UPDATE uploads SET likes = likes + 1 WHERE id=?", (uid,))
    conn.commit()
    cur.execute("SELECT likes, views FROM uploads WHERE id=?", (uid,))
    likes, views = cur.fetchone()
    markup = build_buttons(uid, likes, views)
    edit_buttons(chat_id, msg_id, markup)

def save_upload(chat_id, user_id, utype, content, file_id=None):
    uid = str(uuid.uuid4())[:8]
    cur.execute("INSERT INTO uploads (id, uploader_id, type, content, file_id) VALUES (?, ?, ?, ?, ?)",
                (uid, user_id, utype, content, file_id))
    conn.commit()
    send_message(chat_id, f"✅ ذخیره شد!\nلینک دسترسی:\n/start_{uid}")

def broadcast_message(message):
    cur.execute("SELECT DISTINCT uploader_id FROM uploads")
    users = [r[0] for r in cur.fetchall()]
    for user_id in users:
        try:
            requests.post(URL + "/copyMessage", json={
                "chat_id": user_id,
                "from_chat_id": message['chat']['id'],
                "message_id": message['message_id']
            })
        except:
            continue

def main():
    offset = None
    waiting_text = {}

    while True:
        try:
            updates = get_updates(offset)
            for upd in updates:
                offset = upd['update_id'] + 1

                if 'message' in upd:
                    msg = upd['message']
                    chat_id = msg['chat']['id']
                    user_id = msg['from']['id']
                    username = msg['from'].get('username', '')
                    text = msg.get('text', '')
                    is_admin = username in ADMINS

                    # Start link
                    if text.startswith("/start"):
                        handle_start(chat_id, text, username)
                        continue

                    # Broadcast
                    if is_admin and text == "/broadcast":
                        send_message(chat_id, "پیام را فوروارد کنید یا ارسال نمایید.")
                        waiting_text[user_id] = 'broadcast'
                        continue

                    if user_id in waiting_text:
                        action = waiting_text.pop(user_id)
                        if action == 'broadcast':
                            broadcast_message(msg)
                            send_message(chat_id, "📢 ارسال شد.")
                        continue

                    # Handle admin uploads
                    if is_admin:
                        if 'text' in msg:
                            save_upload(chat_id, user_id, "text", msg['text'])
                        elif 'photo' in msg:
                            file_id = msg['photo'][-1]['file_id']
                            caption = msg.get('caption', '')
                            save_upload(chat_id, user_id, "photo", caption, file_id)
                        elif 'document' in msg:
                            file_id = msg['document']['file_id']
                            caption = msg.get('caption', '')
                            save_upload(chat_id, user_id, "document", caption, file_id)
                        else:
                            send_message(chat_id, "❌ نوع فایل پشتیبانی نمی‌شود.")
                    else:
                        send_message(chat_id, "این بات مخصوص مدیران است.")
                
                elif 'callback_query' in upd:
                    cb = upd['callback_query']
                    data = cb['data']
                    chat_id = cb['message']['chat']['id']
                    msg_id = cb['message']['message_id']
                    user_id = cb['from']['id']

                    if data.startswith('like:'):
                        handle_like(chat_id, user_id, data, msg_id)
                    elif data == 'noop':
                        pass

        except Exception as e:
            print("Error:", e)
            time.sleep(1)

if __name__ == "__main__":
    main()
