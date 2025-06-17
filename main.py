#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import requests
import sqlite3
import os
import string
import random
import time
import threading
from urllib.parse import urljoin

# Bot Configuration
BOT_TOKEN = "812616487:PcCYPrqiWmEmfVpPWaWWzxNtvIhjoOSNrK7yFLAX"  # Replace with your bot token
ADMIN_IDS = [844843541]  # Replace with admin Telegram IDs
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"

# Database setup
DB_PATH = "/tmp/uploader_bot.db"
FILES_DIR = "/tmp/bot_files/"

# Ensure directories exist
os.makedirs(FILES_DIR, exist_ok=True)

def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            file_path TEXT,
            text_content TEXT,
            caption TEXT,
            admin_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            views INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(upload_id, user_id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_states (
            admin_id INTEGER PRIMARY KEY,
            state TEXT DEFAULT 'normal'
        )
    ''')
    
    conn.commit()
    conn.close()

def generate_random_string(length=10):
    """Generate random string for upload IDs"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def send_request(method, params=None, files=None):
    """Send request to Telegram API"""
    url = urljoin(BASE_URL, method)
    try:
        if files:
            response = requests.post(url, data=params, files=files, timeout=30)
        else:
            response = requests.post(url, json=params, timeout=30)
        return response.json()
    except Exception as e:
        print(f"Request error: {e}")
        return None

def send_message(chat_id, text, reply_markup=None):
    """Send text message"""
    params = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        params['reply_markup'] = json.dumps(reply_markup)
    
    return send_request('sendMessage', params)

def send_document(chat_id, document_path, caption=None, reply_markup=None):
    """Send document file"""
    params = {
        'chat_id': chat_id,
        'parse_mode': 'HTML'
    }
    if caption:
        params['caption'] = caption
    if reply_markup:
        params['reply_markup'] = json.dumps(reply_markup)
    
    with open(document_path, 'rb') as doc:
        files = {'document': doc}
        return send_request('sendDocument', params, files)

def send_photo(chat_id, photo_path, caption=None, reply_markup=None):
    """Send photo file"""
    params = {
        'chat_id': chat_id,
        'parse_mode': 'HTML'
    }
    if caption:
        params['caption'] = caption
    if reply_markup:
        params['reply_markup'] = json.dumps(reply_markup)
    
    with open(photo_path, 'rb') as photo:
        files = {'photo': photo}
        return send_request('sendPhoto', params, files)

def send_video(chat_id, video_path, caption=None, reply_markup=None):
    """Send video file"""
    params = {
        'chat_id': chat_id,
        'parse_mode': 'HTML'
    }
    if caption:
        params['caption'] = caption
    if reply_markup:
        params['reply_markup'] = json.dumps(reply_markup)
    
    with open(video_path, 'rb') as video:
        files = {'video': video}
        return send_request('sendVideo', params, files)

def send_audio(chat_id, audio_path, caption=None, reply_markup=None):
    """Send audio file"""
    params = {
        'chat_id': chat_id,
        'parse_mode': 'HTML'
    }
    if caption:
        params['caption'] = caption
    if reply_markup:
        params['reply_markup'] = json.dumps(reply_markup)
    
    with open(audio_path, 'rb') as audio:
        files = {'audio': audio}
        return send_request('sendAudio', params, files)

def download_file(file_id, file_path):
    """Download file from Telegram"""
    # Get file info
    params = {'file_id': file_id}
    file_info = send_request('getFile', params)
    
    if not file_info or not file_info.get('ok'):
        return False
    
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info['result']['file_path']}"
    
    try:
        response = requests.get(file_url, timeout=30)
        with open(file_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"Download error: {e}")
        return False

def get_admin_keyboard():
    """Get admin reply keyboard"""
    return {
        'keyboard': [
            ['📁 آپلود فایل', '📝 آپلود متن'],
            ['📢 ارسال پیام همگانی', '📊 آمار بات'],
            ['❌ لغو عملیات']
        ],
        'resize_keyboard': True,
        'one_time_keyboard': False
    }

def get_content_keyboard(upload_id, views, likes_count, user_liked=False):
    """Get inline keyboard for content"""
    like_text = "💚 لایک شده" if user_liked else "🤍 لایک"
    
    return {
        'inline_keyboard': [
            [
                {'text': f'👁 {views} بازدید', 'callback_data': f'views_{upload_id}'},
                {'text': f'{like_text} ({likes_count})', 'callback_data': f'like_{upload_id}'}
            ]
        ]
    }

def get_admin_state(admin_id):
    """Get admin current state"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT state FROM admin_states WHERE admin_id = ?', (admin_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 'normal'

def set_admin_state(admin_id, state):
    """Set admin state"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO admin_states (admin_id, state) VALUES (?, ?)', 
                   (admin_id, state))
    conn.commit()
    conn.close()

def save_upload(upload_id, upload_type, file_path=None, text_content=None, caption=None, admin_id=None):
    """Save upload to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO uploads (upload_id, type, file_path, text_content, caption, admin_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (upload_id, upload_type, file_path, text_content, caption, admin_id))
    conn.commit()
    conn.close()

def get_upload(upload_id):
    """Get upload from database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM uploads WHERE upload_id = ?', (upload_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def increment_views(upload_id):
    """Increment view count"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE uploads SET views = views + 1 WHERE upload_id = ?', (upload_id,))
    conn.commit()
    conn.close()

def toggle_like(upload_id, user_id):
    """Toggle like for user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if already liked
    cursor.execute('SELECT id FROM likes WHERE upload_id = ? AND user_id = ?', (upload_id, user_id))
    existing = cursor.fetchone()
    
    if existing:
        # Remove like
        cursor.execute('DELETE FROM likes WHERE upload_id = ? AND user_id = ?', (upload_id, user_id))
        action = 'removed'
    else:
        # Add like
        cursor.execute('INSERT INTO likes (upload_id, user_id) VALUES (?, ?)', (upload_id, user_id))
        action = 'added'
    
    conn.commit()
    conn.close()
    return action

def get_likes_count(upload_id):
    """Get likes count for upload"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM likes WHERE upload_id = ?', (upload_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def user_has_liked(upload_id, user_id):
    """Check if user has liked the upload"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM likes WHERE upload_id = ? AND user_id = ?', (upload_id, user_id))
    result = cursor.fetchone()
    conn.close()
    return bool(result)

def get_bot_stats():
    """Get bot statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM uploads')
    total_uploads = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(views) FROM uploads')
    total_views = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT COUNT(*) FROM likes')
    total_likes = cursor.fetchone()[0]
    
    conn.close()
    
    return {
        'uploads': total_uploads,
        'views': total_views,
        'likes': total_likes
    }

def broadcast_message(message_text, admins_only=False):
    """Broadcast message to all users (simplified - you'd need to track users)"""
    # This is a simplified version - in production you'd maintain a users table
    pass

def handle_start_command(chat_id, user_id, args):
    """Handle /start command"""
    if args:
        # Handle start link
        upload_id = args
        upload = get_upload(upload_id)
        
        if not upload:
            send_message(chat_id, "⚠️ پیوند نامعتبر یا منقضی شده است.")
            return
        
        # Increment views
        increment_views(upload_id)
        
        # Get updated stats
        views = upload[8] + 1  # views + 1
        likes_count = get_likes_count(upload_id)
        user_liked = user_has_liked(upload_id, user_id)
        
        # Create keyboard
        keyboard = get_content_keyboard(upload_id, views, likes_count, user_liked)
        
        if upload[2] == 'text':
            # Send text
            text = upload[4] or "📝 متن ارسالی"
            send_message(chat_id, text, keyboard)
        else:
            # Send file
            file_path = upload[3]
            caption = upload[5] or ""
            
            if upload[2] == 'photo':
                send_photo(chat_id, file_path, caption, keyboard)
            elif upload[2] == 'video':
                send_video(chat_id, file_path, caption, keyboard)
            elif upload[2] == 'audio':
                send_audio(chat_id, file_path, caption, keyboard)
            else:
                send_document(chat_id, file_path, caption, keyboard)
    else:
        # Regular start
        if user_id in ADMIN_IDS:
            send_message(chat_id, 
                        "🔥 سلام ادمین عزیز!\n"
                        "به بات آپلودر خوش آمدید.\n\n"
                        "🎛 از کیبورد زیر برای مدیریت بات استفاده کنید:",
                        get_admin_keyboard())
        else:
            send_message(chat_id, 
                        "👋 سلام و خوش آمدید!\n"
                        "این بات برای اشتراک فایل و متن استفاده می‌شود.\n\n"
                        "📎 برای دریافت محتوا، روی پیوندهای اشتراک کلیک کنید.")

def handle_admin_message(chat_id, user_id, message):
    """Handle admin messages"""
    text = message.get('text', '')
    state = get_admin_state(user_id)
    
    # Handle cancel
    if text == '❌ لغو عملیات':
        set_admin_state(user_id, 'normal')
        send_message(chat_id, "✅ عملیات لغو شد.", get_admin_keyboard())
        return
    
    if state == 'normal':
        if text == '📁 آپلود فایل':
            set_admin_state(user_id, 'waiting_file')
            send_message(chat_id, "📁 فایل مورد نظر را ارسال کنید:")
            
        elif text == '📝 آپلود متن':
            set_admin_state(user_id, 'waiting_text')
            send_message(chat_id, "📝 متن مورد نظر را ارسال کنید:")
            
        elif text == '📢 ارسال پیام همگانی':
            set_admin_state(user_id, 'waiting_broadcast')
            send_message(chat_id, "📢 پیام همگانی را ارسال کنید:")
            
        elif text == '📊 آمار بات':
            stats = get_bot_stats()
            stats_text = (
                f"📊 آمار بات:\n\n"
                f"📁 کل آپلودها: {stats['uploads']}\n"
                f"👁 کل بازدیدها: {stats['views']}\n"
                f"❤️ کل لایک‌ها: {stats['likes']}"
            )
            send_message(chat_id, stats_text, get_admin_keyboard())
            
    elif state == 'waiting_text':
        # Save text upload
        upload_id = generate_random_string()
        save_upload(upload_id, 'text', text_content=text, admin_id=user_id)
        
        start_link = f"/start {upload_id}"
        response_text = (
            f"✅ متن با موفقیت ذخیره شد!\n\n"
            f"🔗 پیوند اشتراک:\n"
            f"<code>{start_link}</code>\n\n"
            f"📋 برای کپی روی پیوند کلیک کنید."
        )
        
        set_admin_state(user_id, 'normal')
        send_message(chat_id, response_text, get_admin_keyboard())
        
    elif state == 'waiting_broadcast':
        # Handle broadcast
        # In a real implementation, you'd send to all users
        send_message(chat_id, "📢 پیام همگانی ارسال شد! (نسخه ساده)", get_admin_keyboard())
        set_admin_state(user_id, 'normal')

def handle_admin_file(chat_id, user_id, message):
    """Handle admin file uploads"""
    state = get_admin_state(user_id)
    
    if state != 'waiting_file':
        return
    
    # Determine file type and get file_id
    file_id = None
    file_type = None
    file_extension = ""
    
    if 'photo' in message:
        file_id = message['photo'][-1]['file_id']  # Get highest resolution
        file_type = 'photo'
        file_extension = '.jpg'
    elif 'document' in message:
        file_id = message['document']['file_id']
        file_type = 'document'
        file_name = message['document'].get('file_name', 'file')
        file_extension = os.path.splitext(file_name)[1] or '.bin'
    elif 'video' in message:
        file_id = message['video']['file_id']
        file_type = 'video'
        file_extension = '.mp4'
    elif 'audio' in message:
        file_id = message['audio']['file_id']
        file_type = 'audio'
        file_extension = '.mp3'
    elif 'voice' in message:
        file_id = message['voice']['file_id']
        file_type = 'audio'
        file_extension = '.ogg'
    elif 'video_note' in message:
        file_id = message['video_note']['file_id']
        file_type = 'video'
        file_extension = '.mp4'
    
    if not file_id:
        send_message(chat_id, "⚠️ نوع فایل پشتیبانی نمی‌شود.")
        return
    
    # Generate upload ID and file path
    upload_id = generate_random_string()
    file_path = os.path.join(FILES_DIR, f"{upload_id}{file_extension}")
    
    # Download file
    if download_file(file_id, file_path):
        # Get caption if exists
        caption = message.get('caption', '')
        
        # Save upload
        save_upload(upload_id, file_type, file_path, caption=caption, admin_id=user_id)
        
        start_link = f"/start {upload_id}"
        response_text = (
            f"✅ فایل با موفقیت آپلود شد!\n\n"
            f"📁 نوع: {file_type}\n"
            f"🔗 پیوند اشتراک:\n"
            f"<code>{start_link}</code>\n\n"
            f"📋 برای کپی روی پیوند کلیک کنید."
        )
        
        set_admin_state(user_id, 'normal')
        send_message(chat_id, response_text, get_admin_keyboard())
    else:
        send_message(chat_id, "❌ خطا در دانلود فایل. دوباره تلاش کنید.")

def handle_callback_query(callback_query):
    """Handle inline keyboard callbacks"""
    query_id = callback_query['id']
    user_id = callback_query['from']['id']
    chat_id = callback_query['message']['chat']['id']
    message_id = callback_query['message']['message_id']
    data = callback_query['data']
    
    if data.startswith('like_'):
        upload_id = data.replace('like_', '')
        
        # Toggle like
        action = toggle_like(upload_id, user_id)
        
        # Get updated stats
        upload = get_upload(upload_id)
        if upload:
            views = upload[8]
            likes_count = get_likes_count(upload_id)
            user_liked = user_has_liked(upload_id, user_id)
            
            # Update keyboard
            keyboard = get_content_keyboard(upload_id, views, likes_count, user_liked)
            
            # Edit message
            params = {
                'chat_id': chat_id,
                'message_id': message_id,
                'reply_markup': json.dumps(keyboard)
            }
            send_request('editMessageReplyMarkup', params)
            
            # Answer callback
            like_text = "❤️ لایک شد!" if action == 'added' else "💔 لایک برداشته شد!"
            params = {
                'callback_query_id': query_id,
                'text': like_text,
                'show_alert': False
            }
            send_request('answerCallbackQuery', params)
    
    elif data.startswith('views_'):
        # Just show views count
        upload_id = data.replace('views_', '')
        upload = get_upload(upload_id)
        if upload:
            views = upload[8]
            params = {
                'callback_query_id': query_id,
                'text': f"👁 تعداد بازدید: {views}",
                'show_alert': True
            }
            send_request('answerCallbackQuery', params)

def process_update(update):
    """Process single update"""
    try:
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            user_id = message['from']['id']
            
            # Handle commands
            if 'text' in message and message['text'].startswith('/'):
                if message['text'].startswith('/start'):
                    args = message['text'][7:].strip() if len(message['text']) > 6 else None
                    handle_start_command(chat_id, user_id, args)
                return
            
            # Handle admin messages
            if user_id in ADMIN_IDS:
                if any(key in message for key in ['photo', 'document', 'video', 'audio', 'voice', 'video_note']):
                    handle_admin_file(chat_id, user_id, message)
                else:
                    handle_admin_message(chat_id, user_id, message)
            else:
                # Non-admin users
                send_message(chat_id, "🔒 شما دسترسی ادمین ندارید.")
        
        elif 'callback_query' in update:
            handle_callback_query(update['callback_query'])
            
    except Exception as e:
        print(f"Error processing update: {e}")

def get_updates(offset=0):
    """Get updates from Telegram"""
    params = {
        'offset': offset,
        'timeout': 30,
        'allowed_updates': ['message', 'callback_query']
    }
    return send_request('getUpdates', params)

def main():
    """Main bot loop"""
    print("🚀 Bot starting...")
    
    # Initialize database
    init_database()
    
    # Set bot commands
    commands = [
        {'command': 'start', 'description': 'شروع بات'}
    ]
    send_request('setMyCommands', {'commands': commands})
    
    print("✅ Bot started successfully!")
    print("📱 Bot is running with long polling...")
    
    offset = 0
    
    while True:
        try:
            # Get updates
            result = get_updates(offset)
            
            if result and result.get('ok'):
                updates = result.get('result', [])
                
                for update in updates:
                    # Process update in separate thread for instant response
                    threading.Thread(target=process_update, args=(update,), daemon=True).start()
                    offset = update['update_id'] + 1
            
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
