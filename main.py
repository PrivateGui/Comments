import requests
import json
import time

# ========================
# Configuration
# ========================
TELEGRAM_BOT_TOKEN = "1787705750:DbEVgZz3exqOGj5fmSxvc9QsP_Dds7qeXZA"
GEMINI_API_KEY = "AIzaSyAwDKkp8cWNYFePpK3GHHfhbCMOTf5AWS4"

STATE_ID = 2  # Tehran
STATIONS_URL = f"https://aqms.doe.ir/Service/api/v2/Station/GetStationsByStateId/?StateId={STATE_ID}"
AQI_URL = f"https://aqms.doe.ir/Service/api/v2/AQI/Get/?StateId={STATE_ID}"
REGIONS_URL = f"https://aqms.doe.ir/Service/api/v1/Region/Get/?StateId={STATE_ID}"
LOGIN_URL = "https://aqms.doe.ir/Service/v1/login/"

HEADERS = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "content-type": "application/x-www-form-urlencoded",
    "pragma": "no-cache",
    "referer": "https://aqms.doe.ir/App/",
}

# ========================
# Bearer Token Generation
# ========================
def generate_bearer_token():
    payload = {
        "grant_type": "password",
        "username": "doeWebAppUser",
        "password": "doeW3bAppU$er"
    }
    headers = {"accept": "application/json", "content-type": "application/x-www-form-urlencoded"}
    resp = requests.post(LOGIN_URL, data=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise Exception("Failed to generate bearer token")
    return token

# ========================
# AQI Data Functions
# ========================
def fetch_json(url):
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    return resp.json()

def build_station_map(stations_data):
    mapping = {}
    for st in stations_data:
        mapping[st["stationId"]] = {
            "name_en": st.get("stationName_En"),
            "name_fa": st.get("stationName_Fa"),
            "regionId": st.get("regionId")
        }
    return mapping

def build_region_map(regions_data):
    mapping = {}
    for r in regions_data:
        mapping[r["regionId"]] = {
            "name_en": r["regionName_En"],
            "name_fa": r["regionName_Fa"]
        }
    return mapping

def enrich_aqi_data(aqi_records, station_map, region_map):
    enriched = []
    for rec in aqi_records:
        sid = rec.get("stationId")
        rid = rec.get("regionId")
        station_info = station_map.get(sid, {})
        region_info = region_map.get(rid, {})
        rec["stationName_En"] = station_info.get("name_en")
        rec["stationName_Fa"] = station_info.get("name_fa")
        rec["regionName_En"] = region_info.get("name_en")
        rec["regionName_Fa"] = region_info.get("name_fa")
        enriched.append(rec)
    return enriched

def calculate_tehran_avg_aqi(enriched_data):
    tehran_stations = [rec for rec in enriched_data if rec.get("regionId") == 2]
    aqi_values = [rec["aqi"] for rec in tehran_stations if rec.get("aqi") is not None]
    if not aqi_values:
        return None
    return sum(aqi_values) / len(aqi_values)

def get_tehran_aqi_data():
    token = generate_bearer_token()
    HEADERS["authorization"] = f"Bearer {token}"
    
    stations_data = fetch_json(STATIONS_URL)
    regions_data = fetch_json(REGIONS_URL)
    aqi_data = fetch_json(AQI_URL)
    
    station_map = build_station_map(stations_data)
    region_map = build_region_map(regions_data)
    enriched = enrich_aqi_data(aqi_data, station_map, region_map)
    
    tehran_avg = calculate_tehran_avg_aqi(enriched)
    
    return enriched, tehran_avg

# ========================
# Gemini AI Functions
# ========================
def analyze_closure_probability(avg_aqi):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent"
    
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }
    
    prompt = f"""با توجه به شاخص کیفیت هوای تهران که {avg_aqi:.1f} است، احتمال تعطیلی مدارس و ادارات را تحلیل کن.

معیارهای تعطیلی در ایران:
- شاخص 151-200 (ناسالم): احتمال تعطیلی کم
- شاخص 201-300 (ناسالم برای همه): احتمال تعطیلی متوسط تا زیاد
- شاخص بالای 300 (خطرناک): احتمال تعطیلی بسیار زیاد

لطفاً در 3-4 خط فارسی، با استفاده از ایموجی مناسب:
1. وضعیت فعلی هوا را توضیح بده
2. احتمال تعطیلی را به صورت درصد مشخص کن
3. توصیه کوتاه بده

پاسخ را مستقیم و بدون مقدمه بنویس."""

    body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=body, timeout=15)
        if response.status_code == 200:
            data = response.json()
            for candidate in data.get("candidates", []):
                content = candidate.get("content", {})
                parts = content.get("parts", [])
                text = "".join([part.get("text", "") for part in parts])
                return text.strip()
        return "❌ خطا در تحلیل احتمال تعطیلی"
    except Exception as e:
        return f"❌ خطا در ارتباط با AI: {str(e)}"

# ========================
# Telegram Bot Functions
# ========================
def send_message(chat_id, text, reply_markup=None):
    url = f"https://tapi.bale.ai/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    requests.post(url, json=payload)

