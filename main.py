import requests
import time
import os
import urllib.parse
import mimetypes

BOT_TOKEN = "2124491577:UZoLny3LBu_O16iKFGB9FobkYLN9fVUyig4"
API_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def get_updates(offset=None):
    params = {"timeout": 60, "offset": offset}
    try:
        r = requests.get(API_URL + "getUpdates", params=params, timeout=70)
        return r.json()
    except Exception:
        return {}


def send_photo(chat_id, photo_bytes, filename="image.jpg", content_type=None):
    # If requests needs a content type, supply it as the third item in the tuple
    file_tuple = (filename, photo_bytes) if not content_type else (filename, photo_bytes, content_type)
    files = {"photo": file_tuple}
    try:
        requests.post(API_URL + "sendPhoto", data={"chat_id": chat_id}, files=files, timeout=30)
    except Exception as e:
        print("send_photo error:", e)


def send_message(chat_id, text):
    try:
        requests.post(API_URL + "sendMessage", data={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception as e:
        print("send_message error:", e)


def _guess_ext_from_url(url):
    path = urllib.parse.urlparse(url).path
    root, ext = os.path.splitext(path)
    if ext:
        return ext.lower()
    # fallback to common default
    return ""


def _guess_content_type_from_ext(ext):
    if not ext:
        return None
    ct, _ = mimetypes.guess_type("file" + ext)
    return ct


def fetch_waifu_image():
    # get the waifu image URL
    res = requests.get("https://api.waifu.pics/nsfw/waifu", timeout=15)
    res.raise_for_status()
    data = res.json()
    img_url = data.get("url")
    if not img_url:
        raise ValueError("No image url in response")

    # download the actual image/GIF
    img_resp = requests.get(img_url, timeout=30)
    img_resp.raise_for_status()
    img_bytes = img_resp.content

    # determine filename/extension
    ext = _guess_ext_from_url(img_url)
    if not ext:
        # try content-type header
        ct = img_resp.headers.get("Content-Type", "")
        ext = mimetypes.guess_extension(ct.split(";")[0].strip() or "") or ""
    if not ext:
        ext = ".jpg"  # final fallback

    filename = os.path.basename(urllib.parse.urlparse(img_url).path) or f"waifu{ext}"
    # sanitize filename
    filename = filename.split("?")[0]
    if not os.path.splitext(filename)[1]:
        filename = filename + ext

    content_type = _guess_content_type_from_ext(ext) or img_resp.headers.get("Content-Type")

    return img_bytes, filename, content_type


def save_image_locally(img_bytes, filename):
    path = os.path.join(DOWNLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(img_bytes)
    return path


def main():
    last_update_id = None

    while True:
        updates = get_updates(last_update_id)

        if not updates:
            time.sleep(0.5)
            continue

        results = updates.get("result", [])
        if results:
            for update in results:
                # update_id handling for offset
                update_id = update.get("update_id")
                if update_id is not None:
                    last_update_id = update_id + 1

                if "message" not in update:
                    continue

                msg = update["message"]
                chat_id = msg["chat"]["id"]
                text = msg.get("text", "")

                if text == "/pic":
                    try:
                        img_bytes, filename, content_type = fetch_waifu_image()
                        # save locally
                        saved_path = save_image_locally(img_bytes, filename)
                        print("Saved image to:", saved_path)

                        # send to user
                        send_photo(chat_id, img_bytes, filename=filename, content_type=content_type)

                        # optional: notify user
                        send_message(chat_id, f"Saved and sent: {filename}")
                    except Exception as e:
                        print("Error while handling /pic:", e)
                        send_message(chat_id, f"Error: {e}")

        # small sleep to avoid hammering
        time.sleep(0.5)


if __name__ == "__main__":
    main()
