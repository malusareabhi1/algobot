import os
import requests
import streamlit as st
from dotenv import load_dotenv

# LOAD .env FILE
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
#CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CHAT_ID=-1003574666083

st.write("BOT_TOKEN:", BOT_TOKEN)
st.write("CHAT_ID:", CHAT_ID)



def send_telegram_alert(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    r = requests.post(url, json=payload, timeout=10)
    return r.status_code == 200

if st.button("Send Test Message"):
    resp = send_telegram_alert("Secure Telegram test 🚀")

    st.write("Status Code:", resp.status_code)
    st.write("Response:", resp.text)
