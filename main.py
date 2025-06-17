import requests, time, threading, sqlite3, random
from datetime import datetime

TOKEN = "1355028807:usfJSB4MLHdZsWBh6nGwKwuic8gfAkM5H6wld7zJ"
ADMIN_USERNAMES = ["zonercm"]
ADMIN_ID = 844843541
CHANNEL_ID = 5702875694
CHANNEL_LINK = "https://ble.ir/snacks"
API_URL = f"https://tapi.bale.ai/bot{TOKEN}"

conn = sqlite3.connect("/tmp/feedbackssss.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    phone_sent INTEGER DEFAULT 0,
    last_feedback TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS feedbacks (
    id TEXT PRIMARY KEY,
    user_id INTEGER,
    text TEXT,
    username TEXT,
    date TEXT
)
""")
conn.commit()

admin_waiting_for_id = set()
admin_reply_targets = {}  # admin_id -> {user_id, feedback_id}

def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    requests.post(f"{API_URL}/sendMessage", json=payload)

def send_typing(chat_id):
    requests.post(f"{API_URL}/sendChatAction", data={"chat_id": chat_id, "action": "typing"})

def forward_message(to_id, from_id, msg_id, reply_markup=None):
    data = {"chat_id": to_id, "from_chat_id": from_id, "message_id": msg_id}
    if reply_markup:
        data["reply_markup"] = reply_markup
    requests.post(f"{API_URL}/forwardMessage", data=data)

def send_photo(chat_id, file_id, caption=None):
    data = {"chat_id": chat_id, "photo": file_id}
    if caption:
        data["caption"] = caption
        data["parse_mode"] = "HTML"
    requests.post(f"{API_URL}/sendPhoto", data=data)

def check_channel_membership(user_id):
    res = requests.get(f"{API_URL}/getChatMember?chat_id={CHANNEL_ID}&user_id={user_id}").json()
    return res.get("result", {}).get("status") in ["member", "creator", "administrator"]

def has_sent_phone(user_id):
    cur.execute("SELECT phone_sent FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    return row and row[0] == 1

def mark_phone_sent(user_id):
    cur.execute("INSERT OR IGNORE INTO users (id, phone_sent) VALUES (?, 1)", (user_id,))
    cur.execute("UPDATE users SET phone_sent=1 WHERE id=?", (user_id,))
    conn.commit()

def can_send_feedback(user_id):
    cur.execute("SELECT last_feedback FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        return True
    return row[0] != datetime.utcnow().strftime("%Y-%m-%d")

def update_feedback_time(user_id):
    cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
    cur.execute("UPDATE users SET last_feedback=? WHERE id=?", (datetime.utcnow().strftime("%Y-%m-%d"), user_id))
    conn.commit()

def generate_feedback_id():
    while True:
        new_id = str(random.randint(100000, 999999))
        cur.execute("SELECT id FROM feedbacks WHERE id=?", (new_id,))
        if not cur.fetchone():
            return new_id

def save_feedback(user_id, username, text):
    feedback_id = generate_feedback_id()
    cur.execute("INSERT INTO feedbacks (id, user_id, text, username, date) VALUES (?, ?, ?, ?, ?)",
                (feedback_id, user_id, text, username, datetime.utcnow().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    return feedback_id

def get_admin_keyboard():
    return {"keyboard": [["📬 پاسخ به بازخورد"]], "resize_keyboard": True, "one_time_keyboard": False}

def get_phone_keyboard():
    return {
        "keyboard": [[{"text": "📱 ارسال شماره", "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }

def get_join_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "📢 عضویت در کانال", "url": CHANNEL_LINK}],
            [{"text": "✅ بررسی عضویت", "callback_data": "check_join"}]
        ]
    }

def main():
    offset = None
    while True:
        try:
            res = requests.get(f"{API_URL}/getUpdates", params={"timeout": 60, "offset": offset}).json()
            for update in res.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                callback = update.get("callback_query")

                if callback:
                    data = callback["data"]
                    user_id = callback["from"]["id"]

                    if data == "check_join":
                        if check_channel_membership(user_id):
                            requests.post(f"{API_URL}/deleteMessage", data={"chat_id": user_id, "message_id": callback["message"]["message_id"]})
                            send_message(user_id, "✅ عضویت شما تایید شد! حالا می‌توانید بازخورد خود را ارسال کنید.")
                        else:
                            send_message(user_id, "⛔ هنوز عضو کانال نیستید!", reply_markup=get_join_keyboard())
                    continue

                if not msg:
                    continue

                chat_id = msg["chat"]["id"]
                user = msg["from"]
                first_name = user.get("first_name", "")
                username = user.get("username", "")
                is_admin = username in ADMIN_USERNAMES
                text = msg.get("text", "")
                contact = msg.get("contact")
                photo = msg.get("photo")

                send_typing(chat_id)

                if is_admin:
                    if chat_id in admin_waiting_for_id:
                        try:
                            feedback_id = text.strip()
                            cur.execute("SELECT user_id, text FROM feedbacks WHERE id=?", (feedback_id,))
                            fb = cur.fetchone()
                            if not fb:
                                send_message(chat_id, "❌ شناسه بازخورد نامعتبر است.")
                            else:
                                admin_reply_targets[chat_id] = {"user_id": fb[0], "feedback_id": feedback_id}
                                admin_waiting_for_id.remove(chat_id)
                                send_message(chat_id, f"✏️ لطفا پیام پاسخ خود را برای شناسه <b>{feedback_id}</b> ارسال کنید.")
                        except:
                            send_message(chat_id, "❌ لطفا فقط عدد شناسه بازخورد را وارد کنید.")
                        continue

                    if chat_id in admin_reply_targets:
                        target_user_id = admin_reply_targets[chat_id]["user_id"]
                        if photo:
                            file_id = photo[-1]["file_id"]
                            caption = msg.get("caption", "")
                            send_photo(target_user_id, file_id, caption=caption)
                        elif text:
                            send_message(target_user_id, f"📬 پاسخ ادمین به بازخورد شما:\n\n{text}")
                        send_message(chat_id, "✅ پاسخ ارسال شد.")
                        del admin_reply_targets[chat_id]
                        continue

                    if text == "/start":
                        send_message(chat_id, "🎛 پنل ادمین\nبرای پاسخ به بازخورد روی دکمه زیر بزنید.", reply_markup=get_admin_keyboard())
                        continue

                    if text == "📬 پاسخ به بازخورد":
                        admin_waiting_for_id.add(chat_id)
                        send_message(chat_id, "📨 لطفا شماره شناسه بازخورد را ارسال کنید.")
                        continue
                    continue

                if contact:
                    if contact["user_id"] == chat_id:
                        forward_message(ADMIN_ID, chat_id, msg["message_id"])
                        mark_phone_sent(chat_id)
                        send_message(chat_id, f"✅ شماره شما دریافت شد {first_name} عزیز. حالا می‌توانید بازخورد خود را ارسال کنید.", reply_markup={"remove_keyboard": True})
                    continue

                if text == "/start":
                    if has_sent_phone(chat_id):
                        send_message(chat_id, f"📝 {first_name} عزیز، لطفا بازخورد خود را ارسال کنید.")
                    else:
                        send_message(chat_id, f"📞 سلام {first_name} عزیز، لطفا شماره تماس خود را ارسال کنید.\nاین شماره فقط برای جلوگیری از اسپم استفاده می‌شود.", reply_markup=get_phone_keyboard())
                    continue

                if not has_sent_phone(chat_id):
                    send_message(chat_id, "📱 لطفا اول شماره تماس خود را ارسال کنید:", reply_markup=get_phone_keyboard())
                    continue

                if not check_channel_membership(chat_id):
                    send_message(chat_id, "📢 برای ادامه لطفا عضو کانال شوید:", reply_markup=get_join_keyboard())
                    continue

                if not can_send_feedback(chat_id):
                    send_message(chat_id, "⛔ امروز فقط یک بار می‌توانید بازخورد ارسال کنید. فردا دوباره امتحان کنید.")
                    continue

                feedback_id = save_feedback(chat_id, username, text)
                update_feedback_time(chat_id)

                # Send full info to admin
                info = f"""📩 <b>بازخورد جدید دریافت شد</b>

🆔 <b>شناسه بازخورد:</b> <code>{feedback_id}</code>
👤 <b>نام:</b> {first_name}
🔗 <b>یوزرنیم:</b> @{username if username else 'ندارد'}
🗓 <b>زمان:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}
💬 <b>متن:</b>
{text}"""

                send_message(ADMIN_ID, info)

                send_message(chat_id, f"✅ بازخورد شما ثبت شد. ممنون از نظر شما 🙏")

        except Exception as e:
            print("Error:", e)
            time.sleep(2)

# Run in a thread
threading.Thread(target=main).start()