def get_aqi_status_emoji(aqi):
    if aqi is None:
        return "❓"
    elif aqi <= 50:
        return "🟢"
    elif aqi <= 100:
        return "🟡"
    elif aqi <= 150:
        return "🟠"
    elif aqi <= 200:
        return "🔴"
    elif aqi <= 300:
        return "🟣"
    else:
        return "🟤"

def get_aqi_status_text(aqi):
    if aqi is None:
        return "نامشخص"
    elif aqi <= 50:
        return "سالم"
    elif aqi <= 100:
        return "قابل قبول"
    elif aqi <= 150:
        return "ناسالم برای گروه‌های حساس"
    elif aqi <= 200:
        return "ناسالم"
    elif aqi <= 300:
        return "بسیار ناسالم"
    else:
        return "خطرناک"

def format_aqi_message(enriched_data, avg_aqi):
    tehran_stations = [rec for rec in enriched_data if rec.get("regionId") == 2]
    
    message = "🌆 <b>شاخص کیفیت هوای تهران</b>\n\n"
    
    if avg_aqi:
        emoji = get_aqi_status_emoji(avg_aqi)
        status = get_aqi_status_text(avg_aqi)
        message += f"{emoji} <b>میانگین شاخص: {avg_aqi:.1f}</b>\n"
        message += f"وضعیت: {status}\n\n"
    
    message += "📍 <b>ایستگاه‌های اندازه‌گیری:</b>\n\n"
    
    for rec in tehran_stations:
        station_name = rec.get('stationName_Fa', 'نامشخص')
        aqi = rec.get('aqi')
        emoji = get_aqi_status_emoji(aqi)
        
        if aqi is not None:
            message += f"{emoji} {station_name}: <b>{aqi}</b>\n"
        else:
            message += f"❓ {station_name}: داده موجود نیست\n"
    
    message += f"\n🕐 آخرین بروزرسانی: الان"
    
    return message

def handle_start(chat_id):
    keyboard = {
        "keyboard": [
            [{"text": "📊 شاخص هوای تهران"}],
            [{"text": "🎲 احتمال تعطیلی"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    
    welcome_msg = """👋 سلام! به ربات شاخص کیفیت هوای تهران خوش آمدید

از منوی زیر یکی از گزینه‌ها را انتخاب کنید:

📊 <b>شاخص هوای تهران</b>
مشاهده شاخص کیفیت هوای تمام ایستگاه‌های تهران

🎲 <b>احتمال تعطیلی</b>
تحلیل احتمال تعطیلی مدارس و ادارات با هوش مصنوعی"""
    
    send_message(chat_id, welcome_msg, keyboard)

def handle_aqi_request(chat_id):
    send_message(chat_id, "⏳ در حال دریافت اطلاعات...")
    
    try:
        enriched_data, avg_aqi = get_tehran_aqi_data()
        message = format_aqi_message(enriched_data, avg_aqi)
        send_message(chat_id, message)
    except Exception as e:
        send_message(chat_id, f"❌ خطا در دریافت اطلاعات: {str(e)}")

def handle_closure_request(chat_id):
    send_message(chat_id, "🤖 در حال تحلیل احتمال تعطیلی با هوش مصنوعی...")
    
    try:
        enriched_data, avg_aqi = get_tehran_aqi_data()
        
        if avg_aqi is None:
            send_message(chat_id, "❌ داده‌های کیفیت هوا در دسترس نیست")
            return
        
        emoji = get_aqi_status_emoji(avg_aqi)
        status = get_aqi_status_text(avg_aqi)
        
        analysis = analyze_closure_probability(avg_aqi)
        
        message = f"""🎲 <b>تحلیل احتمال تعطیلی</b>

{emoji} <b>شاخص فعلی تهران: {avg_aqi:.1f}</b>
وضعیت: {status}

━━━━━━━━━━━━━━━━

🤖 <b>تحلیل هوش مصنوعی:</b>

{analysis}

━━━━━━━━━━━━━━━━

💡 این تحلیل بر اساس داده‌های آلودگی هوا و سوابق تعطیلی‌های گذشته انجام شده است."""
        
        send_message(chat_id, message)
    except Exception as e:
        send_message(chat_id, f"❌ خطا در تحلیل: {str(e)}")

def process_update(update):
    try:
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        
        if not chat_id:
            return
        
        if text == "/start":
            handle_start(chat_id)
        elif text == "📊 شاخص هوای تهران":
            handle_aqi_request(chat_id)
        elif text == "🎲 احتمال تعطیلی":
            handle_closure_request(chat_id)
        else:
            send_message(chat_id, "لطفاً از منوی زیر یکی از گزینه‌ها را انتخاب کنید.")
    except Exception as e:
        print(f"Error processing update: {e}")

def run_bot():
    print("🤖 Bot started...")
    offset = 0
    
    while True:
        try:
            url = f"https://tapi.bale.ai/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {"offset": offset, "timeout": 30}
            response = requests.get(url, params=params, timeout=35)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    updates = data.get("result", [])
                    for update in updates:
                        process_update(update)
                        offset = update["update_id"] + 1
            else:
                print(f"Error: {response.status_code}")
                time.sleep(5)
                
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
