import requests
import json
import time
import random
import string
import os
import mysql.connector
from mysql.connector import Error
import threading
from datetime import datetime

# Bot configuration
BOT_TOKEN = "812616487:PcCYPrqiWmEmfVpPWaWWzxNtvIhjoOSNrK7yFLAX"
API_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"

# Admin user IDs (replace with actual admin user IDs)
ADMIN_IDS = [844843541]  # Add your admin user IDs here

# Database configuration
DB_CONFIG = {
    'host': 'cests',
    'port': 3306,
    'user': 'root',
    'password': 'flTurEdlcHlTcvZ9xYVsGdBY',
    'database': 'gallant_yonath'
}

class TelegramBot:
    def __init__(self):
        self.offset = 0
        self.user_states = {}
        self.init_database()
        
    def init_database(self):
        """Initialize database tables"""
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # Create files table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS files (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    file_id VARCHAR(255),
                    file_type VARCHAR(50),
                    file_name VARCHAR(255),
                    file_path VARCHAR(500),
                    link_code VARCHAR(100) UNIQUE,
                    content TEXT,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    views INT DEFAULT 0
                )
            ''')
            
            # Create likes table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS likes (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT,
                    link_code VARCHAR(100),
                    like_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_like (user_id, link_code)
                )
            ''')
            
            # Create broadcast messages table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS broadcast_queue (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    message_type VARCHAR(50),
                    content TEXT,
                    file_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent BOOLEAN DEFAULT FALSE
                )
            ''')
            
            conn.commit()
            conn.close()
            print("✅ دیتابیس با موفقیت راه‌اندازی شد")
            
        except Error as e:
            print(f"❌ خطا در راه‌اندازی دیتابیس: {e}")
    
    def generate_random_code(self, length=12):
        """Generate random string for links"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    def get_db_connection(self):
        """Get database connection"""
        return mysql.connector.connect(**DB_CONFIG)
    
    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        """Send message to user"""
        data = {
            'chat_id': chat_id,
            'text': text
        }
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
        if parse_mode:
            data['parse_mode'] = parse_mode
            
        requests.post(API_URL + "sendMessage", data=data)
    
    def send_document(self, chat_id, file_path, caption=None, reply_markup=None):
        """Send document to user"""
        try:
            with open(file_path, 'rb') as file:
                files = {'document': file}
                data = {'chat_id': chat_id}
                if caption:
                    data['caption'] = caption
                if reply_markup:
                    data['reply_markup'] = json.dumps(reply_markup)
                    
                requests.post(API_URL + "sendDocument", files=files, data=data)
        except Exception as e:
            self.send_message(chat_id, f"❌ خطا در ارسال فایل: {str(e)}")
    
    def send_photo_by_id(self, chat_id, file_id, caption=None, reply_markup=None):
        """Send photo by file_id"""
        try:
            data = {
                'chat_id': chat_id,
                'photo': file_id
            }
            if caption:
                data['caption'] = caption
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
                
            requests.post(API_URL + "sendPhoto", data=data)
        except Exception as e:
            print(f"خطا در ارسال عکس با file_id: {e}")
            self.send_message(chat_id, f"❌ خطا در ارسال عکس: {str(e)}")
    
    def send_document_by_id(self, chat_id, file_id, caption=None, reply_markup=None):
        """Send document by file_id"""
        try:
            data = {
                'chat_id': chat_id,
                'document': file_id
            }
            if caption:
                data['caption'] = caption
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
                
            requests.post(API_URL + "sendDocument", data=data)
        except Exception as e:
            print(f"خطا در ارسال فایل با file_id: {e}")
            self.send_message(chat_id, f"❌ خطا در ارسال فایل: {str(e)}")
    
        """Send photo to user"""
        try:
            with open(file_path, 'rb') as file:
                files = {'photo': file}
                data = {'chat_id': chat_id}
                if caption:
                    data['caption'] = caption
                if reply_markup:
                    data['reply_markup'] = json.dumps(reply_markup)
                    
                requests.post(API_URL + "sendPhoto", files=files, data=data)
        except Exception as e:
            self.send_message(chat_id, f"❌ خطا در ارسال عکس: {str(e)}")
    
    def download_file(self, file_id):
        """Download file from Telegram"""
        try:
            # Get file info
            response = requests.get(API_URL + f"getFile?file_id={file_id}")
            file_info = response.json()
            
            if file_info['ok']:
                file_path = file_info['result']['file_path']
                file_url = f"https://tapi.bale.ai/file/bot{BOT_TOKEN}/{file_path}"
                
                # Download file
                file_response = requests.get(file_url)
                
                if file_response.status_code == 200:
                    # Save to tmp directory
                    filename = file_path.split('/')[-1]
                    # Add timestamp to avoid conflicts
                    timestamp = str(int(time.time()))
                    local_path = f"/tmp/{timestamp}_{filename}"
                    
                    # Create tmp directory if it doesn't exist
                    os.makedirs("/tmp", exist_ok=True)
                    
                    with open(local_path, 'wb') as f:
                        f.write(file_response.content)
                    
                    return local_path
                else:
                    print(f"خطا در دانلود فایل: HTTP {file_response.status_code}")
                    return None
            else:
                print(f"خطا در دریافت اطلاعات فایل: {file_info}")
                return None
                
        except Exception as e:
            print(f"خطا در دانلود فایل: {e}")
            return None
    
    def get_admin_keyboard(self):
        """Get admin reply keyboard"""
        return {
            'keyboard': [
                ['📤 آپلود فایل', '📝 آپلود متن'],
                ['📢 ارسال پیام همگانی', '📊 آمار'],
                ['❌ لغو']
            ],
            'resize_keyboard': True,
            'one_time_keyboard': False
        }
    
    def get_file_stats_keyboard(self, link_code, user_id):
        """Get inline keyboard for file stats"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Get views count
        cursor.execute("SELECT views FROM files WHERE link_code = %s", (link_code,))
        views_result = cursor.fetchone()
        views = views_result[0] if views_result else 0
        
        # Get likes count
        cursor.execute("SELECT COUNT(*) FROM likes WHERE link_code = %s", (link_code,))
        likes_result = cursor.fetchone()
        likes_count = likes_result[0] if likes_result else 0
        
        # Check if user already liked
        cursor.execute("SELECT 1 FROM likes WHERE user_id = %s AND link_code = %s", (user_id, link_code))
        user_liked = cursor.fetchone() is not None
        
        conn.close()
        
        like_text = "❤️ لایک شده" if user_liked else "🤍 لایک"
        
        return {
            'inline_keyboard': [
                [
                    {'text': f'👁 {views} بازدید', 'callback_data': f'stats_{link_code}'},
                    {'text': f'{like_text} ({likes_count})', 'callback_data': f'like_{link_code}'}
                ]
            ]
        }
    
    def handle_start_command(self, chat_id, user_id, text):
        """Handle /start command"""
        parts = text.split(' ')
        
        if len(parts) > 1:
            # Start with link code
            link_code = parts[1]
            self.handle_file_request(chat_id, user_id, link_code)
        else:
            # Regular start
            if user_id in ADMIN_IDS:
                self.send_message(
                    chat_id,
                    "👋 سلام ادمین عزیز!\n\n"
                    "از منوی زیر انتخاب کنید:",
                    reply_markup=self.get_admin_keyboard()
                )
            else:
                self.send_message(
                    chat_id,
                    "👋 سلام و خوش آمدید!\n\n"
                    "این ربات برای به اشتراک گذاری فایل‌ها طراحی شده است.\n"
                    "لینک مخصوص خود را از ادمین دریافت کنید. 😊"
                )
    
    def handle_file_request(self, chat_id, user_id, link_code):
        """Handle file request with link code"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get file info
            cursor.execute("SELECT id, file_id, file_type, file_name, file_path, link_code, content, upload_date, views FROM files WHERE link_code = %s", (link_code,))
            file_info = cursor.fetchone()
            
            if file_info:
                # Update view count
                cursor.execute("UPDATE files SET views = views + 1 WHERE link_code = %s", (link_code,))
                conn.commit()
                
                file_id = file_info[1]
                file_type = file_info[2]
                file_name = file_info[3]
                file_path = file_info[4]
                content = file_info[6]
                
                # Get stats keyboard
                keyboard = self.get_file_stats_keyboard(link_code, user_id)
                
                if file_type == 'text':
                    # Send text content
                    self.send_message(chat_id, content, reply_markup=keyboard)
                elif file_type in ['photo', 'image']:
                    # Send photo
                    if file_path and os.path.exists(file_path):
                        self.send_photo(chat_id, file_path, reply_markup=keyboard)
                    else:
                        # Fallback: send via file_id
                        self.send_photo_by_id(chat_id, file_id, reply_markup=keyboard)
                else:
                    # Send document
                    if file_path and os.path.exists(file_path):
                        self.send_document(chat_id, file_path, reply_markup=keyboard)
                    else:
                        # Fallback: send via file_id
                        self.send_document_by_id(chat_id, file_id, reply_markup=keyboard)
            else:
                self.send_message(chat_id, "❌ فایل مورد نظر یافت نشد!")
            
            conn.close()
            
        except Exception as e:
            print(f"خطا در handle_file_request: {e}")
            self.send_message(chat_id, f"❌ خطا در دریافت فایل: {str(e)}")
    
    def handle_callback_query(self, callback_query):
        """Handle inline keyboard callbacks"""
        query_id = callback_query['id']
        user_id = callback_query['from']['id']
        chat_id = callback_query['message']['chat']['id']
        data = callback_query['data']
        
        if data.startswith('like_'):
            link_code = data.replace('like_', '')
            
            try:
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                # Check if user already liked
                cursor.execute("SELECT 1 FROM likes WHERE user_id = %s AND link_code = %s", (user_id, link_code))
                
                if cursor.fetchone():
                    # Remove like
                    cursor.execute("DELETE FROM likes WHERE user_id = %s AND link_code = %s", (user_id, link_code))
                    response_text = "💔 لایک حذف شد"
                else:
                    # Add like
                    cursor.execute("INSERT INTO likes (user_id, link_code) VALUES (%s, %s)", (user_id, link_code))
                    response_text = "❤️ لایک شد!"
                
                conn.commit()
                conn.close()
                
                # Update keyboard
                new_keyboard = self.get_file_stats_keyboard(link_code, user_id)
                
                # Edit message markup
                requests.post(API_URL + "editMessageReplyMarkup", data={
                    'chat_id': chat_id,
                    'message_id': callback_query['message']['message_id'],
                    'reply_markup': json.dumps(new_keyboard)
                })
                
                # Answer callback query
                requests.post(API_URL + "answerCallbackQuery", data={
                    'callback_query_id': query_id,
                    'text': response_text
                })
                
            except Exception as e:
                requests.post(API_URL + "answerCallbackQuery", data={
                    'callback_query_id': query_id,
                    'text': f"❌ خطا: {str(e)}"
                })
    
    def handle_file_upload(self, chat_id, message):
        """Handle file upload from admin"""
        try:
            file_id = None
            file_type = None
            file_name = None
            
            if 'document' in message:
                file_id = message['document']['file_id']
                file_type = 'document'
                file_name = message['document'].get('file_name', 'document')
            elif 'photo' in message:
                file_id = message['photo'][-1]['file_id']  # Get highest quality
                file_type = 'photo'
                file_name = 'photo.jpg'
            elif 'video' in message:
                file_id = message['video']['file_id']
                file_type = 'video'
                file_name = 'video.mp4'
            elif 'audio' in message:
                file_id = message['audio']['file_id']
                file_type = 'audio'
                file_name = 'audio.mp3'
            
            if file_id:
                # Download file
                file_path = self.download_file(file_id)
                
                if file_path:
                    # Generate link code
                    link_code = self.generate_random_code()
                    
                    # Save to database
                    conn = self.get_db_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO files (file_id, file_type, file_name, file_path, link_code)
                        VALUES (%s, %s, %s, %s, %s)
                    ''', (file_id, file_type, file_name, file_path, link_code))
                    
                    conn.commit()
                    conn.close()
                    
                    # Send link to admin
                    share_link = f"/start {link_code}"
                    self.send_message(
                        chat_id,
                        f"✅ فایل با موفقیت آپلود شد!\n\n"
                        f"📎 نام فایل: {file_name}\n"
                        f"🔗 لینک اشتراک‌گذاری:\n"
                        f"`{share_link}`\n\n"
                        f"این لینک را برای کاربران ارسال کنید.",
                        parse_mode='Markdown'
                    )
                    
                    # Reset user state
                    self.user_states[chat_id] = None
                else:
                    self.send_message(chat_id, "❌ خطا در دانلود فایل!")
            
        except Exception as e:
            self.send_message(chat_id, f"❌ خطا در آپلود فایل: {str(e)}")
    
    def handle_text_upload(self, chat_id, text):
        """Handle text upload from admin"""
        try:
            # Generate link code
            link_code = self.generate_random_code()
            
            # Save to database
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO files (file_type, content, link_code)
                VALUES (%s, %s, %s)
            ''', ('text', text, link_code))
            
            conn.commit()
            conn.close()
            
            # Send link to admin
            share_link = f"/start {link_code}"
            self.send_message(
                chat_id,
                f"✅ متن با موفقیت آپلود شد!\n\n"
                f"📝 محتوا: {text[:50]}{'...' if len(text) > 50 else ''}\n"
                f"🔗 لینک اشتراک‌گذاری:\n"
                f"`{share_link}`\n\n"
                f"این لینک را برای کاربران ارسال کنید.",
                parse_mode='Markdown'
            )
            
            # Reset user state
            self.user_states[chat_id] = None
            
        except Exception as e:
            self.send_message(chat_id, f"❌ خطا در آپلود متن: {str(e)}")
    
    def handle_broadcast_message(self, chat_id, message):
        """Handle broadcast message from admin"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Save broadcast message to queue
            if 'text' in message:
                cursor.execute('''
                    INSERT INTO broadcast_queue (message_type, content)
                    VALUES (%s, %s)
                ''', ('text', message['text']))
            elif 'document' in message:
                file_id = message['document']['file_id']
                cursor.execute('''
                    INSERT INTO broadcast_queue (message_type, file_id)
                    VALUES (%s, %s)
                ''', ('document', file_id))
            elif 'photo' in message:
                file_id = message['photo'][-1]['file_id']
                cursor.execute('''
                    INSERT INTO broadcast_queue (message_type, file_id)
                    VALUES (%s, %s)
                ''', ('photo', file_id))
            
            conn.commit()
            conn.close()
            
            self.send_message(chat_id, "✅ پیام برای ارسال همگانی ذخیره شد!")
            self.user_states[chat_id] = None
            
        except Exception as e:
            self.send_message(chat_id, f"❌ خطا در ذخیره پیام: {str(e)}")
    
    def get_stats(self, chat_id):
        """Get bot statistics"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get total files
            cursor.execute("SELECT COUNT(*) FROM files")
            total_files = cursor.fetchone()[0]
            
            # Get total views
            cursor.execute("SELECT SUM(views) FROM files")
            total_views = cursor.fetchone()[0] or 0
            
            # Get total likes
            cursor.execute("SELECT COUNT(*) FROM likes")
            total_likes = cursor.fetchone()[0]
            
            # Get most viewed file
            cursor.execute("SELECT file_name, views FROM files ORDER BY views DESC LIMIT 1")
            most_viewed = cursor.fetchone()
            
            conn.close()
            
            stats_text = f"📊 آمار ربات:\n\n"
            stats_text += f"📁 تعداد کل فایل‌ها: {total_files}\n"
            stats_text += f"👁 تعداد کل بازدیدها: {total_views}\n"
            stats_text += f"❤️ تعداد کل لایک‌ها: {total_likes}\n"
            
            if most_viewed:
                stats_text += f"\n🏆 پربازدیدترین فایل:\n"
                stats_text += f"📎 {most_viewed[0] or 'متن'} - {most_viewed[1]} بازدید"
            
            self.send_message(chat_id, stats_text)
            
        except Exception as e:
            self.send_message(chat_id, f"❌ خطا در دریافت آمار: {str(e)}")
    
    def handle_message(self, message):
        """Handle incoming messages"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        
        # Handle callback queries
        if 'callback_query' in message:
            self.handle_callback_query(message['callback_query'])
            return
        
        # Handle text messages
        if 'text' in message:
            text = message['text']
            
            # Handle commands
            if text.startswith('/start'):
                self.handle_start_command(chat_id, user_id, text)
                return
            
            # Handle admin messages
            if user_id in ADMIN_IDS:
                current_state = self.user_states.get(chat_id)
                
                if current_state == 'uploading_file':
                    self.send_message(chat_id, "📤 لطفاً فایل خود را ارسال کنید:")
                    return
                elif current_state == 'uploading_text':
                    self.handle_text_upload(chat_id, text)
                    return
                elif current_state == 'broadcasting':
                    self.handle_broadcast_message(chat_id, message)
                    return
                
                # Handle admin menu
                if text == '📤 آپلود فایل':
                    self.user_states[chat_id] = 'uploading_file'
                    self.send_message(chat_id, "📤 لطفاً فایل خود را ارسال کنید:")
                elif text == '📝 آپلود متن':
                    self.user_states[chat_id] = 'uploading_text'
                    self.send_message(chat_id, "📝 لطفاً متن خود را ارسال کنید:")
                elif text == '📢 ارسال پیام همگانی':
                    self.user_states[chat_id] = 'broadcasting'
                    self.send_message(chat_id, "📢 پیام خود را برای ارسال همگانی بنویسید:")
                elif text == '📊 آمار':
                    self.get_stats(chat_id)
                elif text == '❌ لغو':
                    self.user_states[chat_id] = None
                    self.send_message(chat_id, "❌ عملیات لغو شد.", reply_markup=self.get_admin_keyboard())
                else:
                    self.send_message(chat_id, "لطفاً از منوی زیر انتخاب کنید:", reply_markup=self.get_admin_keyboard())
            else:
                self.send_message(chat_id, "متوجه نشدم! لطفاً از لینک مخصوص استفاده کنید.")
        
        # Handle file uploads from admins
        elif user_id in ADMIN_IDS and self.user_states.get(chat_id) == 'uploading_file':
            self.handle_file_upload(chat_id, message)
        
        # Handle broadcast messages from admins
        elif user_id in ADMIN_IDS and self.user_states.get(chat_id) == 'broadcasting':
            self.handle_broadcast_message(chat_id, message)
    
    def get_updates(self):
        """Get updates from Telegram"""
        try:
            response = requests.get(f"{API_URL}getUpdates?offset={self.offset}&timeout=30")
            if response.status_code == 200:
                data = response.json()
                if data['ok']:
                    return data['result']
            return []
        except Exception as e:
            print(f"خطا در دریافت آپدیت‌ها: {e}")
            return []
    
    def run(self):
        """Main bot loop"""
        print("🤖 ربات شروع به کار کرد...")
        
        while True:
            try:
                updates = self.get_updates()
                
                for update in updates:
                    self.offset = update['update_id'] + 1
                    
                    if 'message' in update:
                        self.handle_message(update['message'])
                    elif 'callback_query' in update:
                        self.handle_callback_query(update['callback_query'])
                
            except Exception as e:
                print(f"خطا در حلقه اصلی: {e}")
                time.sleep(1)

if __name__ == "__main__":
    # Replace with your actual bot token
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ لطفاً توکن ربات را در BOT_TOKEN وارد کنید")
        exit(1)
    
    # Replace with actual admin user IDs
    if ADMIN_IDS == [123456789, 987654321]:
        print("⚠️ لطفاً آیدی ادمین‌ها را در ADMIN_IDS وارد کنید")
    
    bot = TelegramBot()
    bot.run()
