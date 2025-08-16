import requests
import time
import datetime
from persiantools.jdatetime import JalaliDateTime

# === CONFIG ===
BOT_TOKEN = "1782025704:FqXmSfs6Rn82c65UIxWFH81J2i4m9gluqq6K6hCw"
API_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"
WHITELIST = [844843541, 443595656]  # فقط آیدی عددی ادمین‌ها
REQUESTS_API = "https://mjvmwuifdbhahgomffvd.supabase.co/functions/v1/get-admin-requests"
BOT_USERNAME = "tgzsystembot"  # نام کاربری ربات (بدون @)

# حافظه درخواست‌ها
known_requests = set()

# === FUNCTIONS ===
def get_updates(offset=None):
    params = {"timeout": 30, "offset": offset}
    try:
        resp = requests.get(f"{API_URL}/getUpdates", params=params, timeout=40)
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"result": []}
    except Exception as e:
        print("❌ get_updates error:", e)
        return {"result": []}

def send_message(chat_id, text, reply_markup=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        requests.post(f"{API_URL}/sendMessage", json=data, timeout=20)
    except Exception as e:
        print("❌ send_message error:", e)

def get_admin_requests():
    try:
        res = requests.get(REQUESTS_API, timeout=10)
        return res.json().get("data", [])
    except Exception as e:
        print("❌ get_admin_requests error:", e)
        return []

def to_persian_digits(text: str) -> str:
    persian_map = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return str(text).translate(persian_map)

def format_datetime(iso_time: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        jalali = JalaliDateTime.to_jalali(dt)
        return to_persian_digits(jalali.strftime("%Y/%m/%d ⏰ %H:%M"))
    except:
        return "⏰ نامشخص"

def format_request(r):
    status_map = {
        "approved": "✅ تایید شده",
        "rejected": "❌ رد شده"
    }
    status = status_map.get(r.get("status"), "⏳ در انتظار")

    msg = (
        f"*👤 نام:* {r.get('full_name')}\n"
        f"*🔗 یوزرنیم:* {r.get('username')}\n"
        f"*📞 تلفن:* {to_persian_digits(r.get('phone'))}\n"
        f"*📧 ایمیل:* {r.get('email')}\n"
        f"*📝 دلیل:* {r.get('reason')}\n"
        f"*وضعیت:* {status}\n"
        f"*⏰ ایجاد:* {format_datetime(r.get('created_at'))}\n"
        f"*🔄 آخرین تغییر:* {format_datetime(r.get('updated_at'))}\n"
        f"[/start](https://ble.ir/{BOT_USERNAME}?start={r.get('id')})"
    )
    return msg

# === KEYBOARD ===
MAIN_KEYBOARD = {
    "keyboard": [
        ["📋 درخواست ها"],
        ["ℹ️ راهنما", "🚪 خروج"]
    ],
    "resize_keyboard": True
}

# === BACKGROUND CHECKER ===
def check_new_requests():
    global known_requests
    reqs = get_admin_requests()
    new_found = []
    for r in reqs:
        if r["id"] not in known_requests:
            known_requests.add(r["id"])
            new_found.append(r)
    return new_found

# === MAIN LOOP ===
def main():
    print("🤖 Bot is running...")
    offset = None

    # پر کردن known_requests برای جلوگیری از اسپم اولیه
    for r in get_admin_requests():
        known_requests.add(r["id"])

    while True:
        # --- Telegram updates ---
        updates = get_updates(offset)

        if "result" in updates:
            for update in updates["result"]:
                offset = update["update_id"] + 1

                if "message" in update:
                    chat_id = update["message"]["chat"]["id"]
                    user_id = update["message"]["from"]["id"]
                    text = update["message"].get("text", "")

                    if user_id not in WHITELIST:
                        send_message(chat_id, "🚫 شما دسترسی ندارید.")
                        continue

                    # شروع
                    if text.startswith("/start"):
                        args = text.split()
                        if len(args) > 1:  # /start <id>
                            req_id = args[1]
                            all_reqs = get_admin_requests()
                            for r in all_reqs:
                                if r["id"] == req_id:
                                    send_message(chat_id, format_request(r))
                                    break
                        else:
                            send_message(chat_id, "سلام ادمین عزیز ✨\nبه پنل مدیریت خوش آمدید 🌹",
                                         reply_markup=MAIN_KEYBOARD)

                    elif text == "📋 درخواست ها":
                        reqs = get_admin_requests()
                        if not reqs:
                            send_message(chat_id, "📭 هیچ درخواستی وجود ندارد.")
                        else:
                            for r in reqs:
                                send_message(chat_id, format_request(r))

                    elif text == "ℹ️ راهنما":
                        send_message(chat_id, "📖 راهنما:\n- درخواست‌ها در بخش «📋 درخواست ها» نمایش داده می‌شوند.\n- درخواست‌های جدید به صورت خودکار اطلاع‌رسانی می‌شوند.")

                    elif text == "🚪 خروج":
                        send_message(chat_id, "👋 خداحافظ! برای بازگشت دوباره /start بزنید.")

        # --- Background new request check ---
        new_reqs = check_new_requests()
        if new_reqs:
            for admin_id in WHITELIST:
                for r in new_reqs:
                    send_message(admin_id, f"🆕 درخواست جدید دریافت شد!\n\n{format_request(r)}")

        time.sleep(2)

if __name__ == "__main__":
    main()
