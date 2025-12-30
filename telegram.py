import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    return requests.post(url, json={"chat_id": CHAT_ID, "text": message})

send_telegram_message("Secure Telegram test 🚀")
