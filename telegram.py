import os
import requests
import streamlit as st
from dotenv import load_dotenv

# LOAD .env FILE
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

st.write("BOT_TOKEN:", BOT_TOKEN)
st.write("CHAT_ID:", CHAT_ID)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        json={"chat_id": CHAT_ID, "text": message},
        timeout=10
    )
    return response

if st.button("Send Test Message"):
    resp = send_telegram_message("Secure Telegram test 🚀")

    st.write("Status Code:", resp.status_code)
    st.write("Response:", resp.text)
