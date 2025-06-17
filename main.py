import sqlite3
import os
import random
import string
import requests
from time import time

# Configuration
TOKEN = "812616487:PcCYPrqiWmEmfVpPWaWWzxNtvIhjoOSNrK7yFLAX"
API_URL = f"https://tapi.bale.ai/bot{TOKEN}"
ADMINS = [844843541]  # Replace with your admin chat IDs
TMP_DIR = "/tmp/telegram_bot_files"
os.makedirs(TMP_DIR, exist_ok=True)

# Initialize DB
conn = sqlite3.connect('/tmp/telegram_bot.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT,
    file_type TEXT,
    file_path TEXT,
    text_content TEXT,
    start_link TEXT UNIQUE,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER,
    user_id INTEGER,
    UNIQUE(file_id, user_id)
)
''')

conn.commit()

def generate_start_link():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

def save_file(file_info, file_type):
    file_id = file_info['file_id']
    file_url = f"{API_URL}/getFile?file_id={file_id}"
    response = requests.get(file_url).json()
    file_path = response['result']['file_path']
    
    download_url = f"https://tapi.bale.ai/file/bot{TOKEN}/{file_path}"
    local_path = os.path.join(TMP_DIR, os.path.basename(file_path))
    
    with requests.get(download_url, stream=True) as r:
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    
    return local_path

def send_message(chat_id, text, reply_markup=None):
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    
    requests.post(f"{API_URL}/sendMessage", json=payload)

def get_admin_keyboard():
    return {
        'keyboard': [
            ['📤 آپلود فایل', '📝 آپلود متن'],
            ['📢 ارسال پیام به همه', '📊 آمار']
        ],
        'resize_keyboard': True
    }

def process_message(message):
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    text = message.get('text', '')
    
    # Check if admin
    is_admin = user_id in ADMINS
    
    # Handle /start commands
    if text.startswith('/start'):
        parts = text.split()
        if len(parts) > 1:
            start_link = parts[1]
            cursor.execute('SELECT * FROM files WHERE start_link = ?', (start_link,))
            file_data = cursor.fetchone()
            
            if file_data:
                # Update view count
                cursor.execute('UPDATE files SET views = views + 1 WHERE id = ?', (file_data[0],))
                conn.commit()
                
                # Send the file/message
                if file_data[2] == 'text':
                    keyboard = {
                        'inline_keyboard': [
                            [
                                {'text': f'👁️ {file_data[6]} بازدید', 'callback_data': f'views_{file_data[0]}'},
                                {'text': f'❤️ {file_data[7]} پسندیدم', 'callback_data': f'like_{file_data[0]}'}
                            ]
                        ]
                    }
                    send_message(chat_id, file_data[4], reply_markup=keyboard)
                else:
                    # Send file based on type
                    file_path = file_data[3]
                    file_type = file_data[2]
                    
                    with open(file_path, 'rb') as f:
                        files = {file_type: f}
                        payload = {
                            'chat_id': chat_id,
                            'caption': f'بازدید: {file_data[6]} | پسندیدم: {file_data[7]}'
                        }
                        requests.post(f"{API_URL}/send{file_type.capitalize()}", files=files, data=payload)
            else:
                send_message(chat_id, '⚠️ لینک مورد نظر یافت نشد!')
        else:
            if is_admin:
                send_message(chat_id, 'سلام ادمین گرامی! چه کاری می‌تونم براتون انجام بدم؟', 
                           reply_markup=get_admin_keyboard())
            else:
                send_message(chat_id, 'سلام! برای دریافت فایل، لینک اختصاصی را ارسال کنید.')
    
    # Handle admin commands
    elif is_admin:
        if text == '📤 آپلود فایل':
            send_message(chat_id, 'لطفا فایل مورد نظر را ارسال کنید.')
        
        elif text == '📝 آپلود متن':
            send_message(chat_id, 'لطفا متن مورد نظر را ارسال کنید.')
        
        elif text == '📢 ارسال پیام به همه':
            send_message(chat_id, 'لطفا پیام عمومی را ارسال کنید.')
        
        elif text == '📊 آمار':
            cursor.execute('SELECT COUNT(*) FROM files')
            count = cursor.fetchone()[0]
            send_message(chat_id, f'📊 آمار ربات:\n\n🔗 تعداد لینک‌ها: {count}')
        
        # Check if we're expecting a file or text from admin
        elif 'document' in message:
            file_info = message['document']
            file_type = 'document'
            file_path = save_file(file_info, file_type)
            
            start_link = generate_start_link()
            cursor.execute('INSERT INTO files (file_id, file_type, file_path, start_link) VALUES (?, ?, ?, ?)',
                          (file_info['file_id'], file_type, file_path, start_link))
            conn.commit()
            
            send_message(chat_id, f'✅ فایل با موفقیت آپلود شد!\n\nلینک اختصاصی:\n/start {start_link}',
                       reply_markup=get_admin_keyboard())
        
        elif 'photo' in message:
            file_info = message['photo'][-1]  # Get highest resolution photo
            file_type = 'photo'
            file_path = save_file(file_info, file_type)
            
            start_link = generate_start_link()
            cursor.execute('INSERT INTO files (file_id, file_type, file_path, start_link) VALUES (?, ?, ?, ?)',
                          (file_info['file_id'], file_type, file_path, start_link))
            conn.commit()
            
            send_message(chat_id, f'✅ عکس با موفقیت آپلود شد!\n\nلینک اختصاصی:\n/start {start_link}',
                       reply_markup=get_admin_keyboard())
        
        elif 'video' in message:
            file_info = message['video']
            file_type = 'video'
            file_path = save_file(file_info, file_type)
            
            start_link = generate_start_link()
            cursor.execute('INSERT INTO files (file_id, file_type, file_path, start_link) VALUES (?, ?, ?, ?)',
                          (file_info['file_id'], file_type, file_path, start_link))
            conn.commit()
            
            send_message(chat_id, f'✅ ویدیو با موفقیت آپلود شد!\n\nلینک اختصاصی:\n/start {start_link}',
                       reply_markup=get_admin_keyboard())
        
        elif 'text' in message and not any(cmd in text for cmd in ['📤', '📝', '📢', '📊']):
            # Check if this is a broadcast message
            cursor.execute('SELECT text FROM files ORDER BY id DESC LIMIT 1')
            last_command = cursor.fetchone()
            
            if last_command and last_command[0] == '📢 ارسال پیام به همه':
                # This is a broadcast message
                cursor.execute('SELECT DISTINCT user_id FROM likes')
                users = cursor.fetchall()
                
                for user in users:
                    try:
                        send_message(user[0], f"📢 پیام عمومی:\n\n{text}")
                    except:
                        continue
                
                send_message(chat_id, f'✅ پیام به {len(users)} کاربر ارسال شد!',
                           reply_markup=get_admin_keyboard())
            else:
                # This is a text to be saved
                start_link = generate_start_link()
                cursor.execute('INSERT INTO files (text_content, start_link) VALUES (?, ?)',
                              (text, start_link))
                conn.commit()
                
                send_message(chat_id, f'✅ متن با موفقیت ذخیره شد!\n\nلینک اختصاصی:\n/start {start_link}',
                           reply_markup=get_admin_keyboard())

def process_callback_query(callback_query):
    data = callback_query['data']
    chat_id = callback_query['message']['chat']['id']
    user_id = callback_query['from']['id']
    message_id = callback_query['message']['message_id']
    
    if data.startswith('like_'):
        file_id = int(data.split('_')[1])
        
        # Check if user already liked
        cursor.execute('SELECT 1 FROM likes WHERE file_id = ? AND user_id = ?', (file_id, user_id))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO likes (file_id, user_id) VALUES (?, ?)', (file_id, user_id))
            cursor.execute('UPDATE files SET likes = likes + 1 WHERE id = ?', (file_id,))
            conn.commit()
        
        # Get updated counts
        cursor.execute('SELECT views, likes FROM files WHERE id = ?', (file_id,))
        views, likes = cursor.fetchone()
        
        # Update message buttons
        keyboard = {
            'inline_keyboard': [
                [
                    {'text': f'👁️ {views} بازدید', 'callback_data': f'views_{file_id}'},
                    {'text': f'❤️ {likes} پسندیدم', 'callback_data': f'like_{file_id}'}
                ]
            ]
        }
        
        requests.post(f"{API_URL}/editMessageReplyMarkup", json={
            'chat_id': chat_id,
            'message_id': message_id,
            'reply_markup': keyboard
        })
        
        requests.post(f"{API_URL}/answerCallbackQuery", json={
            'callback_query_id': callback_query['id'],
            'text': 'ممنون از پسندیدن شما!'
        })

def main():
    offset = 0
    while True:
        try:
            response = requests.get(f"{API_URL}/getUpdates", params={'offset': offset, 'timeout': 10}).json()
            
            if response.get('result'):
                for update in response['result']:
                    offset = update['update_id'] + 1
                    
                    if 'message' in update:
                        process_message(update['message'])
                    elif 'callback_query' in update:
                        process_callback_query(update['callback_query'])
        
        except Exception as e:
            print(f"Error: {e}")
            continue

if __name__ == '__main__':
    main()
