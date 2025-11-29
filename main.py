import requests
import time

BOT_TOKEN = "2124491577:UZoLny3LBu_O16iKFGB9FobkYLN9fVUyig4"
API_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"


def get_updates(offset=None):
    params = {"timeout": 60, "offset": offset}
    return requests.get(API_URL + "getUpdates", params=params).json()


def send_photo(chat_id, photo_bytes):
    files = {"photo": ("image.gif", photo_bytes)}
    requests.post(API_URL + "sendPhoto", data={"chat_id": chat_id}, files=files)


def send_message(chat_id, text):
    requests.post(API_URL + "sendMessage", data={"chat_id": chat_id, "text": text})


def fetch_waifu_image():
    res = requests.get("https://api.waifu.pics/nsfw/waifu")
    data = res.json()
    img_url = data["url"]

    # download the actual image/GIF
    img_data = requests.get(img_url).content
    return img_data


def main():
    last_update_id = None

    while True:
        updates = get_updates(last_update_id)

        if "result" in updates and len(updates["result"]) > 0:
            for update in updates["result"]:
                last_update_id = update["update_id"] + 1

                if "message" not in update:
                    continue

                msg = update["message"]
                chat_id = msg["chat"]["id"]
                text = msg.get("text", "")

                # user sent /pic
                if text == "/pic":
                    try:
                        img = fetch_waifu_image()
                        send_photo(chat_id, img)
                    except Exception as e:
                        send_message(chat_id, f"Error: {e}")


if __name__ == "__main__":
    main()
