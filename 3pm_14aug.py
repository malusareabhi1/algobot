from kiteconnect import KiteConnect
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import streamlit as st
load_dotenv()

KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")
NIFTY_TOKEN = 256265  # Nifty 50 spot

kite = KiteConnect(api_key=KITE_API_KEY)
kite.set_access_token(KITE_ACCESS_TOKEN)

to_date = datetime.now()
from_date = to_date - timedelta(days=1)

try:
    data = kite.historical_data(NIFTY_TOKEN, from_date, to_date, interval="15minute")
    df = pd.DataFrame(data)
    st.write(df.head())
except Exception as e:
     st.write("Error fetching historical data:", e)
