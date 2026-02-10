from telegram.ext import Updater, CommandHandler
import threading


from dotenv import load_dotenv  # pip install python-dotenv
import os

load_dotenv()  # this will read your .env and put values into os.environ[web:22][web:23]

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

algo_running = False
algo_thread = None

# ---------------- ALGO FUNCTION ----------------
def run_algo():
    global algo_running
    algo_running = True
    while algo_running:
        print("Algo Running...")
        # इथे तुमचा trading logic call करा
        time.sleep(5)

# ---------------- COMMANDS ----------------

def start_algo(update, context):
    global algo_thread, algo_running
    if not algo_running:
        algo_thread = threading.Thread(target=run_algo)
        algo_thread.start()
        update.message.reply_text("✅ Algo Started")
    else:
        update.message.reply_text("⚠ Algo Already Running")

def stop_algo(update, context):
    global algo_running
    algo_running = False
    update.message.reply_text("🛑 Algo Stopped")

def status(update, context):
    if algo_running:
        update.message.reply_text("🟢 Algo is RUNNING")
    else:
        update.message.reply_text("🔴 Algo is STOPPED")

# ---------------- MAIN ----------------

updater = Updater(BOT_TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start_algo", start_algo))
dp.add_handler(CommandHandler("stop_algo", stop_algo))
dp.add_handler(CommandHandler("status", status))

updater.start_polling()
updater.idle()
