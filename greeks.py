from zerodha_emergency import emergency_exit_fno
import time
import base64
import json
#from datetime import datetime, time, timedelta
from datetime import date,time, datetime, timedelta
#from datetime import datetime, timedelta
from typing import Dict
import pytz
#import math
from dateutil import parser
import os   # <-- ADD THIS
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import requests
import yfinance as yf
from streamlit_autorefresh import st_autorefresh
import re
import math 
from kiteconnect.exceptions import PermissionException, TokenException
from dotenv import load_dotenv    
from math import log, sqrt, exp
from scipy.stats import norm
from config import QTY_PER_LOT
from config import NIFTY_TOKEN

def send_telegram_signal(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    r = requests.post(url, data=payload, timeout=5)
    return r.json()
    
def send_greeks_to_telegram(greeks_param_df):
    msg = df_to_telegram_table(
        greeks_param_df,
        title="GREEKS VALUES"
    )
    send_telegram_signal(msg)



# greeks.py


def df_to_telegram_table(df, title):
    header = "| {:<14} | {:<12} | {:<18} | {:<6} |".format(
        "PARAMETER", "VALUE", "RANGE", "RESULT"
    )
    separator = "|" + "-"*16 + "|" + "-"*14 + "|" + "-"*20 + "|" + "-"*8 + "|"

    rows = []
    for _, row in df.iterrows():
        rows.append(
            "| {:<14} | {:<12} | {:<18} | {:<6} |".format(
                str(row["Parameter"])[:14],
                str(row["Value"])[:12],
                str(row["Range"])[:18],
                str(row["Result"])[:6]
            )
        )

    table = "\n".join([header, separator] + rows)

    return f"""
🧮 *{title}*




