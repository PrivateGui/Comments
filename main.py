import os
import time
import json
import random
import string
import sqlite3
import requests

TOKEN = '812616487:PcCYPrqiWmEmfVpPWaWWzxNtvIhjoOSNrK7yFLAX'
URL = f'https://tapi.bale.ai/bot{TOKEN}'
ADMIN_USERNAMES = ['zonercm']  # change to your usernames
DB_PATH = '/tmp/uploader.db'
UPLOAD_DIR = '/tmp'

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()

cur.execute('''CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY,
    type TEXT,
    content TEXT,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0
)''')
conn.commit()


def get_updates(offset=None):
    params = {'timeout': 0}
    if offset:
        params['offset'] = offset
    r = requests.get(f'{URL}/getUpdates', params=params)
    return r.json()['result']


def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = json.dumps(reply_markup)
    requests.post(f'{URL}/sendMessage', data=data)


def send_typing(chat_id):
    requests.post(f'{URL}/sendChatAction', data={'chat_id': chat_id, 'action': 'typing'})


def forward_message(chat_id, from_chat_id, message_id):
    requests.post(f'{URL}/forwardMessage', data={
        'chat_id': chat_id,
        'from_chat_id': from_chat_id,
        'message_id': message_id
    })


def generate_id(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def is_admin(username):
    return username in ADMIN_USERNAMES


def save_upload(upload_type, content):
    upload_id = generate_id()
    cur.execute("INSERT INTO uploads (id, type, content) VALUES (?, ?, ?)", (upload_id, upload_type, content))
    conn.commit()
    return upload_id


def increment_view(upload_id):
    cur.execute("UPDATE uploads SET views = views + 1 WHERE id = ?", (upload_id,))
    conn.commit()


def increment_like(upload_id):
    cur.execute("UPDATE uploads SET likes = likes + 1 WHERE id = ?", (upload_id,))
    conn.commit()


def get_upload(upload_id):
    cur.execute("SELECT * FROM uploads WHERE id = ?", (upload_id,))
    return cur.fetchone()


def handle_start(chat_id, text, username):
    args = text.split()
    if len(args) == 2:
        upload_id = args[1]
        row = get_upload(upload_id)
        if row:
            increment_view(upload_id)
            _, typ, content, views, likes = row
            if typ == 'text':
                send_message(chat_id, f"<b>📄 متن:</b>\n{content}\n\n👁 تعداد بازدید: {views}\n❤️ لایک: {likes}",
                             reply_markup={'keyboard': [[f'❤️ لایک {upload_id}'], ['🔙 بازگشت']], 'resize_keyboard': True})
            elif typ == 'file':
                with open(content, 'rb') as f:
                    requests.post(f'{URL}/sendDocument', data={'chat_id': chat_id}, files={'document': f})
                send_message(chat_id, f"👁 تعداد بازدید: {views}\n❤️ لایک: {likes}",
                             reply_markup={'keyboard': [[f'❤️ لایک {upload_id}'], ['🔙 بازگشت']], 'resize_keyboard': True})
        else:
            send_message(chat_id, "⛔️ فایل پیدا نشد.")
    else:
        send_message(chat_id, "سلام! 👋\nبرای دریافت فایل، لینک مربوطه را بفرستید.",
                     reply_markup={'keyboard': [['📤 آپلود فایل'], ['🔙 بازگشت']], 'resize_keyboard': True})


def handle_like(chat_id, text):
    parts = text.split()
    if len(parts) == 3:
        upload_id = parts[2]
        increment_like(upload_id)
        row = get_upload(upload_id)
        if row:
            _, _, _, views, likes = row
            send_message(chat_id, f"❤️ با موفقیت لایک شد!\n👁 بازدید: {views} | ❤️ لایک: {likes}")


def handle_upload_file(chat_id, message, username):
    file_id = message['document']['file_id']
    file_name = message['document']['file_name']
    file_path = requests.get(f'{URL}/getFile', params={'file_id': file_id}).json()['result']['file_path']
    file_url = f'https://api.telegram.org/file/bot{TOKEN}/{file_path}'
    file_data = requests.get(file_url).content
    save_path = f'{UPLOAD_DIR}/{file_name}'
    with open(save_path, 'wb') as f:
        f.write(file_data)
    upload_id = save_upload('file', save_path)
    send_message(chat_id, f"✅ فایل ذخیره شد!\nلینک اشتراک: /start {upload_id}")


def handle_upload_text(chat_id, text, username):
    upload_id = save_upload('text', text)
    send_message(chat_id, f"✅ متن ذخیره شد!\nلینک اشتراک: /start {upload_id}")


def handle_broadcast(message):
    cur.execute("SELECT DISTINCT content FROM uploads")
    users = [row[0] for row in cur.fetchall()]
    for user in users:
        try:
            forward_message(user, message['chat']['id'], message['message_id'])
        except:
            continue


def main():
    offset = None
    print("Bot is running...")

    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update['update_id'] + 1

            if 'message' not in update:
                continue

            msg = update['message']
            chat_id = msg['chat']['id']
            username = msg['from'].get('username', '')
            text = msg.get('text', '')

            send_typing(chat_id)

            if 'document' in msg and is_admin(username):
                handle_upload_file(chat_id, msg, username)
            elif text:
                if text.startswith('/start'):
                    handle_start(chat_id, text, username)
                elif text.startswith('❤️ لایک'):
                    handle_like(chat_id, text)
                elif is_admin(username):
                    if text.startswith('/broadcast'):
                        handle_broadcast(msg)
                    else:
                        handle_upload_text(chat_id, text, username)
                else:
                    send_message(chat_id, "سلام! لطفاً لینک دریافت محتوا را وارد کنید.")


if __name__ == '__main__':
    main()
