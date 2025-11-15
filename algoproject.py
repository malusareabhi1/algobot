import streamlit as st
from streamlit_option_menu import option_menu
from datetime import datetime
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
#from utils import generate_mock_data
import random
import requests
from kiteconnect import KiteConnect
import time
import threading
#import datetime
from datetime import datetime, timedelta
import os
import pytz  # ✅ Add this for details ssfsdfsdf 
from streamlit_autorefresh import st_autorefresh
from math import floor
from dotenv import load_dotenv
import numpy as np
import matplotlib.pyplot as plt
from ta.momentum import RSIIndicator


# Global kite object placeholder
if 'kite' not in st.session_state:
    st.session_state.kite = None
# Page configuration
st.set_page_config(layout="wide", page_title="Trade Strategy Dashboard")
    
# Sidebar navigation
with st.sidebar:
    selected = option_menu(
    menu_title="ALGO BOT  ",
    options=[
        "Dashboard",  "KITE API", "Live Algo Trading","Paper Trade","Volatility Scanner","Telegram Demo","NIFTY PCR","3PM OPTION","NIFTY OI,PCR,D "
    ],
    icons=[
        "bar-chart", "search", "cpu", "cpu","cpu", "cpu","cpu","cpu","cpu","cpu", "arrow-repeat",
        
    ],
    menu_icon="cast",
    default_index=0,
)   

# Main area rendering
st.markdown("""
    <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .card {
            background-color: white;
            border-radius: 15px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.05);
            padding: 20px;
            margin: 10px 0;
        }
        .card-title {
            font-size: 18px;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)
