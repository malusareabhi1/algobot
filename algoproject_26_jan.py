#upadtaed 26 jan
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

# Auto-refresh every 30 seconds
# Market hours condition
#import pytz
# Define IST timezone FIRST
ist = pytz.timezone("Asia/Kolkata")
start = time(9, 15)   # 9:30 AM
end = time(15, 0)    # 3:25 PM
now = datetime.now(ist).time()    
# Refresh only between 9:30–3:25
if start <= now <= end:
     st_autorefresh(interval=30000, key="refresh")  # 1 minute refresh
#else:
    #st.info("Auto-refresh is paused — Outside market hours (9:30 AM to 3:25 PM).")

if "paper_trades" not in st.session_state:
    st.session_state["paper_trades"] = []

if "last_executed_signal_time" not in st.session_state:
    st.session_state.last_executed_signal_time = None

if "trades_signals" not in st.session_state:
                   st.session_state.trades_signals = [] 

if "last_option_entry_price" not in st.session_state:
    st.session_state.last_option_entry_price = None

if "NIFTY_TOKEN" not in st.session_state:
    st.session_state.NIFTY_TOKEN = 256265

if "signal_cache" not in st.session_state:
    st.session_state.signal_cache = {}

if "position_size" not in st.session_state:
    st.session_state.position_size = None

if "lot_qty" not in st.session_state:
    st.session_state.lot_qty = 1

#===================================================================================================================

def monitor_position_live_with_theta_table_and_exit(
    kite,
    symbol,
    qty,
    entry_price,
    strike,
    expiry_date,
    option_type="CALL"
):  
    #============================================SHOW CHART===================================================
    df_option = get_option_ohlc(kite,symbol, interval="5minute")
    #st.write("Option data",df_option)  
    initial_sl,risk1=get_initial_sl_and_risk(df_option, entry_price, option_type)
    st.write("initial_sl,risk1",initial_sl,risk1)  
    #st.write(df_option) 
    #st.write("symbol, qty, entry_price,strike,expiry_date,option_type",symbol, qty, entry_price, strike,  expiry_date,  option_type)   
    import time as tm 
    ist = pytz.timezone("Asia/Kolkata")
    placeholder = st.empty()
    trailing_sl = entry_price * 0.30
     
    status = "LIVE"
    amount=entry_price*qty
    fund=get_fund_status(kite)
    cash=fund['net'] 
    cash=100000 
    risk=cash*(5/100) 
    orisk= (entry_price-initial_sl)*qty
    #st.write("Total Capital(100%)=",cash)
    #st.write("Capital RISK   (5%)  =",risk)
    #st.write("Option AMOUNT   ()  =",amount) 
    #st.write("Option RISK   (entry_price-initial_sl*QTY)  =",orisk) 
    
    #st.write("Qty=",qty) 
    amount= entry_price*qty
    orisk= (entry_price-initial_sl)*qty 
    #st.write("New Option AMOUNT   ()  =",amount) 
    pprofit=orisk+entry_price+2
    #st.write("Partial pprofit=",pprofit) 
    #st.write("New Option RISK   (entry_price-initial_sl*QTY)  =",orisk)  
    #---------------------------------------------------------------------------------------SL------------  
    # ------------------ RISK MANAGEMENT ------------------

    lot_size = 65 #nearest_itm.get("lot_size", qty)
     
    max_capital_risk = cash * 0.05  # 5%
    per_unit_risk = abs(entry_price - initial_sl)
     
    qty = int(qty)  # safety
    orisk = per_unit_risk * qty
     
    
     # Final validated qty
    amount = entry_price * qty
    greek_theta=st.session_state.GREEKtheta 
    option_iv=st.session_state.option_iv

    st.success("✅Monitor  Risk validation ")
    #st.write("Final Qty =", qty)
    st.write("Option Risk =", round(orisk, 2))
    st.write("Capital Risk (5%) =", round(max_capital_risk, 2))
    st.write("Position Value =", round(amount, 2))  
    st.write("Partial Profit Value =", round(pprofit, 2))
    st.write("Theta  Value =", round(greek_theta, 2))
    st.write("IV Value =", round(option_iv, 2))
    
  
    #show_option_chart_with_trade_levels( df_option, symbol, entry_price=180, stop_loss=120,trailing_sl=st.session_state.get("trailing_sl") )
     #---------------------------------------------------------------------------------------SL------------
     
    #========================================================================================================== 
    while True:
        now = datetime.now(ist)
        ltp = kite.ltp(f"NFO:{symbol}")[f"NFO:{symbol}"]["last_price"]
        if(option_type=="CALL"): 
             pnl =(ltp - entry_price) * qty
        if (option_type == "PUT"):
             pnl =(entry_price - ltp) * qty
             
        #theta = st.session_state.get("GREEKtheta", 0)
        
        if ltp > entry_price * 1.01:
            trailing_sl = max(trailing_sl, ltp * 0.97)
       
        # ---- EXIT LOGIC ----
        if option_iv >= 50:
            status = "❌ IV Blast Exit"
        if pprofit <= pnl:
            status = "❌ Partial Exit"
        if ltp <= trailing_sl:
            status = "❌ SL HIT"
        elif greek_theta <= -80:
            status = "⚠ THETA EXIT"
        elif now.hour == 15 and now.minute >= 20:
            status = "🕒 EOD EXIT"

        # ---- DATAFRAME ----
        df = pd.DataFrame([{
            "Symbol": symbol,
            "Type": option_type,
            "Qty": qty,
            "Entry": round(entry_price, 2),
            "LTP": round(ltp, 2),
            "P&L": round(pnl, 2),
            "Theta": round(greek_theta, 2),
            "Trailing SL": round(trailing_sl, 2),
            "Status": status,
            "Time": now.strftime("%H:%M:%S")
        }])

        def color_pnl(val):
            return "color: green" if val > 0 else "color: red"

        def color_status(val):
            if "LIVE" in val:
                return "color: blue"
            if "SL" in val:
                return "color: red"
            return "color: orange"

        styled = (
            df.style
            .applymap(color_pnl, subset=["P&L"])
            .applymap(color_status, subset=["Status"])
        )

        with placeholder.container():
            st.subheader("📊 Live Option Monitor")
            st.dataframe(styled, use_container_width=True, hide_index=True)
        if (status == "❌ Partial Exit"):
            if(qty==65):
                qty=65
            else:    
                qty=qty/2
            place_exit_order(kite, symbol, qty, status)
            st.write("Placing Partial place_exit_order") 
            break
        if status != "LIVE":
            place_exit_order(kite, symbol, qty, status)
            st.write("place_exit_order triggred") 
            break

        tm.sleep(1)



#==============================================Trade Validation +++++++++++++++++=====================================


def trade_validation(
    kite,
    symbol,
    qty,
    entry_price,
    strike,
    expiry_date,
    option_type="CALL"
):  
    #============================================SHOW CHART===================================================
    df_option = get_option_ohlc(kite,symbol, interval="5minute")
    #st.write("Option data",df_option)  
    initial_sl,risk1=get_initial_sl_and_risk(df_option, entry_price, option_type)
    
    #st.write(df_option) 
    #st.write("symbol, qty, entry_price,strike,expiry_date,option_type",symbol, qty, entry_price, strike,  expiry_date,  option_type)   
    import time as tm 
    ist = pytz.timezone("Asia/Kolkata")
    placeholder = st.empty()
    trailing_sl = entry_price * 0.30
    oldqty=qty 
    status = "LIVE"
    amount=entry_price*qty
    fund=get_fund_status(kite)
    cash=fund['net'] 
    cash=100000 
    risk=cash*(5/100) 
    orisk= (entry_price-initial_sl)*qty
    #st.write("Total Capital(100%)=",cash)
    #st.write("Capital RISK   (5%)  =",risk)
    #st.write("Option AMOUNT   ()  =",amount) 
    #st.write("Option RISK   (entry_price-initial_sl*QTY)  =",orisk) 
    if(orisk>risk):
         qty=qty/2
    #st.write("Qty=",qty) 
    amount= entry_price*qty
    orisk= (entry_price-initial_sl)*qty 
    #st.write("New Option AMOUNT   ()  =",amount) 
    pprofit=orisk+entry_price+2
    #st.write("Partial pprofit=",pprofit) 
    #st.write("New Option RISK   (entry_price-initial_sl*QTY)  =",orisk)  
    #---------------------------------------------------------------------------------------SL------------  
    # ------------------ RISK MANAGEMENT ------------------

    lot_size = 65 #nearest_itm.get("lot_size", qty)
     
    max_capital_risk = cash * 0.05  # 5%
    per_unit_risk = abs(entry_price - initial_sl)
     
    qty = int(qty)  # safety
    orisk = per_unit_risk * qty
     
    while orisk > max_capital_risk:
         qty -= lot_size
     
         if qty <= 0:
             #st.error("❌ Trade rejected: Risk too high even for 1 lot")
             #return  # EXIT FUNCTION
             trade_allowed = False
             st.error("❌ Trade rejected: Risk too high even for 1 lot ")
             break     
     
         orisk = per_unit_risk * qty
     
     # Final validated qty
    #amount = entry_price * qty
    #st.write("initial_sl,risk1",initial_sl,risk1)  
    #st.write("Old Qty",qty) 
    #st.success("✅ Risk validated")
    #st.write("Final Qty =", qty)
    #st.write("Option AMOUNT   ()  =",amount)  
    #st.write("Option Risk =", round(orisk, 2))
    #st.write("Capital Risk (5%) =", round(max_capital_risk, 2))
    #st.write("Position Value =", round(amount, 2))  

    risk_table = pd.DataFrame([
        {"Metric": "Initial SL / Risk", "Value": f"{initial_sl} , {risk1}"},
        {"Metric": "Old Qty", "Value": oldqty},
        {"Metric": "Final Qty", "Value": qty},
        {"Metric": "Option Amount", "Value": round(amount, 2)},
        {"Metric": "Option Risk", "Value": round(orisk, 2)},
        {"Metric": "Capital Risk (5%)", "Value": round(max_capital_risk, 2)},
        {"Metric": "Position Value", "Value": round(amount, 2)},
        {"Metric": "Profit", "Value": round(pprofit,2)},
    ])

    st.success("✅ Risk validated")

    st.dataframe(
        risk_table,
        use_container_width=True,
        hide_index=True
    )
    return qty 
    #show_option_chart_with_trade_levels( df_option, symbol, entry_price=180, stop_loss=120,trailing_sl=st.session_state.get("trailing_sl") )
     #---------------------------------------------------------------------------------------SL------------
     
    #========================================================================================================== 
    

    

#===========================================Get Lot Qty+=============================================================


def  get_lot_qty(new_iv_result,vix_now,vix_result,pcr_result):
    lot_qty = 0  
    if new_iv_result == "Fail" : #or iv_rank_result == "Fail":
            lot_qty = 2
    if new_iv_result == "Pass"  and vix_result=="pass" and pcr_result=="pass":
            lot_qty = 6    
    if vix_now < 10 :
            lot_qty = 1 
    if 10< vix_now < 15 :
            lot_qty = 2
    if 15< vix_now < 20 :
            lot_qty = 4
    if vix_now > 20 :
            lot_qty = 1 
    return lot_qty             
    #add_param_row("LOT QTY", lot_qty, "0,1,2,4,6", "OK")


#==========================================================TRADE LOG++=======================================================\


def log_trade_to_csv(
    symbol,
    qty,
    entry_price,
    exit_price,
    pnl,
    exit_reason,
    filename="trade_log.csv"
):
    ist = pytz.timezone("Asia/Kolkata")

    row = {
        "Date": datetime.now(ist).strftime("%Y-%m-%d"),
        "Time": datetime.now(ist).strftime("%H:%M:%S"),
        "Symbol": symbol,
        "Qty": qty,
        "Entry Price": round(entry_price, 2),
        "Exit Price": round(exit_price, 2),
        "P&L": round(pnl, 2),
        "Exit Reason": exit_reason
    }

    df = pd.DataFrame([row])

    if os.path.exists(filename):
        df.to_csv(filename, mode="a", header=False, index=False)
    else:
        df.to_csv(filename, mode="w", header=True, index=False)
     

#=========================================================New Moniter=========================================================


def monitor_all_open_positions_live(
    kite,
    poll_interval=1,
    theta_exit_level=-50
):
    import pandas as pd
    import time
    from datetime import datetime
    import pytz
    import streamlit as st

    ist = pytz.timezone("Asia/Kolkata")
    placeholder = st.empty()

    # Store trailing SL per symbol
    if "trailing_sl_map" not in st.session_state:
        st.session_state.trailing_sl_map = {}

    while True:
        now = datetime.now(ist)
        positions = kite.positions()["net"]

        live_rows = []

        for p in positions:
            if p["quantity"] == 0:
                continue  # ignore closed positions

            symbol = p["tradingsymbol"]
            qty = abs(p["quantity"])
            entry_price = p["average_price"]
            ltp = p["last_price"]
            pnl = p["pnl"]

            option_type = "CALL" if symbol.endswith("CE") else "PUT"
            theta = st.session_state.get(f"GREEKtheta_{symbol}", 0)

            # Initialize trailing SL
            if symbol not in st.session_state.trailing_sl_map:
                st.session_state.trailing_sl_map[symbol] = entry_price * 0.75

            trailing_sl = st.session_state.trailing_sl_map[symbol]

            # Trailing SL logic
            if ltp > entry_price * 1.01:
                trailing_sl = max(trailing_sl, ltp * 0.97)
                st.session_state.trailing_sl_map[symbol] = trailing_sl

            # Exit conditions
            status = "LIVE"
            if ltp <= trailing_sl:
                status = "❌ SL HIT"
            elif theta >= theta_exit_level:
                status = "⚠ THETA EXIT"
            elif now.hour == 15 and now.minute >= 20:
                status = "🕒 EOD EXIT"

            live_rows.append({
                "Symbol": symbol,
                "Type": option_type,
                "Qty": qty,
                "Entry": round(entry_price, 2),
                "Amount":round(entry_price*qty), 
                "LTP": round(ltp, 2),
                "P&L": round(pnl, 2),
                "Theta": round(theta, 2),
                "Trailing SL": round(trailing_sl, 2),
                "Status": status,
                "Time": now.strftime("%H:%M:%S")
            })

            # Exit hook (paper / real)
            if status != "LIVE":
                # place_exit_order(kite, symbol, qty, status)
                exit_price = ltp
                log_trade_to_csv(symbol=symbol,qty=qty,entry_price=entry_price,exit_price=exit_price, pnl=pnl,exit_reason=status)

                   # place_exit_order(kite, symbol, qty, status)  # real trade later

                st.success(f"{symbol} EXITED → {status}") 
                st.warning(f"{symbol} EXIT → {status}")

        if not live_rows:
            #st.info("No open positions")
            time.sleep(poll_interval)
            continue

        df = pd.DataFrame(live_rows)

        # Styling
        def pnl_color(v): return "color: green" if v > 0 else "color: red"
        def status_color(v):
            if "LIVE" in v: return "color: blue"
            if "SL" in v: return "color: red"
            return "color: orange"

        styled_df = (
            df.style
            .applymap(pnl_color, subset=["P&L"])
            .applymap(status_color, subset=["Status"])
        )

        with placeholder.container():
            st.subheader("📊 LIVE OPTION POSITION MONITOR")
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

        time.sleep(poll_interval)

#=====================================================monitor_position_live_with_theta===================================================

def get_initial_sl_and_risk(df, entry_price, option_type):
    df = df.copy()
    # Ensure datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])
            df.set_index("datetime", inplace=True)
        else:
            return None, None

    # Get 9:15 candle
    candle_915 = df[df.index.time == datetime.strptime("09:15", "%H:%M").time()]
    #
    #st.write("candle_915",candle_915)
    if candle_915.empty:
        return None, None

    if option_type == "PUT":
        initial_sl = candle_915["low"].iloc[0]
        risk = entry_price - initial_sl
    else:
        initial_sl = candle_915["high"].iloc[0]
        risk = initial_sl - entry_price
    #st.write("initial_sl,risk",initial_sl,risk)
    # ❌ Invalid trade → skip safely
    #if risk <= 0:
        #return None, None

    return initial_sl, risk


def get_instrument_token(kite, symbol):
    instruments = kite.instruments("NFO")
    for ins in instruments:
        if ins["tradingsymbol"] == symbol:
            return ins["instrument_token"]
    return None



def get_option_ohlc(
    kite,
    symbol,
    interval="5minute",
    lookback_days=7
):
    """
    Fetch option OHLC from latest working trading day (09:15 IST) to now
    Automatically handles weekends & holidays
    """

    import pandas as pd
    import pytz
    import datetime as dt

    token = get_instrument_token(kite, symbol)
    if token is None:
        return pd.DataFrame()

    IST = pytz.timezone("Asia/Kolkata")
    now_ist = dt.datetime.now(IST)

    for day_offset in range(lookback_days):
        trade_day = now_ist.date() - dt.timedelta(days=day_offset)

        market_start = IST.localize(
            dt.datetime.combine(trade_day, dt.time(9, 15))
        )

        market_end = IST.localize(
            dt.datetime.combine(trade_day, dt.time(15, 30))
        )

        # If today → till now, else full day
        to_time = now_ist if day_offset == 0 else market_end

        # Skip future / pre-open time
        if to_time <= market_start:
            continue

        try:
            data = kite.historical_data(
                instrument_token=token,
                from_date=market_start,
                to_date=to_time,
                interval=interval,
                continuous=False,
                oi=False
            )
        except Exception:
            continue

        if data:
            df = pd.DataFrame(data)
            df["datetime"] = pd.to_datetime(df["date"])

            return (
                df[["datetime", "open", "high", "low", "close", "volume"]]
                .sort_values("datetime")
                .reset_index(drop=True)
            )

    # No data found even after lookback
    return pd.DataFrame()

def get_option_ohlc0(
    kite,
    symbol,
    interval="5minute"
):
    """
    Fetch option OHLC from today's market open (09:15 IST) to now
    """
    #st.write("Symbol ",symbol) 
    import pandas as pd
    import pytz
    import datetime as dt

    token = get_instrument_token(kite, symbol)
    if token is None:
        return pd.DataFrame()
    #st.write("Token ",token) 
    IST = pytz.timezone("Asia/Kolkata")
    now_ist = dt.datetime.now(IST)

    # ✅ Market start time: 09:15 IST today
    market_start = now_ist.replace(
        hour=9,
        minute=15,
        second=0,
        microsecond=0
    )

    # Safety: before market open
    if now_ist < market_start:
        return pd.DataFrame()

    data = kite.historical_data(
        instrument_token=token,
        from_date=market_start,
        to_date=now_ist,
        interval=interval,
        continuous=False,
        oi=False
    )

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["datetime"] = pd.to_datetime(df["date"])

    return df[["datetime", "open", "high", "low", "close", "volume"]] \
             .sort_values("datetime") \
             .reset_index(drop=True)
def get_option_ohlc1(
    kite,
    symbol,
    interval="5minute",
    lookback_minutes=300
):
    """
    Fetch OHLC data for option symbol
    interval: "minute", "3minute", "5minute"
    """

    token = get_instrument_token(kite, symbol)
    st.write("token",token) 
    if token is None:
        return pd.DataFrame()
    from datetime import datetime
    import pytz
     
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist) 
    #st.write("now_ist",now_ist) 
    to_dt = datetime.now(ist)
    from_dt = to_dt - timedelta(minutes=lookback_minutes)
    #st.write("from_dt",from_dt)
    #st.write("to_dt",to_dt) 
    data = kite.historical_data(
        instrument_token=token,
        from_date=from_dt,
        to_date=to_dt,
        interval=interval,
        continuous=False,
        oi=False
    )
    #st.write("data token",data) 
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["datetime"] = pd.to_datetime(df["date"])

    return df[["datetime", "open", "high", "low", "close", "volume"]]



def show_option_candle_chart(df, symbol):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df["datetime"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name=symbol
    ))

    fig.update_layout(
        title=f"{symbol} Option Chart",
        xaxis_title="Time",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False,
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

def show_option_chart_with_trade_levels(
    df,
    symbol,
    entry_price,
    stop_loss,
    trailing_sl=None
):
    fig = go.Figure()
    #st.write(df)
    # Candles
    fig.add_trace(go.Candlestick(
        x=df["datetime"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="Price"
    ))

    # Entry Line
    fig.add_hline(
        y=entry_price,
        line_dash="dot",
        line_color="blue",
        annotation_text="ENTRY",
        annotation_position="right"
    )

    # Stop Loss Line
    fig.add_hline(
        y=stop_loss,
        line_dash="dot",
        line_color="red",
        annotation_text="SL",
        annotation_position="right"
    )

    # Trailing SL Line
    if trailing_sl:
        fig.add_hline(
            y=trailing_sl,
            line_dash="dash",
            line_color="orange",
            annotation_text="TRAIL SL",
            annotation_position="right"
        )

    fig.update_layout(
        title=f"{symbol} Option Trade Chart",
        xaxis_rangeslider_visible=False,
        height=550
    )

    st.plotly_chart(fig, use_container_width=True)


def monitor_position_live_with_theta_table(
    kite,
    symbol,
    qty,
    entry_price,
    strike,
    expiry_date,
    option_type="CALL"
):  
    #============================================SHOW CHART===================================================
    df_option = get_option_ohlc(kite,symbol, interval="5minute")
    #st.write("Option data",df_option)  
    initial_sl,risk1=get_initial_sl_and_risk(df_option, entry_price, option_type)
    st.write("initial_sl,risk1",initial_sl,risk1)  
    #st.write(df_option) 
    #st.write("symbol, qty, entry_price,strike,expiry_date,option_type",symbol, qty, entry_price, strike,  expiry_date,  option_type)   
    import time as tm 
    ist = pytz.timezone("Asia/Kolkata")
    placeholder = st.empty()
    trailing_sl = entry_price * 0.30
     
    status = "LIVE"
    amount=entry_price*qty
    fund=get_fund_status(kite)
    cash=fund['net'] 
    cash=100000 
    risk=cash*(5/100) 
    orisk= (entry_price-initial_sl)*qty
    st.write("Total Capital(100%)=",cash)
    st.write("Capital RISK   (5%)  =",risk)
    st.write("Option AMOUNT   ()  =",amount) 
    st.write("Option RISK   (entry_price-initial_sl*QTY)  =",orisk) 
    if(orisk>risk):
         qty=qty/2
    st.write("Qty=",qty) 
    amount= entry_price*qty
    orisk= (entry_price-initial_sl)*qty 
    st.write("New Option AMOUNT   ()  =",amount) 
    pprofit=orisk+entry_price+2
    st.write("Partial pprofit=",pprofit) 
    st.write("New Option RISK   (entry_price-initial_sl*QTY)  =",orisk)  
    #---------------------------------------------------------------------------------------SL------------  
    # ------------------ RISK MANAGEMENT ------------------

    lot_size = 65 #nearest_itm.get("lot_size", qty)
     
    max_capital_risk = cash * 0.05  # 5%
    per_unit_risk = abs(entry_price - initial_sl)
     
    qty = int(qty)  # safety
    orisk = per_unit_risk * qty
     
    while orisk > max_capital_risk:
         qty -= lot_size
     
         if qty <= 0:
             #st.error("❌ Trade rejected: Risk too high even for 1 lot")
             #return  # EXIT FUNCTION
             trade_allowed = False
             st.error("❌ Trade rejected: Risk too high even for 1 lot")
             break     
     
         orisk = per_unit_risk * qty
     
     # Final validated qty
    amount = entry_price * qty
     
    st.success("✅ Risk validated")
    st.write("Final Qty =", qty)
    st.write("Option Risk =", round(orisk, 2))
    st.write("Capital Risk (5%) =", round(max_capital_risk, 2))
    st.write("Position Value =", round(amount, 2))  
  
    #show_option_chart_with_trade_levels( df_option, symbol, entry_price=180, stop_loss=120,trailing_sl=st.session_state.get("trailing_sl") )
     #---------------------------------------------------------------------------------------SL------------
     
    #========================================================================================================== 
    while True:
        now = datetime.now(ist)
        ltp = kite.ltp(f"NFO:{symbol}")[f"NFO:{symbol}"]["last_price"]
        pnl = (
            (ltp - entry_price) * qty
            if option_type == "PUT"
            else (entry_price - ltp) * qty
        )
        theta = st.session_state.get("GREEKtheta", 0)
        
        if ltp > entry_price * 1.01:
            trailing_sl = max(trailing_sl, ltp * 0.97)

        # ---- EXIT LOGIC ----
        if ltp <= trailing_sl:
            status = "❌ SL HIT"
        elif theta >= 50:
            status = "⚠ THETA EXIT"
        elif now.hour == 15 and now.minute >= 20:
            status = "🕒 EOD EXIT"

        # ---- DATAFRAME ----
        df = pd.DataFrame([{
            "Symbol": symbol,
            "Type": option_type,
            "Qty": qty,
            "Entry": round(entry_price, 2),
            "LTP": round(ltp, 2),
            "P&L": round(pnl, 2),
            "Theta": round(theta, 2),
            "Trailing SL": round(trailing_sl, 2),
            "Status": status,
            "Time": now.strftime("%H:%M:%S")
        }])

        def color_pnl(val):
            return "color: green" if val > 0 else "color: red"

        def color_status(val):
            if "LIVE" in val:
                return "color: blue"
            if "SL" in val:
                return "color: red"
            return "color: orange"

        styled = (
            df.style
            .applymap(color_pnl, subset=["P&L"])
            .applymap(color_status, subset=["Status"])
        )

        with placeholder.container():
            st.subheader("📊 Live Option Monitor")
            st.dataframe(styled, use_container_width=True, hide_index=True)

        if status != "LIVE":
            #place_exit_order(kite, symbol, qty, status)
            st.write("place_exit_order") 
            break

        tm.sleep(1)


def monitor_position_live_with_theta(
    kite,
    symbol,
    qty,
    entry_price,
    strike,
    expiry_date,
    option_type
):
    import time
    import pytz
    from datetime import datetime
    import streamlit as st

    ist = pytz.timezone("Asia/Kolkata")
    placeholder = st.empty()

    sl = entry_price * 0.75

    while True:
        now = datetime.now(ist)

        ltp = kite.ltp(f"NFO:{symbol}")[f"NFO:{symbol}"]["last_price"]

        pnl = (ltp - entry_price) * qty if option_type == "CALL" else (entry_price - ltp) * qty

        # ✅ USE STORED THETA
        theta = st.session_state.get("GREEKtheta", 0)

        if ltp > entry_price * 1.01:
            sl = max(sl, ltp * 0.97)

        with placeholder.container():
            st.metric("LTP", round(ltp, 2))
            st.metric("P&L", f"₹{round(pnl, 2)}")
            st.metric("Trailing SL", round(sl, 2))
            st.metric("Theta", round(theta, 2))
            st.metric("Time", now.strftime("%H:%M:%S"))

        if ltp <= sl:
            place_exit_order(kite, symbol, qty, "STOP LOSS HIT")
            break

        if theta >= 50:
            place_exit_order(kite, symbol, qty, "THETA DECAY EXIT")
            break

        if now.hour == 15 and now.minute >= 20:
            place_exit_order(kite, symbol, qty, "EOD EXIT")
            break

        time.sleep(1)

#===========================================================================================================================

def normalize_nsei_columns(df):
    rename_map = {}

    for col in df.columns:
        if col == "Datetime":
            continue

        # Convert everything to string
        c = str(col)

        # Remove duplicate NSEI tags
        c = c.replace(",^NSEI", "")
        c = c.replace("_^NSEI", "")
        c = c.replace("^NSEI", "")

        # Final standardized name
        if "Open" in c:
            rename_map[col] = "Open_^NSEI"
        elif "High" in c:
            rename_map[col] = "High_^NSEI"
        elif "Low" in c:
            rename_map[col] = "Low_^NSEI"
        elif "Close" in c:
            rename_map[col] = "Close_^NSEI"
        elif "Volume" in c:
            rename_map[col] = "Volume"

    df.rename(columns=rename_map, inplace=True)
    return df


#==============================================calculate_and_cache_signal================================================================



def calculate_and_cache_signal(signal_id, data):
    """
    data = {
        spot, strike, T, iv, option_type,
        vix, pcr, cash, lot_qty, signal_time
    }
    """

    if signal_id in st.session_state.signal_cache:
        return st.session_state.signal_cache[signal_id]

    # ---- Greeks (calculated ONCE) ----
    greeks = OptionGreeks(
        S=data["spot"],
        K=data["strike"],
        T=data["T"],
        r=0.06,
        sigma=data["iv"],
        option_type=data["option_type"]
    ).summary()

    cached = {
        "signal_time": data["signal_time"],
        "spot": data["spot"],
        "strike": data["strike"],
        "option_type": data["option_type"],

        # Parameters
        "cash": data["cash"],
        "iv": data["iv"],
        "vix": data["vix"],
        "pcr": data["pcr"],
        "lot_qty": data["lot_qty"],

        # Greeks
        "greeks": greeks
    }

    st.session_state.signal_cache[signal_id] = cached
    return cached

#=========================================New Signals===============================================================

def trading_multi2_signal_all_conditions_5min(
    df_5m,
    quantity=10 * 65,
    max_trades_per_day=2,
):
    """
    Multi-timeframe intraday option strategy

    TF Usage:
    - 15m: Previous day base candle (15:00)
    - 15m: Current day opening range (09:15–09:30)
    - 5m : Signal execution
    """

    import pandas as pd
    from datetime import timedelta
    #st.write("CANDELS") 
    #st.write(df_5m.tail(5))

    df_5m = df_5m.copy()
    df_5m["Datetime"] = pd.to_datetime(df_5m["Datetime"])
    df_5m["Date"] = df_5m["Datetime"].dt.date

    unique_days = sorted(df_5m["Date"].unique())
    if len(unique_days) < 2:
        return None

    day0, day1 = unique_days[-2], unique_days[-1]

    # =================================================
    # 15-MIN RESAMPLE (FOR BASE + OPENING RANGE)
    # =================================================
    df_15m = (
        df_5m
        .set_index("Datetime")
        .resample("15min")
        .agg({
            "Open_^NSEI": "first",
            "High_^NSEI": "max",
            "Low_^NSEI": "min",
            "Close_^NSEI": "last",
        })
        .dropna()
        .reset_index()
    )
    df_15m["Date"] = df_15m["Datetime"].dt.date

    # ---------------- BASE CANDLE (DAY0 @ 15:00) ----------------
    base_candle = df_15m[
        (df_15m["Date"] == day0)
        & (df_15m["Datetime"].dt.hour == 15)
        & (df_15m["Datetime"].dt.minute == 0)
    ]
    if base_candle.empty:
        return None

    base_open = base_candle.iloc[0]["Open_^NSEI"]
    base_close = base_candle.iloc[0]["Close_^NSEI"]
    base_low, base_high = sorted([base_open, base_close])

    # ---------------- OPENING RANGE (09:15–09:30) ----------------
    or_candle = df_15m[
        (df_15m["Date"] == day1)
        & (df_15m["Datetime"].dt.hour == 9)
        & (df_15m["Datetime"].dt.minute == 15)
    ]
    if or_candle.empty:
        return None

    O1 = or_candle.iloc[0]["Open_^NSEI"]
    H1 = or_candle.iloc[0]["High_^NSEI"]
    L1 = or_candle.iloc[0]["Low_^NSEI"]
    C1 = or_candle.iloc[0]["Close_^NSEI"]

     
    entry_start_time = or_candle.iloc[0]["Datetime"] + timedelta(minutes=15)

    trade_end_time = entry_start_time.replace(hour=14, minute=30)
    expiry = get_nearest_weekly_expiry(pd.to_datetime(day1))

    # =================================================
    # 5-MIN DATA (FOR EXECUTION)
    # =================================================
    day_df_5m = df_5m[
        (df_5m["Date"] == day1)
        & (df_5m["Datetime"] >= entry_start_time)
        & (df_5m["Datetime"] <= trade_end_time)
    ].sort_values("Datetime")
    # ================= DEBUG HERE =================
    #st.write("📌 Base Low / High:", base_low, base_high,"📌 OR Low / High:", L1, H1)
    #st.write("📌 OR Low / High:", L1, H1)
    #st.write("📌 C1 (9:15 Close):", C1,"📌 Latest Close:", day_df_5m.iloc[-1]["Close_^NSEI"])
    #st.write("📌 Latest Close:", day_df_5m.iloc[-1]["Close_^NSEI"])
    

    #st.table(debug_table)
 
    # ============================================== 
    # =================================================
    # SAFETY
    # =================================================
    signals = []
    fired_conditions = set()
    trade_count = 0

    # =================================================
    # HELPERS
    # =================================================
    def recent_swing(ts):
        recent = day_df_5m[day_df_5m["Datetime"] < ts].tail(10)
        if recent.empty:
            return None, None
        return recent["High_^NSEI"].max(), recent["Low_^NSEI"].min()

    def monitor_trade(sig):
        sl = sig["stoploss"]
        exit_deadline = sig["entry_time"] + timedelta(minutes=16)

        for _, c in day_df_5m.iterrows():
            if c["Datetime"] <= sig["entry_time"]:
                continue

            if c["Datetime"] >= exit_deadline:
                sig["exit_price"] = c["Close_^NSEI"]
                sig["exit_time"] = c["Datetime"]
                sig["status"] = "Time Exit"
                return sig

            high, low = recent_swing(c["Datetime"])

            if sig["option_type"] == "CALL" and low:
                sl = max(sl, low)
                if c["Low_^NSEI"] <= sl:
                    sig["exit_price"] = sl
                    sig["exit_time"] = c["Datetime"]
                    sig["status"] = "SL Hit"
                    return sig

            if sig["option_type"] == "PUT" and high:
                sl = min(sl, high)
                if c["High_^NSEI"] >= sl:
                    sig["exit_price"] = sl
                    sig["exit_time"] = c["Datetime"]
                    sig["status"] = "SL Hit"
                    return sig

        last = day_df_5m.iloc[-1]
        sig["exit_price"] = last["Close_^NSEI"]
        sig["exit_time"] = last["Datetime"]
        sig["status"] = "Forced Exit 14:30"
        return sig

    # =================================================
    # SIGNAL LOGIC (5-MIN)
    # =================================================
    for i in range(1, len(day_df_5m)):
        if trade_count >= max_trades_per_day:
            break

        candle = day_df_5m.iloc[i]
        prev = day_df_5m.iloc[i - 1]
        high, low = recent_swing(candle["Datetime"])

        # ---- GAP DOWN → PUT ----
        if (
            2 not in fired_conditions
            and C1 < base_low
            and prev["Low_^NSEI"] > L1
            and candle["Low_^NSEI"] <= L1
        ):
            sig = {
                "condition": 2,
                "option_type": "PUT",
                "buy_price": L1,
                "entry_time": candle["Datetime"],
                "spot_price": candle["Close_^NSEI"],
                "stoploss": high,
                "quantity": quantity,
                "expiry": expiry,
                "message": "Cond 2: OR breakdown → BUY PUT",
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            fired_conditions.add(2)
            trade_count += 1

        # ---- GAP UP → CALL ----
        if (
            3 not in fired_conditions
            and C1 > base_high
            and prev["High_^NSEI"] < H1
            and candle["High_^NSEI"] >= H1
        ):
            sig = {
                "condition": 3,
                "option_type": "CALL",
                "buy_price": H1,
                "entry_time": candle["Datetime"],
                "spot_price": candle["Close_^NSEI"],
                "stoploss": low,
                "quantity": quantity,
                "expiry": expiry,
                "message": "Cond 3: OR breakout → BUY CALL",
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            fired_conditions.add(3)
            trade_count += 1

          # ==============================
          # CONDITION-4 : GAP DOWN → DIRECT OR BREAKDOWN → PUT
          # ==============================
          
        if (
              4 not in fired_conditions
              and C1 < base_low                     # GAP DOWN
              and candle["Close_^NSEI"] < L1        # OR Low breakdown & acceptance
          ):
              sig = {
                  "condition": 4,
                  "option_type": "PUT",
                  "buy_price": L1,
                  "entry_time": candle["Datetime"],
                  "spot_price": candle["Close_^NSEI"],
                  "stoploss": high,                 # OR High / recent swing high
                  "quantity": quantity,
                  "expiry": expiry,
                  "message": "Cond 4: Gap Down → OR Breakdown → BUY PUT",
              }
          
              sig = monitor_trade(sig)
              signals.append(sig)
              fired_conditions.add(4)
              trade_count += 1

        # ---- CONDITION 5: GAP-UP TREND CONTINUATION → CALL ----
        if (
              5 not in fired_conditions
              and C1 > base_high                      # Gap-up above base
              and C1 > H1                             # 9:15 close above OR high
              and prev["Close_^NSEI"] > H1            # Acceptance above OR
              and candle["High_^NSEI"] > prev["High_^NSEI"]  # Higher high (momentum)
          ):
              sig = {
                  "condition": 5,
                  "option_type": "CALL",
                  "buy_price": candle["Close_^NSEI"],  # market continuation entry
                  "entry_time": candle["Datetime"],
                  "spot_price": candle["Close_^NSEI"],
                  "stoploss": low,                     # recent swing low
                  "quantity": quantity,
                  "expiry": expiry,
                  "message": "Cond 5: Gap-up trend continuation → BUY CALL",
              }
              sig = monitor_trade(sig)
              signals.append(sig)
              fired_conditions.add(5)
              trade_count += 1

               # ==============================
          # CONDITION 6: BASE LOW ACCEPTANCE BREAKDOWN → PUT
          # ==============================
        if (
              6 not in fired_conditions
              and C1 <= base_high                  # No strong gap-up
              and candle["Close_^NSEI"] < base_low # Acceptance below base low
              and prev["Close_^NSEI"] >= base_low  # First breakdown candle
          ):
              sig = {
                  "condition": 6,
                  "option_type": "PUT",
                  "buy_price": candle["Close_^NSEI"],  # market entry
                  "entry_time": candle["Datetime"],
                  "spot_price": candle["Close_^NSEI"],
                  "stoploss": high,                   # recent swing high / base low
                  "quantity": quantity,
                  "expiry": expiry,
                  "message": "Cond 6: Base low acceptance → BUY PUT",
              }
          
              sig = monitor_trade(sig)
              signals.append(sig)
              fired_conditions.add(6)
              trade_count += 1
    
     

     

    return signals if signals else None


def trading_signal_all_conditions_final(df, quantity=10*65):
    """
    Base Zone Re-Cross Strategy (FINAL)

    Rules:
    - Max 2 trades per day
    - Trade ONLY when price re-enters Base Zone and breaks again
    - Single active trade at a time
    - Trailing SL using last 10 candles swing
    - NO time exit
    """
    #st.write 
    from datetime import time as dtime 
    import numpy as np
    import pandas as pd
    TRADE_START_TIME = dtime(9, 35)
    TRADE_EXIT_CUTOFF = dtime(15, 20) 
    signals = []

    # =========================
    # PREPROCESS
    # =========================
    df = df.copy()
    df['Date'] = df['Datetime'].dt.date
    unique_days = sorted(df['Date'].unique())

    if len(unique_days) < 2:
        return None

    day0, day1 = unique_days[-2], unique_days[-1]

    # =========================
    # BASE ZONE (Previous Day 3:00 PM)
    # =========================
    candle_3pm = df[
        (df['Date'] == day0) &
        (df['Datetime'].dt.hour == 15) &
        (df['Datetime'].dt.minute == 0)
    ]

    if candle_3pm.empty:
        return None

    base_open = candle_3pm.iloc[0]['Open_^NSEI']
    base_close = candle_3pm.iloc[0]['Close_^NSEI']
    base_low = min(base_open, base_close)
    base_high = max(base_open, base_close)

    # =========================
    # CURRENT DAY DATA
    # =========================
    day1_df = df[df['Date'] == day1].sort_values('Datetime')

    expiry = get_nearest_weekly_expiry(pd.to_datetime(day1))

    # =========================
    # HELPERS
    # =========================
    def is_inside_base(price):
        return base_low < price < base_high

    def get_recent_swing(ts):
        recent = day1_df[day1_df['Datetime'] < ts].tail(10)
        if recent.empty:
            return np.nan, np.nan
        return recent['High_^NSEI'].max(), recent['Low_^NSEI'].min()

    def monitor_trade(sig):
        """
        Trailing SL only (NO TIME EXIT)
        """
        sl = sig['stoploss']

        for _, c in day1_df[day1_df['Datetime'] > sig['entry_time']].iterrows():

            high, low = get_recent_swing(c['Datetime'])

            # ----- CALL -----
            if sig['option_type'] == 'CALL' and not np.isnan(low):
                sl = max(sl, low) if not np.isnan(sl) else low
                sig['stoploss'] = sl

                if c['Low_^NSEI'] <= sl:
                    sig['exit_price'] = sl
                    sig['status'] = 'Trailing SL Hit'
                    return sig

            # ----- PUT -----
            if sig['option_type'] == 'PUT' and not np.isnan(high):
                sl = min(sl, high) if not np.isnan(sl) else high
                sig['stoploss'] = sl

                if c['High_^NSEI'] >= sl:
                    sig['exit_price'] = sl
                    sig['status'] = 'Trailing SL Hit'
                    return sig

        # If SL never hit → exit at last candle (EOD)
        sig['exit_price'] = day1_df.iloc[-1]['Close_^NSEI']
        sig['status'] = 'EOD Exit'
        return sig

    # =========================
    # CORE LOGIC (MAX 2 TRADES)
    # =========================
    MAX_TRADES = 3
    trade_count = 0
    last_break = None
    price_inside_base = True
    #st.write("Data",day1_df)
    for _, c in day1_df.iterrows():

        if trade_count >= MAX_TRADES:
            break

        close = c['Close_^NSEI']
        candle_time = c['Datetime'].time() 
        if candle_time < TRADE_START_TIME:
            continue
        # Track price returning into base zone
        if is_inside_base(close):
            price_inside_base = True
            last_break = None
            continue

        # ======================
        # CALL BREAKOUT
        # ======================
        if (
            price_inside_base
            and close > base_high
            and last_break != "CALL"
        ):
            swing_high, swing_low = get_recent_swing(c['Datetime'])

            sig = {
                'condition': 'Base Re-Break',
                'option_type': 'CALL',
                'buy_price': c['High_^NSEI'],
                'stoploss': swing_low,
                'quantity': quantity,
                'expiry': expiry,
                'entry_time': c['Datetime'],
                'message': f'CALL Base Zone Break #{trade_count + 1}'
            }

        # ======================
        # PUT BREAKDOWN
        # ======================
        elif (
            price_inside_base
            and close < base_low
            and last_break != "PUT"
        ):
            swing_high, swing_low = get_recent_swing(c['Datetime'])

            sig = {
                'condition': 'Base Re-Break',
                'option_type': 'PUT',
                'buy_price': c['Low_^NSEI'],
                'stoploss': swing_high,
                'quantity': quantity,
                'expiry': expiry,
                'entry_time': c['Datetime'],
                'message': f'PUT Base Zone Break #{trade_count + 1}'
            }
        else:
            continue

        # ======================
        # EXECUTE & MONITOR
        # ======================
        sig = monitor_trade(sig)
        signals.append(sig)

        trade_count += 1
        last_break = sig['option_type']
        price_inside_base = False

    return signals if signals else None

#===================================================Signal=================================================================

def trading_signal_all_conditions_new(df, quantity=10*65, return_all_signals=True):
    """
    Optimized Base Zone Strategy
    - ONE trade per day (state machine)
    - First valid break only
    - Clean entry → monitor → exit flow
    """

    from datetime import timedelta, time
    import numpy as np
    import pandas as pd

    signals = []
    state = "IDLE"   # IDLE → ENTERED → EXITED

    df = df.copy()
    df['Date'] = df['Datetime'].dt.date

    unique_days = sorted(df['Date'].unique())
    if len(unique_days) < 2:
        return None

    day0, day1 = unique_days[-2], unique_days[-1]

    # --- Base Zone (Previous day 3:00 PM)
    candle_3pm = df[
        (df['Date'] == day0) &
        (df['Datetime'].dt.hour == 15) &
        (df['Datetime'].dt.minute == 0)
    ]

    if candle_3pm.empty:
        return None

    base_open = candle_3pm.iloc[0]['Open_^NSEI']
    base_close = candle_3pm.iloc[0]['Close_^NSEI']
    base_low = min(base_open, base_close)
    base_high = max(base_open, base_close)

    # --- 9:15–9:30 candle
    candle_915 = df[
        (df['Date'] == day1) &
        (df['Datetime'].dt.hour == 9) &
        (df['Datetime'].dt.minute == 30)
    ]

    if candle_915.empty:
        return None

    H1 = candle_915.iloc[0]['High_^NSEI']
    L1 = candle_915.iloc[0]['Low_^NSEI']
    C1 = candle_915.iloc[0]['Close_^NSEI']
    entry_time = candle_915.iloc[0]['Datetime']

    expiry = get_nearest_weekly_expiry(pd.to_datetime(day1))

    day1_after_915 = df[
        (df['Date'] == day1) &
        (df['Datetime'] > entry_time)
    ].sort_values('Datetime')

    # --- Swing helper
    def get_recent_swing(ts):
        recent = df[(df['Date'] == day1) & (df['Datetime'] < ts)].tail(10)
        if recent.empty:
            return np.nan, np.nan
        return recent['High_^NSEI'].max(), recent['Low_^NSEI'].min()

    # --- Trade monitor (called ONCE)
    def monitor_trade(sig):
        sl = sig['stoploss']
        deadline = sig['entry_time'] + timedelta(minutes=16)

        for _, c in day1_after_915.iterrows():
            if c['Datetime'] >= deadline:
                sig['exit_price'] = c['Close_^NSEI']
                sig['status'] = 'Time Exit'
                return sig

            high, low = get_recent_swing(c['Datetime'])

            # trailing SL
            if sig['option_type'] == 'CALL' and not np.isnan(low):
                sl = max(sl, low) if not np.isnan(sl) else low
                if c['Low_^NSEI'] <= sl:
                    sig['exit_price'] = sl
                    sig['status'] = 'Trailing SL Hit'
                    return sig

            if sig['option_type'] == 'PUT' and not np.isnan(high):
                sl = min(sl, high) if not np.isnan(sl) else high
                if c['High_^NSEI'] >= sl:
                    sig['exit_price'] = sl
                    sig['status'] = 'Trailing SL Hit'
                    return sig

            sig['stoploss'] = sl

        sig['exit_price'] = day1_after_915.iloc[-1]['Close_^NSEI']
        sig['status'] = 'EOD Exit'
        return sig

    # =========================
    # ENTRY LOGIC (STATE = IDLE)
    # =========================

    # --- Condition 1 & 4 (No Gap)
    if state == "IDLE" and (L1 < base_high and H1 > base_low):

        swing_high, swing_low = get_recent_swing(entry_time)

        if C1 > base_high:
            sig = {
                'condition': 1,
                'option_type': 'CALL',
                'buy_price': H1,
                'stoploss': swing_low,
                'quantity': quantity,
                'expiry': expiry,
                'entry_time': entry_time,
                'message': 'Base Zone Breakout CALL'
            }

        elif C1 < base_low:
            sig = {
                'condition': 4,
                'option_type': 'PUT',
                'buy_price': L1,
                'stoploss': swing_high,
                'quantity': quantity,
                'expiry': expiry,
                'entry_time': entry_time,
                'message': 'Base Zone Breakdown PUT'
            }
        else:
            sig = None

        if sig:
            state = "ENTERED"
            sig = monitor_trade(sig)
            signals.append(sig)
            state = "EXITED"
            return signals

    # --- Gap Trades (Condition 2 & 3)
    if state == "IDLE":

        for _, c in day1_after_915.iterrows():

            if c['Datetime'].time() > time(11, 0):
                break  # no late entries

            swing_high, swing_low = get_recent_swing(c['Datetime'])

            # Gap Down
            if C1 < base_low and c['Low_^NSEI'] <= L1:
                sig = {
                    'condition': 2,
                    'option_type': 'PUT',
                    'buy_price': L1,
                    'stoploss': swing_high,
                    'quantity': quantity,
                    'expiry': expiry,
                    'entry_time': c['Datetime'],
                    'message': 'Gap Down PUT'
                }

            # Gap Up
            elif C1 > base_high and c['High_^NSEI'] >= H1:
                sig = {
                    'condition': 3,
                    'option_type': 'CALL',
                    'buy_price': H1,
                    'stoploss': swing_low,
                    'quantity': quantity,
                    'expiry': expiry,
                    'entry_time': c['Datetime'],
                    'message': 'Gap Up CALL'
                }
            else:
                continue

            state = "ENTERED"
            sig = monitor_trade(sig)
            signals.append(sig)
            state = "EXITED"
            break

    return signals if signals else None

#====================================================NEW GREEKS ===========================================================

class OptionGreeks:
    def __init__(self, S, K, T, r, sigma, option_type="call"):
        self.S = S
        self.K = K
        self.T = T
        self.r = r
        self.sigma = sigma
        self.option_type = option_type.lower()

    def d1(self):
        return (math.log(self.S / self.K) + (self.r + 0.5 * self.sigma**2) * self.T) / (self.sigma * math.sqrt(self.T))

    def d2(self):
        return self.d1() - self.sigma * math.sqrt(self.T)

    def delta(self):
        return norm.cdf(self.d1()) if self.option_type == "call" else norm.cdf(self.d1()) - 1

    def gamma(self):
        return norm.pdf(self.d1()) / (self.S * self.sigma * math.sqrt(self.T))

    def theta(self):
        d1, d2 = self.d1(), self.d2()
        first_term = -(self.S * norm.pdf(d1) * self.sigma) / (2 * math.sqrt(self.T))
        if self.option_type == "call":
            second_term = -self.r * self.K * math.exp(-self.r * self.T) * norm.cdf(d2)
        else:
            second_term = self.r * self.K * math.exp(-self.r * self.T) * norm.cdf(-d2)
        return first_term + second_term

    def vega(self):
        return self.S * norm.pdf(self.d1()) * math.sqrt(self.T)

    def rho(self):
        if self.option_type == "call":
            return self.K * self.T * math.exp(-self.r * self.T) * norm.cdf(self.d2())
        else:
            return -self.K * self.T * math.exp(-self.r * self.T) * norm.cdf(-self.d2())

    def summary(self):
        return {
            "Delta": self.delta(),
            "Gamma": self.gamma(),
            "Theta": self.theta(),
            "Vega": self.vega(),
            "Rho": self.rho()
        }

     #===================================================LAST Price================

def get_option_ltp(tradingsymbol):
        EXCHANGE = "NFO"
        q = kite.ltp(f"{EXCHANGE}:{tradingsymbol}")
        return q[f"{EXCHANGE}:{tradingsymbol}"]["last_price"]


#=============================================LAST 7Days Data ========================================================
IST = pytz.timezone("Asia/Kolkata")

def get_last_n_trading_days(n=11):
    days = []
    d = datetime.now(IST).date()

    while len(days) < n:
        if d.weekday() < 5:  # Mon–Fri
            days.append(d)
        d -= timedelta(days=1)

    return min(days), max(days)
     

def fetch_nifty_daily_last_7_days(kite):
    from_date, to_date = get_last_n_trading_days(11)
    NIFTY_TOKEN = 256265 
    data = kite.historical_data(
        instrument_token=NIFTY_TOKEN,
        from_date=from_date,
        to_date=to_date,
        interval="day"
    )

    df = pd.DataFrame(data)

    if df.empty:
        return None

    # Standardize columns
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    df.set_index("date", inplace=True)

    df = df[["open", "high", "low", "close", "volume"]]

    return df


#====================================================================================================

def save_signal_log(signal: dict):
    if not isinstance(signal, dict):
        return   # safety guard

    file_path = f"signals_{TODAY}.csv"

    safe_signal = {}
    for k, v in signal.items():
        safe_signal[k] = str(v) if hasattr(v, "isoformat") else v

    df = pd.DataFrame([safe_signal])

    write_header = not os.path.exists(file_path)
    df.to_csv(file_path, mode="a", header=write_header, index=False)

def save_trade_log(trade: dict):
    file_path = f"trades_{TODAY}.csv"    # ✅ current working dir

    trade_copy = trade.copy()

    for k in ["entry_time", "exit_time", "signal_time"]:
        if k in trade_copy and trade_copy[k] is not None:
            trade_copy[k] = str(trade_copy[k])

    df = pd.DataFrame([trade_copy])

    write_header = not os.path.exists(file_path)
    df.to_csv(file_path, mode="a", header=write_header, index=False)
#=================================================SAFE GREEK =================================================

def evaluate(value, min_val=None, max_val=None):
    if min_val is not None and value < min_val:
        return "Fail"
    if max_val is not None and value > max_val:
        return "Fail"
    return "Pass"
#====================================================================================================


import os
from datetime import date

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

TODAY = date.today().strftime("%Y-%m-%d")


#=================================================SAFE initial SL =================================================

def calculate_initial_sl_from_15min(df_15m):
    """
    Initial SL logic:
    - Default: Low of current 15-min candle
    - If current candle size > avg size of last 7 trading days:
        SL = Mean of current candle
    """

    candles_per_day = 26
    lookback = 7 * candles_per_day

    if len(df_15m) < lookback + 1:
        return None, "INSUFFICIENT DATA FOR SL"

    current = df_15m.iloc[-1]

    cur_high = current["high"]
    cur_low = current["low"]

    cur_size = cur_high - cur_low
    cur_mean = (cur_high + cur_low) / 2

    recent = df_15m.iloc[-lookback:]
    avg_7d_size = (recent["high"] - recent["low"]).mean()

    if cur_size > avg_7d_size:
        return cur_mean, "BIG 15M CANDLE → SL = MEAN"
    else:
        return cur_low, "NORMAL 15M CANDLE → SL = LOW"


def calculate_initial_sl_15min(df):
    """
    df : DataFrame with 15-min candles
         Must contain columns: ['open', 'high', 'low', 'close']
         Latest candle should be the current candle
    """

    # ---- Current 15-min candle ----
    current = df.iloc[-1]
    current_high = current["high"]
    current_low = current["low"]

    current_candle_size = current_high - current_low
    current_candle_mean = (current_high + current_low) / 2

    # ---- Last 7 trading days average candle size ----
    candles_per_day = 26
    lookback_candles = 7 * candles_per_day

    recent_df = df.iloc[-lookback_candles:]

    avg_candle_size_7d = (recent_df["high"] - recent_df["low"]).mean()

    # ---- Decision Logic ----
    if current_candle_size > avg_candle_size_7d:
        initial_sl = current_candle_mean
        sl_reason = "BIG CANDLE → SL = CANDLE MEAN"
    else:
        initial_sl = current_low
        sl_reason = "NORMAL CANDLE → SL = 15MIN LOW"

    return initial_sl, sl_reason


#=================================================SAFE EXIT NEW  =================================================

def monitor_and_exit_last_position(kite, df_15m):
    pos = get_last_open_position(kite)

    if not pos:
        st.info("No open position to monitor")
        return

    symbol = pos["tradingsymbol"]
    qty = abs(pos["quantity"])
    entry_price = pos["average_price"]

    ltp = kite.ltp(f"NFO:{symbol}")[f"NFO:{symbol}"]["last_price"]

    # ---- Time ----
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)

    # ---- INITIAL SL FROM 15 MIN LOGIC ----
    initial_sl, sl_reason = calculate_initial_sl_from_15min(df_15m)

    if initial_sl is None:
        st.warning(sl_reason)
        return

    # ---- TRAILING LOGIC ----
    trail_start = entry_price * 1.007      # trail after +0.7%
    trail_step = 0.3 / 100                 # 0.3%

    if ltp > trail_start:
        tsl = max(initial_sl, ltp * (1 - trail_step))
    else:
        tsl = initial_sl

    # ---- TARGET ----
    target = entry_price * 1.02

    # ---- DISPLAY ----
    st.write("Initial SL:", initial_sl)
    st.write("SL Logic:", sl_reason)
    st.write("Trailing SL:", tsl)
    st.write("Target:", target)
    st.write("LTP:", ltp)
    st.write("Theta:", theta)
    # ---- EXIT CONDITIONS ----
    theta=st.session_state.GREEKtheta   
    if theta >= 50:
         reason = "THETA DECAY EXIT" 
    if ltp <= tsl:
        reason = "STOP LOSS HIT"
    elif ltp >= target:
        reason = "TARGET HIT"
    elif now.hour == 15 and now.minute >= 20:
        reason = "EOD EXIT"
    else:
        show_live_position(pos, ltp, tsl, target)
        return

    place_exit_order(kite, symbol, qty, reason)

#=================================================paper log =================================================

if "trade_log" not in st.session_state:
    st.session_state.trade_log = pd.DataFrame(columns=[
        "symbol",
        "entry_time",
        "signal_time",
        "entry_price",
        "quantity",
        "status",
        "remark"
    ])

def log_paper_trade(symbol, entry_price, qty, signal_time, remark):
    trade = {
        "symbol": symbol,
        "entry_time": datetime.now(),
        "signal_time": signal_time,
        "entry_price": entry_price,
        "quantity": qty,
        "status": "PAPER ENTRY",
        "remark": remark
    }

    # ---- Session log ----
    st.session_state.trade_log = pd.concat(
        [st.session_state.trade_log, pd.DataFrame([trade])],
        ignore_index=True
    )

    # ---- Persistent CSV ----
    file_path = "paper_trades.csv"
    df = pd.DataFrame([trade])

    if os.path.exists(file_path):
        df.to_csv(file_path, mode="a", header=False, index=False)
    else:
        df.to_csv(file_path, index=False)

#================================================= monitor_and_exit_trade =================================================

if "active_trade" not in st.session_state:
    st.session_state.active_trade = None   # holds current paper position

if "trade_log" not in st.session_state:
    st.session_state.trade_log = pd.DataFrame()
     
def get_live_option_price(kite, instrument_token):
    try:
        quote = kite.ltp([instrument_token])
        return quote[instrument_token]["last_price"]
    except Exception:
        return None



def monitor_and_exit_paper_trade(kite):
    trade = st.session_state.active_trade

    if trade is None or trade["status"] != "OPEN":
        return

    ltp = get_live_option_price(kite, trade["instrument_token"])
    if ltp is None:
        return

    entry = trade["entry_price"]

    # --------- EXIT CONDITIONS ---------
    exit_reason = None

    # 1️⃣ Stop Loss
    if ltp <= trade["sl"]:
        exit_reason = "STOP LOSS HIT"

    # 2️⃣ Target
    elif ltp >= trade["target"]:
        exit_reason = "TARGET HIT"

    # 3️⃣ Trailing SL update
    elif ltp > entry:
        new_trailing_sl = max(trade["trailing_sl"], ltp * 0.95)
        trade["trailing_sl"] = new_trailing_sl

        if ltp <= trade["trailing_sl"]:
            exit_reason = "TRAILING SL HIT"

    # 4️⃣ Time-based exit
    now = datetime.now().time()
    if now >= time(13, 30):
        exit_reason = "TIME EXIT"

    # --------- EXECUTE EXIT ---------
    if exit_reason:
        trade["exit_price"] = ltp
        trade["exit_time"] = datetime.now()
        trade["status"] = "CLOSED"
        trade["exit_reason"] = exit_reason
        trade["pnl"] = (ltp - entry) * trade["quantity"]

        # log trade
        st.session_state.trade_log = pd.concat(
            [st.session_state.trade_log, pd.DataFrame([trade])],
            ignore_index=True
        )

        st.session_state.active_trade = None

#=================================================SAFE exit =================================================


from datetime import datetime, timedelta
import pytz

def monitor_and_exit_paper_trades(kite):
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist)

    if not st.session_state.paper_trades:
        return

    for trade in st.session_state.paper_trades:

        # Process only OPEN trades
        if trade["status"] != "OPEN":
            continue

        symbol = trade["symbol"]
        option_type = trade["option_type"]
        entry_price = trade["entry_price"]
        qty = trade["quantity"]
        #sl = trade["stoploss"]
        if option_type == "CALL":
              sl = entry_price * 0.90
        else:  # PUT
              sl = entry_price * 1.10 
        entry_time = trade["entry_time"]

        # --- LIVE PRICE ---
        try:
            ltp = kite.ltp(f"NFO:{symbol}")[f"NFO:{symbol}"]["last_price"]
        except Exception:
            continue

        trade["ltp"] = ltp   # MTM tracking

        # -------------------------------
        # TRAILING SL LOGIC
        # -------------------------------
        trail_start = entry_price * 1.007    # +0.7%
        trail_step = 0.003                   # 0.3%

        if option_type == "CALL" and ltp > trail_start:
            sl = max(sl, ltp * (1 - trail_step))

        if option_type == "PUT" and ltp < trail_start:
           sl = min(sl, ltp * (1 + trail_step))

        #sl = trade["stoploss"]

        # -------------------------------
        # EXIT CONDITIONS
        # -------------------------------
        exit_reason = None

        if option_type == "CALL" and ltp <= sl:
            exit_reason = "SL HIT"

        if option_type == "PUT" and ltp >= sl:
            exit_reason = "SL HIT"

        #if now >= entry_time + timedelta(minutes=16):
            #exit_reason = "TIME EXIT"

        if now.hour == 15 and now.minute >= 20:
            exit_reason = "EOD EXIT"

        # -------------------------------
        # EXIT UPDATE
        # -------------------------------
        if exit_reason:
            trade["exit_price"] = ltp
            trade["exit_time"] = now
            trade["status"] = "CLOSED"
            trade["exit_reason"] = exit_reason

            trade["pnl"] = (
                (ltp - entry_price)
                * qty
                * (1 if option_type == "CALL" else -1)
            )
        return trade

#=================================================SAFE GREEK =================================================

def safe_option_greeks(S, K, expiry_dt, r, iv_percent, option_type="CALL"):
    #st.write("S, K, expiry_dt, r, iv_percent, option_type", S, K, expiry_dt, r, iv_percent, option_type) 
    now = datetime.now()
    #st.write("strike value:", strike)
    #st.write("strike type:", type(strike))
    #K = float(df["strike"].values[0])
    seconds = max((expiry_dt - now).total_seconds(), 3600)
    T = seconds / (365 * 24 * 60 * 60)

    sigma = max(iv_percent / 100, 0.05)

    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "CALL":
        delta = norm.cdf(d1)
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                 - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
    else:
        delta = norm.cdf(d1) - 1
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                 + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365

    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100
    #st.write("DEBUG GREEKS:", {"S": S, "K": K,"T": expiry_dt,"sigma": iv_percent,"delta": delta})
    return {
        "Delta": round(delta, 3),
        "Gamma": round(gamma, 6),
        "Theta": round(theta, 2),
        "Vega": round(vega, 2),
        "IV%": round(iv_percent, 2)
    }


#=================================================SAFE GREEK =================================================

def safe_option_greeks_15_jan(S, K, T, r, sigma, option_type="CALL"):

    T = max(T, 1/365)
    sigma = max(sigma, 0.05)

    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "CALL":
        delta = norm.cdf(d1)
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                 - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
    else:
        delta = norm.cdf(d1) - 1
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                 + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365

    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100

    return {
        "Delta": round(delta, 4),
        "Gamma": round(gamma, 6),
        "Theta": round(theta, 2),
        "Vega": round(vega, 2),
        "IV": round(sigma * 100, 2)
    }


#==================================================GREEKS========================================

import numpy as np
from scipy.stats import norm

def option_greeks(S, K, T, r, sigma, option_type="CE"):
    if T <= 0 or sigma <= 0:
        return None
    st.write("S, K, T, r, sigma, option_type",S, K, T, r, sigma, option_type)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    greeks = {}

    if option_type == "CE":
        greeks["Delta"] = norm.cdf(d1)
        greeks["Theta"] = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                            - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
    else:
        greeks["Delta"] = norm.cdf(d1) - 1
        greeks["Theta"] = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                            + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365

    greeks["Gamma"] = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    greeks["Vega"] = (S * norm.pdf(d1) * np.sqrt(T)) / 100
    greeks["IV"] = sigma * 100

    return greeks

#================================================================================================

def parse_signal_json(cell):
    if pd.isna(cell):
        return None
    try:
        return json.loads(cell)
    except Exception:
        return None


#=================================================================================================

def get_last_buy_order(kite):
    orders = kite.orders()

    buy_orders = [
        o for o in orders
        if o["transaction_type"] == "BUY"
        and o["status"] == "COMPLETE"
        and o["exchange"] == "NFO"
    ]

    if not buy_orders:
        return None

    # Latest order by time
    buy_orders.sort(
        key=lambda x: x["order_timestamp"],
        reverse=True
    )

    return buy_orders[0]


#=================================================================================================

def get_open_position_for_symbol(kite, tradingsymbol):
    positions = kite.positions()["net"]

    for p in positions:
        if (
            p["tradingsymbol"] == tradingsymbol
            and p["quantity"] != 0
        ):
            return p

    return None


#=================================================================================================
def exit_last_open_position(kite):
    last_order = get_last_buy_order(kite)

    if not last_order:
        st.info("No BUY order found today.")
        return

    symbol = last_order["tradingsymbol"]

    position = get_open_position_for_symbol(kite, symbol)

    if not position:
        st.info("Last order already exited. No open position.")
        return

    qty = abs(position["quantity"])

    try:
        kite.place_order(
            tradingsymbol=symbol,
            exchange=kite.EXCHANGE_NFO,
            transaction_type=kite.TRANSACTION_TYPE_SELL,
            quantity=qty,
            order_type=kite.ORDER_TYPE_MARKET,
            variety=kite.VARIETY_REGULAR,
            product=position["product"]
        )

        st.success(f"✅ Position EXITED: {symbol} | Qty: {qty}")

    except Exception as e:
        st.error(f"❌ Exit failed: {e}")



#=================================================================================================

def show_open_positions(kite):
    positions = kite.positions()["net"]

    open_pos = [p for p in positions if p["quantity"] != 0]

    if not open_pos:
        st.info("ℹ️ No Open Positions")
        return 0

    rows = []
    total_pnl = 0

    for p in open_pos:
        symbol = p["tradingsymbol"]
        qty = p["quantity"]
        entry = p["average_price"]

        ltp = kite.ltp(f"NFO:{symbol}")[f"NFO:{symbol}"]["last_price"]

        pnl = round((ltp - entry) * qty, 2)
        pnl_pct = round(((ltp - entry) / entry) * 100, 2)

        total_pnl += pnl

        rows.append({
            "Symbol": symbol,
            "Qty": qty,
            "Entry": entry,
            "LTP": ltp,
            "P&L (₹)": pnl,
            "P&L %": pnl_pct
        })

    df = pd.DataFrame(rows)

    st.subheader("📈 Open Positions")
    st.dataframe(df, use_container_width=True)

    st.metric("Open P&L", f"₹ {total_pnl:,.2f}")
    return total_pnl


#=================================================================================================


def show_closed_positions(kite):
    positions = kite.positions()["net"]

    closed_pos = [
        p for p in positions
        if p["quantity"] == 0 and p["buy_quantity"] > 0 and p["sell_quantity"] > 0
    ]

    if not closed_pos:
        st.info("ℹ️ No Closed Positions Today")
        return 0

    rows = []
    total_pnl = 0

    for p in closed_pos:
        symbol = p["tradingsymbol"]

        buy_qty = p["buy_quantity"]
        sell_qty = p["sell_quantity"]

        buy_val = p["buy_value"]
        sell_val = p["sell_value"]

        buy_price = round(buy_val / buy_qty, 2)
        sell_price = round(sell_val / sell_qty, 2)

        pnl = round(sell_val - buy_val, 2)
        pnl_pct = round((pnl / buy_val) * 100, 2)

        total_pnl += pnl

        rows.append({
            "Symbol": symbol,
            "Buy Qty": buy_qty,
            "Buy Price": buy_price,
            "Sell Qty": sell_qty,
            "Sell Price": sell_price,
            "Realized P&L (₹)": pnl,
            "P&L %": pnl_pct
        })

    df = pd.DataFrame(rows)

    st.subheader("📕 Closed Positions (Today)")
    st.dataframe(df, use_container_width=True)

    st.metric("Closed P&L", f"₹ {total_pnl:,.2f}")
    return total_pnl


def show_closed_positions0(kite):
    positions = kite.positions()["net"]

    closed_pos = [
        p for p in positions
        if p["quantity"] == 0 and (p["buy_quantity"] > 0 or p["sell_quantity"] > 0)
    ]

    if not closed_pos:
        st.info("ℹ️ No Closed Positions Today")
        return 0

    rows = []
    total_pnl = 0

    for p in closed_pos:
        symbol = p["tradingsymbol"]
        buy_val = p["buy_value"]
        sell_val = p["sell_value"]

        pnl = round(sell_val - buy_val, 2)

        pnl_pct = round((pnl / buy_val) * 100, 2) if buy_val > 0 else 0

        total_pnl += pnl

        rows.append({
            "Symbol": symbol,
            "Buy Value": buy_val,
            "Sell Value": sell_val,
            "Realized P&L (₹)": pnl,
            "P&L %": pnl_pct
        })

    df = pd.DataFrame(rows)

    st.subheader("📕 Closed Positions (Today)")
    st.dataframe(df, use_container_width=True)

    st.metric("Closed P&L", f"₹ {total_pnl:,.2f}")
    return total_pnl



#=================================================================================================


def get_last_open_position(kite):
    positions = kite.positions()["net"]
    for p in positions:
        if p["quantity"] != 0:
            return p
    return None


#-------------------------------------------------------------------------------
from datetime import datetime, timedelta
import pytz

def monitor_and_exit_last_position0(kite):
    pos = get_last_open_position(kite)

    if not pos:
        st.info("ℹ️ No open position to monitor")
        return

    symbol = pos["tradingsymbol"]
    qty = abs(pos["quantity"])
    entry_price = pos["average_price"]

    ltp = kite.ltp(f"NFO:{symbol}")[f"NFO:{symbol}"]["last_price"]

    # --- Time logic (minimum hold 16 minutes) ---
    ist = pytz.timezone("Asia/Kolkata")
    entry_time = pos["exchange_timestamp"]
    now = datetime.now(ist)

    #if now < entry_time + timedelta(minutes=16):
        #st.warning("⏳ Hold time < 16 min → Exit blocked")
        #return

    # --- BEST TRAILING SL ---
    # Initial SL: -0.5%
    # Trail after +0.7%
    initial_sl = entry_price * 0.90
    trail_start = entry_price * 0.993
    trail_step = 0.3 / 100     # 0.3%
    st.write("initial SL", initial_sl)  
    if ltp > trail_start:
        tsl = ltp * (1 - trail_step)
    else:
        tsl = initial_sl
    st.write("Trail SL", tsl) 
    # --- TARGET (optional safety cap) ---
    target = entry_price * 1.02   # 2%
    st.write("Target ", target)
    # --- EXIT CONDITIONS ---
    if ltp <= tsl:
        reason = "TRAIL SL HIT"
    elif ltp >= target:
        reason = "TARGET HIT"
    elif now.hour == 15 and now.minute >= 20:
        reason = "EOD EXIT"
    else:
        show_live_position(pos, ltp, tsl, target)
        return

    place_exit_order(kite, symbol, qty, reason)


#=================================================================================================


def place_exit_order(kite, symbol, qty, reason):
    try:
        kite.place_order(
            tradingsymbol=symbol,
            exchange=kite.EXCHANGE_NFO,
            transaction_type=kite.TRANSACTION_TYPE_SELL,
            quantity=qty,
            order_type=kite.ORDER_TYPE_MARKET,
            variety=kite.VARIETY_REGULAR,
            product=kite.PRODUCT_MIS
        )
        st.success(f"🚀 Exit Done → {symbol} | {reason}")

    except Exception as e:
        st.error(f"❌ Exit Failed: {e}")




#======================================show_live_position ===========================================================


def show_live_position(pos, ltp, tsl, target):
    pnl = (ltp - pos["average_price"]) * abs(pos["quantity"])
    pnl_pct = (ltp - pos["average_price"]) / pos["average_price"] * 100

    st.subheader("🟢 Live Open Position")
    st.write({
        "Symbol": pos["tradingsymbol"],
        "Qty": pos["quantity"],
        "Entry Price": pos["average_price"],
        "LTP": ltp,
        "P&L (₹)": round(pnl, 2),
        "P&L %": round(pnl_pct, 2),
        "Trailing SL": round(tsl, 2),
        "Target": round(target, 2)
    })



#==========================================has_open_position=======================================================

def has_open_position0(kite):
    positions = kite.positions()["net"]
    for p in positions:
        if p["quantity"] != 0 and p["product"] == kite.PRODUCT_MIS:
            return True
    return False

def has_open_position(kite, tradingsymbol=None):
    positions = kite.positions()["net"]
    for p in positions:
        if p["quantity"] != 0:
            if tradingsymbol is None or p["tradingsymbol"] == tradingsymbol:
                return True
    return False


#=================================================================================================

#=================================================================================================

#=================================================================================================

#=================================================================================================

#=================================================================================================

#=================================================================================================

#=================================================================================================




#===============================Exit Logic========================================================

def exit_logic(kite, order):
    symbol = order["tradingsymbol"]
    qty = order["quantity"]
    entry_price = order["average_price"]

    ltp = kite.ltp(f"NFO:{symbol}")[f"NFO:{symbol}"]["last_price"]

    target = entry_price * 1.01
    stoploss = entry_price * 0.995

    if ltp >= target:
        reason = "TARGET HIT"
    elif ltp <= stoploss:
        reason = "STOP LOSS HIT"
    else:
        return   # ❌ No exit yet

    try:
        kite.place_order(
            tradingsymbol=symbol,
            exchange=kite.EXCHANGE_NFO,
            transaction_type=kite.TRANSACTION_TYPE_SELL,
            quantity=qty,
            order_type=kite.ORDER_TYPE_MARKET,
            variety=kite.VARIETY_REGULAR,
            product=kite.PRODUCT_MIS
        )

        st.success(f"Exit done: {reason}")

    except Exception as e:
        st.error(f"Exit failed: {e}")


#-----------------------LAST ORDER----------------------------------------


def get_last_active_order(kite):
    orders = kite.orders()

    # Filter only BUY orders that are complete
    buy_orders = [
        o for o in orders
        if o["transaction_type"] == "BUY"
        and o["status"] == "COMPLETE"
    ]

    if not buy_orders:
        return None

    # Sort by order time (latest first)
    buy_orders.sort(
        key=lambda x: x["order_timestamp"],
        reverse=True
    )

    return buy_orders[0]   # ✅ Last active order


#--------------------------------------------Zerodha Instrument------------------

INSTRUMENTS_URL = "https://api.kite.trade/instruments"

@st.cache_data(ttl=24*60*60)  # cache for 1 day
def download_zerodha_instruments():
    df = pd.read_csv(INSTRUMENTS_URL)
    return df
#-------------------------------------------------------------------------------------------
if "instruments" not in st.session_state:
    st.session_state["instruments"] = download_zerodha_instruments()


#-----------------------------------------------telegram----------------------------------
from dotenv import load_dotenv  # pip install python-dotenv
import os

load_dotenv()  # this will read your .env and put values into os.environ[web:22][web:23]

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        # Optional: show warning in Streamlit
        # st.warning("Telegram env vars not set")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        requests.post(url, json=payload, timeout=5)  # sendMessage expects chat_id & text[web:8]
    except Exception as e:
        st.error(f"Telegram send error: {e}")

#-----------------------------------------------KITE---------------------------------------------------
 # --------------------------------------------------

 # Add after data processing:
def is_kite_connected(kite):
        try:
            kite.profile()
            return True
        except:
            return False

#-------------------------------------------------Singal 2------------------------------------------------------

def trading_multi2_signal_all_conditions(
    df,
    quantity=10 * 65,
    max_trades_per_day=2,
):
    """
    Multi-condition intraday option strategy
    - One trade per condition
    - First-break logic only
    - Trailing SL using swing points
    - Time exit after 16 minutes or 14:30
    """

    df = df.copy()
    signals = []

    # ---------------- BASIC SETUP ----------------
    df["Date"] = df["Datetime"].dt.date
    unique_days = sorted(df["Date"].unique())
    if len(unique_days) < 2:
        return None

    day0, day1 = unique_days[-2], unique_days[-1]

    # ---------------- BASE ZONE (3PM) ----------------
    candle_3pm = df[
        (df["Date"] == day0)
        & (df["Datetime"].dt.hour == 15)
        & (df["Datetime"].dt.minute == 0)
    ]
    if candle_3pm.empty:
        return None

    base_open = candle_3pm.iloc[0]["Open_^NSEI"]
    base_close = candle_3pm.iloc[0]["Close_^NSEI"]
    base_low, base_high = sorted([base_open, base_close])

    # ---------------- 9:15 CANDLE ----------------
    candle_915 = df[
        (df["Date"] == day1)
        & (df["Datetime"].dt.hour == 9)
        & (df["Datetime"].dt.minute == 15)
    ]
    if candle_915.empty:
        return None

    O1 = candle_915.iloc[0]["Open_^NSEI"]
    H1 = candle_915.iloc[0]["High_^NSEI"]
    L1 = candle_915.iloc[0]["Low_^NSEI"]
    C1 = candle_915.iloc[0]["Close_^NSEI"]
    entry_start_time = candle_915.iloc[0]["Datetime"]

    trade_end_time = entry_start_time.replace(hour=14, minute=30)
    expiry = get_nearest_weekly_expiry(pd.to_datetime(day1))
    spot_price = df["Close_^NSEI"].iloc[-1]

    day_df = df[
        (df["Date"] == day1)
        & (df["Datetime"] > entry_start_time)
        & (df["Datetime"] <= trade_end_time)
    ].sort_values("Datetime")

    # ---------------- SAFETY GUARDS ----------------
    fired_conditions = set()
    trade_count = 0

    # ---------------- HELPERS ----------------
    def recent_swing(time):
        recent = day_df[day_df["Datetime"] < time].tail(10)
        if recent.empty:
            return None, None
        return recent["High_^NSEI"].max(), recent["Low_^NSEI"].min()

    def monitor_trade(sig):
        sl = sig["stoploss"]
        exit_deadline = sig["entry_time"] + timedelta(minutes=16)

        for _, c in day_df.iterrows():
            if c["Datetime"] <= sig["entry_time"]:
                continue
            if c["Datetime"] >= exit_deadline:
                sig["exit_price"] = c["Close_^NSEI"]
                sig["exit_time"] = c["Datetime"]
                sig["status"] = "Time Exit"
                return sig

            high, low = recent_swing(c["Datetime"])

            if sig["option_type"] == "CALL" and low:
                sl = max(sl, low)
                if c["Low_^NSEI"] <= sl:
                    sig["exit_price"] = sl
                    sig["exit_time"] = c["Datetime"]
                    sig["status"] = "SL Hit"
                    return sig

            if sig["option_type"] == "PUT" and high:
                sl = min(sl, high)
                if c["High_^NSEI"] >= sl:
                    sig["exit_price"] = sl
                    sig["exit_time"] = c["Datetime"]
                    sig["status"] = "SL Hit"
                    return sig

        last = day_df.iloc[-1]
        sig["exit_price"] = last["Close_^NSEI"]
        sig["exit_time"] = last["Datetime"]
        sig["status"] = "Forced Exit 14:30"
        return sig

    # ---------------- MAIN LOOP ----------------
    for i in range(1, len(day_df)):
        if trade_count >= max_trades_per_day:
            break

        candle = day_df.iloc[i]
        prev = day_df.iloc[i - 1]
        high, low = recent_swing(candle["Datetime"])

        # -------- CONDITION 2 (PUT GAP DOWN) --------
        if (
            2 not in fired_conditions
            and C1 < base_low
            and prev["Low_^NSEI"] > L1
            and candle["Low_^NSEI"] <= L1
        ):
            sig = {
                "condition": 2,
                "option_type": "PUT",
                "buy_price": L1,
                "entry_time": candle["Datetime"],
                "spot_price": spot_price,
                "stoploss": high,
                "quantity": quantity,
                "expiry": expiry,
                "message": "Cond 2: First break below L1 → BUY PUT",
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            fired_conditions.add(2)
            trade_count += 1
            continue

        # -------- CONDITION 3 (CALL GAP UP) --------
        if (
            3 not in fired_conditions
            and C1 > base_high
            and prev["High_^NSEI"] < H1
            and candle["High_^NSEI"] >= H1
        ):
            sig = {
                "condition": 3,
                "option_type": "CALL",
                "buy_price": H1,
                "entry_time": candle["Datetime"],
                "spot_price": spot_price,
                "stoploss": low,
                "quantity": quantity,
                "expiry": expiry,
                "message": "Cond 3: First break above H1 → BUY CALL",
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            fired_conditions.add(3)
            trade_count += 1
            continue

    return signals if signals else None

#------------------------------------------------Signal generation -------------------------------------------------------
def trading_multi1_signal_all_conditions(df, quantity=10*65, return_all_signals=True):
    def get_recent_swing(current_time):
        recent = df[(df['Date'] == day1) &
                    (df['Datetime'] < current_time)].tail(10)
        if recent.empty:
            return np.nan, np.nan
        return float(recent['High_^NSEI'].max()), float(recent['Low_^NSEI'].min())

    def update_trailing_sl(option_type, sl, current_time):
        high, low = get_recent_swing(current_time)

        if option_type == 'CALL' and pd.notna(low):
            return max(sl, low) if pd.notna(sl) else low

        if option_type == 'PUT' and pd.notna(high):
            return min(sl, high) if pd.notna(sl) else high

        return sl

    def monitor_trade(sig):
         sl = sig['stoploss']
         exit_deadline = sig['entry_time'] + timedelta(minutes=16)
         
         for _, candle in day1_after_915.iterrows():
     
             # Stop monitoring after 2:30 PM
             if candle['Datetime'] > trade_end_time:
                 break
     
             # Ignore candles before entry
             if candle['Datetime'] <= sig['entry_time']:
                 continue
     
             # Time-based exit
             if candle['Datetime'] >= exit_deadline:
                 sig['exit_price'] = candle['Close_^NSEI']
                 sig['exit_time'] = candle['Datetime']
                 sig['status'] = 'Time Exit'
                 return sig
     
             # Update trailing SL
             sl = update_trailing_sl(sig['option_type'], sl, candle['Datetime'])
             sig['stoploss'] = sl
     
             # SL hit checks
             if sig['option_type'] == 'CALL' and pd.notna(sl) and candle['Low_^NSEI'] <= sl:
                 sig['exit_price'] = sl
                 sig['exit_time'] = candle['Datetime']
                 sig['status'] = 'SL Hit'
                 return sig
     
             if sig['option_type'] == 'PUT' and pd.notna(sl) and candle['High_^NSEI'] >= sl:
                 sig['exit_price'] = sl
                 sig['exit_time'] = candle['Datetime']
                 sig['status'] = 'SL Hit'
                 return sig
     
         # Force exit at 2:30 or last available candle
         last_candle = day1_after_915[day1_after_915['Datetime'] <= trade_end_time].iloc[-1]
         sig['exit_price'] = last_candle['Close_^NSEI']
         sig['exit_time'] = last_candle['Datetime']
         sig['status'] = 'Forced Exit @ 14:30'
         return sig    
 
    signals = []
    spot_price = df['Close_^NSEI'].iloc[-1]

    df = df.copy()
    df['Date'] = df['Datetime'].dt.date
    unique_days = sorted(df['Date'].unique())
    if len(unique_days) < 2:
        return None

    day0 = unique_days[-2]
    day1 = unique_days[-1]

    candle_3pm = df[(df['Date'] == day0) &
                    (df['Datetime'].dt.hour == 15) &
                    (df['Datetime'].dt.minute == 0)]
    if candle_3pm.empty:
        return None

    base_open = candle_3pm.iloc[0]['Open_^NSEI']
    base_close = candle_3pm.iloc[0]['Close_^NSEI']
    base_low = min(base_open, base_close)
    base_high = max(base_open, base_close)

    candle_915 = df[(df['Date'] == day1) &
                    (df['Datetime'].dt.hour == 9) &
                    (df['Datetime'].dt.minute == 15)]
    if candle_915.empty:
        return None
    O1 = candle_915.iloc[0]['Open_^NSEI'] 
    H1 = candle_915.iloc[0]['High_^NSEI']
    L1 = candle_915.iloc[0]['Low_^NSEI']
    C1 = candle_915.iloc[0]['Close_^NSEI']

    #st.subheader("9:15 AM Candle (NIFTY)")
    #st.write({"Open": O1,"High": H1,"Low": L1,"Close": C1})  
    entry_time = candle_915.iloc[0]['Datetime']
    trade_end_time = entry_time.replace(hour=14, minute=30, second=0)
    expiry = get_nearest_weekly_expiry(pd.to_datetime(day1))

    day1_after_915 = df[(df['Date'] == day1) &
                        (df['Datetime'] > entry_time)].sort_values('Datetime')

    last_exit_time = None   # ✅ TRACK LAST TRADE EXIT

   
    # ==================================================
    # CONDITION SCANS (MULTIPLE SIGNALS)
    # ==================================================
    #exit_deadline = candle['entry_time'] + timedelta(minutes=16) 
    for _, candle in day1_after_915.iterrows():
        if candle['Datetime'] > trade_end_time:
             break

        #//if candle['Datetime'] <= exit_deadline:
             #/continue  
        if last_exit_time and candle['Datetime'] <= last_exit_time:
            continue
        swing_high, swing_low = get_recent_swing(candle['Datetime'])

        # ---- Condition 1
        if (L1 < base_high and H1 > base_low) and C1 > base_high:
            sig = {
                'condition': 1,
                'option_type': 'CALL',
                'buy_price': H1,
                'stoploss': swing_low,
                'quantity': quantity,
                'expiry': expiry,
                'entry_time': candle['Datetime'],
                'spot_price': spot_price,
                'message': 'Condition 1: Bullish breakout above Base Zone → Buy CALL above H1'
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            last_exit_time = sig['exit_time']
            continue

        # ---- Condition 2
        if C1 < base_low and candle['Low_^NSEI'] <= L1:
            sig = {
                'condition': 2,
                'option_type': 'PUT',
                'buy_price': L1,
                'entry_time': candle['Datetime'],
                'spot_price': spot_price,
                'message': 'Condition 2: Gap down confirmed → Buy PUT below L1',
                'stoploss': swing_high,
                'quantity': quantity,
                'expiry': expiry
               
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            last_exit_time = sig['exit_time']
            continue

        # ---- Flip 2.7
        if C1 < base_low and candle['Close_^NSEI'] > base_high:
            sig = {
                'condition': 2.7,
                'option_type': 'CALL',
                'entry_time': candle['Datetime'],
                'buy_price': candle['High_^NSEI'],
                'spot_price': spot_price,
                'stoploss': swing_low,
                'quantity': quantity,
                'expiry': expiry, 
                'message': 'Condition 2.7 Flip: Later candle closed above Base Zone → Buy CALL'
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            last_exit_time = sig['exit_time']
            continue

        # ---- Condition 3
        if C1 > base_high and candle['High_^NSEI'] >= H1:
            sig = {
                'condition': 3,
                'option_type': 'CALL',
                'buy_price': H1,
                'entry_time': candle['Datetime'],
                'spot_price': spot_price,
                'stoploss': swing_low,
                'quantity': quantity,
                'expiry': expiry,
                'message': 'Condition 3: Gap up confirmed → Buy CALL above H1'
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            last_exit_time = sig['exit_time']
            continue

        # ---- Flip 3.7
        if C1 > base_high and candle['Close_^NSEI'] < base_low:
            sig = {
                'condition': 3.7,
                'option_type': 'PUT',
                'buy_price': candle['Low_^NSEI'],
                'entry_time': candle['Datetime'],
                'spot_price': spot_price,
                'stoploss': swing_high,
                'quantity': quantity,
                'expiry': expiry,
                'message': 'Condition 3 Flip: Later candle closed below Base Zone → Buy PUT'
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            last_exit_time = sig['exit_time']
            continue

        # ---- Condition 4
        if (L1 < base_high and H1 > base_low) and C1 < base_low:
            sig = {
                'condition': 4,
                'option_type': 'PUT',
                'buy_price': L1,
                'entry_time': candle['Datetime'],
                'spot_price': spot_price,
                'message': 'Condition 4: Bearish breakdown below Base Zone → Buy PUT below L1',
                'stoploss': swing_high,
                'quantity': quantity,
                'expiry': expiry,
                
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            last_exit_time = sig['exit_time']
            continue

    return signals if signals else None

#-----------------------------------------Exit paper Trade----------------------------------------------------

def normalize_trade(trade):
    trade.setdefault("highest_price", trade["entry_price"])
    trade.setdefault("partial_exit_done", False)
    trade.setdefault("final_exit_done", False)
    trade.setdefault("remaining_qty", trade["quantity"])
    trade.setdefault("status", "OPEN")

#=================================================================================================== 
def manage_exit_papertrade(kite, trade):

    normalize_trade(trade)   # 🔒 ALWAYS normalize first

    entry_time = trade.get("entry_time")
    entry_price = trade.get("entry_price")
    qty = trade.get("remaining_qty", 0)

    if trade["status"] != "OPEN":
        return

    symbol = f"NFO:{trade['symbol']}"

    try:
        ltp = kite.ltp(symbol)[symbol]["last_price"]
    except:
        return

    # 🧠 Example exit logic
    target = entry_price * 1.25
    sl = entry_price * 0.85

    # 🎯 Partial exit (50%)
    if not trade["partial_exit_done"] and ltp >= target:
        trade["remaining_qty"] = qty // 2
        trade["partial_exit_done"] = True
        st.success(f"Partial exit @ {ltp}")

    # ❌ Final SL / Exit
    if ltp <= sl:
        trade["remaining_qty"] = 0
        trade["final_exit_done"] = True
        trade["status"] = "CLOSED"
        st.error(f"Trade exited @ {ltp}")
#===================================================================================================     
def manage_exit_papertrade23(kite, trade):

    if trade["status"] != "OPEN":
        return

    symbol = f"NFO:{trade['symbol']}"
    ltp = kite.ltp(symbol)[symbol]["last_price"]

    entry = trade["entry_price"]
    now = datetime.now()
    from zoneinfo import ZoneInfo
    now = datetime.now(ZoneInfo("Asia/Kolkata")) 
    st.write("Time Now=",now) 

    # Update highest price (trailing SL base)
    #trade["highest_price"] = max(trade["highest_price"], ltp)
    if "highest_price" not in trade:
         trade["highest_price"] = trade["entry_price"]
     
    trade["highest_price"] = max(trade["highest_price"], ltp)
 

    # ---------- EXIT CALCULATIONS ----------
    trailing_sl = round(trade["highest_price"] * 0.90, 2)
    partial_target = round(entry * 1.10, 2)
    #time_exit_at = trade["entry_time"] + timedelta(minutes=16)
    IST = ZoneInfo("Asia/Kolkata") 
    # 🔒 FORCE entry_time to Python datetime (IST)
    entry_time = trade["entry_time"]

    if isinstance(entry_time, pd.Timestamp):
         entry_time = entry_time.to_pydatetime()

    if entry_time.tzinfo is None:
         entry_time = entry_time.replace(tzinfo=IST)

    trade["entry_time"] = entry_time  # overwrite safely 
     
    time_exit_at = entry_time + timedelta(minutes=16)
     
    trade["ltp"] = ltp
    trade["trailing_sl"] = trailing_sl

    # ---------- PARTIAL EXIT (50%) ----------
    if (not trade["partial_exit_done"]) and ltp >= partial_target:
        trade["partial_exit_done"] = True
        trade["remaining_qty"] = trade["quantity"] // 2
        tradeIT;
        trade["partial_exit_price"] = ltp
        trade["partial_exit_time"] = now
        trade["exit_reason"] = "50% BOOKED @ +10%"

    # ---------- FINAL EXIT CONDITIONS ----------
    exit_reason = None

    if ltp <= trailing_sl:
        exit_reason = "TRAILING SL HIT"

    elif now >= time_exit_at:
        exit_reason = "TIME EXIT (16 MIN)"

    # ---------- FINAL EXIT ----------
    if exit_reason and not trade["final_exit_done"]:
        trade["final_exit_done"] = True
        trade["status"] = "CLOSED"
        trade["exit_reason"] = exit_reason
        trade["exit_price"] = ltp
        trade["exit_time"] = now
        trade["remaining_qty"] = 0


#--------------------------------------Check Trade Time-------------------------------------------------------

def trade_already_taken(signal_time, symbol):
    for trade in st.session_state.paper_trades:
        if (
            trade["entry_time"] == signal_time
            and trade["symbol"] == symbol
            and trade["status"] == "OPEN"
        ):
            return True
    return False

#----------------------------Moniter Paper tRade----------------------------------------------------


def monitor_paper_trades(kite):
    if not st.session_state.get("paper_trades"):
        return

    rows = []

    for trade in st.session_state.paper_trades:

        # 🛡 Normalize trade (important)
        trade.setdefault("quantity", trade.get("remaining_qty", 0))
        trade.setdefault("remaining_qty", trade.get("quantity", 0))
        trade.setdefault("status", "OPEN")

        if trade["status"] != "OPEN":
            continue

        symbol = f"NFO:{trade['symbol']}"

        try:
            ltp = kite.ltp(symbol)[symbol]["last_price"]
        except Exception as e:
            st.warning(f"LTP fetch failed for {trade['symbol']}")
            continue

        qty = trade.get("quantity", 0)

        pnl = round(
            (ltp - trade.get("entry_price", 0)) * qty,
            2
        )

        rows.append({
            "Entry Time": trade.get("entry_time"),
            "Symbol": trade.get("symbol"),
            "Type": trade.get("option_type"),
            "Entry Price": trade.get("entry_price"),
            "LTP": ltp,
            "Qty": qty,
            "P&L (₹)": pnl,
            "Status": trade.get("status")
        })

    if rows:
        df = pd.DataFrame(rows)

        #st.subheader("📊 Paper Trade Monitor")
        #st.dataframe(df, use_container_width=True)

        #st.metric(            "Total P&L",            f"₹ {df['P&L (₹)'].sum():,.2f}"        )

#==========================================================================================================
def monitor_paper_trades23(kite):
    if not st.session_state.paper_trades:
        return

    rows = []

    for trade in st.session_state.paper_trades:
        if trade["status"] != "OPEN":
            continue

        symbol = f"NFO:{trade['symbol']}"
        ltp = kite.ltp(symbol)[symbol]["last_price"]

        pnl = round(
            (ltp - trade["entry_price"]) * trade["quantity"], 2
        )

        rows.append({
            "Entry Time": trade["entry_time"],
            "Symbol": trade["symbol"],
            "Type": trade["option_type"],
            "Entry Price": trade["entry_price"],
            "LTP": ltp,
            "Qty": trade["quantity"],
            "P&L (₹)": pnl,
            "Status": trade["status"]
        })

    if rows:
        df = pd.DataFrame(rows)

        st.subheader("📊 Paper Trade Monitor")
        st.dataframe(df, use_container_width=True)

        st.metric("Total P&L", f"₹ {df['P&L (₹)'].sum():,.2f}")

#st_autorefresh(interval=30000, key="live_data_refresh")
#st.sidebar.image("shree.jpg",width=15)  # Correct parameter
# ------------------------------------------------------------
# Page Config & Global Theming
#---------------------------------------------------------------------------------------------------------------
def compute_iv_rank(current_iv, iv_min=0.10, iv_max=0.35):
         """
         Very simple IV rank model:
         rank = (current_iv - min) / (max - min)
         """
         if current_iv is None:
             return None
     
         if iv_max == iv_min:
             return None
     
         rank = (current_iv - iv_min) / (iv_max - iv_min)
         return max(0, min(rank, 1))

from math import log, sqrt, exp
from scipy.stats import norm

def black_scholes_call_iv(spot, strike, time_to_expiry, ltp, r=0.0, tol=1e-5, max_iter=100):
    """
    Robust IV solver for CALL option using Newton-Raphson.
    Returns None if IV cannot be computed safely.
    """

    try:
        spot = float(spot)
        strike = float(strike)
        ltp = float(ltp)
        time_to_expiry = float(time_to_expiry)
    except (TypeError, ValueError):
        return None

    if spot <= 0 or strike <= 0 or ltp <= 0 or time_to_expiry <= 0:
        return None

    # Intrinsic value check (CRITICAL)
    intrinsic = max(spot - strike, 0.0)
    if ltp < intrinsic:
        return None

    sigma = 0.20  # initial guess

    for _ in range(max_iter):
        try:
            d1 = (log(spot/strike) + (r + 0.5*sigma*sigma)*time_to_expiry) / (sigma*sqrt(time_to_expiry))
            d2 = d1 - sigma*sqrt(time_to_expiry)

            theoretical = spot * norm.cdf(d1) - strike * exp(-r*time_to_expiry) * norm.cdf(d2)
            vega = spot * norm.pdf(d1) * sqrt(time_to_expiry)
        except Exception:
            return None

        if vega < 1e-8:
            return None

        diff = theoretical - ltp

        if abs(diff) < tol:
            return round(sigma, 4)

        sigma = sigma - diff / vega

        # Sigma bounds
        if sigma <= 0 or sigma > 5:
            return None

    return None

def black_scholes_call_iv_jan_26(spot, strike, time_to_expiry, ltp, r=0.0, tol=1e-5, max_iter=100):
         """
         Safe IV solver for CALL option using Newton-Raphson.
         Returns None if no valid IV found.
         """
     
         if ltp <= 0 or spot <= 0 or time_to_expiry <= 0:
             return None
     
         sigma = 0.20  # initial guess
     
         for _ in range(max_iter):
             d1 = (log(spot/strike) + (r + 0.5*sigma*sigma)*time_to_expiry) / (sigma*sqrt(time_to_expiry))
             d2 = d1 - sigma*sqrt(time_to_expiry)
     
             theoretical = spot*norm.cdf(d1) - strike*exp(-r*time_to_expiry)*norm.cdf(d2)
     
             vega = spot * norm.pdf(d1) * sqrt(time_to_expiry)
     
             if vega < 1e-8:    # too flat, cannot converge
                 return None
     
             diff = theoretical - ltp
     
             if abs(diff) < tol:
                 return sigma
     
             sigma = sigma - diff/vega
     
             if sigma <= 0:
                 return None
     
         return None
     #-------------------------------------------------------------------------------------
def compute_option_iv_details(option_dict, spot_price):
         """
         option_dict example:
         {
             "tradingsymbol":"NIFTY25D1625850CE",
             "strike":25850,
             "instrument_token":12343810,
             "option_type":"CALL",
             "expiry": Timestamp('2025-12-16 00:00:00'),
             "lot_size":75,
             "tick_size":0.05,
             "segment":"NFO-OPT",
             "exchange":"NFO",
             "name":"NIFTY",
             "ltp":138.65
         }
         """
         spot_price=option_dict.get("spot")
         ltp = option_dict.get("ltp")
         strike = option_dict.get("strike")
         expiry = option_dict.get("expiry")
         is_call = option_dict.get("option_type") == "CALL"
     
         # Compute time to expiry (in years)
         days_to_exp = days_to_expiry(expiry)
         time_to_expiry = days_to_exp / 365
     
         # Compute IV
         iv = black_scholes_call_iv(
             spot=spot_price,
             strike=strike,
             time_to_expiry=time_to_expiry,
             ltp=ltp,
             r=0.065
         )
     
         # Compute IV Rank
         iv_rank = compute_iv_rank(iv)
     
         # If IV fails, return zeros (based on your requirement)
         if iv is None:
             iv = 0
         if iv_rank is None:
             iv_rank = 0
     
         return {
             "ltp": ltp,
             "spot": spot_price,
             "strike": strike,
             "days_to_expiry": days_to_exp,
             "time_to_expiry_years": time_to_expiry,
             "is_call": is_call,
             "iv": iv,
             "iv_rank": iv_rank
         }
# -----------------------------------Exit Logic----------------------------------------------------------------

#------------------------------------------------------------------------------------------------------------
def manage_exit(kite, tradingsymbol, qty):

    if not st.session_state.trade_active:
        return

    # Live LTP
    ltp = kite.ltp(f"NFO:{tradingsymbol}")[f"NFO:{tradingsymbol}"]["last_price"]

    entry = st.session_state.entry_price
    now = datetime.now()

    # Update highest price for trailing SL
    st.session_state.highest_price = max(
        st.session_state.highest_price, ltp
    )

    # ---------- EXIT CALCULATIONS ----------
    trailing_sl = round(st.session_state.highest_price * 0.90, 2)
    partial_target = round(entry * 1.10, 2)
    time_exit_at = st.session_state.entry_time + timedelta(minutes=16)

    st.info(
        f"LTP: {ltp} | SL: {trailing_sl} | Partial TP: {partial_target}"
    )

    # ---------- PARTIAL EXIT (50%) ----------
    if not st.session_state.partial_exit_done and ltp >= partial_target:
        try:
            kite.place_order(
                tradingsymbol=tradingsymbol,
                exchange=kite.EXCHANGE_NFO,
                transaction_type=kite.TRANSACTION_TYPE_SELL,
                quantity=qty // 2,
                order_type=kite.ORDER_TYPE_MARKET,
                product=kite.PRODUCT_MIS,
                variety=kite.VARIETY_REGULAR
            )
            st.session_state.partial_exit_done = True
            st.success("✅ 50% Profit Booked @ +10%")

        except Exception as e:
            st.error(f"Partial Exit Failed: {e}")

    # ---------- TRAILING STOPLOSS ----------
    if ltp <= trailing_sl:
        exit_reason = "TRAILING SL HIT"

    # ---------- TIME EXIT ----------
    elif now >= time_exit_at:
        exit_reason = "TIME EXIT (16 min)"

    else:
        exit_reason = None

    # ---------- FINAL EXIT ----------
    if exit_reason and not st.session_state.final_exit_done:
        try:
            kite.place_order(
                tradingsymbol=tradingsymbol,
                exchange=kite.EXCHANGE_NFO,
                transaction_type=kite.TRANSACTION_TYPE_SELL,
                quantity=qty if not st.session_state.partial_exit_done else qty // 2,
                order_type=kite.ORDER_TYPE_MARKET,
                product=kite.PRODUCT_MIS,
                variety=kite.VARIETY_REGULAR
            )

            st.session_state.final_exit_done = True
            st.session_state.trade_active = False
            st.success(f"🚪 Trade Exited: {exit_reason}")

        except Exception as e:
            st.error(f"Final Exit Failed: {e}")

#------------------------Parameters-----------------------------------------------------------------------------
st.set_page_config(
    page_title="TALK AlgoLabs Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
if "kite" not in st.session_state:
        st.session_state.kite = None
else:
        kite = st.session_state.get("kite")

def is_kite_connected(kite):
        try:
            kite.profile()
            return True
        except:
            return False
             

@st.cache_data
def load_kite_instruments():
    return pd.read_csv("instruments.csv")


 #-------------------------------------------------------NEW IV CLACL--------------------------------------- 
import math

     # Black-Scholes call price
def bs_call_price(S, K, T, r, sigma):
         if sigma <= 0:
             return 0.0
         d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
         d2 = d1 - sigma * math.sqrt(T)
         Nd1 = 0.5 * (1.0 + math.erf(d1 / math.sqrt(2.0)))
         Nd2 = 0.5 * (1.0 + math.erf(d2 / math.sqrt(2.0)))
         return S * Nd1 - K * math.exp(-r * T) * Nd2

def implied_vol_call(S, K, T, r, C_mkt, tol=1e-6, max_iter=100):
     
         # ---------- HARD GUARDS ----------
         # ---------- HARD GUARDS ----------
         if S is None or K is None or T is None or C_mkt is None:
             return None
     
         try:
             S = float(S)
             K = float(K)
             T = float(T)
             C_mkt = float(C_mkt)
         except (TypeError, ValueError):
             return None
     
         if S <= 0 or K <= 0 or T <= 0 or C_mkt <= 0:
             return None 
         #if S <= 0 or K <= 0:
             #return None
     
        # if T <= 0:
             #return None   # expired
     
         if C_mkt is None or C_mkt <= 0:
             return None   # invalid option price
               
         low, high = 1e-6, 5.0  # 0.0001% to 500% vol
     
         for _ in range(max_iter):
             sigma = 0.5 * (low + high)
     
             price = bs_call_price(S, K, T, r, sigma)
             if price is None:
                 return None
     
             if abs(price - C_mkt) < tol:
                 return sigma
     
             if price > C_mkt:
                 high = sigma
             else:
                 low = sigma
     
         return sigma  # best guess


def implied_vol_call1(S, K, T, r, C_mkt, tol=1e-6, max_iter=100):
         low, high = 1e-6, 5.0      # 0.0001% to 500% vol range
          # ---- HARD GUARDS ----
         if S <= 0 or K <= 0:
             return None

         if T <= 0:
             return None   # expiry reached
     
         if mid <= 0:
             return None   # no valid option price
     
         try:
             price = bs_call_price(S, K, T, r, mid)
             return price
         except ZeroDivisionError:
             return None
 
         for _ in range(max_iter):
             mid = 0.5 * (low + high)
             price = bs_call_price(S, K, T, r, mid)
             if abs(price - C_mkt) < tol:
                 return mid
             if price > C_mkt:
                 high = mid
             else:
                 low = mid
         return mid  # best guess if not converged
def get_option_instrument_details0(tradingsymbol):
         df = load_kite_instruments()
         row = df[df["tradingsymbol"] == tradingsymbol]
     
         if row.empty:
             return None
     
         row = row.iloc[0]
     
         return {
             "tradingsymbol": tradingsymbol,
             "strike": row["strike"],
             "instrument_token": int(row["instrument_token"]),
             "option_type": "CALL" if row["instrument_type"] == "CE" else "PUT",
             "expiry": str(row["expiry"]),
             "lot_size": int(row["lot_size"]),
             "tick_size": float(row["tick_size"]),
             "segment": row["segment"],
             "exchange": row["exchange"],
             "name": row["name"]
         }

def get_option_instrument_details(tradingsymbol):
    #df = instruments_df.copy()
    df = load_kite_instruments()  
    df.columns = df.columns.str.strip().str.lower()

    if "tradingsymbol" not in df.columns:
        raise ValueError(f"'tradingsymbol' column not found. Columns = {df.columns.tolist()}")

    row = df.loc[df["tradingsymbol"] == tradingsymbol]

    if row.empty:
        raise ValueError(f"Tradingsymbol not found: {tradingsymbol}")

    return row.iloc[0].to_dict()


def get_option_instrument_details1(tradingsymbol):
    # force scalar
    if isinstance(tradingsymbol, pd.Series):
        tradingsymbol = tradingsymbol.iloc[0]

    row = df[df["tradingsymbol"] == tradingsymbol]

    if row.empty:
        return None

    return row.iloc[0].to_dict()

def enrich_with_ltp(kite, option_data):
    symbol = f"NFO:{option_data['tradingsymbol']}"

    try:
        ltp_data = kite.ltp(symbol)

        if not ltp_data or symbol not in ltp_data:
            st.error("LTP data missing from Kite response")
            return None

        option_data["ltp"] = ltp_data[symbol]["last_price"]
        return option_data

    except PermissionException:
        st.error(
            "🚫 No permission for live market data.\n"
            "Check Kite API subscription and derivatives access."
        )
        return None

    except TokenException:
        st.error("🔑 Kite session expired. Please re-login.")
        return None

    except Exception as e:
        st.error(f"Unexpected error while fetching LTP: {e}")
        return None


def enrich_with_ltp10(kite, option_data):
         #st.write("Optiion Data",option_data) 
         symbol = f"NFO:{option_data['tradingsymbol']}"
         #st.write("Optiion Symbol",symbol)   
         #ltp_data = kite.ltp(symbol)
         try:
             ltp_data = kite.ltp(symbol)
             return ltp_data
     
         except PermissionException:
             st.error(
                 "🚫 You do not have permission to access live market data or algo trading.\n\n"
                 "Please check:\n"
                 "• Kite API subscription status\n"
                 "• Market data / derivatives access\n"
                 "• Whether your API key is active\n"
             )
             return None
     
         except TokenException:
             st.error("🔑 Session expired. Please re-login to Kite.")
             return None
     
         except Exception as e:
             st.error(f"Unexpected error while fetching LTP: {e}")
             return None 
         #st.write("Optiion ltp_data",ltp_data)     
         option_data["ltp"] = ltp_data[symbol]["last_price"]
         return option_data
         
def get_live_option_details(kite, tradingsymbol):
         base = get_option_instrument_details(tradingsymbol)
         if base is None:
             return None
         return enrich_with_ltp(kite, base)
     
     
def days_to_expiry(expiry_timestamp):
         """Robust expiry calculator handling messy formats like Timestamp('2025-12-16')."""
     
         if expiry_timestamp is None:
             return 0
     
         # Convert strings safely
         if isinstance(expiry_timestamp, str):
     
             # Case: "Timestamp('2025-12-16 00:00:00')"
             if expiry_timestamp.startswith("Timestamp("):
                 # Remove Timestamp( and )
                 expiry_timestamp = expiry_timestamp.replace("Timestamp(", "").replace(")", "")
                 # Remove extra single quotes:  '2025-12-16 00:00:00'
                 expiry_timestamp = expiry_timestamp.strip("'").strip('"')
     
             # Now convert clean string to datetime
             try:
                 expiry_timestamp = pd.to_datetime(expiry_timestamp)
             except Exception:
                 # Fallback: return 0 days
                 return 0
     
         # If still not a pandas Timestamp → convert it
         if not hasattr(expiry_timestamp, "tzinfo"):
             expiry_timestamp = pd.to_datetime(expiry_timestamp)
     
         # Timezone aware vs naive handling
         if expiry_timestamp.tzinfo is None:
             now = datetime.now()
         else:
             now = datetime.now(expiry_timestamp.tzinfo)
     
         diff = expiry_timestamp - now
         days = diff.total_seconds() / 86400
     
         return max(days, 0)

#--------------------------------------------------------NEW IV Calc-----------------------------------------
#--------------------------------------------SIGNAL TIME-----------------------------------------------------

from datetime import datetime, time
import pytz

import pytz
#import datetime
def is_valid_signal_time(signal_dt):
    """Return True only if signal date is today and time is within trading window."""

    from datetime import datetime, time
    import pytz

    IST = pytz.timezone("Asia/Kolkata")

    START_TIME = time(9, 30)      # ✅ FIXED
    END_TIME   = time(14, 30)     # ✅ FIXED

    # Ensure timezone-aware
    if signal_dt.tzinfo is None:
        signal_dt = IST.localize(signal_dt)

    now = datetime.now(IST)

    # Same trading day
    if signal_dt.date() != now.date():
        return False

    # Trading window
    if not (START_TIME <= signal_dt.time() <= END_TIME):
        return False

    return True

def is_valid_signal_time03(signal_dt):
    """Return True only if signal date is today and time is within trading window."""
    from datetime import datetime, time
    import pytz 
    IST = pytz.timezone("Asia/Kolkata")

    #START_TIME = datetime.time(9, 30)     # ✅ SAFE
    #END_TIME   = datetime.time(14, 30)    # ✅ SAFE
    START_TIME = time(9, 30)      # ✅ FIXED
    END_TIME   = time(14, 30)     # ✅ FIXED 
    #st.write("type(datetime):", type(datetime))
    # Ensure timezone-aware
    if signal_dt.tzinfo is None:
        signal_dt = IST.localize(signal_dt)

    now = datetime.datetime.now(IST)

    # Same trading day
    if signal_dt.date() != now.date():
        return False

    # Trading window
    if not (START_TIME <= signal_dt.time() <= END_TIME):
        return False

    return True

def is_valid_signal_time02(signal_dt):
    """Return True only if signal date is today and time is within trading window."""

    IST = pytz.timezone("Asia/Kolkata")

    START_TIME = time(9, 30)    # 09:30 IST
    END_TIME   = time(14, 30)   # 14:30 IST

    # Ensure timezone-aware
    if signal_dt.tzinfo is None:
        signal_dt = IST.localize(signal_dt)

    now = datetime.now(IST)

    # Same trading day check
    if signal_dt.date() != now.date():
        return False

    # Trading window check
    if not (START_TIME <= signal_dt.time() <= END_TIME):
        return False

    return True

def is_valid_signal_time01(signal_dt):
    """Return True only if signal date is today and time is within trading window."""
    import pytz
    import time
 
     # Trading window (GLOBAL CONSTANTS)
    START_TIME = time(9, 30)   # 9:30 AM
    END_TIME   = time(14, 30)  # 2:30 PM
     
   # IST = pytz.timezone("Asia/Kolkata")
    IST = pytz.timezone("Asia/Kolkata") 

    if signal_dt.tzinfo is None:
        signal_dt = IST.localize(signal_dt)

    now = datetime.now(IST).replace(second=0, microsecond=0)

    # 1. Check same date
    if signal_dt.date() != now.date():
        return False

    # 2. Check time window
    if not (START_TIME <= signal_dt.time() <= END_TIME):
        return False

    return True

#------------------------------------------IV-------------------------------------------------------
import math

def compute_iv(ltp, spot, strike, time_to_expiry, is_call=True):
    try:
        # Avoid invalid values
        if ltp <= 0 or time_to_expiry <= 0:
            return 0

        # Approximation formula
        intrinsic = max(0, spot - strike) if is_call else max(0, strike - spot)
        extrinsic = max(ltp - intrinsic, 0.01)

        # Very stable approximate IV formula
        iv = math.sqrt(2 * math.pi) * (extrinsic / (spot * math.sqrt(time_to_expiry)))

        # Bound the IV inside 0–1
        if iv < 0:
            iv = 0
        if iv > 1:
            iv = 1

        return iv

    except Exception:
        return 0

#----------------------------------------IV-----------------------------------------------------

#from py_vollib_vectorized import vectorized_implied_volatility_black

RISK_FREE_RATE = 0.07      # adjust if you want 0.065 0r 0.07
RISK_FREE_RATE =  0.065
MIN_TIME_TO_EXPIRY = 1/365 # 1 day minimum to avoid zero T

def get_live_iv_nifty_option(kite, option_token: int, index_symbol="NSE:NIFTY 50"):
    """
    Return live implied volatility (annualized, in %) for a single NIFTY option.
    Uses Black model on futures/spot with robust exception handling.
    - option_token: instrument_token of the option
    """
    try:
        # 1) Get live quotes
        q_opt = kite.ltp(option_token)[str(option_token)]
        q_idx = kite.ltp(index_symbol)[index_symbol]

        opt_ltp = float(q_opt["last_price"])
        spot    = float(q_idx["last_price"])

        # sanity: below intrinsic -> IV undefined
        # you can choose to return None or a floor value
        # assume European index options
        instrument = kite.instrument_by_token(option_token)  # your helper
        strike = float(instrument["strike"])
        oi_flag = instrument["instrument_type"]  # 'CE' or 'PE'

        if oi_flag == "CE":
            intrinsic = max(spot - strike, 0.0)
            flag = "c"
        else:
            intrinsic = max(strike - spot, 0.0)
            flag = "p"

        if opt_ltp <= intrinsic + 0.01:
            return None   # almost no time value, IV not meaningful

        # 2) Time to expiry (year fraction)
        expiry = pd.to_datetime(instrument["expiry"]).date()
        today  = datetime.now().date()
        days_to_expiry = max((expiry - today).days, 1)
        t = max(days_to_expiry / 365.0, MIN_TIME_TO_EXPIRY)

        # 3) Use Black model implied vol (index options) [web:47][web:70]
        price   = pd.Series([opt_ltp])
        F       = pd.Series([spot])      # using spot as forward approx
        K       = pd.Series([strike])
        t_ser   = pd.Series([t])
        r       = pd.Series([RISK_FREE_RATE])

        iv = vectorized_implied_volatility_black(
            price=price,
            F=F,
            K=K,
            r=r,
            t=t_ser,
            flag=flag,
            return_as="numpy"
        )[0]

        # guard against NaN or crazy values
        if not math.isfinite(iv) or iv <= 0 or iv > 5:   # >500% -> likely bad tick
            return None

        return round(iv * 100, 2)   # convert to %

    except Exception as e:
        # log the error in your app logger if needed
        # print("IV calc error:", e)
        return None

#----------------------------------IV , RANK------------------------------------------------------------

def safe_float(x, default=None):
    try:
        if x is None:
            return default
        if isinstance(x, str):
            x = x.strip()
            if x in ["", "--", "NaN", "None"]:
                return default
        return float(x)
    except Exception:
        return default

def get_iv_rank(kite, option, lookback_days=252):
    """
    Calculate IV and IV Rank for a selected NIFTY option using Zerodha kite.
    - option: dict with keys: instrument_token, strike, option_type (CE/PE), expiry, tradingsymbol (optional)
    - compute_option_iv(option_dict, spot_price) must accept option_dict and spot and return float IV (in % or decimal depending on impl).
    """
    try:
        # --- 1) Get current spot ---
        spot_resp = kite.ltp("NSE:NIFTY 50")
        # safe extraction
        spot_now = None
        try:
            spot_now = safe_float(spot_resp["NSE:NIFTY 50"]["last_price"])
        except Exception:
            # try alternative keys
            try:
                spot_now = safe_float(list(spot_resp.values())[0]["last_price"])
            except Exception:
                spot_now = None

        if spot_now is None:
            raise ValueError("Cannot read NIFTY spot from kite.ltp response")

        # --- 2) Current option LTP (real-time) ---
        # Try to fetch option LTP via instrument token or tradingsymbol
        opt_ltp = None
        try:
            # if option contains tradingsymbol use it
            if "tradingsymbol" in option:
                opt_sym = option["tradingsymbol"]
                opt_resp = kite.ltp(opt_sym)
                # choose the first value
                opt_ltp = safe_float(list(opt_resp.values())[0].get("last_price"))
            else:
                opt_resp = kite.ltp(option["instrument_token"])
                opt_ltp = safe_float(list(opt_resp.values())[0].get("last_price"))
        except Exception:
            # fallback: if option dict itself has an ltp/last_price provided externally
            opt_ltp = safe_float(option.get("ltp") or option.get("last_price"))

        # Build a dict to pass to compute_option_iv
        cur_option_for_iv = {
            "strike": option["strike"],
            "option_type": option["option_type"],
            "expiry": option["expiry"],
            # the key name 'market_price' or 'ltp' must match what compute_option_iv expects
            "market_price": opt_ltp if opt_ltp is not None else 0.0
        }

        current_iv = compute_option_iv(cur_option_for_iv, spot_now)
        # if compute_option_iv returns decimal (0.09) and you expect percent (9.0), normalize accordingly
        # handle None
        if current_iv is None:
            # debug: show what we tried
            print("DEBUG: compute_option_iv returned None for current option. Inputs:", cur_option_for_iv, "spot", spot_now)
            return {"iv": None, "iv_rank": None}

        # ensure numeric
        current_iv = safe_float(current_iv)
        if current_iv is None:
            return {"iv": None, "iv_rank": None}

        # --- 3) Historical fetch (we will align by date) ---
        # fetch a bigger historical window to accommodate holidays
        from_date = (datetime.now() - timedelta(days=lookback_days * 2)).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")

        # spot history
        nifty_token = kite.ltp("NSE:NIFTY 50")
        # extract instrument_token safely
        try:
            nifty_token_val = list(nifty_token.values())[0]["instrument_token"]
        except Exception:
            nifty_token_val = None

        if nifty_token_val is None:
            raise ValueError("Could not obtain instrument_token for NIFTY from kite.ltp")

        nifty_hist = kite.historical_data(
            instrument_token=nifty_token_val,
            from_date=from_date,
            to_date=to_date,
            interval="day"
        )
        nifty_df = pd.DataFrame(nifty_hist)
        if not nifty_df.empty:
            # ensure datetime column named 'date' exists and normalized to date only
            if 'date' in nifty_df.columns:
                nifty_df['date'] = pd.to_datetime(nifty_df['date']).dt.date
            else:
                # create date from 'time'/'datetime' columns if present
                nifty_df['date'] = pd.to_datetime(nifty_df.iloc[:,0]).dt.date

            nifty_df = nifty_df[['date', 'close']].rename(columns={'close':'spot_close'})

        # option history
        option_hist = kite.historical_data(
            instrument_token=option["instrument_token"],
            from_date=from_date,
            to_date=to_date,
            interval="day"
        )
        option_df = pd.DataFrame(option_hist)
        if not option_df.empty:
            option_df['date'] = pd.to_datetime(option_df['date']).dt.date
            option_df = option_df[['date', 'close']].rename(columns={'close':'opt_close'})

        # Merge on date using inner join to ensure matching days only
        if option_df.empty or nifty_df.empty:
            print("DEBUG: historical data empty. option_df len:", len(option_df), "nifty_df len:", len(nifty_df))
            return {"iv": round(current_iv,2), "iv_rank": None}

        merged = pd.merge(nifty_df, option_df, on='date', how='inner')
        if merged.empty:
            # try nearest-date merge (in case of mismatched trading days)
            merged = pd.merge_asof(option_df.sort_values('date'), 
                                   nifty_df.sort_values('date'), 
                                   on='date', direction='nearest', tolerance=pd.Timedelta('2D'))
            # after merge_asof, column names might be opt_close and spot_close
            if merged is None or merged.empty:
                print("DEBUG: No merged historical rows after merge_asof")
                return {"iv": round(current_iv,2), "iv_rank": None}

        # Compute historical IVs
        ivs = []
        for _, row in merged.iterrows():
            hist_opt = {
                "strike": option["strike"],
                "option_type": option["option_type"],
                "ltp": safe_float(row.get('opt_close')),
                "expiry": option["expiry"],
                # ensure compute_option_iv gets the same key name it expects; adjust if needed
            }
            spot_price = safe_float(row.get('spot_close'))
            if hist_opt["ltp"] is None or spot_price is None:
                continue
            iv_val = compute_option_iv(hist_opt, spot_price)
            iv_val = safe_float(iv_val)
            if iv_val is not None:
                ivs.append(iv_val)

        if not ivs:
            print("DEBUG: no historical IVs computed. merged rows:", len(merged))
            return {"iv": round(current_iv,2), "iv_rank": None}

        iv_low = min(ivs)
        iv_high = max(ivs)

        if iv_high - iv_low == 0:
            iv_rank = 0.0
        else:
            iv_rank = (current_iv - iv_low) / (iv_high - iv_low) * 100.0

        return {"iv": round(current_iv, 2), "iv_rank": round(iv_rank, 2)}

    except Exception as e:
        print("IV Rank error:", e)
        return {"iv": 0, "iv_rank": 0}

#----------------------------------------------------------------------------------------
def get_iv_rank0(kite, option, lookback_days=252):
        """
        Calculate IV and IV Rank for a selected NIFTY option using Zerodha.
        """
        try:
            # 1️⃣ Current spot price
            spot_now = kite.ltp("NSE:NIFTY 50")["NSE:NIFTY 50"]["last_price"]
    
            # 2️⃣ Current IV
            current_iv = compute_option_iv(option, spot_now)
    
            # 3️⃣ Fetch historical NIFTY spot for lookback
            from_date = (datetime.now() - timedelta(days=lookback_days*2)).strftime("%Y-%m-%d")
            to_date = datetime.now().strftime("%Y-%m-%d")
    
            nifty_hist = kite.historical_data(
                instrument_token=kite.ltp("NSE:NIFTY 50")["NSE:NIFTY 50"]["instrument_token"],
                from_date=from_date,
                to_date=to_date,
                interval="day"
            )
            nifty_df = pd.DataFrame(nifty_hist)
    
            # 4️⃣ Fetch option historical LTP
            option_hist = kite.historical_data(
                instrument_token=option["instrument_token"],
                from_date=from_date,
                to_date=to_date,
                interval="day"
            )
            option_df = pd.DataFrame(option_hist)
    
            # Match historical dates (NIFTY spot + option LTP)
            min_len = min(len(nifty_df), len(option_df))
            ivs = []
            for i in range(min_len):
                hist_opt = {
                    "strike": option["strike"],
                    "option_type": option["option_type"],
                    "ltp": option_df.iloc[i]["close"],
                    "expiry": option["expiry"]
                }
                spot_price = nifty_df.iloc[i]["close"]
                iv = compute_option_iv(hist_opt, spot_price)
                if iv is not None:
                    ivs.append(iv)
    
            if not ivs or current_iv is None:
                return {"iv": current_iv, "iv_rank": None}
    
            iv_low = min(ivs)
            iv_high = max(ivs)
    
            if iv_high - iv_low == 0:
                iv_rank = 0
            else:
                iv_rank = (current_iv - iv_low) / (iv_high - iv_low) * 100
    
            return {"iv": round(current_iv, 2), "iv_rank": round(iv_rank, 2)}
    
        except Exception as e:
            print("IV Rank error:", e)
            return {"iv": None, "iv_rank": None}
#--------------------------------------Fund Status------------------------------------

def get_fund_status(kite, segment="equity"):
    """
    Returns Zerodha fund/margin status.
    segment = "equity" or "commodity"
    """

    try:
        funds = kite.margins(segment=segment)

        result = {
            "net": funds.get("net", 0),
            "cash": funds["available"].get("cash", 0),
            #"opening_balance": funds["available"].get("opening_balance", 0),
            #"collateral": funds["available"].get("collateral", 0),
            #"intraday_payin": funds["available"].get("intraday_payin", 0),
            #"option_premium": funds["utilised"].get("option_premium", 0),
            #"span": funds["utilised"].get("span", 0),
            #"exposure": funds["utilised"].get("exposure", 0),
            #"payout": funds["utilised"].get("payout", 0)
        }

        return result

    except Exception as e:
        return {"error": str(e)}

#-------------------------------------PARA-----------------------------------------------------
if "param_rows" not in st.session_state:
    st.session_state.param_rows = []

def add_param_row(parameter, value, value_range, result):
    st.session_state.param_rows.append({
        "Parameters": parameter,
        "Values": value,
        "Range": value_range,
        "Result": result
    })


#-------------------------------------PCR---------------------------------------------------
def get_nifty_pcr(kite, instruments_csv="instruments.csv"):
    import pandas as pd

    # Load instruments file
    inst = pd.read_csv(instruments_csv)

    nifty_opts = inst[
        (inst['name'] == 'NIFTY') &
        (inst['segment'] == 'NFO-OPT')
    ]

    # Nearest weekly expiry
    nearest_expiry = nifty_opts['expiry'].min()

    weekly = nifty_opts[nifty_opts['expiry'] == nearest_expiry]

    calls = weekly[weekly['instrument_type'] == 'CE']
    puts  = weekly[weekly['instrument_type'] == 'PE']

    call_symbols = [f"NFO:{ts}" for ts in calls['tradingsymbol']]
    put_symbols  = [f"NFO:{ts}" for ts in puts['tradingsymbol']]

    # Fetch OI
    call_data = kite.quote(call_symbols)
    put_data  = kite.quote(put_symbols)

    total_call_oi = sum(call_data[s]['oi'] for s in call_symbols)
    total_put_oi  = sum(put_data[s]['oi'] for s in put_symbols)

    # Calculate PCR
    pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0

    return pcr

    
#--------------------------------------------LOT SIZE-----------------------------------


def get_lot_size(cash):
    if cash >= 100000:
        return 6
    elif cash >= 50000:
        return 4
    elif cash >= 25000:
        return 2
    else:
        return 0   # avoid trade





#----------------------------------VIX KITE------------------------------

def fetch_india_vix_kite(kite):
    try:
        # India VIX instrument token: 264969
        #data = kite.ltp("NSE:INDIAVIX")
        vix = kite.ltp("264969")
        vix_value = vix["264969"]["last_price"]
        #vix = data["NSE:INDIAVIX"]["last_price"]
        #st.write(kite.ltp("NSE:INDIAVIX"))
        #st.write(kite.ltp("264969"))
        #st.write(kite.ltp("INDICES:INDIAVIX"))
        return (vix_value)
    except Exception as e:
        st.write("VIX fetch error from Kite:", e)
        return None

#---------------------------------ORDeRS----------------------------

def show_kite_orders(kite):
    try:
        orders = kite.orders()   # fetch all orders
        
        if not orders:
            st.warning("No orders found.")
            return
        
        # Convert to DataFrame for neat display
        import pandas as pd
        df = pd.DataFrame(orders)

        # Optional: sort latest first
        df = df.sort_values("order_timestamp", ascending=False)

        st.subheader("📦 Order Book")
        st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"Error fetching orders: {e}")

# ---------------------------------VIX---------------------------

def fetch_india_vix():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com/"
    })
    s.get("https://www.nseindia.com", timeout=10)  # cookies सेट

    r = s.get("https://www.nseindia.com/api/allIndices", timeout=10)
    data = r.json()

    for idx in data["data"]:
        if idx.get("index") == "INDIA VIX":
            return float(idx["last"])

#vix_now = fetch_india_vix()
#----------------------------------VIX----------------------------------------------

#import requests

def fetch_vix_from_fyers():
    """
    Reliable India VIX fetcher (public API, always JSON)
    """
    url = "https://api.indiavix.in/vix"

    try:
        r = requests.get(url, timeout=10)

        # Verify JSON content
        if "application/json" not in r.headers.get("Content-Type", ""):
            print("Non-JSON response received")
            return None

        data = r.json()

        return float(data.get("vix", None))
    
    except Exception as e:
        print(f"VIX fetch error: {e}")
        return None


# -------------------------
# IV Filter Functions
# -------------------------
def iv_filter(iv_value, iv_rank):
    if iv_value > 35 or iv_value < 10:
        return False
    if iv_rank < 20 or iv_rank > 70:
        return False
    return True

def vix_filter(vix_value):
    if vix_value < 12 or vix_value > 22:
        return False
    return True

def combined_filter(option_iv, iv_rank, vix_value):
    if iv_filter(option_iv, iv_rank) and vix_filter(vix_value):
        size = "half" if option_iv > 25 or vix_value > 18 else "full"
        return True, size
    else:
        return False, "none"

# ---------- 1. Parse NIFTY option symbol ----------
def parse_nifty_symbol0(ts):
            """
            Parse NIFTY option symbol like NIFTY25D0926200CE
            Returns: underlying, expiry_date (date), strike (float), opt_type ('c'/'p')
            """
            # Format: NIFTY YY M DD STRIKE CE/PE
            # NIFTY25D09 26200 CE
            underlying = "NIFTY"
    
            yy = int(ts[5:7])          # '25'
            m_code = ts[7]             # 'D'
            dd = int(ts[8:10])         # '09'
            strike = float(ts[10:-2])  # '26200'
            opt_code = ts[-2:]         # 'CE' or 'PE'
    
            # month code map as per NSE short codes
            month_map = {
                "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
                "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
                "A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6,
                "G": 7, "H": 8, "I": 9, "J": 10, "K": 11, "L": 12,
            }
            mm = month_map[m_code]
            yyyy = 2000 + yy
    
            expiry_date = date(yyyy, mm, dd)
            opt_type = "c" if opt_code.upper() == "CE" else "p"
    
            return underlying, expiry_date, strike, opt_type

# ------------------------------------------------------------


def parse_nifty_symbol(symbol):
    """
    Parse Zerodha NIFTY/BANKNIFTY option symbol to extract expiry, strike, and option type.
    
    Example:
    'NIFTY25DEC25950CE' -> {
        'index': 'NIFTY',
        'expiry': datetime(2025, 12, 25),
        'strike': 5950,
        'option_type': 'CE'
    }
    """
    try:
        # Identify index
        if symbol.startswith("NIFTY"):
            index = "NIFTY"
            rest = symbol[5:]
        elif symbol.startswith("BANKNIFTY"):
            index = "BANKNIFTY"
            rest = symbol[9:]
        else:
            return None
        
        # Extract DDMONYY
        dd = int(rest[:2])
        mon = rest[2:5].upper()
        yy = int(rest[5:7])
        expiry = datetime.strptime(f"{dd}{mon}{yy:02d}", "%d%b%y")
        
        # Remaining string is strike + option type
        strike_str = rest[7:-2]
        option_type = rest[-2:]
        strike = float(strike_str)
        
        return {
            "index": index,
            "expiry": expiry,
            "strike": strike,
            "option_type": option_type
        }
        
    except Exception as e:
        print(f"Error parsing symbol {symbol}: {e}")
        return None


# ------------------------------------------------------------


def compute_current_iv_3(kite, selected_option):
                    spot = get_nifty_spot(kite)
                    opt_ltp = kite.ltp(f"NFO:{selected_option['tradingsymbol']}")[f"NFO:{selected_option['tradingsymbol']}"]["ltp"]
                
                    strike = float(selected_option["strike"])
                    expiry = selected_option["expiry"]          # '2025-12-09'
                    opt_type = "c" if selected_option["instrument_type"] == "CE" else "p"
                
                    T_days = days_to_expiry(expiry)
                    if T_days <= 0:
                        return np.nan
                
                    T = T_days / 365.0
                    intrinsic = max(0.0, spot - strike) if opt_type == "c" else max(0.0, strike - spot)
                    opt_ltp = max(opt_ltp, intrinsic + 0.01)
                
                    try:
                        iv = implied_volatility(opt_ltp, spot, strike, T, R, opt_type)
                        return iv * 100.0  # %
                    except Exception:
                        return np.nan

# ------------------------------------------------------------

def days_to_expiry0s(expiry):
    """
    Compute days to expiry safely.
    expiry: datetime, pd.Timestamp, or datetime.date
    """
    today = date.today()
    
    # Convert pandas Timestamp or datetime to date
    if hasattr(expiry, 'date'):
        expiry_date = expiry.date()
    else:
        expiry_date = expiry
    
    return max((expiry_date - today).days, 0)


# ------------------------------------------------------------

def compute_current_iv(kite, selected_option):
    """
    Compute IV safely using Kite LTP and expiry.
    """
    try:
        expiry = selected_option.get("expiry")
        if expiry is None:
            st.error("Expiry not found in selected_option")
            return None
        
        # Safe days to expiry
        T_days = days_to_expiry(expiry)

        symbol = f"NFO:{selected_option['tradingsymbol']}"
        ltp_data = kite.ltp(symbol)
        
        if symbol not in ltp_data:
            st.error(f"{symbol} not found in LTP response")
            return None
        
        opt_ltp = ltp_data[symbol].get("last_price") or ltp_data[symbol].get("ltp")
        if opt_ltp is None:
            st.error(f"LTP not available for {symbol}")
            return None
        
        option_type = selected_option.get("option_type")
        if option_type not in ["CE", "PE"]:
            st.error(f"Invalid option type: {option_type}")
            return None
        
        opt_type = "c" if option_type == "CE" else "p"
        
        spot_price = selected_option.get("spot_price", opt_ltp)

        # Dummy IV for now
        iv = round((opt_ltp / spot_price) * 0.15, 2)
        
        return iv
    
    except Exception as e:
        st.error(f"Error computing IV: {e}")
        return None


# ------------------------------------------------------------


from datetime import datetime
from py_vollib.black.implied_volatility import implied_volatility

def compute_option_iv(option, spot_price):
    try:
        strike = float(option["strike"])
        #st.write("Strike-",strike)
        opt_type = option["option_type"].lower()
        #st.write("opt_type-",opt_type)
        ltp = float(option["ltp"])
        #st.write("ltp-",ltp)

        expiry = option["expiry"].to_pydatetime()
        now = datetime.now()

        days_to_expiry = (expiry - now).total_seconds() / (60*60*24)
        if days_to_expiry <= 0:
            return None

        T = days_to_expiry / 365
        r = 0.07

        # Correct: positional args only
        iv = implied_volatility(
            ltp,
            spot_price,
            strike,
            T,
            r,
            'c' if opt_type == "call" else 'p'
        )

        return round(iv*100, 2)

    except Exception as e:
        print("IV calc error:", e)
        return None
# ------------------------------------------------------------




def get_iv_rank_zerodha(kite, option, lookback_days=30):
    """
    Calculate IV and IV Rank for a selected NIFTY option using Zerodha data.

    Parameters:
    - kite: connected Kite object
    - option: dict of selected ITM option (tradingsymbol, strike, option_type, expiry, ltp)
    - lookback_days: number of past days to calculate IV Rank

    Returns:
    - dict: {"iv": current_iv, "iv_rank": iv_rank}
    """
    try:
        tsymbol = option["tradingsymbol"]
        expiry = option["expiry"].to_pydatetime() if hasattr(option["expiry"], "to_pydatetime") else option["expiry"]

        # 1️⃣ Fetch historical data from Zerodha
        # OHLC candles for the option; interval = "day"
        from_date = (datetime.now() - timedelta(days=lookback_days*2)).strftime("%Y-%m-%d")  # buffer for holidays
        to_date = datetime.now().strftime("%Y-%m-%d")

        historical = kite.historical_data(
            instrument_token=option["instrument_token"],
            from_date=from_date,
            to_date=to_date,
            interval="day"
        )

        if not historical:
            return {"iv": None, "iv_rank": None}

        hist_df = pd.DataFrame(historical)

        # 2️⃣ Compute IVs for each day
        ivs = []
        for _, row in hist_df.iterrows():
            hist_opt = {
                "strike": option["strike"],
                "option_type": option["option_type"],
                "ltp": row["close"],  # use close price of option
                "expiry": expiry
            }
            # Spot price of NIFTY on that day
            spot_price = row.get("underlying_value", None)
            if spot_price is None:
                # fallback to last known spot
                spot_price = option["ltp"]  # approximate

            iv = compute_option_iv(hist_opt, spot_price)
            if iv is not None:
                ivs.append(iv)

        if not ivs:
            return {"iv": None, "iv_rank": None}

        iv_low = min(ivs)
        iv_high = max(ivs)

        # 3️⃣ Current IV
        spot_now = kite.ltp("NSE:NIFTY 50")["NSE:NIFTY 50"]["last_price"]
        current_iv = compute_option_iv(option, spot_now)

        # 4️⃣ Compute IV Rank
        if iv_high - iv_low == 0:
            iv_rank = 0
        else:
            iv_rank = (current_iv - iv_low) / (iv_high - iv_low) * 100

        return {"iv": round(current_iv, 2), "iv_rank": round(iv_rank, 2)}

    except Exception as e:
        print("IV Rank calculation error:", e)
        return {"iv": None, "iv_rank": None}


# ------------------------------------------------------------
    


# ------------------------------------------------------------

# ------------------------------------------------------------

# ------------------------------------------------------------

# ------------------------------------------------------------

# ------------------------------------------------------------

# ------------------------------------------------------------

# ------------------------------------------------------------

# ------------------------------------------------------------

def find_nearest_itm_from_zerodha(chain, spot_price, option_type):
    if option_type.upper() not in ["CALL", "PUT"]:
        raise ValueError("option_type must be CALL or PUT")

    # Split into CE / PE
    if option_type.upper() == "CALL":
        ce_chain = chain[chain["tradingsymbol"].str.endswith("CE")].copy()
        # ITM CALL = strike < spot
        ce_chain["diff"] = spot_price - ce_chain["strike"]
        ce_chain = ce_chain[ce_chain["diff"] >= 0]
        selected = ce_chain.sort_values("diff").head(1)

    else:  # PUT
        pe_chain = chain[chain["tradingsymbol"].str.endswith("PE")].copy()
        # ITM PUT = strike > spot
        pe_chain["diff"] = pe_chain["strike"] - spot_price
        pe_chain = pe_chain[pe_chain["diff"] >= 0]
        selected = pe_chain.sort_values("diff").head(1)

    if selected.empty:
        raise ValueError(f"❌ No ITM {option_type} found!")

    return selected.iloc[0].to_dict()


# ------------------------------------------------------------

def get_expiry_from_symbol(tradingsymbol):
    """
    Extract expiry date from Zerodha option symbol.
    
    Example:
    'NIFTY25DEC25950CE' → datetime(2025, 12, 25)
    """
    try:
        # Zerodha format: <INDEX><DD><MON><YY><STRIKE><CE/PE>
        # Example: NIFTY25DEC25950CE
        date_str = tradingsymbol[5:11]  # '25DEC25'
        expiry = datetime.strptime(date_str, "%d%b%y")
        return expiry
    except Exception as e:
        #print(f"Error parsing expiry from {tradingsymbol}: {e}")
        return None


# ------------------------------------------------------------

def load_instruments():
    file_path = "instruments.csv"
    if not os.path.exists(file_path):
        raise FileNotFoundError("instruments.csv not found. Please login first to download.")
    return pd.read_csv(file_path)


# ------------------------------------------------------------------------------------------------

def load_zerodha_instruments():
    try:
        df = pd.read_csv("instruments.csv")
    except Exception as e:
        raise FileNotFoundError(f"❌ Cannot load instruments.csv: {e}")

    # Keep only required columns
    required_cols = ["instrument_token", "exchange", "segment", "tradingsymbol",
                     "name", "instrument_type", "expiry", "strike", "tick_size"]
    df = df[[c for c in required_cols if c in df.columns]]

    # Clean
    df = df.dropna(subset=["tradingsymbol"])
    df = df[df["exchange"] == "NFO"]

    # Convert expiry to datetime
    if "expiry" in df.columns:
        df["expiry"] = pd.to_datetime(df["expiry"], errors="coerce")

    return df

#------------------------------------------------------------------------------------------------------------


def get_nifty_option_chain(df):
    if df.empty:
        return df

    # 1) Filter only NFO options (no futures)
    chain = df[
        (df["exchange"] == "NFO") &
        (df["tradingsymbol"].str.startswith("NIFTY")) &
        (df["instrument_type"].isin(["CE", "PE", "OPTIDX"]))
    ].copy()

    if chain.empty:
        print("⚠ Warning: NIFTY not found with CE/PE/OPTIDX labels. Retrying relaxed filter...")
        chain = df[
            (df["exchange"] == "NFO") &
            (df["tradingsymbol"].str.contains("NIFTY")) &
            (df["strike"] > 0)
        ].copy()

    if chain.empty:
        raise ValueError("❌ Still no NIFTY options found! Your instruments.csv may be outdated.")

    # 2) Fix expiry
    chain["expiry"] = pd.to_datetime(chain["expiry"], errors="coerce")

    # 3) Auto-select nearest upcoming expiry (weekly OR monthly)
    upcoming = chain["expiry"].dropna().sort_values().unique()
    if len(upcoming) == 0:
        raise ValueError("❌ No expiry dates found in NIFTY chain!")

    nearest_expiry = upcoming[0]   # closest expiry date

    chain = chain[chain["expiry"] == nearest_expiry]

    # 4) Remove anything invalid
    chain = chain[chain["strike"] > 0]

    return chain



        
#--------------------------------------------------------------------------------------------------


def find_nearest_itm_option(kite, spot_price, option_type):
    """
    Returns the nearest ITM option (CALL/PUT) for NIFTY based on the live spot price.

    option_type: "CALL" or "PUT"
    """

    df = load_zerodha_instruments()

    # --------- Filter only NIFTY index weekly options ---------
    chain = get_nifty_option_chain(df)
    if chain is None or chain.empty:
        raise ValueError("❌ No NIFTY options found in Zerodha instruments!")

    # --------- Find ITM option using custom logic ---------
    selected = find_nearest_itm_from_zerodha(chain, spot_price, option_type)
    if selected is None:
        raise ValueError("❌ Failed to find nearest ITM option!")

    tradingsymbol = selected.get("tradingsymbol")
    if not tradingsymbol:
        raise ValueError("❌ Missing tradingsymbol for selected option")

    # --------- Fetch LTP safely ---------
    try:
        ltp = get_ltp(kite, tradingsymbol)
    except Exception as e:
        ltp = None
        print(f"⚠ Warning: Unable to fetch LTP for {tradingsymbol}: {e}")

    
    # Prepare detailed output
    detailed = {
        "tradingsymbol": selected["tradingsymbol"],
        "strike": float(selected["strike"]),
        "spot": float(spot_price),
        "instrument_token": int(selected["instrument_token"]),
        "option_type": option_type.upper(),
        "expiry": selected.get("expiry"),
        "lot_size": selected.get("lot_size", selected.get("lot_sizes", 65)),
        "tick_size": selected.get("tick_size"),
        "segment": selected.get("segment"),
        "exchange": selected.get("exchange", "NFO"),
        "name": selected.get("name", "NIFTY"),
        "ltp": ltp
    }

    return detailed
#=========================================================================================================

def nifty_320_breakout_strategy(df, quantity=65, return_all_signals=False):
    """
    NIFTY 3:20 PM Breakout Options Strategy

    Rules:
    - Use 3:15–3:20 candle as Base Box
    - Break above → Buy CALL
    - Break below → Buy PUT
    - Stoploss = Opposite side of box
    - Target = 1.5 x Risk
    - Time Exit = 3:29 PM
    """

    import pandas as pd
    from datetime import datetime, time

    signals = []

    df = df.copy()
    df["Date"] = df["Datetime"].dt.date

    today = df["Date"].iloc[-1]

    # ----------------------------
    # 1️⃣ Get 3:20 Candle
    # ----------------------------
    box = df[
        (df["Date"] == today) &
        (df["Datetime"].dt.hour == 15) &
        (df["Datetime"].dt.minute == 20)
    ]

    if box.empty:
        return None

    box_high = box.iloc[0]["High_^NSEI"]
    box_low  = box.iloc[0]["Low_^NSEI"]
    entry_time = box.iloc[0]["Datetime"]

    # ----------------------------
    # 2️⃣ Monitor candles after 3:20
    # ----------------------------
    after = df[
        (df["Date"] == today) &
        (df["Datetime"] > entry_time)
    ].sort_values("Datetime")

    trade_taken = False

    for _, candle in after.iterrows():

        price = candle["Close_^NSEI"]
        current_time = candle["Datetime"].time()

        # 3:29 PM hard exit
        if current_time >= time(15,29):
            break

        # ----------------------------
        # CALL Breakout
        # ----------------------------
        if not trade_taken and price > box_high:
            risk = box_high - box_low
            target = box_high + (1.5 * risk)

            sig = {
                "strategy": "NIFTY 3:20 Breakout",
                "option_type": "CALL",
                "entry_price": box_high,
                "spot_price": box_high, 
                "stoploss": box_low,
                "target": target,
                "entry_time": candle["Datetime"],
                "quantity": quantity,
                "status": "OPEN"
            }

            trade_taken = True

        # ----------------------------
        # PUT Breakout
        # ----------------------------
        elif not trade_taken and price < box_low:
            risk = box_high - box_low
            target = box_low - (1.5 * risk)

            sig = {
                "strategy": "NIFTY 3:20 Breakout",
                "option_type": "PUT",
                "entry_price": box_low,
                "spot_price": box_high,  
                "stoploss": box_high,
                "target": target,
                "entry_time": candle["Datetime"],
                "quantity": quantity,
                "status": "OPEN"
            }

            trade_taken = True

        # ----------------------------
        # Manage Open Trade
        # ----------------------------
        if trade_taken:
            if sig["option_type"] == "CALL":
                if candle["Low_^NSEI"] <= sig["stoploss"]:
                    sig["exit_price"] = sig["stoploss"]
                    sig["status"] = "SL HIT"
                    break
                if candle["High_^NSEI"] >= sig["target"]:
                    sig["exit_price"] = sig["target"]
                    sig["status"] = "TARGET HIT"
                    break

            if sig["option_type"] == "PUT":
                if candle["High_^NSEI"] >= sig["stoploss"]:
                    sig["exit_price"] = sig["stoploss"]
                    sig["status"] = "SL HIT"
                    break
                if candle["Low_^NSEI"] <= sig["target"]:
                    sig["exit_price"] = sig["target"]
                    sig["status"] = "TARGET HIT"
                    break

    # ----------------------------
    # Time Exit if still open
    # ----------------------------
    if trade_taken and "exit_price" not in sig:
        last_price = after.iloc[-1]["Close_^NSEI"]
        sig["exit_price"] = last_price
        sig["spot_price"] = last_price 
        sig["status"] = "TIME EXIT"

    if trade_taken:
        sig["pnl_points"] = (sig["exit_price"] - sig["entry_price"]) if sig["option_type"]=="CALL" else (sig["entry_price"] - sig["exit_price"])
        sig["pnl"] = sig["pnl_points"] * quantity
        signals.append(sig)

    return signals if return_all_signals else (signals[0] if signals else None)


#============================================================================================================
#----------------------------------------------------------------------------------------
def trading_signal_all_conditions(df, quantity=10*65, return_all_signals=True):
        """
        Evaluate trading conditions based on Base Zone strategy with:
        - CALL stop loss = recent swing low (last 10 candles)
        - PUT stop loss = recent swing high (last 10 candles)
        - Dynamic trailing stop loss based on swing points
        - Time exit after 16 minutes if neither SL nor trailing SL hit
        - Single active trade per day
        """
        trade_taken = False

        signals = []
        spot_price = df['Close_^NSEI'].iloc[-1]
    
        # Preprocess
        df = df.copy()
        df['Date'] = df['Datetime'].dt.date
        unique_days = sorted(df['Date'].unique())
        if len(unique_days) < 2:
            return None
    
        # Day 0 and Day 1
        day0 = unique_days[-2]  # Previous trading day
        day1 = unique_days[-1]  # Current trading day
    
        # Get Base Zone from 3 PM candle of previous day
        candle_3pm = df[(df['Date'] == day0) &
                        (df['Datetime'].dt.hour == 15) &
                        (df['Datetime'].dt.minute == 0)]
        if candle_3pm.empty:
            return None
    
        base_open = candle_3pm.iloc[0]['Open_^NSEI']
        base_close = candle_3pm.iloc[0]['Close_^NSEI']
        base_low = min(base_open, base_close)
        base_high = max(base_open, base_close)
    
        # Get 09:15–09:30 candle of current day
        candle_915 = df[(df['Date'] == day1) &
                        (df['Datetime'].dt.hour == 9) &
                        (df['Datetime'].dt.minute == 30)]
        if candle_915.empty:
            return None
    
        H1 = candle_915.iloc[0]['High_^NSEI']
        L1 = candle_915.iloc[0]['Low_^NSEI']
        C1 = candle_915.iloc[0]['Close_^NSEI']
        entry_time = candle_915.iloc[0]['Datetime']
    
        expiry = get_nearest_weekly_expiry(pd.to_datetime(day1))
    
        # Data after 09:30
        day1_after_915 = df[(df['Date'] == day1) & (df['Datetime'] > entry_time)].sort_values('Datetime')
    
        # Helper functions
        def get_recent_swing(current_time):
            """
            Return scalar swing_high, swing_low from last 10 candles before current_time.
            If insufficient data return (np.nan, np.nan).
            """
            recent_data = df[(df['Date'] == day1) & (df['Datetime'] < current_time)].tail(10)
            if recent_data.empty:
                return np.nan, np.nan
            # ensure scalar float values (not Series)
            swing_high = recent_data['High_^NSEI'].max()
            swing_low = recent_data['Low_^NSEI'].min()
            # convert numpy scalars to python floats when possible
            swing_high = float(swing_high) if not pd.isna(swing_high) else np.nan
            swing_low = float(swing_low) if not pd.isna(swing_low) else np.nan
            return swing_high, swing_low
    
        def update_trailing_sl(option_type, current_sl, current_time):
            """
            Safely update trailing SL using last-10-candle swing points.
            - For CALL: SL tracks the most recent swing_low (move up only)
            - For PUT: SL tracks the most recent swing_high (move down only)
            """
            new_high, new_low = get_recent_swing(current_time)
    
            # CALL: set/raise SL to new_low if valid
            if option_type == 'CALL':
                if pd.isna(new_low):
                    # nothing to update
                    return current_sl
                # if current_sl is missing, initialize it
                if current_sl is None or pd.isna(current_sl):
                    return new_low
                # update only if new_low is higher than current_sl (trail upward)
                if new_low > current_sl:
                    return new_low
                return current_sl
    
            # PUT: set/lower SL to new_high if valid
            if option_type == 'PUT':
                if pd.isna(new_high):
                    return current_sl
                if current_sl is None or pd.isna(current_sl):
                    return new_high
                # update only if new_high is lower than current_sl (trail downward)
                if new_high < current_sl:
                    return new_high
                return current_sl
    
            return current_sl
    
        def monitor_trade(sig):
            """
            Monitor trade after entry:
            - update trailing SL every new 15-min candle
            - exit when SL is hit or when 16 minutes passed since entry (time exit)
            - safe handling when there are no monitoring candles
            """
            current_sl = sig.get('stoploss', None)
            entry_dt = sig['entry_time']
            exit_deadline = entry_dt + timedelta(minutes=16)
    
            # if there are no candles to monitor, exit immediately at entry (safe fallback)
            if day1_after_915.empty:
                sig['exit_price'] = sig.get('buy_price', spot_price)
                sig['status'] = 'No candles to monitor - exited'
                return sig
    
            exited = False
            for _, candle in day1_after_915.iterrows():
                # Time exit check (exit at or after deadline)
                if candle['Datetime'] >= exit_deadline:
                    # Exit at market (use candle close as approximation of market exit)
                    sig['exit_price'] = candle['Close_^NSEI']
                    sig['status'] = 'Exited due to time limit'
                    exited = True
                    break
    
                # Update trailing SL safely
                current_sl = update_trailing_sl(sig['option_type'], current_sl, candle['Datetime'])
                sig['stoploss'] = current_sl
    
                # Only check SL-hit if SL is a valid numeric value
                if sig['option_type'] == 'CALL' and pd.notna(current_sl):
                    if candle['Low_^NSEI'] <= current_sl:
                        sig['exit_price'] = current_sl
                        sig['status'] = 'Exited at Trailing SL'
                        exited = True
                        break
                elif sig['option_type'] == 'PUT' and pd.notna(current_sl):
                    if candle['High_^NSEI'] >= current_sl:
                        sig['exit_price'] = current_sl
                        sig['status'] = 'Exited at Trailing SL'
                        exited = True
                        break
    
            # If not exited in loop, set EOD exit (or last candle close)
            if not exited:
                last_close = day1_after_915.iloc[-1]['Close_^NSEI']
                sig['exit_price'] = last_close
                sig['status'] = 'Exited at EOD/no SL hit'
    
            return sig
    
        # Condition 1 — Break above Base Zone (CALL)
        if (L1 < base_high and H1 > base_low) and (C1 > base_high):
            swing_high, swing_low = get_recent_swing(entry_time)
            sig = {
                'condition': 1,
                'option_type': 'CALL',
                'buy_price': H1,
                'stoploss': swing_low,  # may be np.nan if insufficient history
                'quantity': quantity,
                'expiry': expiry,
                'entry_time': entry_time,
                'message': 'Condition 1: Bullish breakout above Base Zone → Buy CALL above H1',
                'spot_price': spot_price
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            trade_taken = True 
            if not return_all_signals:
                return sig
    
        # Condition 2 — Major Gap Down (PUT) and flip 2.7
        if C1 < base_low:
            for _, next_candle in day1_after_915.iterrows():
                swing_high, swing_low = get_recent_swing(next_candle['Datetime'])
                # Primary PUT entry on break below L1
                if next_candle['Low_^NSEI'] <= L1:
                    sig = {
                        'condition': 2,
                        'option_type': 'PUT',
                        'buy_price': L1,
                        'stoploss': swing_high,
                        'quantity': quantity,
                        'expiry': expiry,
                        'entry_time': next_candle['Datetime'],
                        'message': 'Condition 2: Gap down confirmed → Buy PUT below L1',
                        'spot_price': spot_price
                    }
                    sig = monitor_trade(sig)
                    signals.append(sig)
                    trade_taken = True 
                    if not return_all_signals:
                        return sig
    
                # Flip rule 2.7: bullish recovery -> CALL
                if next_candle['Close_^NSEI'] > base_high:
                    ref_high = next_candle['High_^NSEI']
                    sig_flip = {
                        'condition': 2.7,
                        'option_type': 'CALL',
                        'buy_price': ref_high,
                        'stoploss': swing_low,
                        'quantity': quantity,
                        'expiry': expiry,
                        'entry_time': next_candle['Datetime'],
                        'message': 'Condition 2 Flip: Later candle closed above Base Zone → Buy CALL',
                        'spot_price': spot_price
                    }
                    sig_flip = monitor_trade(sig_flip)
                    signals.append(sig_flip)
                    trade_taken = True 
                    if not return_all_signals:
                        return sig_flip
    
        # Condition 3 — Major Gap Up (CALL) and flip 3.7
        if C1 > base_high:
            for _, next_candle in day1_after_915.iterrows():
                swing_high, swing_low = get_recent_swing(next_candle['Datetime'])
                if next_candle['High_^NSEI'] >= H1:
                    sig = {
                        'condition': 3,
                        'option_type': 'CALL',
                        'buy_price': H1,
                        'stoploss': swing_low,
                        'quantity': quantity,
                        'expiry': expiry,
                        'entry_time': next_candle['Datetime'],
                        'message': 'Condition 3: Gap up confirmed → Buy CALL above H1',
                        'spot_price': spot_price
                    }
                    sig = monitor_trade(sig)
                    signals.append(sig)
                    trade_taken = True 
                    if not return_all_signals:
                        return sig
    
                # Flip rule 3.7: bearish recovery -> PUT
                if next_candle['Close_^NSEI'] < base_low:
                    ref_low = next_candle['Low_^NSEI']
                    sig_flip = {
                        'condition': 3.7,
                        'option_type': 'PUT',
                        'buy_price': ref_low,
                        'stoploss': swing_high,
                        'quantity': quantity,
                        'expiry': expiry,
                        'entry_time': next_candle['Datetime'],
                        'message': 'Condition 3 Flip: Later candle closed below Base Zone → Buy PUT',
                        'spot_price': spot_price
                    }
                    sig_flip = monitor_trade(sig_flip)
                    signals.append(sig_flip)
                    trade_taken = True 
                    if not return_all_signals:
                        return sig_flip
    
        # Condition 4 — Break below Base Zone on Day 1 open (PUT)
        if (L1 < base_high and H1 > base_low) and (C1 < base_low):
            swing_high, swing_low = get_recent_swing(entry_time)
            sig = {
                'condition': 4,
                'option_type': 'PUT',
                'buy_price': L1,
                'stoploss': swing_high,
                'quantity': quantity,
                'expiry': expiry,
                'entry_time': entry_time,
                'message': 'Condition 4: Bearish breakdown below Base Zone → Buy PUT below L1',
                'spot_price': spot_price
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            trade_taken = True 
            if not return_all_signals:
                return sig
    
        return signals if signals else None


#------------------------------------------------------------------------------------------------------

def trading_multi_signal_all_conditions(df, quantity=10*75, return_all_signals=True):

    signals = []
    last_exit_time = None
    spot_price = df['Close_^NSEI'].iloc[-1]

    df = df.copy()
    df['Date'] = df['Datetime'].dt.date
    unique_days = sorted(df['Date'].unique())
    if len(unique_days) < 2:
        return None

    day0, day1 = unique_days[-2], unique_days[-1]

    candle_3pm = df[(df['Date'] == day0) &
                    (df['Datetime'].dt.hour == 15) &
                    (df['Datetime'].dt.minute == 0)]
    if candle_3pm.empty:
        return None

    base_open = candle_3pm.iloc[0]['Open_^NSEI']
    base_close = candle_3pm.iloc[0]['Close_^NSEI']
    base_low, base_high = min(base_open, base_close), max(base_open, base_close)

    candle_915 = df[(df['Date'] == day1) &
                    (df['Datetime'].dt.hour == 9) &
                    (df['Datetime'].dt.minute == 30)]
    if candle_915.empty:
        return None

    H1 = candle_915.iloc[0]['High_^NSEI']
    L1 = candle_915.iloc[0]['Low_^NSEI']
    C1 = candle_915.iloc[0]['Close_^NSEI']
    entry_time = candle_915.iloc[0]['Datetime']

    expiry = get_nearest_weekly_expiry(pd.to_datetime(day1))

    day1_after_915 = df[(df['Date'] == day1) &
                        (df['Datetime'] > entry_time)].sort_values('Datetime')

    def get_recent_swing(t):
        recent = df[(df['Date'] == day1) & (df['Datetime'] < t)].tail(10)
        if recent.empty:
            return np.nan, np.nan
        return float(recent['High_^NSEI'].max()), float(recent['Low_^NSEI'].min())

    def update_trailing_sl(opt, sl, t):
        hi, lo = get_recent_swing(t)
        if opt == 'CALL' and not pd.isna(lo):
            return lo if sl is None or lo > sl else sl
        if opt == 'PUT' and not pd.isna(hi):
            return hi if sl is None or hi < sl else sl
        return sl

    def monitor_trade(sig):
        sl = sig['stoploss']
        entry = sig['entry_time']
        deadline = entry + timedelta(minutes=16)

        for _, c in day1_after_915.iterrows():
            if c['Datetime'] <= entry:
                continue

            if c['Datetime'] >= deadline:
                sig['exit_price'] = c['Close_^NSEI']
                sig['exit_time'] = c['Datetime']
                sig['status'] = 'Time Exit'
                return sig

            sl = update_trailing_sl(sig['option_type'], sl, c['Datetime'])
            sig['stoploss'] = sl

            if sig['option_type'] == 'CALL' and pd.notna(sl) and c['Low_^NSEI'] <= sl:
                sig['exit_price'] = sl
                sig['exit_time'] = c['Datetime']
                sig['status'] = 'Trailing SL Hit'
                return sig

            if sig['option_type'] == 'PUT' and pd.notna(sl) and c['High_^NSEI'] >= sl:
                sig['exit_price'] = sl
                sig['exit_time'] = c['Datetime']
                sig['status'] = 'Trailing SL Hit'
                return sig

        sig['exit_price'] = day1_after_915.iloc[-1]['Close_^NSEI']
        sig['exit_time'] = day1_after_915.iloc[-1]['Datetime']
        sig['status'] = 'EOD Exit'
        return sig

    # ---------------- CONDITIONS ---------------- #

    for _, candle in day1_after_915.iterrows():

        if last_exit_time and candle['Datetime'] <= last_exit_time:
            continue

        swing_high, swing_low = get_recent_swing(candle['Datetime'])

        # Condition 1
        if (L1 < base_high and H1 > base_low) and C1 > base_high:
            sig = {
                'condition': 1,
                'option_type': 'CALL',
                'buy_price': H1,
                'stoploss': swing_low,
                'quantity': quantity,
                'expiry': expiry,
                'entry_time': candle['Datetime'],
                'spot_price': spot_price
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            last_exit_time = sig['exit_time']

        # Condition 2
        if C1 < base_low and candle['Low_^NSEI'] <= L1:
            sig = {
                'condition': 2,
                'option_type': 'PUT',
                'buy_price': L1,
                'stoploss': swing_high,
                'quantity': quantity,
                'expiry': expiry,
                'entry_time': candle['Datetime'],
                'spot_price': spot_price
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            last_exit_time = sig['exit_time']

        # Flip 2.7
        if C1 < base_low and candle['Close_^NSEI'] > base_high:
            sig = {
                'condition': 2.7,
                'option_type': 'CALL',
                'buy_price': candle['High_^NSEI'],
                'stoploss': swing_low,
                'quantity': quantity,
                'expiry': expiry,
                'entry_time': candle['Datetime'],
                'spot_price': spot_price
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            last_exit_time = sig['exit_time']

        # Condition 3
        if C1 > base_high and candle['High_^NSEI'] >= H1:
            sig = {
                'condition': 3,
                'option_type': 'CALL',
                'buy_price': H1,
                'stoploss': swing_low,
                'quantity': quantity,
                'expiry': expiry,
                'entry_time': candle['Datetime'],
                'spot_price': spot_price
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            last_exit_time = sig['exit_time']

        # Flip 3.7
        if C1 > base_high and candle['Close_^NSEI'] < base_low:
            sig = {
                'condition': 3.7,
                'option_type': 'PUT',
                'buy_price': candle['Low_^NSEI'],
                'stoploss': swing_high,
                'quantity': quantity,
                'expiry': expiry,
                'entry_time': candle['Datetime'],
                'spot_price': spot_price
            }
            sig = monitor_trade(sig)
            signals.append(sig)
            last_exit_time = sig['exit_time']

    return signals if signals else None


#-----------------------------------------------------------------------------------------------------------
    
def get_ltp(kite, tradingsymbol):
    try:
        data = kite.ltp(f"NFO:{tradingsymbol}")
        return data[f"NFO:{tradingsymbol}"]["last_price"]
    except Exception as e:
        print("LTP fetch error:", e)
        return None



def download_instruments_csv(kite, file_path="instruments.csv"):
    try:
        instruments = kite.instruments()
        df = pd.DataFrame(instruments)
        df.to_csv(file_path, index=False)
        return file_path
    except Exception as e:
        raise Exception(f"Failed to download instruments.csv → {e}")





        
def display_todays_candles_with_trend_and_signal(df):
        """
        Display all today's candles with OHLC + Trend + Signal columns in Streamlit.
    
        Args:
        - df: DataFrame with columns ['Datetime', 'Open_^NSEI', 'High_^NSEI', 'Low_^NSEI', 'Close_^NSEI']
              'Datetime' must be timezone-aware or convertible to datetime.
    
        Output:
        - Shows table in Streamlit with added Trend and Signal columns.
        """
        if df.empty:
            st.warning("No candle data available.")
            return
        
        # Get today date from last datetime in df (assumes df sorted)
        today_date = df['Datetime'].dt.date.max()
        
        # Filter today's data
        todays_df = df[df['Datetime'].dt.date == today_date].copy()
        if todays_df.empty:
            st.warning(f"No data for today: {today_date}")
            return
        
        # Calculate Trend column
        def calc_trend(row):
            if row['Close_^NSEI'] > row['Open_^NSEI']:
                return "Bullish 🔥"
            elif row['Close_^NSEI'] < row['Open_^NSEI']:
                return "Bearish ❄️"
            else:
                return "Doji ⚪"
        
        todays_df['Trend'] = todays_df.apply(calc_trend, axis=1)
        
        # Calculate Signal column
        signals = []
        for i in range(len(todays_df)):
            if i == 0:
                # No previous candle, so no signal
                signals.append("-")
            else:
                prev_high = todays_df.iloc[i-1]['High_^NSEI']
                prev_low = todays_df.iloc[i-1]['Low_^NSEI']
                curr_close = todays_df.iloc[i]['Close_^NSEI']
                curr_trend = todays_df.iloc[i]['Trend']
                
                if curr_trend == "Bullish 🔥" and curr_close > prev_high:
                    signals.append("Buy")
                elif curr_trend == "Bearish ❄️" and curr_close < prev_low:
                    signals.append("Sell")
                else:
                    signals.append("-")
    
              
        
        todays_df['Signal'] = signals
        
        # Format datetime for display
        todays_df['Time'] = todays_df['Datetime'].dt.strftime('%H:%M')
        
        # Select and reorder columns to display
        display_df = todays_df[['Time', 'Open_^NSEI', 'High_^NSEI', 'Low_^NSEI', 'Close_^NSEI', 'Trend', 'Signal']].copy()
        display_df.rename(columns={
            'Open_^NSEI': 'Open',
            'High_^NSEI': 'High',
            'Low_^NSEI': 'Low',
            'Close_^NSEI': 'Close'
        }, inplace=True)
        
        #st.write(f"All 15-min candles for today ({today_date}):")
        #st.table(display_df)
    
    
    ###################################################################################################
def compute_performance(signal_df, brokerage_per_trade=20, gst_rate=0.18, stamp_duty_rate=0.00015, starting_capital=0):
    """
    Compute performance summary from signal log with PnL and include daily costs.
    
    Returns:
    - summary_df: Overall performance summary (including Total Expense)
    - pnl_per_day: Daily PnL with Total PnL, Net Expense, and Net PnL
    """
    import pandas as pd
    
    total_trades = len(signal_df)
    winning_trades = signal_df[signal_df['PnL'] > 0]
    losing_trades = signal_df[signal_df['PnL'] <= 0]
    
    total_pnl = signal_df['PnL'].sum()
    avg_pnl = signal_df['PnL'].mean() if total_trades > 0 else 0
    max_pnl = signal_df['PnL'].max() if total_trades > 0 else 0
    min_pnl = signal_df['PnL'].min() if total_trades > 0 else 0
    
    win_pct = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
    loss_pct = len(losing_trades) / total_trades * 100 if total_trades > 0 else 0
    
    # Group by date and calculate daily PnL
    pnl_per_day = signal_df.groupby('Date').agg({'PnL': 'sum', 'Quantity': 'sum'}).reset_index()
    
    cost_per_trade_list = []
    net_pnl_list = []
    capital_needed_list = []
    capital_after_list = []
    
    current_capital = starting_capital  # Initialize overall capital tracker
    
    for idx, row in pnl_per_day.iterrows():
        day_trades = signal_df[signal_df['Date'] == row['Date']]
        day_expense = 0
        day_capital_needed = 0  # Initialize daily capital before summing
        
        for _, trade in day_trades.iterrows():
            turnover = trade['Buy Premium'] * trade['Quantity'] * 2  # Buy + Sell
            brokerage = brokerage_per_trade
            gst = brokerage * gst_rate
            stamp_duty = turnover * stamp_duty_rate
            total_cost = brokerage + gst + stamp_duty
            day_expense += total_cost

            # Calculate capital needed for each trade
            trade_capital = trade['Buy Premium'] * trade['Quantity']
            day_capital_needed += trade_capital
        
        # Update capital after daily PnL
        current_capital += row['PnL'] - day_expense
        
        cost_per_trade_list.append(round(day_expense, 2))
        net_pnl_list.append(round(row['PnL'] - day_expense, 2))
        capital_needed_list.append(round(day_capital_needed, 2))
        capital_after_list.append(round(current_capital, 2))
    
    pnl_per_day['Total PnL'] = pnl_per_day['PnL'].round(2)
    pnl_per_day['Net Expense'] = cost_per_trade_list
    pnl_per_day['Net PnL'] = net_pnl_list
    pnl_per_day['Capital Needed'] = capital_needed_list
    pnl_per_day['Capital After'] = capital_after_list
    
    pnl_per_day = pnl_per_day[['Date', 'Total PnL', 'Net Expense', 'Net PnL', 'Capital Needed', 'Capital After']]
    
    total_expense = sum(cost_per_trade_list)
    
    summary = {
        "Total Trades": total_trades,
        "Winning Trades": len(winning_trades),
        "Losing Trades": len(losing_trades),
        "Win %": round(win_pct, 2),
        "Loss %": round(loss_pct, 2),
        "Total PnL": round(total_pnl, 2),
        "Average PnL": round(avg_pnl, 2),
        "Max PnL": round(max_pnl, 2),
        "Min PnL": round(min_pnl, 2),
        "Total Expense": round(total_expense, 2),
        "Net PnL (After Expenses)": round(sum(net_pnl_list), 2),
        "Final Capital": round(current_capital, 2)
    }
    
    summary_df = pd.DataFrame([summary])
    return summary_df, pnl_per_day

def compute_trade_pnl(signal_log_df, df):
    """
    Compute PnL and exit reason for each signal in signal_log_df based on price data in df.
    Returns updated DataFrame with Sell Price, PnL, and Exit Reason.
    """
    trade_results = []

    for _, row in signal_log_df.iterrows():
        day = row['Date']
        entry_time = row['Entry Time']
        exit_time = row['Time Exit (16 mins after entry)']
        buy_premium = row['Buy Premium']
        qty = row['Quantity']
        stoploss = row['Stoploss (Trailing 10%)']
        take_profit = row['Take Profit (10% rise)']
        option_type = row['Option Selected']

        # Filter df for the trading day and after entry
        day_df = df[df['Datetime'].dt.date == day]
        day_after_entry = day_df[(day_df['Datetime'] >= entry_time) & (day_df['Datetime'] <= exit_time)].sort_values('Datetime')

        sell_price = None
        actual_exit_time = exit_time
        exit_reason = "Time Exit"

        for _, candle in day_after_entry.iterrows():
            price = candle['Close_^NSEI']  #  used for simulation; replace with option price if available
            
            # Check Take Profit for CALL or PUT
            if take_profit and (
                (option_type.upper() == "CE" and price >= take_profit) or
                (option_type.upper() == "PE" and price <= take_profit)
            ):
                sell_price = take_profit
                exit_reason = "Take Profit"
                actual_exit_time = candle['Datetime']
                break

            # Check Stoploss
            elif stoploss and (
                (option_type.upper() == "CE" and price <= stoploss) or
                (option_type.upper() == "PE" and price >= stoploss)
            ):
                sell_price = stoploss
                exit_reason = "Stoploss"
                actual_exit_time = candle['Datetime']
                break

        # If neither TP nor SL hit, exit at last available price (time exit)
        if sell_price is None:
            sell_price = day_after_entry['Close_^NSEI'].iloc[-1]

        # Compute PnL
        pnl = (sell_price - buy_premium) * qty if option_type.upper() == "CE" else (buy_premium - sell_price) * qty

        trade_results.append({
            **row.to_dict(),
            "Sell Price": sell_price,
            "Exit Reason": exit_reason,
            "Actual Exit Time": actual_exit_time,
            "PnL": pnl
        })

    return pd.DataFrame(trade_results)

def calculate_trade_cost(buy_price, sell_price, quantity, option_type="CE", brokerage_type="fixed"):
    """
    Calculate total cost/charges per trade.
    
    Params:
    - buy_price: Entry price per unit
    - sell_price: Exit price per unit
    - quantity: Number of units
    - option_type: "CE" or "PE"
    - brokerage_type: "fixed" or "percentage"
    
    Returns total charges
    """
    turnover = (buy_price + sell_price) * quantity

    # Brokerage
    if brokerage_type == "fixed":
        brokerage = 20  # assume ₹20 per trade
    else:  # percentage
        brokerage = turnover * 0.0003  # 0.03%

    # Exchange Transaction Charges
    exchange_charges = turnover * 0.0000325  # 0.00325%

    # GST on brokerage (18%)
    gst = 0.18 * brokerage

    # SEBI Charges (approx)
    sebi_charges = turnover * 0.000001

    # Stamp Duty (approx)
    stamp_duty = turnover * 0.00003

    total_charges = brokerage + exchange_charges + gst + sebi_charges + stamp_duty
    return total_charges

def compute_trade_pnl_with_costs(signal_log_df, df):
    """
    Compute PnL, exit reason, and capital impact per trade.
    """
    trade_results = []

    capital = 0  # running capital (cumulative PnL)
    

    for _, row in signal_log_df.iterrows():
        day = row['Date']
        entry_time = row['Entry Time']
        exit_time = row['Time Exit (16 mins after entry)']
        buy_premium = row['Buy Premium']
        qty = row['Quantity']
        stoploss = row['Stoploss (Trailing 10%)']
        take_profit = row['Take Profit (10% rise)']
        option_type = row['Option Selected']
        # Capital needed for this trade (premium × quantity)
        capital_needed = buy_premium * qty

        day_df = df[df['Datetime'].dt.date == day]
        day_after_entry = day_df[day_df['Datetime'] >= entry_time].sort_values('Datetime')

        sell_price = None
        exit_reason = "Time Exit"

        for _, candle in day_after_entry.iterrows():
            price = candle['Close_^NSEI']  # Option price if available
            if take_profit and price >= take_profit:
                sell_price = take_profit
                exit_reason = "Take Profit"
                exit_time = candle['Datetime']
                break
            elif stoploss and price <= stoploss:
                sell_price = stoploss
                exit_reason = "Stoploss"
                exit_time = candle['Datetime']
                break

        if sell_price is None:
            sell_price = day_after_entry['Close_^NSEI'].iloc[0]  # fallback

        raw_pnl = (sell_price - buy_premium) * qty if option_type.upper() == "CE" else (buy_premium - sell_price) * qty

        # Calculate brokerage & charges
        total_charges = calculate_trade_cost(buy_premium, sell_price, qty, option_type)
        
        net_pnl = raw_pnl - total_charges
        capital += net_pnl

        trade_results.append({
            **row.to_dict(),
            "Sell Price": sell_price,
            "Exit Reason": exit_reason,
            "Actual Exit Time": exit_time,
            "Raw PnL": raw_pnl,
            "Total Charges": total_charges,
            "Net PnL": net_pnl,
            "Capital Needed": capital_needed,  # ✅ Added column
            "Capital After Trade": capital
        })

    return pd.DataFrame(trade_results)
def display_3pm_candle_info(df, day):
    """
    Display the 3PM candle Open and Close prices for a given day (datetime.date).
    
    Parameters:
    - df: DataFrame with 'Datetime' column (timezone-aware datetime)
    - day: datetime.date object representing the trading day
    
    Returns:
    - (open_price, close_price) tuple or (None, None) if candle not found
    """
    candle = df[(df['Datetime'].dt.date == day) &
                (df['Datetime'].dt.hour == 15) &
                (df['Datetime'].dt.minute == 0)]
    
    if candle.empty:
        st.warning(f"No 3:00 PM candle found for {day}")
        return None, None
    
    open_price = candle.iloc[0]['Open_^NSEI']
    close_price = candle.iloc[0]['Close_^NSEI']
    
    #st.info(f"3:00 PM Candle for {day}: Open = {open_price}, Close = {close_price}")
    #st.write(f"🔵 3:00 PM Open for {day}: {open_price}")
    #st.write(f"🔴 3:00 PM Close for {day}: {close_price}")
    
    return open_price, close_price


def generate_trade_log_from_option(result, trade_signal):
    if result is None or trade_signal is None:
        return None
    # Determine exit reason and price
    stoploss_hit = False
    target_hit = False
    
    #exit_time = pd.to_datetime(exit_time)
    #result.index = pd.to_datetime(result.index)

    
    
    

    option = result['option_data']
    qty = result['total_quantity']

    condition = trade_signal['condition']
    entry_time = trade_signal['entry_time']
    message = trade_signal['message']

    buy_price = option.get('lastPrice', trade_signal.get('buy_price'))
    expiry = option.get('expiryDate', trade_signal.get('expiry'))
    option_type = option.get('optionType', trade_signal.get('option_type'))

    stoploss = buy_price * 0.9
    take_profit = buy_price * 1.10
    partial_qty = qty // 2
    time_exit = entry_time + timedelta(minutes=16)

    

    

    trade_log = {
        "Condition": condition,
        "Option Type": option_type,
        "Strike Price": option.get('strikePrice'),
        #"Exit Price": exit_price,  # ✅ new column
        "Buy Premium": buy_price,
        "Stoploss (Trailing 10%)": stoploss,
        "Take Profit (10% rise)": take_profit,
        "Quantity": qty,
        "Partial Profit Booking Qty (50%)": partial_qty,
        "Expiry Date": expiry.strftime('%Y-%m-%d') if hasattr(expiry, 'strftime') else expiry,
        "Entry Time": entry_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(entry_time, 'strftime') else entry_time,
        "Time Exit (16 mins after entry)": time_exit.strftime('%Y-%m-%d %H:%M:%S'),
        "Trade Message": message
        #"Trade Details": row["Trade Details"],
        #"Exit Reason": reason
    }

    # Add condition-specific details
    if condition == 1:
        trade_log["Trade Details"] = (
            "Buy nearest ITM CALL option. Stoploss trailing 10% below buy premium. "
            "Book 50% qty profit when premium rises 10%. "
            "Time exit after 16 minutes if no target hit."
        )
    elif condition == 2:
        trade_log["Trade Details"] = (
            "Major gap down. Buy nearest ITM PUT option when next candle crosses low of 9:30 candle. "
            "Stoploss trailing 10% below buy premium."
        )
    elif condition == 3:
        trade_log["Trade Details"] = (
            "Major gap up. Buy nearest ITM CALL option. Stoploss trailing 10% below buy premium. "
            "Book 50% qty profit when premium rises 10%. "
            "Time exit after 16 minutes if no target hit."
        )
    elif condition == 4:
        trade_log["Trade Details"] = (
            "Buy nearest ITM PUT option. Stoploss trailing 10% below buy premium. "
            "Book 50% qty profit when premium rises 10%. "
            "Time exit after 16 minutes if no target hit."
        )
    else:
        trade_log["Trade Details"] = "No specific trade details available."

    trade_log_df = pd.DataFrame([trade_log])
    return trade_log_df
def option_chain_finder(option_chain_df, spot_price, option_type, lots=10, lot_size=75):
    """
    Find nearest ITM option in option chain DataFrame.

    Parameters:
    - option_chain_df: pd.DataFrame with columns including ['strikePrice', 'expiryDate', 'optionType', ...]
    - spot_price: float, current underlying price
    - option_type: str, 'CE' for Call or 'PE' for Put
    - lots: int, number of lots to trade (default 10)
    - lot_size: int, lot size per option contract (default 75)

    Returns:
    - dict with keys:
        'strikePrice', 'expiryDate', 'optionType', 'total_quantity', 'option_data' (pd.Series row)
    """

    # Ensure expiryDate is datetime
    if not pd.api.types.is_datetime64_any_dtype(option_chain_df['expiryDate']):
        option_chain_df['expiryDate'] = pd.to_datetime(option_chain_df['expiryDate'])

    today = pd.Timestamp.today().normalize()

    # Find nearest expiry on or after today
    expiries = option_chain_df.loc[option_chain_df['expiryDate'] >= today, 'expiryDate'].unique()
    if len(expiries) == 0:
        raise ValueError("No expiry dates found on or after today.")
    nearest_expiry = min(expiries)

    # Filter for nearest expiry and option type
    df_expiry = option_chain_df[
        (option_chain_df['expiryDate'] == nearest_expiry) &
        (option_chain_df['optionType'] == option_type)
    ]

    if df_expiry.empty:
        raise ValueError(f"No options found for expiry {nearest_expiry.date()} and type {option_type}")

    # Find nearest ITM strike
    if option_type == "CALL":
        itm_strikes = df_expiry[df_expiry['strikePrice'] <= spot_price]
        if itm_strikes.empty:
            # fallback to minimum strike (OTM)
            nearest_strike = df_expiry['strikePrice'].min()
        else:
            nearest_strike = itm_strikes['strikePrice'].max()
    else:  # 'PE'
        itm_strikes = df_expiry[df_expiry['strikePrice'] >= spot_price]
        if itm_strikes.empty:
            # fallback to maximum strike (OTM)
            nearest_strike = df_expiry['strikePrice'].max()
        else:
            nearest_strike = itm_strikes['strikePrice'].min()

    # Get option row
    option_row = df_expiry[df_expiry['strikePrice'] == nearest_strike].iloc[0]

    total_qty = lots * lot_size

    return {
        'strikePrice': nearest_strike,
        'expiryDate': nearest_expiry,
        'optionType': option_type,
        'total_quantity': total_qty,
        'option_data': option_row
    }
def find_nearest_itm_option0():
    import nsepython
    from nsepython import nse_optionchain_scrapper


    option_chain = nse_optionchain_scrapper('NIFTY')
    df = []
    
    for item in option_chain['records']['data']:
        strike = item['strikePrice']
        expiry = item['expiryDate']
        if 'CE' in item:
            ce = item['CE']
            ce['strikePrice'] = strike
            ce['expiryDate'] = expiry
            ce['optionType'] = 'CE'
            df.append(ce)
        if 'PE' in item:
            pe = item['PE']
            pe['strikePrice'] = strike
            pe['expiryDate'] = expiry
            pe['optionType'] = 'PE'
            df.append(pe)
    
    #import pandas as pd
    option_chain_df = pd.DataFrame(df)
    option_chain_df['expiryDate'] = pd.to_datetime(option_chain_df['expiryDate'])
    #st.write(option_chain_df.head())
    return  option_chain_df

def find_nearest_itm_option_dec(kite, spot_price, option_type):
    df = load_zerodha_instruments()
    chain = get_nifty_option_chain(df)

    if chain.empty:
        raise ValueError("No NIFTY options found in Zerodha instruments")

    selected = find_nearest_itm_from_zerodha(chain, spot_price, option_type)

    tradingsymbol = selected["tradingsymbol"]
    ltp = get_ltp(kite, tradingsymbol)

    return {
        "tradingsymbol": tradingsymbol,
        "strike": selected["strike"],
        "instrument_token": selected["instrument_token"],
        "option_type": option_type.upper(),
        "ltp": ltp
    }




def get_nearest_weekly_expiry(today):
    """
    Placeholder: implement your own logic to find nearest weekly expiry date
    For demo, returns today + 7 days (Saturday)
    """
    return today + pd.Timedelta(days=7)
    
def plot_nifty_multiday(df, trading_days):
    """
    Plots Nifty 15-min candles for multiple trading days with each previous day's 3PM Open/Close
    marked only on the next trading day and extending only until 3PM candle.
    
    Parameters:
    - df : DataFrame with columns ['Datetime', 'Open_^NSEI', 'High_^NSEI', 'Low_^NSEI', 'Close_^NSEI']
    - trading_days : list of sorted trading dates (datetime.date)
    """
    
    fig = go.Figure()
    
    for i in range(1, len(trading_days)):
        day0 = trading_days[i-1]  # Previous day (for Base Zone)
        day1 = trading_days[i]    # Current day
        
        # Filter data for current day only
        df_day1 = df[df['Datetime'].dt.date == day1]
        
        # Add candlestick trace for current day
        fig.add_trace(go.Candlestick(
            x=df_day1['Datetime'],
            open=df_day1['Open_^NSEI'],
            high=df_day1['High_^NSEI'],
            low=df_day1['Low_^NSEI'],
            close=df_day1['Close_^NSEI'],
            name=f"{day1}"
        ))
        
        # Get 3 PM candle of previous day (Base Zone)
        candle_3pm = df[df['Datetime'].dt.date == day0]
        candle_3pm = candle_3pm[(candle_3pm['Datetime'].dt.hour == 15) &
                                (candle_3pm['Datetime'].dt.minute == 0)]
        
        if not candle_3pm.empty:
            open_3pm = candle_3pm.iloc[0]['Open_^NSEI']
            close_3pm = candle_3pm.iloc[0]['Close_^NSEI']
            
            # Get day1 3PM candle time for line end
            day1_3pm_candle = df_day1[(df_day1['Datetime'].dt.hour == 15) &
                                       (df_day1['Datetime'].dt.minute == 0)]
            if not day1_3pm_candle.empty:
                x_end = day1_3pm_candle['Datetime'].iloc[0]
                x_start = df_day1['Datetime'].min()
                
                # Horizontal line for Open
                fig.add_shape(
                    type="line",
                    x0=x_start,
                    x1=x_end,
                    y0=open_3pm,
                    y1=open_3pm,
                    line=dict(color="blue", width=1, dash="dot"),
                )
                
                # Horizontal line for Close
                fig.add_shape(
                    type="line",
                    x0=x_start,
                    x1=x_end,
                    y0=close_3pm,
                    y1=close_3pm,
                    line=dict(color="red", width=1, dash="dot"),
                )
    
    # Layout adjustments
    fig.update_layout(
        title="Nifty 15-min Candles with Previous Day 3PM Open/Close Lines (to next day 3PM)",
        xaxis_rangeslider_visible=False,
        xaxis=dict(
            rangebreaks=[
                dict(bounds=["sat", "mon"]),          # Hide weekends
                dict(bounds=[15.5, 9.25], pattern="hour")  # Hide off-hours
            ]
        )
    )
    
    return fig   

##############################################################################





    

# 🎨 Modern colorful theme (light/dark aware)
BASE_CSS = """
<style>
/* App background */
.stApp {
  background: linear-gradient(135deg, #eef2ff 0%, #ffffff 60%);
}
[data-theme="dark"] .stApp, .stApp[theme="dark"] {
  background: linear-gradient(135deg, #0b1220 0%, #111827 60%);
}

:root {
  --blue: #2563eb;    /* indigo-600 */
  --amber: #f59e0b;   /* amber-500 */
  --purple: #9333ea;  /* purple-600 */
  --teal: #14b8a6;    /* teal-500 */
  --green: #16a34a;   /* green-600 */
  --red: #dc2626;     /* red-600 */
  --card-bg: rgba(255,255,255,0.75);
  --card-border: rgba(0,0,0,0.08);
}
[data-theme="dark"] :root, .stApp[theme="dark"] :root {
  --card-bg: rgba(17,24,39,0.65);
  --card-border: rgba(255,255,255,0.08);
}

/* Generic colorful card */
.card {
  background: var(--card-bg);
  border: 1px solid var(--card-border);
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 6px 22px rgba(0,0,0,0.08);
}
.card h3 { margin-top: 0 !important; }

/* KPI tiles */
.kpi-card { text-align:center; border-radius:16px; padding:16px; }
.kpi-title { margin:0; font-weight:700; font-size:14px; opacity:.9; }
.kpi-value { font-size:30px; font-weight:800; margin-top:6px; }

/* Buttons */
.stButton > button {
  background: linear-gradient(135deg, var(--blue), #3b82f6);
  color: #fff; border: none; border-radius: 10px; padding: 10px 18px; font-weight:700;
  box-shadow: 0 6px 18px rgba(37,99,235,0.3);
}
.stButton > button:hover { filter: brightness(1.05); }

/* Secondary variants via data-color attr */
.button-amber > button { background: linear-gradient(135deg, var(--amber), #fbbf24); box-shadow: 0 6px 18px rgba(245,158,11,.35); }
.button-purple > button { background: linear-gradient(135deg, var(--purple), #a855f7); box-shadow: 0 6px 18px rgba(147,51,234,.35); }
.button-teal > button { background: linear-gradient(135deg, var(--teal), #2dd4bf); box-shadow: 0 6px 18px rgba(20,184,166,.35); }

/* Badges */
.badge { display:inline-block; padding:4px 10px; border-radius:9999px; font-size:12px; font-weight:700; }
.badge.success { background: rgba(22,163,74,.15); color: var(--green); }
.badge.danger { background: rgba(220,38,38,.15); color: var(--red); }

/* Dataframes */
[data-testid="stDataFrame"] div .row_heading, [data-testid="stDataFrame"] div .blank {background: transparent;}

/* Dividers */
hr { border-top: 1px solid rgba(0,0,0,.08); }
</style>
"""
st.markdown(BASE_CSS, unsafe_allow_html=True)

# ------------------------------------------------------------
# Session State Defaults
# ------------------------------------------------------------
def _init_state():
    defaults = dict(
        theme_dark=False,
        api_status={"Zerodha": False, "Fyers": False, "AliceBlue": False},
        connected_broker=None,
        live_running=False,
        live_strategy=None,
        trade_logs=pd.DataFrame(columns=["Time","Symbol","Action","Qty","Price","PnL"]),
        capital=100000.0,
        risk_per_trade_pct=1.0,
        max_trades=3,
        strategies=[
            {"name": "3PM  Strategy 1.0", "short": "3PM 15min  with  last day breakout with today", "metrics": {"CAGR": 18.3, "Win%": 85.8, "MaxDD%": 15.6}},
            {"name": "Doctor Strategy 1.0", "short": "BB 20 SMA breakout with IV filter", "metrics": {"CAGR": 18.3, "Win%": 64.8, "MaxDD%": 12.6}},
            {"name": "ORB (Opening Range Breakout)", "short": "Range breakout after first 15m", "metrics": {"CAGR": 14.1, "Win%": 57.4, "MaxDD%": 10.9}},
            {"name": "EMA20 + Volume", "short": "Momentum confirmation with volume push", "metrics": {"CAGR": 11.7, "Win%": 55.0, "MaxDD%": 9.8}},
        ],
        selected_strategy="Doctor Strategy 1.0",
        pricing=[
            {"name": "Basic", "price": 699, "features": ["1 live strategy","Backtests & charts","Telegram alerts","Email support"]},
            {"name": "Pro", "price": 1499, "features": ["3 live strategies","Automation (paper/live)","Custom risk settings","Priority support"]},
            {"name": "Enterprise", "price": 3999, "features": ["Unlimited strategies","Broker API integration","SLA & onboarding","Dedicated manager"]},
        ],
        faq=[
            ("Is algo trading risky?", "Yes. Markets involve risk. Backtests are not guarantees. Manage risk per trade and overall exposure."),
            ("Which brokers are supported?", "Zerodha, Fyers, AliceBlue out-of-the-box. Others upon request."),
            ("Do you store my API keys?", "Keys are stored encrypted on device/server per your deployment. You control revocation."),
        ],
    )
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ------------------------------------------------------------
# Utility: Colors & Components
# ------------------------------------------------------------

STRAT_COLORS: Dict[str, str] = {
    "Doctor Strategy 1.0": "var(--blue)",
    "ORB (Opening Range Breakout)": "var(--amber)",
    "EMA20 + Volume": "var(--teal)",
}


def kpi_card(title: str, value: str, color_css: str):
    st.markdown(
        f"""
        <div class='kpi-card' style='background: linear-gradient(135deg, {color_css}15, transparent); border:1px solid {color_css}35'>
            <div class='kpi-title' style='color:{color_css}'>{title}</div>
            <div class='kpi-value' style='color:{color_css}'>{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def strategy_card(name: str, desc: str, metrics: Dict[str, float]):
    color = STRAT_COLORS.get(name, "var(--purple)")
    st.markdown(
        f"""
        <div class='card' style='border-left:6px solid {color};'>
            <h3 style='color:{color}'>{name}</h3>
            <p style='margin:6px 0 14px 0'>{desc}</p>
            <div style='display:flex;gap:16px;flex-wrap:wrap'>
                <div class='badge' style='background:{color}15;color:{color}'><b>CAGR</b>&nbsp;{metrics.get('CAGR',0):.1f}%</div>
                <div class='badge' style='background:{color}15;color:{color}'><b>Win%</b>&nbsp;{metrics.get('Win%',0):.1f}%</div>
                <div class='badge' style='background:{color}15;color:{color}'><b>Max DD</b>&nbsp;{metrics.get('MaxDD%',0):.1f}%</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def plot_equity_curve(pnl_series: pd.Series, title: str = "Equity Curve"):
    if pnl_series is None or len(pnl_series) == 0:
        st.info("Upload backtest CSV to see equity curve.")
        return
    cum = pnl_series.cumsum()
    fig = go.Figure()
    fig.add_trace(go.Scatter(y=cum, mode='lines', name='Equity', line=dict(width=3)))
    fig.update_layout(
        height=360,
        title=title,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)


def plot_candles(df: pd.DataFrame, title: str = "Candlestick Chart"):
    req = {"Datetime", "Open", "High", "Low", "Close"}
    if not req.issubset(df.columns):
        st.warning("Candlestick requires columns: Datetime, Open, High, Low, Close")
        return
    fig = go.Figure(data=[go.Candlestick(x=df['Datetime'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(
        height=420,
        title=title,
        xaxis_rangeslider_visible=False,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)


def add_trade_log(symbol: str, side: str, qty: int, price: float, pnl: float):
    row = {
        "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Symbol": symbol,
        "Action": side,
        "Qty": qty,
        "Price": price,
        "PnL": pnl,
    }
    st.session_state.trade_logs = pd.concat([st.session_state.trade_logs, pd.DataFrame([row])], ignore_index=True)

# ------------------------------------------------------------
# Sidebar Navigation
# ------------------------------------------------------------
with st.sidebar:
    st.image("logo_new.png", width=120)
    st.title("TALK ALGO LABS")
    # Theme toggle (visual only)
    st.session_state.theme_dark = st.toggle("Dark Theme", value=st.session_state.theme_dark)
    # Mark attribute for CSS targeting
    st.markdown(f"<div style='display:none' data-theme={'dark' if st.session_state.theme_dark else 'light'}></div>", unsafe_allow_html=True)

    #st.image(
        #"https://assets-global.website-files.com/5e0a1f0d3a9f1b6f7f1b6f34/5e0a1f63a4f62a5534b5f5f9_finance-illustration.png",
        #use_container_width=True,
    #)

    MENU = st.radio(
        "Navigate",
        ["🏠 Home", "My Account", "Login Zerodha  API","Strategy Signals","Strategy Multi Signals", "Backtest","Live Trade","Setting","Paper Trade", "Products", "Support","10.10 Strategy","LIVE TRADE 3","Telegram","Moniter Position Test","Download Instrument","NIFTY 3:20 PM Intraday Strategy","Logout"],
        index=0,
    )

# ------------------------------------------------------------
# Home
# ------------------------------------------------------------
if MENU == "🏠 Home":
    st.title("Welcome to TALK ALGO LABS  Trading Platform")
    st.write("Automate your trades with smart, auditable strategies. Connect your broker, choose a strategy, and manage risk — all from one dashboard.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### What is Algo Trading?")
        st.markdown(
        r"""
        Algorithmic Trading (**Algo Trading**) means using **computer programs** to automatically place
        **buy/sell orders** based on predefined, rule‑based logic. Instead of clicking buttons manually,
        algorithms monitor data streams (price, volume, indicators) and execute trades **fast**, **consistently**,
        and **without emotions**.
        
        
        ---
        
        
        ### 🔑 Why Traders Use It
        - **Automation**: Executes your plan 24×7 (where markets allow) exactly as written.
        - **Speed**: Milliseconds matter for entries, exits, and order routing.
        - **Backtesting**: Test your ideas on **historical data** before going live.
        - **Scalability**: Watch dozens of instruments simultaneously.
        
        
        ### ⚠️ Risks to Respect
        - **Bad logic = fast losses** (garbage in, garbage out).
        - **Overfitting**: Great on the past, weak in live markets.
        - **Operational**: Data glitches, API limits, slippage, latency.
        
        
        > **TL;DR**: Algo Trading = *rules → code → automated execution*.
        """
        )
        st.write("Algorithmic trading executes orders using pre-defined rules for entries, exits, and risk management.")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### Why Choose Us?")
        st.markdown("""
        At **Shree Software**, we are committed to delivering **high-quality software solutions** that cater to your business needs. Our approach combines **innovation, reliability, and customer focus** to ensure your success.
        
        
        ---
        
        
        ### 🔑 Key Reasons to Choose Us
        
        
        1. **Expert Team**: Experienced developers and designers who understand your business challenges.
        2. **Customized Solutions**: Tailored software to match your specific requirements.
        3. **On-Time Delivery**: We value your time and ensure project timelines are met.
        4. **Affordable Pricing**: Competitive pricing without compromising on quality.
        5. **24/7 Support**: Dedicated support team to help you whenever you need assistance.
        
        
        > Our mission is to empower businesses through technology, making processes **efficient, reliable, and scalable**.
        
        
        ### 🎯 Our Approach
        - **Consultation & Analysis**: Understanding your business goals.
        - **Design & Development**: Building robust and scalable software.
        - **Testing & Quality Assurance**: Ensuring flawless performance.
        - **Deployment & Maintenance**: Smooth launch and continuous support.
        
        
        We combine the best of **technology, strategy, and creativity** to ensure your project stands out.
        """)
        
        
        # Optional HTML Styling for Highlight
        st.markdown(
        """
        <div style='padding:12px;border-radius:12px;background:#f0f8ff;border:1px solid #cce0ff;'>
        <h4 style='margin:0 0 6px 0;'>Client Commitment</h4>
        <p style='margin:0;'>We focus on delivering solutions that <b>drive growth, efficiency, and innovation</b> for our clients.</p>
        </div>
        """,
        unsafe_allow_html=True
        )
        
        
        st.success("Learn more about our services by contacting us today!")
        st.write("Colorful, clean UI, safer defaults, backtests, paper trading, and live automation with popular brokers.")
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("### Risk Disclaimer")
        st.write("Algorithmic trading executes orders using pre-defined rules for entries, exits, and risk management.Trading involves risk. Past performance does not guarantee future returns. Trade responsibly.")
        
        st.markdown("""
        ---
        ### ⚠️ Risk Disclaimer
        
        1. **Informational Purpose Only**  
           All content, services, or solutions provided by **Shree Software** are for **informational and educational purposes only**. They do not constitute financial, legal, or professional advice.
        
        2. **No Guaranteed Outcomes**  
           While we aim to provide accurate and timely information, **we do not guarantee any specific results, profits, or success** from using our services.
        
        3. **User Responsibility**  
           Clients and users must exercise **due diligence**, make **informed decisions**, and consult qualified professionals when necessary before acting on any information or solutions provided.
        
        4. **Limitation of Liability**  
           **Shree Software shall not be liable** for any direct, indirect, or consequential loss or damage resulting from the use of our services, content, or advice.
        
        5. **Third-Party Dependencies**  
           We may provide data, tools, or links from third-party sources. **We are not responsible for the accuracy, completeness, or outcomes** associated with such third-party information.
        
        6. **Market / Technology Risks** *(if applicable)*  
           For financial or technical solutions, market conditions, system failures, or software limitations may impact results. Users must acknowledge these **inherent risks**.
        ---
        """)
        st.write("Trading involves risk. Past performance does not guarantee future returns. Trade responsibly.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    st.subheader("Quick KPIs")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi_card("Capital", f"₹{st.session_state.capital:,.0f}", "var(--blue)")
    with k2:
        kpi_card("Risk / Trade", f"{st.session_state.risk_per_trade_pct:.1f}%", "var(--amber)")
    with k3:
        kpi_card("Max Trades", str(st.session_state.max_trades), "var(--purple)")
    with k4:
        connected = st.session_state.connected_broker or "—"
        color = "var(--green)" if connected != "—" else "var(--red)"
        kpi_card("Broker", connected, color)

    st.divider()
    st.info("Use the sidebar to explore Strategies, connect Broker APIs, and run the live Dashboard.")


elif MENU == "Moniter Position Test":
    st.title("📊 Monitor Live Option Position")

    col1, col2 = st.columns(2)

    with col1:
        symbol = st.text_input(
            "Option Symbol",
            value="NIFTY26JAN25150PE",
            help="Example: NIFTY26JAN25150PE"
        )

        qty = st.number_input(
            "Quantity",
            min_value=1,
            step=1,
            value=130
        )

        entry_price = st.number_input(
            "Average Entry Price",
            min_value=0.0,
            step=0.05,
            value=127.15
        )

    with col2:
        strike = st.number_input(
            "Strike Price",
            min_value=0,
            step=50,
            value=25150
        )

        expiry_date = st.date_input(
            "Expiry Date",
            value=date(2026, 1, 27)
        )

        option_type = st.selectbox(
            "Option Type",
            ["CALL", "PUT"]
        )

    start_monitor = st.button("▶ Start Monitoring")

    if start_monitor:
        if not symbol:
            st.error("Please enter a valid option symbol")
            st.stop()

        
    monitor_position_live_with_theta_table(
            kite=kite,
            symbol=symbol,
            qty=int(qty),
            entry_price=float(entry_price),
            strike=int(strike),
            expiry_date=expiry_date,
            option_type=option_type
        )

# ------------------------------------------------------------
# Backtest Strategies
# ------------------------------------------------------------
     
elif MENU == "Backtest":
    st.title("Backtest Strategies")
    st.session_state.param_rows = []
    if "signal_log" not in st.session_state:
         st.session_state.signal_log = []
    #today = latest_time.date()
    st.title("🔴 BACKTEST LIVE TRADE ")
    #st.title("🔴 Live Nifty 15-Minute Chart + Signal Engine")
    if not is_kite_connected(kite):
        st.warning("Please login first to access LIVE trade.")
        st.stop()     # Stop page execution safely

    #st.success("You are logged in.")
     
    st.session_state.param_rows = []
    from streamlit_autorefresh import st_autorefresh
    import time             # Python's time module
    from datetime import time  # datetime.time (conflict!)
    # Initialize Kite in session_state
    if "kite" not in st.session_state:
        st.session_state.kite = None
    else:
        kite = st.session_state.get("kite")
    # --- SESSION STATE INIT ---
    if "order_executed" not in st.session_state:
        st.session_state.order_executed = False
        
    
    if "signal_time" not in st.session_state:
        st.session_state.signal_time = None
    # Add after data processing:
    def is_kite_connected(kite):
        try:
            kite.profile()
            return True
        except:
            return False

    

    #st.title("Algo Trading Dashboard")

    # ===== ROW 1 =====
    col1, col2 = st.columns([1, 3])

    with col1:
        funds = get_fund_status(kite)
        #st.write(funds) 
        cash = (funds['cash'])
        cash = (funds['net'])  

        st.subheader("Connection Status") 
        if is_kite_connected(kite):
             st.success("Kite connection active")
        else:
             st.error("Kite session expired. Please login again.") 
        st.subheader("WebSocket Status")
        #st.success("Kite Connected")
        st.info("WebSocket: Running")
        st.subheader("FUND Status")
        st.metric("Funds ₹.", cash)

    with col2:
         st.subheader("NIFTY 50 / 15 Min Chart")
        #---------------------------------------------------------------------
         ist = pytz.timezone("Asia/Kolkata")
         now = datetime.now(ist).time()
         
         # Market hours condition
         start = time(9, 15)   # 9:30 AM
         end = time(15, 25)    # 3:25 PM
         
         # Refresh only between 9:30–3:25
         if start <= now <= end:
             #st_autorefresh(interval=60000, key="refresh")  # 1 minute refresh
             st_autorefresh(interval=60000, key="refresh_live3")
         else:
             st.info("Auto-refresh is paused — Outside market hours (9:30 AM to 3:25 PM).")
     
         #st.title("Nifty 15-min Chart")
         
         # Select date input (default today)
         selected_date = st.date_input("Select date", value=datetime.today())
         
         # Calculate date range to download (7 days before selected_date to day after selected_date)
         start_date = selected_date - timedelta(days=7)
         end_date = selected_date + timedelta(days=1)
         
         # Download data for ^NSEI from start_date to end_date
         df = yf.download("^NSEI", start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="15m")
         
         if df.empty:
             st.warning("No data downloaded for the selected range.")
             st.stop()
         df.reset_index(inplace=True)
         
         if 'Datetime_' in df.columns:
             df.rename(columns={'Datetime_': 'Datetime'}, inplace=True)
         elif 'Date' in df.columns:
             df.rename(columns={'Date': 'Datetime'}, inplace=True)
         # Add any other detected name if needed
         
         
         #st.write(df.columns)
         #st.write(df.head(10))
         # Flatten columns if MultiIndex
         if isinstance(df.columns, pd.MultiIndex):
             df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
         
         # Rename datetime column if needed
         if 'Datetime' not in df.columns and 'datetime' in df.columns:
             df.rename(columns={'datetime': 'Datetime'}, inplace=True)
         #st.write(df.columns)
         #st.write(df.columns)
         # Convert to datetime & timezone aware
         #df['Datetime'] = pd.to_datetime(df['Datetime'])
         if df['Datetime_'].dt.tz is None:
             df['Datetime'] = df['Datetime_'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
         else:
             df['Datetime'] = df['Datetime_'].dt.tz_convert('Asia/Kolkata')
         
         #st.write(df.columns)
         #st.write(df.head(10))
         
         # Filter for last two trading days to plot
         unique_days = df['Datetime'].dt.date.unique()
         if len(unique_days) < 2:
             st.warning("Not enough data for two trading days")
         else:
             last_day = unique_days[-2]
             today = unique_days[-1]
         
             df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
         
             # Get last day 3PM candle open and close
             candle_3pm = df_plot[(df_plot['Datetime'].dt.date == last_day) &
                                  (df_plot['Datetime'].dt.hour == 15) &
                                  (df_plot['Datetime'].dt.minute == 0)]
         
             if not candle_3pm.empty:
                 open_3pm = candle_3pm.iloc[0]['Open_^NSEI']
                 close_3pm = candle_3pm.iloc[0]['Close_^NSEI']
             else:
                 open_3pm = None
                 close_3pm = None
                 st.warning("No 3:00 PM candle found for last trading day.")
             #-----------------------------Marking 9.15 Candle---------------------------------
             # Get today's 9:15 AM candle
             candle_915 = df_plot[(df_plot['Datetime'].dt.date == today) &
                               (df_plot['Datetime'].dt.hour == 9) &
                               (df_plot['Datetime'].dt.minute == 15)]
          
             if not candle_915.empty:
                   o_915 = candle_915.iloc[0]['Open_^NSEI']
                   h_915 = candle_915.iloc[0]['High_^NSEI']
                   l_915 = candle_915.iloc[0]['Low_^NSEI']
                   c_915 = candle_915.iloc[0]['Close_^NSEI']
                   t_915 = candle_915.iloc[0]['Datetime']
             else:
                   o_915 = h_915 = l_915 = c_915 = t_915 = None
                   st.warning("No 9:15 AM candle found for today.")    
              
              #---------------------------------------------------------------------------------
         
              
         
             # Plot candlestick chart
             fig = go.Figure(data=[go.Candlestick(
                 x=df_plot['Datetime'],
                 open=df_plot['Open_^NSEI'],
                 high=df_plot['High_^NSEI'],
                 low=df_plot['Low_^NSEI'],
                 close=df_plot['Close_^NSEI']
             )])
             if t_915 is not None:
                   fig.add_vrect(
                       x0=t_915,
                       x1=t_915 + pd.Timedelta(minutes=15),
                       fillcolor="orange",
                       opacity=0.25,
                       layer="below",
                       line_width=0,
                       annotation_text="9:15 Candle",
                       annotation_position="top left"
                   )
             
             
     
             if o_915 is not None and c_915 is not None:
                   fig.add_hline(y=o_915, line_dash="solid", line_color="green",
                                 annotation_text="9:15 Open")
                   fig.add_hline(y=c_915, line_dash="solid", line_color="orange",
                                 annotation_text="9:15 Close") 
             if open_3pm and close_3pm:
                 fig.add_hline(y=open_3pm, line_dash="dot", line_color="blue", annotation_text="3PM Open")
                 fig.add_hline(y=close_3pm, line_dash="dot", line_color="red", annotation_text="3PM Close")
         
         
         
         
             # Draw horizontal lines as line segments only between 3PM last day and 3PM next day
         
             
             fig.update_layout(title="Nifty 15-min candles - Last Day & Today", xaxis_rangeslider_visible=False)
             fig.update_layout(
             xaxis=dict(
                 rangebreaks=[
                     # Hide weekends (Saturday and Sunday)
                     dict(bounds=["sat", "mon"]),
                     # Hide hours outside of trading hours (NSE trading hours 9:15 to 15:30)
                     dict(bounds=[15.5, 9.25], pattern="hour"),
                 ]
             )
         )
         
         
             st.plotly_chart(fig, use_container_width=True)  
        
    st.divider()
#==============================================================================================================================
    # ===== ROW 2 =====
    col3, col4 = st.columns(2)

    with col3:
        import json 
        st.subheader("Signal Log")
        df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
        #signal = trading_signal_all_conditions(df_plot)
        signal = trading_signal_all_conditions_final(df_plot) 
        save_signal_log(signal) 
        #st.write("DEBUG signal:", signal)
        #st.write("Type:", type(signal))
        df_sig1 = pd.DataFrame(signal)

        if signal and isinstance(signal, list):
              last_signal = signal[-1]
              st.success(f"✅ SIGNAL GENERATED: {last_signal['message']}")
 
        if signal is None:
            st.warning("⚠ No signal yet (conditions not met).")
        else:
            #st.success(f"✅ SIGNAL GENERATED: {signal['message']}")
            last_signal = signal[-1]  
            #df_sig1 = pd.DataFrame([signal])
            df_sig1 = pd.DataFrame(signal) 
            signal_time = df_plot["Datetime"].iloc[-1]   # last candle timestamp
            last_signal["signal_time"] = signal_time
            signal_time1=last_signal["signal_time"] 

             
 
                
                # Display as table
            #st.table(df_sig1) 
            #st.write(df_sig1) 
            st.subheader("📊 Signal Log")
            #st.write(df_sig1) 
            st.dataframe(df_sig1, use_container_width=True, hide_index=True) 
            st.session_state.trades_signals.append(df_sig1) 
            #=========================JSON TO TABLE========================
            

     #=============================================================================================
        
                           
#==============================================================================================================================
   
    with col4:
            st.subheader("Option Log")
         
            entry_time = last_signal['entry_time']
            #st.write("entry_time",entry_time) 
            #st.write("Signal Time only:", entry_time.strftime("%H:%M:%S"))  # HH:MM:SS
            signal_time=entry_time.strftime("%H:%M:%S")
            #st.write("Signal Time only:-", signal_time)  # HH:MM:SS
            #            st.write(signal)
#--------------------------------------------------------------------------------

            def generate_signals_stepwise(df):
                 all_signals = []
                 
                 # We run strategy for each candle progressively
                 for i in range(40, len(df)):   # start after enough candles
                     sub_df = df.iloc[:i].copy()
                     sig = trading_signal_all_conditions(sub_df)
                     if sig is not None:
                         all_signals.append((sub_df.iloc[-1]["Datetime"], sig))
             
                 return all_signals
     #-------------------------------------Total signals-------------------------------------------
     
            step_signals = generate_signals_stepwise(df_plot)
            if step_signals:
                     #st.info(f"Total signals detected so far: {len(step_signals)}")
                 
                     latest_time, latest_sig = step_signals[-1]
                     
                     st.success(f"🟢 Latest Candle Signal ({latest_time}):")
                     #st.write(latest_sig)
                     # Convert to DataFrame
                     df_sig = pd.DataFrame([latest_sig])
                     
                     # Display as table
                     #st.table(df_sig)
            else:
                     st.warning("No signal triggered in any candle yet.")
        
     
     #-----------------------------------Nearest ITM Option ---------------------------------------------
     
            if signal is not None:
                 #signal_time = df["Datetime"].iloc[-1].time()   # last candle time
                 option_type = last_signal["option_type"]     # CALL / PUT
                 #st.write("Option type ",option_type)
                 spot = last_signal["buy_price"]
                 #st.write("Option spot ",spot)
                 try:
                     nearest_itm = find_nearest_itm_option(kite, spot, option_type)
                     
                     st.success("Nearest ITM Option Found")
                     #                st.write(nearest_itm)
                     nearest_itm1 = pd.DataFrame([nearest_itm])
                     
                     # Display as table
                     st.table(nearest_itm1)
                     trending_symbol=nearest_itm['tradingsymbol']
                     #st.write("tradingsymbol-",trending_symbol)
                  #====================================================FLAG SIGNAL================================
                     st.session_state.trade_status = "SIGNAL"
                     st.session_state.signal_time = signal_time
                     st.session_state.signal_price = nearest_itm['ltp']   # LTP at signal candle
                     st.session_state.symbol = trending_symbol 
     
                  #==================================================================================================
             
                 except Exception as e:
                     st.error(f"Failed to fetch option: {e}")


    st.divider()
#==============================================================================================================================

    # ===== ROW 3 =====
    col5, col6 = st.columns(2)

    with col5:
            st.subheader("Parameter Values")
            option_dict = get_live_option_details(kite, trending_symbol)
            if not option_dict:
              st.warning("Live option data unavailable. Cannot proceed with trade logic.")
              st.stop()
            spot_price=spot 
            ltp = option_dict.get("ltp")
            strike = option_dict.get("strike")
            expiry = option_dict.get("expiry")
            is_call = option_dict.get("option_type") == "CALL"
          #------------------------------------------PAPER TRADE-------------------------------------------------
            if signal is not None:

              signal_time = last_signal["signal_time"]
          
              # 🔒 ENTRY LOCK — THIS PREVENTS RE-ENTRY ON REFRESH
              if st.session_state.last_executed_signal_time == signal_time:
                  pass  # already traded this signal
          
              else:
                  option_type = last_signal["option_type"]
                  spot = last_signal["spot_price"]
          
                  nearest_itm = find_nearest_itm_option(kite, spot, option_type)
                  trending_symbol = nearest_itm["tradingsymbol"]
                  option_symbol = f"NFO:{trending_symbol}"
          
                  entry_price = kite.ltp(option_symbol)[option_symbol]["last_price"]
                  initial_sl = calculate_initial_sl_15min(df_plot)  
                  
                  trade = {
                        "signal_time": signal_time,
                        "entry_time": pd.Timestamp.now(),
                        "symbol": trending_symbol,
                        "option_type": option_type,
                        "entry_price": entry_price,
                        "quantity": 65,
                        "stoploss": initial_sl,              # 🔒 FIXED AT ENTRY
                        "remaining_qty": 65,
                        "highest_price": entry_price,
                        "partial_exit_done": False,
                        "final_exit_done": False,
                        "status": "OPEN",
                        # 🔢 GREEKS SNAPSHOT AT ENTRY
                        "greeks": {
                            "Delta": greeks["Delta"],
                            "Gamma": greeks["Gamma"],
                            "Theta": greeks["Theta"],
                            "Vega": greeks["Vega"],
                            "IV": greeks["IV"]
                        } 
                    }
                  # ✅ ADD EVAL INSIDE SAME BLOCK
                  trade["greeks_eval"] = {
                      "Delta": evaluate(greeks["Delta"], 0.30, 0.85),
                      "Gamma": evaluate(greeks["Gamma"], 0.0005, None),
                      "Theta": evaluate(greeks["Theta"], -80, None),
                      "Vega": evaluate(greeks["Vega"], 3.0, None),
                      "IV": evaluate(greeks["IV"], 10, 35)
                  } 
          
                  st.session_state.paper_trades.append(trade)
          
                  # 🔐 LOCK THE SIGNAL
                  st.session_state.last_executed_signal_time = signal_time
          
                  #st.success(f"Paper trade entered @ {entry_price}")

            #monitor_paper_trades(kite)
            #for trade in st.session_state.paper_trades:
              #normalize_trade(trade)
              #manage_exit_papertrade(kite, trade)

            #st.write("Moniter")
             

 
   
          #---------------------------------------PAPER TRADE----------------------------------------------------   
              # Compute time to expiry (in years)
            days_to_exp = days_to_expiry(expiry)
            time_to_expiry = days_to_exp / 365 
            r=0.07
            r= 0.065  
            #st.write("spot_price, strike, time_to_expiry, r, ltp",spot_price, strike, time_to_expiry, r, ltp) 
            iv = implied_vol_call(spot_price, strike, time_to_expiry, r, ltp) 
            #st.write("IV  FOr (Option):CE")
            #st.write("IV (decimal):", iv)
            #st.write("IV (%):", iv * 100)    
            result = "Pass" if (iv is not None and 0.10 <= iv <= 0.35) else "Fail"
 
            #result = "Pass" if 0.10 <= iv <= 0.35 else "Fail"
            iv_result = result    
            #add_param_row("IV", round(iv, 2), "0.10 - 0.35", result)
             

#-----------------------------------IV Compute---------------------------------------------

        #spot_price = get_ltp(kite, "NSE:NIFTY 50")["ltp"]
        
         #iv_percent = compute_option_iv(nearest_itm, spot)
        
         #st.write("IV:", iv_percent)    
         
         #get_live_iv_nifty_option(kite, option_token: int, index_symbol="NSE:NIFTY 50"):        
            #st.write(nearest_itm)  

#----------------------------------IV----------------------------------------------

    
        
            iv_info = get_iv_rank0(kite, nearest_itm, lookback_days=250)
       
            #st.write("New Way Iv ",iv)  
            # Fix missing values
            if iv_info["iv"] is None:
                 iv_info["iv"] = 0
     
            if iv_info["iv_rank"] is None:
                iv_info["iv_rank"] = 0

         ##st.write("Current IV:", iv_info["iv"], "%")
         #st.write("IV Rank:", iv_info["iv_rank"], "%")
#-----------------------Add PARA----------------------------------------------
    # IV
            result = "Pass" if 0.10 <= iv_info["iv"] <= 0.35 else "Fail"
            iv_result = result    
            #add_param_row("IV", round(iv_info["iv"], 2), "0.10 - 0.35", result)

    # IV Rank
            result = "Pass" if 0.20 <= iv_info["iv_rank"] <= 0.70 else "Fail"
            iv_rank_result  = result    
            #add_param_row("IV Rank", round(iv_info["iv_rank"], 2), "0.20 - 0.70", result)
#--------------------------------------------------Getting New IV-----------& adding to para----------------------------
            #result = compute_option_iv_details(option, spot)
     
            #st.write(result)  
            option = get_live_option_details(kite, trending_symbol)
     
            #st.write(option)
     
     
            spot = option["strike"]
            #st.write("Spot",spot) 
            #spot = 25900.00  # live NIFTY spot
     
            result = compute_option_iv_details(option, spot)
            #st.write("IV new",result["iv"]) 
            new_iv_result= result["iv"]
            result = "Pass" if 0.10 <= new_iv_result <= 0.35 else "Fail" 
            add_param_row("IV ", round(new_iv_result, 2), "0.10 - 0.35", result) 
#-------------------------------------------------------------------------
            if(iv_info["iv"]=='None'):
             # Safely extract values
                  iv_value = iv_info.get("iv") or 0
                  iv_rank_value = iv_info.get("iv_rank") or 0
             
                  st.write("After None Current IV:", iv_value, "%")
                  st.write("After None IV Rank:", iv_rank_value, "%")
    
        

#--------------------------------VIX------------------------------------------------
         #vix_now =fetch_vix_from_fyers()
         
            vix_now = fetch_india_vix_kite(kite)
         #st.write("India VIX: kite", vix_now)
         #st.write("India VIX:", vix_now)
 #-----------------------Add PARA----------------------------------------------
    # VIX
            result = "Pass" if vix_now > 10 else "Fail"
            vix_result  = result     
            add_param_row("VIX", round(vix_now, 2), "> 10", result)

 #------------------------------------------------------------------------------   
    # Apply IV + VIX Filter
    # -------------------------
        #allowed, position_size = combined_filter(iv_info["iv"], iv_info["iv_rank"], vix_now)
    # Safely extract values
            iv_value = iv_info.get("iv") or 0
            iv_rank_value = iv_info.get("iv_rank") or 0
            allowed, position_size = combined_filter(iv_value, iv_rank_value, vix_now)
            #st.write("Allowed to Trade?", allowed)
            #st.write("Position Size:", position_size)
    #-----------------------------------------------------------------------------------------
    
    #---------------------------------tIME-----------------------------------------------
            import pytz
            
    # IST timezone
            ist = pytz.timezone("Asia/Kolkata")
            now_dt = datetime.now(ist)     # full datetime object
            now = now_dt.time()            # extract time only for comparisons

            tz = pytz.timezone("Asia/Kolkata")
            now = datetime.now(tz)
     #----------------------------------FUND-----------------------------------------------------
            #st.divider()

            funds = get_fund_status(kite)

            #st.subheader("💰 Zerodha Fund Status")
    
            if "error" in funds:
                st.error(funds["error"])
            else:
                  #st.write(f"**Net Balance:** ₹{funds['net']}")
                  #st.write(f"**Cash:** ₹{funds['cash']}")
                  #st.write(f"**Opening Balance:** ₹{funds['opening_balance']}")
                  #st.write(f"**Collateral:** ₹{funds['collateral']}")
                  #st.write(f"**Option Premium Used:** ₹{funds['option_premium']}")
                  #cash_balance = 73500
                  lots = get_lot_size(funds['cash'])
                  #st.write("Lot Size:", lots)
                  qty=65*lots
                  #st.divider()

   
    
    #------------------------------------PLACING ORDERS--------------------------------------------
             #st.write(f"Placing order for:", trending_symbol)
            if(position_size=='none'):
                  position_size=1;
        #st.write(f"Quantity: {qty}, LTP: {ltp}")
        #st.write(f"Quantity  order for:", qty)        
        #if st.button("🚀 PLACE BUY ORDER IN ZERODHA"):
        # Condition 1: Current time >= signal candle time
        # Trading window
            start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
            end_time   = now.replace(hour=14, minute=30, second=0, microsecond=0)
    #st.write("start_time", start_time)
    #st.write("end_time", end_time)
    #st.write("Now Time", now)
    #st.write("signal_time",signal_time)
    
    
    #-------------------------------------------------------------------------------

        # Convert to Python datetime (with timezone if needed)
            signal_time = pd.to_datetime(signal_time).to_pydatetime()
   
    # Optional: ensure same timezone as now
    #import pytz
            tz = pytz.timezone("Asia/Kolkata")
            signal_time = signal_time.replace(tzinfo=tz)
    #    st.write("signal_time",signal_time)
    #st.write("Now Time", now)
    #--------------------------------------------------------------------------------
     #-----------------------Add PARA----------------------------------------------
    # Define IST timezone
            ist = pytz.timezone("Asia/Kolkata")
    
    # Convert signal_time to IST
            signal_time_ist = signal_time.astimezone(ist)
            import datetime as dt

            start = dt.time(9, 30)
            end   = dt.time(14, 30)
    
            sig_t = signal_time_ist.time()
    
            result = "Pass" if start <= sig_t <= end else "Fail"
    
            add_param_row("Signal Time", str(signal_time_ist.time()),"09:30 - 14:30",result)
     #------------------------------------ADD PCR------------------------------------------ 
            pcr_value = get_nifty_pcr(kite)
            result = "Pass" if 0.80 <= pcr_value <= 1.30 else "Fail"
            pcr_result= result
            add_param_row("PCR", round(pcr_value, 2), "0.80 - 1.30", result)

#-------------------------------------lot ty------------------------------------------------
     # Default lot size
            qty = 1*65
     
     # Apply rule
            if iv_result == "Fail" or iv_rank_result == "Fail":
                   lot_qty = 2
            if iv_result == "Pass" and iv_rank_result == "Fail" and vix_result=="pass" and pcr_result=="pass":
                   lot_qty = 6    
            if vix_now < 10 :
                   lot_qty = 0 
                 
            add_param_row("LOT QTY", lot_qty, "0,1,2,4,6", "OK")
     #-----------------------------------------Display PARA-------------------------------------------
            if st.session_state.param_rows:
                  df = pd.DataFrame(st.session_state.param_rows)
                  st.table(df)
            else:
                  st.write("No parameters added yet.")
    #------------------------------------------------------------------------------------------------
#==============================================================================================================================

    with col6:
         days_to_exp = days_to_expiry(expiry)
         time_to_expiry = days_to_exp / 365 
         r=0.07
            #st.write("spot_price, strike, time_to_expiry, r, ltp",spot_price, strike, time_to_expiry, r, ltp) 
         #iv = implied_vol_call(spot_price, strike, time_to_expiry, r, ltp) 
         iv=new_iv_result
         st.subheader("Greeks Values")
         #greeks = option_greeks(S=spot_price,K=strike,T=time_to_expiry,r=r,sigma=iv,option_type=option_type)
         S=spot_price
         K=strike
         T=time_to_expiry
         r=r
         sigma=iv
         option_type=option_type
         
         #greeks= safe_option_greeks(S, K, T, r, sigma, option_type="CALL")
         expiry_dt = datetime.strptime(expiry, "%Y-%m-%d").replace(hour=15, minute=30)
         greeks= safe_option_greeks(S, K, expiry_dt, r, sigma, option_type="CALL")
         #if greeks:
              #st.subheader("Greeks Values")
          
              #col1, col2, col3, col4, col5 = st.columns(5)
              #col1.metric("Delta", round(greeks["Delta"], 3))
              #col2.metric("Gamma", round(greeks["Gamma"], 4))
              #col3.metric("Theta", round(greeks["Theta"], 2))
              #col4.metric("Vega", round(greeks["Vega"], 2))
              #col5.metric("IV %", round(greeks["IV"], 2))
         greeks_param_df = pd.DataFrame([
    {
        "Parameter": "Delta",
        "Value": greeks["Delta"],
        "Range": "0.30 – 0.85",
        "Result": evaluate(greeks["Delta"], 0.30, 0.85)
    },
    {
        "Parameter": "Gamma",
        "Value": greeks["Gamma"],
        "Range": "≥ 0.0005",
        "Result": evaluate(greeks["Gamma"], 0.0005, None)
    },
    {
        "Parameter": "Theta",
        "Value": greeks["Theta"],
        "Range": "≥ -80",
        "Result": evaluate(greeks["Theta"], -80, None)
    },
    {
        "Parameter": "Vega",
        "Value": greeks["Vega"],
        "Range": "≥ 3.0",
        "Result": evaluate(greeks["Vega"], 3.0, None)
    },
    {
        "Parameter": "IV %",
        "Value": greeks["IV%"],
        "Range": "10 – 35",
        "Result": evaluate(greeks["IV%"], 10, 35)
    }
])
 
         st.dataframe(
         greeks_param_df.style.applymap(
            lambda x: "color: green; font-weight: bold"
            if x == "Pass"
            else "color: red; font-weight: bold"
            if x == "Fail"
            else ""
         ),
         use_container_width=True,
         hide_index=True
     )
         #st.session_state.paper_trades.append(trade)
         


         #---------------------------------tIME-----------------------------------------------
         import pytz
            
    # IST timezone
         ist = pytz.timezone("Asia/Kolkata")
         now_dt = datetime.now(ist)     # full datetime object
         now = now_dt.time()            # extract time only for comparisons

         tz = pytz.timezone("Asia/Kolkata")
         now = datetime.now(tz)
     #----------------------------------FUND-----------------------------------------------------
            #st.divider()

         funds = get_fund_status(kite)

            #st.subheader("💰 Zerodha Fund Status")
    
         if "error" in funds:
                st.error(funds["error"])
         else:
                  #st.write(f"**Net Balance:** ₹{funds['net']}")
                  #st.write(f"**Cash:** ₹{funds['cash']}")
                  #st.write(f"**Opening Balance:** ₹{funds['opening_balance']}")
                  #st.write(f"**Collateral:** ₹{funds['collateral']}")
                  #st.write(f"**Option Premium Used:** ₹{funds['option_premium']}")
                  #cash_balance = 73500
                  lots = get_lot_size(funds['cash'])
                  #st.write("Lot Size:", lots)
                  qty=65*lots
                  #st.divider()

   
    
    #------------------------------------PLACING ORDERS--------------------------------------------
             #st.write(f"Placing order for:", trending_symbol)
         if(position_size=='none'):
                  position_size=1;
        #st.write(f"Quantity: {qty}, LTP: {ltp}")
        #st.write(f"Quantity  order for:", qty)        
        #if st.button("🚀 PLACE BUY ORDER IN ZERODHA"):
        # Condition 1: Current time >= signal candle time
        # Trading window
         start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
         end_time   = now.replace(hour=14, minute=30, second=0, microsecond=0)
    #st.wite("start_time", start_time)
    #st.write("end_time", end_time)
    #st.write("Now Time", now)
    #st.write("signal_time",signal_time)
    
    
    #-------------------------------------------------------------------------------

        # Convert to Python datetime (with timezone if needed)
         signal_time = pd.to_datetime(signal_time).to_pydatetime()
   
    # Optional: ensure same timezone as now
    #import pytz
         tz = pytz.timezone("Asia/Kolkata")
         signal_time = signal_time.replace(tzinfo=tz)
    #    st.write("signal_time",signal_time)
    #st.write("Now Time", now)
    #--------------------------------------------------------------------------------
     #-----------------------Add PARA----------------------------------------------
    # Define IST timezone
         ist = pytz.timezone("Asia/Kolkata")
    
    # Convert signal_time to IST
         signal_time_ist = signal_time.astimezone(ist)
         import datetime as dt

         start = dt.time(9, 30)
         end   = dt.time(14, 30)
    
         sig_t = signal_time_ist.time()
    
         result = "Pass" if start <= sig_t <= end else "Fail"
    
         add_param_row("Signal Time", str(signal_time_ist.time()),"09:30 - 14:30",result)
     #------------------------------------ADD PCR------------------------------------------ 
         pcr_value = get_nifty_pcr(kite)
         result = "Pass" if 0.80 <= pcr_value <= 1.30 else "Fail"
         pcr_result= result
         add_param_row("PCR", round(pcr_value, 2), "0.80 - 1.30", result)

#-------------------------------------lot ty------------------------------------------------
     # Default lot size
         qty = 1*65
            
                 
     
     # Apply rule
         if iv_result == "Fail" or iv_rank_result == "Fail":
                   lot_qty = 2
         if iv_result == "Pass" and iv_rank_result == "Fail" and vix_result=="pass" and pcr_result=="pass":
                   lot_qty = 6    
         if vix_now < 10 :
                   lot_qty = 1 
         if 10< vix_now < 15 :
                   lot_qty = 2
         if 15< vix_now < 20 :
                   lot_qty = 4
         if vix_now > 20 :
                   lot_qty = 1     
         add_param_row("LOT QTY", lot_qty, "0,1,2,4,6", "OK")
     #-----------------------------------------Display PARA-------------------------------------------
         if st.session_state.param_rows:
                  df = pd.DataFrame(st.session_state.param_rows)
                  #st.table(df)
         else:
                  st.write("No parameters added yet.")
    #------------------------------------------------------------------------------------------------
         qty=qty*lot_qty
            #qty=0
            #st.subheader("Session State Debug")
            #st.write(st.session_state)
            #st.subheader("Session State (Detailed)")
            #for key, value in st.session_state.items():
                #st.write(f"{key} :", value)

         #st.subheader("Trade State")
         keys_to_show = [
                   "trade_status",
                   "signal_time",
                   "signal_price",
                   "entry_time",
                   "exit_time",
                   "order_id",
                   "symbol"
               ]
               
         #for k in keys_to_show:
                   #if k in st.session_state:
                       #st.write(f"{k} :", st.session_state[k])

 
 
                # Check 1: Only run if current time is within trading window
         if is_valid_signal_time(entry_time):
                 st.warning("Signal time  match today's date .") 
                 if start_time <= now <= end_time:
                 
                 # Check 2: Signal time reached
                    #if now >= entry_time:
                    if abs((now - entry_time).total_seconds()) < 50:  
                         st.info("Execution window In (30 seconds).") 
                         st.write("entry_time-",entry_time)
                         st.write("Now Time-", now)
                      # Check 3: Order placed only once
                         if lot_qty>0: 
                              if has_open_position(kite):

                                  st.warning("⚠️ Open position exists. New trade not allowed.")
                                  
                              else:
                                  if not st.session_state.get("order_executed", False):
                                        try:
                                             # ❌ NO REAL ORDER
                                             # ✅ PAPER TRADE ENTRY
                                            log_paper_trade(
                                                 symbol=trending_symbol,
                                                 entry_price=ltp,
                                                 qty=qty,
                                                 signal_time=entry_time,
                                                 remark="Signal-based paper entry"
                                             )
                                
                                            st.session_state.order_executed = True   # Mark executed
                                            #st.session_state.order_executed = True
                                            #st.session_state.last_order_id = order_id
                                   
                                           # ✅ Mark trade active
                                            st.session_state.trade_active = True
                                            st.session_state.entry_price = ltp
                                            st.session_state.entry_time = datetime.now()
                                            st.session_state.qty = qty
                                            st.session_state.tradingsymbol = trending_symbol 
                                            #st.success(f"Order Placed Successfully! Order ID: {order_id}")
                                            #st.session_state["last_order_id"] = order_id
                                
                                        except Exception as e:
                                            st.error(f"Order Failed: {e}")
                                        
                         else:
                               st.info("Trade Not Allowed Qty=0.")  
                    else:
                         st.info("Order already executed for this signal.")
                 
                 else:
                       st.warning("Trading window closed. Orders allowed only between 9:30 AM and 2:30 PM.")
         else:
                   st.warning("Signal time does not match today's date or is outside trading hours. Order not placed.")     
              
    st.divider()

    # ===== ROW 4 =====
    col7, col8 = st.columns(2)
#==============================================================================================================================

    with col7:
        st.subheader("Paper Order Book")
        st.subheader("📒 Paper Trade Log")
        st.dataframe(
              st.session_state.paper_trades,
              use_container_width=True,
              hide_index=True
          )
        save_trade_log(st.session_state.paper_trades)

#------------------------------------ORDERS--------------------------------------------
       
         #===========================================OPEN POSITION--------------------------------------
        st.divider()

       

#==============================================================================================================================

    with col8:
         st.subheader("Monitoring Trade / Positions")
          
 
#--------------------------------------Manage Order--------------------------------------------------------
         

         # trade = st.session_state.paper_trades
         #st.write(st.session_state.paper_trades)
           
         if st.session_state.paper_trades:
              #st.subheader("📄 Paper Trade Monitor")
              st.subheader("📡 Live Paper Trade Monitor")  
              df_paper = pd.DataFrame(st.session_state.paper_trades)
              
          
              st.dataframe(monitor_and_exit_paper_trades(kite) , use_container_width=True)
         else:
              st.info("No active paper trades.")

         

       
 #--------------------------------------P&L=-----------------------------------------------------------        
       
                  
                 

       
  #========================================================================================================================== 
    
   
    
    
    
   
    

# ------------------------------------------------------------
# Backtest Strategies
# ------------------------------------------------------------

elif MENU == "Backtest1":
    st.title("Backtest Strategies")

    


       

 
########################################################################################################



# ------------------------------------------------------------
# Strategies
# ------------------------------------------------------------

elif MENU == "Strategies":
    st.title("Strategies Library")

    colA, colB = st.columns([2, 1])
    with colA:
        names = [s["name"] for s in st.session_state.strategies]
        st.session_state.selected_strategy = st.selectbox("Select strategy", names, index=0)
    with colB:
        st.caption("Filter")
        _min_win = st.slider("Min Win%", 0, 100, 50)

    for s in st.session_state.strategies:
        if s["metrics"]["Win%"] >= _min_win:
            strategy_card(s["name"], s["short"], s["metrics"])

    st.divider()

    st.subheader("Backtest Viewer")
    st.caption("Upload a CSV with columns: Datetime, Open, High, Low, Close, PnL (optional)")
    up = st.file_uploader("Upload backtest CSV", type=["csv"]) 
    if up:
        df = pd.read_csv(up)
        #####################################################################################################
       


        ######################################################################################################
        # Try parsing datetime
        for col in ["Datetime", "Date", "timestamp", "time"]:
            if col in df.columns:
                try:
                    df["Datetime"] = pd.to_datetime(df[col])
                    break
                except Exception:
                    pass
        st.dataframe(df.head(200), use_container_width=True)
        if {"Open","High","Low","Close","Datetime"}.issubset(df.columns):
            plot_candles(df, title=f"{st.session_state.selected_strategy} – Price")
        if "PnL" in df.columns:
            plot_equity_curve(df["PnL"], title=f"{st.session_state.selected_strategy} – Equity")
#--------------------------------------------------------------------------------------------------------



elif MENU == "Login Zerodha  API":
    from kiteconnect import KiteConnect
    st.title("Zerodha Broker Integration")

    if "kite" not in st.session_state:
        st.session_state.kite = None

    st.text_input("API Key", key="z_key")
    st.text_input("API Secret", type="password", key="z_secret")

    # Step 1: Initialize Kite
    if st.button("Generate Login URL"):
        try:
            kite = KiteConnect(api_key=st.session_state.z_key)
            login_url = kite.login_url()

            st.session_state.kite = kite
            st.session_state.api_status["Zerodha"] = False

            st.success("Login URL generated. Open it, login & paste Request Token.")
            #st.write("👉 Login URL:")
            #st.code(login_url)
            st.markdown(f"[🔗 Open Zerodha Login]({login_url})", unsafe_allow_html=True)
        except Exception as e:
            st.error(e)

    request_token = st.text_input("Enter Request Token")

    # Step 2: Generate Access Token
    if st.button("Connect Zerodha"):
        try:
            kite = st.session_state.kite

            data = kite.generate_session(
                request_token=request_token,
                api_secret=st.session_state.z_secret,
            )

            kite.set_access_token(data["access_token"])

            # Save for dashboard
            st.session_state.kite = kite
            st.session_state.api_status["Zerodha"] = True
            st.session_state.connected_broker = "Zerodha"

            st.success("🎉 Zerodha Connected Successfully!")
            #st.info("Downloading latest instruments.csv…")


        except Exception as e:
            st.error(f"Login failed: {e}")

    # Status Panel
    st.subheader("Connection Status")
    for name, ok in st.session_state.api_status.items():
        badge = f"<span class='badge {'success' if ok else 'danger'}'>{'Connected' if ok else 'Not Connected'}</span>"
        st.markdown(f"**{name}**: {badge}", unsafe_allow_html=True)



       

# ------------------------------------------------------------
# Zerodha Broker API Broker API
# ------------------------------------------------------------
elif MENU == "Zerodha1 Broker API":
    st.title("Broker Integrations")
    st.write("Connect your broker to enable paper/live trading. This demo stores states locally. Replace with secure key vault in production.")

    brokers = ["Zerodha", "Fyers", "AliceBlue"]
    bcol1, bcol2 = st.columns(2)
    with bcol1:
        sel = st.selectbox("Broker", brokers, index=0)
        if sel == "Zerodha":
            st.text_input("API Key", key="z_key")
            st.text_input("API Secret", type="password", key="z_secret")
            with st.container():
                st.markdown("<div class='button-teal'>", unsafe_allow_html=True)
                if st.button("Connect Zerodha"):
                    st.session_state.api_status["Zerodha"] = True
                    st.session_state.connected_broker = "Zerodha"
                    st.success("Zerodha connected (demo)")
                st.markdown("</div>", unsafe_allow_html=True)
        elif sel == "Fyers":
            st.text_input("Client ID", key="f_id")
            st.text_input("Secret Key", type="password", key="f_secret")
            st.markdown("<div class='button-amber'>", unsafe_allow_html=True)
            if st.button("Connect Fyers"):
                st.session_state.api_status["Fyers"] = True
                st.session_state.connected_broker = "Fyers"
                st.success("Fyers connected (demo)")
            st.markdown("</div>", unsafe_allow_html=True)
        elif sel == "AliceBlue":
            st.text_input("User ID", key="a_id")
            st.text_input("API Key", type="password", key="a_key")
            st.markdown("<div class='button-purple'>", unsafe_allow_html=True)
            if st.button("Connect AliceBlue"):
                st.session_state.api_status["AliceBlue"] = True
                st.session_state.connected_broker = "AliceBlue"
                st.success("AliceBlue connected (demo)")
            st.markdown("</div>", unsafe_allow_html=True)

    with bcol2:
        st.subheader("Connection Status")
        for name, ok in st.session_state.api_status.items():
            badge = f"<span class='badge {'success' if ok else 'danger'}'>{'Connected' if ok else 'Not Connected'}</span>"
            st.markdown(f"**{name}**: {badge}", unsafe_allow_html=True)
        st.caption("Replace demo handlers with actual OAuth/API calls. Store tokens securely.")

# ------------------------------------------------------------
# Groww Broker API
# ------------------------------------------------------------
elif MENU == "Groww Broker API":
    import os
    import json
    import streamlit as st
    from groww import GrowwHttpClient

    st.title("Groww Broker API")
    st.write("Connect your Groww account for live/paper trading. This is a demo integration.")

    gcol1, gcol2 = st.columns(2)

    # Init session state
    if "groww_status" not in st.session_state:
        st.session_state.groww_status = False
        st.session_state.groww_client = None

    with gcol1:
        st.subheader("Groww Login")
        st.text_input("Groww Client ID", key="g_client_id")
        st.text_input("Groww Password", type="password", key="g_password")
        st.text_input("Groww PIN", type="password", key="g_pin")

        if st.button("Connect Groww"):
            try:
                client = GrowwHttpClient()

                login_res = client.login(
                    st.session_state.g_client_id,
                    st.session_state.g_password,
                    st.session_state.g_pin
                )

                if login_res.get("success"):
                    st.session_state.groww_status = True
                    st.session_state.groww_client = client
                    st.success("Groww connected successfully!")
                else:
                    st.error("Groww login failed. Check credentials.")

            except Exception as e:
                st.error(f"Error: {e}")

    with gcol2:
        st.subheader("Connection Status")
        status = st.session_state.groww_status
        badge = (
            "<span class='badge success'>Connected</span>"
            if status else
            "<span class='badge danger'>Not Connected</span>"
        )
        st.markdown(f"**Groww**: {badge}", unsafe_allow_html=True)

        st.caption("Login via Groww API (demo). Store tokens securely for production.")


# ------------------------------------------------------------
# Dashboard (Main Trading Panel)
# ------------------------------------------------------------
elif MENU == "Dashboard":
    st.title("Trading Dashboard")

    # Top colorful KPIs
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi_card("Capital", f"₹{st.session_state.capital:,.0f}", "var(--blue)")
    with k2:
        kpi_card("Risk / Trade", f"{st.session_state.risk_per_trade_pct:.1f}%", "var(--amber)")
    with k3:
        kpi_card("Max Trades", str(st.session_state.max_trades), "var(--purple)")
    with k4:
        broker = st.session_state.connected_broker or "—"
        kpi_card("Broker", broker, "var(--green)" if broker != "—" else "var(--red)")

    st.divider()

    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("Strategy Control")
        st.session_state.live_strategy = st.selectbox(
            "Select Strategy", [s["name"] for s in st.session_state.strategies], index=0
        )
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            st.session_state.capital = st.number_input("Capital (₹)", min_value=1000.0, step=1000.0, value=float(st.session_state.capital))
        with cc2:
            st.session_state.risk_per_trade_pct = st.number_input("Risk per Trade (%)", min_value=0.1, max_value=10.0, step=0.1, value=float(st.session_state.risk_per_trade_pct))
        with cc3:
            st.session_state.max_trades = st.number_input("Max Trades", min_value=1, max_value=20, step=1, value=int(st.session_state.max_trades))

        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("▶ Start (Paper)"):
                st.session_state.live_running = True
                st.success("Paper trading started (demo)")
        with b2:
            if st.button("⏸ Stop"):
                st.session_state.live_running = False
                st.warning("Stopped.")
        with b3:
            if st.button("⚙ Send Test Alert"):
                add_trade_log("NIFTY", "BUY", 50, 250.5, 0.0)
                st.info("Test alert → trade log added.")

        
        ###################################################################################
        st.subheader("Live NIFTY 50 Market Data")

        # Predefined NIFTY50 stock list (you can fetch dynamically from NSE if needed)
        nifty50_symbols = ["^NSEI","^NSEBANK" ]
        
        # Fetch data
        data = yf.download(nifty50_symbols, period="1d", interval="1m")["Close"].iloc[-1]
        
        # Convert to DataFrame
        df = pd.DataFrame(data).reset_index()
        df.columns = ["Symbol", "LTP"]
        
        # Calculate % Change from previous close
        prev_close = yf.download(nifty50_symbols, period="2d", interval="1d")["Close"].iloc[-2]
        df["Change%"] = ((df["LTP"] - prev_close.values) / prev_close.values) * 100
        
        # Display in Streamlit
        #st.dataframe(df.style.format({"LTP": "{:.2f}", "Change%": "{:.2f}"}), use_container_width=True)

            # Function to apply color
        def color_change(val):
            if val > 0:
                return "color: green;"
            elif val < 0:
                return "color: red;"
            else:
                return "color: black;"

                # Custom color function for Styler
        def color_positive_negative(val):
            color = 'green' if val > 0 else 'red'
            return f'color: {color}; font-weight: bold;'
        
        # Apply colors to all columns
        styled_df = df.style.format({"LTP": "{:.2f}", "Change%": "{:.2f}"}).applymap(color_positive_negative, subset=["LTP", "Change%"]).applymap(
            lambda x: 'color: black; font-weight: bold;', subset=["Symbol"]
        )
        
        # Apply style
        #styled_df = df.style.format({"LTP": "{:.2f}", "Change%": "{:.2f}"}).applymap(color_change, subset=["Change%"])
        
        # Display in Streamlit
        st.dataframe(styled_df, use_container_width=True)
        #######################################################################################

    

    with right:     
        #st.subheader("NIFTY 15-Minute(Today + Previous Day)")
        # Fetch NIFTY 50 index data
# Fetch NIFTY 50 index data
        # Fetch NIFTY 50 index data
        ticker = "^NSEI"  # NIFTY Index symbol for Yahoo Finance
        end = datetime.now()
        start = end - timedelta(days=2)
        
        # Download data
        df = yf.download(ticker, start=start, end=end, interval="15m")
        
        # Ensure data is available
        if df.empty:
            st.error("⚠️ No 15-min data fetched from Yahoo Finance. Market may be closed or ticker invalid.")
        else:
            # If multi-index, flatten it
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = ['_'.join(col).strip() for col in df.columns.values]
            # Reset index
            df = df.reset_index()
            # Convert to IST
           # Ensure Datetime is in IST
            if df['Datetime'].dt.tz is None:  
                # naive → localize to UTC first
                df['Datetime'] = df['Datetime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
            else:
                # already tz-aware → just convert
                df['Datetime'] = df['Datetime'].dt.tz_convert('Asia/Kolkata')

            df = df.reset_index()

            # Filter only market hours (09:15 - 15:30)
            market_open = pd.to_datetime("09:15:00").time()
            market_close = pd.to_datetime("15:30:00").time()
            df = df[df['Datetime'].dt.time.between(market_open, market_close)]
            #st.write(df)
            # Remove timezone if exists
            #df['Datetime'] = df['Datetime'].dt.tz_localize(None)
            #st.write(df)
            # Extract date
            df['Date'] = df['Datetime'].dt.date
            unique_days = sorted(df['Date'].unique())
        
            # Filter last 2 days
            if len(unique_days) >= 2:
                filtered_df = df[df['Date'].isin(unique_days[-2:])]
            else:
                filtered_df = df
        
            # Plot candlestick chart
            def plot_candles(df, title="Candlestick Chart"):
                fig = go.Figure(data=[go.Candlestick(
                    x=df['Datetime'],
                    open=df['Open_^NSEI'],
                    high=df['High_^NSEI'],
                    low=df['Low_^NSEI'],
                    close=df['Close_^NSEI'],
                    name='candlestick'
                )])
                # Hide non-trading gaps on x-axis
                fig.update_xaxes(rangebreaks=[
                    dict(bounds=["sat", "mon"]),  # hide weekends
                    dict(bounds=[16, 9], pattern="hour"),  # hide non-market hours (after 15:30 until 09:15)
                ])
                # --- Find 3 PM candles ---
               # --- Find 3 PM candles ---
                three_pm = df[(df['Datetime'].dt.hour == 15) & (df['Datetime'].dt.minute == 0)]
                
                for _, row in three_pm.iterrows():
                    start_time = row['Datetime']
                    end_time   = start_time + timedelta(minutes=15)
                
                    open_price  = row['Open_^NSEI']
                    close_price = row['Close_^NSEI']
                
                    # Line for Open
                    fig.add_shape(
                        type="line",
                        x0=start_time, x1=end_time,
                        y0=open_price, y1=open_price,
                        line=dict(color="blue", width=1, dash="dot"),
                    )
                
                    # Line for Close
                    fig.add_shape(
                        type="line",
                        x0=start_time, x1=end_time,
                        y0=close_price, y1=close_price,
                        line=dict(color="red", width=1, dash="dot"),
                    )
                fig.update_layout(title=title, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
        
            plot_candles(filtered_df, title="NIFTY 15-Min Candlestick (Last 2 Days)")

    st.divider()
    def fetch_zerodha_data():
        kite = st.session_state.kite
    
        try:
            funds = kite.margins()["equity"]["available"]["cash"]
            holdings = kite.holdings()
            positions = kite.positions()["net"]
            orders = kite.orders()
    
            return funds, holdings, positions, orders
    
        except Exception as e:
            st.error(f"Error fetching Zerodha data: {e}")
            return 0, [], [], []

    
    
    if st.session_state.api_status.get("Zerodha"):

        funds, holdings, positions, orders = fetch_zerodha_data()
    
        st.subheader("Zerodha Account Overview")
    
        colA, colB = st.columns(2)
    
        with colA:
            st.metric("Total Funds", f"₹{funds:,.0f}")
    
        with colB:
            st.metric("Open Positions", len(positions))
    
        st.markdown("### Holdings")
        st.dataframe(holdings, use_container_width=True, height=200)
    
        st.markdown("### Positions")
        st.dataframe(positions, use_container_width=True, height=200)
    
        st.markdown("### Orders")
        st.dataframe(orders, use_container_width=True, height=200)


    

#############################################################################################################################st.subheader("Trade Logs")
    #st.dataframe(st.session_state.trade_logs, use_container_width=True)
    













############################################################################################################################

# ------------------------------------------------------------
# Products / Pricing
# ------------------------------------------------------------
elif MENU == "Products":
    st.title("Products & Pricing")

    cols = st.columns(3)
    for i, plan in enumerate(st.session_state.pricing):
        with cols[i]:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"### {plan['name']}")
            st.markdown(f"#### ₹{plan['price']}/month")
            for feat in plan['features']:
                st.write(f"• {feat}")
            st.button(f"Subscribe {plan['name']}")
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("What you get")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.write("Automation")
    with c2: st.write("Backtesting")
    with c3: st.write("Paper Trading")
    with c4: st.write("Live Alerts")

# ------------------------------------------------------------
# Support
# ------------------------------------------------------------
elif MENU == "Support":
    st.title("Support & Resources")

    st.subheader("Documentation")
    st.write("• Getting Started  • Strategy Guide  • API Setup  • FAQ")

    st.subheader("FAQ")
    for q, a in st.session_state.faq:
        with st.expander(q):
            st.write(a)

    st.subheader("Contact Us")
    with st.form("contact_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        message = st.text_area("Message")
        submitted = st.form_submit_button("Send")
        if submitted:
            st.success("Thanks! We'll get back to you shortly (demo).")




    #######################################################################################################
elif MENU =="Live Trade":
    #st.write("Live Trade")
    st.session_state.param_rows = []
    if "signal_log" not in st.session_state:
         st.session_state.signal_log = []
    if "last_signal" not in st.session_state:
         st.session_state.last_signal = None     
    #today = latest_time.date()
    st.title("🔴 LIVE TRADE ")
    #st.title("🔴 Live Nifty 15-Minute Chart + Signal Engine")
    if not is_kite_connected(kite):
        st.warning("Please login first to access LIVE trade.")
        st.stop()     # Stop page execution safely

    #st.success("You are logged in.")
     
    st.session_state.param_rows = []
    from streamlit_autorefresh import st_autorefresh
    import time             # Python's time module
    from datetime import time  # datetime.time (conflict!)
    # Initialize Kite in session_state
    if "kite" not in st.session_state:
        st.session_state.kite = None
    else:
        kite = st.session_state.get("kite")
    # --- SESSION STATE INIT ---
    if "order_executed" not in st.session_state:
        st.session_state.order_executed = False
        
    
    if "signal_time" not in st.session_state:
        st.session_state.signal_time = None
    # Add after data processing:
    def is_kite_connected(kite):
        try:
            kite.profile()
            return True
        except:
            return False

    

    #st.title("Algo Trading Dashboard")

    # ===== ROW 1 =====
    col1, col2 = st.columns([1, 3])

    with col1:
        funds = get_fund_status(kite)
        #st.write(funds) 
        cash = (funds['cash'])
        cash = (funds['net'])  
        result = "Fail" if 75000 <= cash <= 25000 else "Pass"
        add_param_row("CASH", cash, "25K - 100K", result)
        st.session_state.capital=cash  
        st.subheader("Connection Status") 
        if is_kite_connected(kite):
             st.success("Kite connection active")
        else:
             st.error("Kite session expired. Please login again.") 
        st.subheader("WebSocket Status")
        #st.success("Kite Connected")
        st.info("WebSocket: Running")
        st.subheader("FUND Status")
        st.metric("Funds ₹.", cash)

    with col2:
         st.subheader("NIFTY 50 / 15 Min Chart")
        #---------------------------------------------------------------------
         ist = pytz.timezone("Asia/Kolkata")
         now = datetime.now(ist).time()
         
         # Market hours condition
         start = time(9, 15)   # 9:30 AM
         end = time(15, 25)    # 3:25 PM
         
         # Refresh only between 9:30–3:25
         if start <= now <= end:
             #st_autorefresh(interval=60000, key="refresh")  # 1 minute refresh
             st_autorefresh(interval=60000, key="refresh_live3")
         else:
             st.info("Auto-refresh is paused — Outside market hours (9:30 AM to 3:25 PM).")
     
         #st.title("Nifty 15-min Chart")
         
         # Select date input (default today)
         selected_date = st.date_input("Select date", value=datetime.today())
         
         # Calculate date range to download (7 days before selected_date to day after selected_date)
         start_date = selected_date - timedelta(days=7)
         end_date = selected_date + timedelta(days=1)
         
         # Download data for ^NSEI from start_date to end_date
         df = yf.download("^NSEI", start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="15m")
         
         if df.empty:
             st.warning("No data downloaded for the selected range.")
             st.stop()
         df.reset_index(inplace=True)
         
         if 'Datetime_' in df.columns:
             df.rename(columns={'Datetime_': 'Datetime'}, inplace=True)
         elif 'Date' in df.columns:
             df.rename(columns={'Date': 'Datetime'}, inplace=True)
         # Add any other detected name if needed
         
         
         #st.write(df.columns)
         #st.write(df.head(10))
         # Flatten columns if MultiIndex
         if isinstance(df.columns, pd.MultiIndex):
             df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
         
         # Rename datetime column if needed
         if 'Datetime' not in df.columns and 'datetime' in df.columns:
             df.rename(columns={'datetime': 'Datetime'}, inplace=True)
         #st.write(df.columns)
         #st.write(df.columns)
         # Convert to datetime & timezone aware
         #df['Datetime'] = pd.to_datetime(df['Datetime'])
         if df['Datetime_'].dt.tz is None:
             df['Datetime'] = df['Datetime_'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
         else:
             df['Datetime'] = df['Datetime_'].dt.tz_convert('Asia/Kolkata')
         
         #st.write(df.columns)
         #st.write(df.head(10))
         
         # Filter for last two trading days to plot
         unique_days = df['Datetime'].dt.date.unique()
         if len(unique_days) < 2:
             st.warning("Not enough data for two trading days")
         else:
             last_day = unique_days[-2]
             today = unique_days[-1]
         
             df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
         
             # Get last day 3PM candle open and close
             candle_3pm = df_plot[(df_plot['Datetime'].dt.date == last_day) &
                                  (df_plot['Datetime'].dt.hour == 15) &
                                  (df_plot['Datetime'].dt.minute == 0)]
         
             if not candle_3pm.empty:
                 open_3pm = candle_3pm.iloc[0]['Open_^NSEI']
                 close_3pm = candle_3pm.iloc[0]['Close_^NSEI']
             else:
                 open_3pm = None
                 close_3pm = None
                 st.warning("No 3:00 PM candle found for last trading day.")
             #-----------------------------Marking 9.15 Candle---------------------------------
             # Get today's 9:15 AM candle
             candle_915 = df_plot[(df_plot['Datetime'].dt.date == today) &
                               (df_plot['Datetime'].dt.hour == 9) &
                               (df_plot['Datetime'].dt.minute == 15)]
          
             if not candle_915.empty:
                   o_915 = candle_915.iloc[0]['Open_^NSEI']
                   h_915 = candle_915.iloc[0]['High_^NSEI']
                   l_915 = candle_915.iloc[0]['Low_^NSEI']
                   c_915 = candle_915.iloc[0]['Close_^NSEI']
                   t_915 = candle_915.iloc[0]['Datetime']
             else:
                   o_915 = h_915 = l_915 = c_915 = t_915 = None
                   st.warning("No 9:15 AM candle found for today.")    
              
              #---------------------------------------------------------------------------------
         
              
         
             # Plot candlestick chart
             fig = go.Figure(data=[go.Candlestick(
                 x=df_plot['Datetime'],
                 open=df_plot['Open_^NSEI'],
                 high=df_plot['High_^NSEI'],
                 low=df_plot['Low_^NSEI'],
                 close=df_plot['Close_^NSEI']
             )])
             if t_915 is not None:
                   fig.add_vrect(
                       x0=t_915,
                       x1=t_915 + pd.Timedelta(minutes=15),
                       fillcolor="orange",
                       opacity=0.25,
                       layer="below",
                       line_width=0,
                       annotation_text="9:15 Candle",
                       annotation_position="top left"
                   )
             
             
     
             if o_915 is not None and c_915 is not None:
                   fig.add_hline(y=o_915, line_dash="solid", line_color="green",
                                 annotation_text="9:15 Open")
                   fig.add_hline(y=c_915, line_dash="solid", line_color="orange",
                                 annotation_text="9:15 Close") 
             if open_3pm and close_3pm:
                 fig.add_hline(y=open_3pm, line_dash="dot", line_color="blue", annotation_text="3PM Open")
                 fig.add_hline(y=close_3pm, line_dash="dot", line_color="red", annotation_text="3PM Close")
         
         
         
         
             # Draw horizontal lines as line segments only between 3PM last day and 3PM next day
         
             
             fig.update_layout(title="Nifty 15-min candles - Last Day & Today", xaxis_rangeslider_visible=False)
             fig.update_layout(
             xaxis=dict(
                 rangebreaks=[
                     # Hide weekends (Saturday and Sunday)
                     dict(bounds=["sat", "mon"]),
                     # Hide hours outside of trading hours (NSE trading hours 9:15 to 15:30)
                     dict(bounds=[15.5, 9.25], pattern="hour"),
                 ]
             )
         )
         
         
             st.plotly_chart(fig, use_container_width=True)  
        
    st.divider()
#==============================================================================================================================
    # ===== ROW 2 =====
    col3, col4 = st.columns(2)

    with col3:
        import json 
        st.subheader("Signal Log")
        df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
        #signal = trading_signal_all_conditions_new(df_plot)
        #signal = trading_signal_all_conditions_final(df_plot) 
        signal = trading_multi2_signal_all_conditions_5min(df_plot)  
        #st.write("DEBUG signal:", signal)
        #st.write("Type:", type(signal))
        df_sig1 = pd.DataFrame(signal)

        if signal and isinstance(signal, list):
              last_signal = signal[-1]
              st.success(f"✅ SIGNAL GENERATED: {last_signal['message']}")
 
        if signal is None:
            st.warning("⚠ No signal yet (conditions not met).")
        else:
            #st.success(f"✅ SIGNAL GENERATED: {signal['message']}")
            last_signal = signal[-1]  
            #df_sig1 = pd.DataFrame([signal])
            df_sig1 = pd.DataFrame(signal) 
            signal_time = df_plot["Datetime"].iloc[-1]   # last candle timestamp
            last_signal["signal_time"] = signal_time
            signal_time1=last_signal["signal_time"] 
                # Display as table
            #st.table(df_sig1) 
            #st.write(df_sig1) 
            st.subheader("📊 Signal Log")
            #st.write(df_sig1) 
            st.dataframe(df_sig1, use_container_width=True, hide_index=True) 
            #=========================JSON TO TABLE========================
            lot_qty=0

            #===============================Cache==============================================================
            #signal_id = f"{signal_time}_{strike}_{option_type}"

            
            
                           
#==============================================================================================================================
   
    with col4:
            st.subheader("Option Log")
            last_signal = st.session_state.last_signal

            if last_signal is None:
                  st.info("Waiting for first signal...")
                  st.stop()
          
            entry_time = last_signal["entry_time"]
            signal_time = entry_time.strftime("%H:%M:%S")  
            #entry_time = last_signal['entry_time']
            #st.write("entry_time",entry_time) 
            #st.write("Signal Time only:", entry_time.strftime("%H:%M:%S"))  # HH:MM:SS
            signal_time=entry_time.strftime("%H:%M:%S")
            #st.write("Signal Time only:-", signal_time)  # HH:MM:SS
            #            st.write(signal)
     #--------------------------------------------------------------------------------

            def generate_signals_stepwise(df):
                 all_signals = []
                 
                 # We run strategy for each candle progressively
                 for i in range(40, len(df)):   # start after enough candles
                     sub_df = df.iloc[:i].copy()
                     sig = trading_signal_all_conditions(sub_df)
                     if sig is not None:
                         all_signals.append((sub_df.iloc[-1]["Datetime"], sig))
             
                 return all_signals
     #-------------------------------------Total signals-------------------------------------------
     
            step_signals = generate_signals_stepwise(df_plot)
            if step_signals:
                     #st.info(f"Total signals detected so far: {len(step_signals)}")
                 
                     latest_time, latest_sig = step_signals[-1]
                     
                     st.success(f"🟢 Latest Candle Signal ({latest_time}):")
                     #st.write(latest_sig)
                     # Convert to DataFrame
                     df_sig = pd.DataFrame([latest_sig])
                     
                     # Display as table
                     #st.table(df_sig)
            else:
                     st.warning("No signal triggered in any candle yet.")
        
     
     #-----------------------------------Nearest ITM Option ---------------------------------------------
     
            if signal is not None:
                 #st.write(last_signal)
                 #signal_time = df["Datetime"].iloc[-1].time()   # last candle time
                 option_type = last_signal["option_type"]     # CALL / PUT
                 #st.write("Option type ",option_type)
                 spot = last_signal["buy_price"]
                 #st.write("Option spot ",spot)
                 try:
                     nearest_itm = find_nearest_itm_option(kite, spot, option_type)
                     
                     st.success("Nearest ITM Option Found")
                     #                st.write(nearest_itm)
                     nearest_itm1 = pd.DataFrame([nearest_itm])
                     
                     # Display as table
                     #display_df = nearest_itm1[["tradingsymbol", "option_type", "expiry", "ltp"]].to_frame().T
                    
                     display_df = nearest_itm1[[
                             "tradingsymbol",
                             "option_type",
                             "expiry",
                             "ltp"
                         ]]
                    
                     st.table(display_df)
                     #st.table(display_df) 
                     #st.table(display_df) 
                     #st.table(nearest_itm1)
                     trending_symbol=nearest_itm['tradingsymbol']
                     #st.write("tradingsymbol-",trending_symbol)
                  #====================================================FLAG SIGNAL================================
                     st.session_state.trade_status = "SIGNAL"
                     st.session_state.signal_time = signal_time
                     st.session_state.signal_price = nearest_itm['ltp']   # LTP at signal candle
                     st.session_state.symbol = trending_symbol 
     
                  #==================================================================================================
             
                 except Exception as e:
                     st.error(f"Failed to fetch option: {e}")


    st.divider()
#==============================================================================================================================

    # ===== ROW 3 =====
    col5, col6 = st.columns(2)

    with col5:
            st.subheader("Parameter Values")
            option_dict = get_live_option_details(kite, trending_symbol)
            #spot_price=26046.00 
            if not option_dict:
                   st.warning("Live option data unavailable. Cannot proceed with trade logic.")
                   st.stop()  
            spot_price=option_dict.get("strike") 
            
            ltp = option_dict.get("ltp")
            strike = option_dict.get("strike")
            expiry = option_dict.get("expiry")
            st.write("expiry=",expiry)
            is_call = option_dict.get("option_type") == "CALL"
          #------------------------------------------PAPER TRADE-------------------------------------------------
            if signal is not None:

              signal_time = last_signal["signal_time"]
          
              # 🔒 ENTRY LOCK — THIS PREVENTS RE-ENTRY ON REFRESH
              if st.session_state.last_executed_signal_time == signal_time:
                  pass  # already traded this signal
                  #st.write("st.session_state.last_executed_signal_time=",st.session_state.last_executed_signal_time)
                  #st.write("System generated last_executed Signal time=",signal_time)  
              else:
                  option_type = last_signal["option_type"]
                  spot = last_signal["buy_price"]
          
                  nearest_itm = find_nearest_itm_option(kite, spot, option_type)
                  trending_symbol = nearest_itm["tradingsymbol"]
                  option_symbol = f"NFO:{trending_symbol}"
          
                  entry_price = kite.ltp(option_symbol)[option_symbol]["last_price"]
          
                  
                  trade = {
                        "signal_time": signal_time,
                        "entry_time": pd.Timestamp.now(),
                        "symbol": trending_symbol,
                        "option_type": option_type,
                        "entry_price": entry_price,
                        "quantity": 65,
                        "remaining_qty": 65,
                        "highest_price": entry_price,
                        "partial_exit_done": False,
                        "final_exit_done": False,
                        "status": "OPEN"
                    }
          
                  st.session_state.paper_trades.append(trade)
          
                  # 🔐 LOCK THE SIGNAL
                  st.session_state.last_executed_signal_time = signal_time
                  st.session_state.last_option_entry_price = entry_price  
          
                  #st.success(f"Paper trade entered @ {entry_price}")

            #monitor_paper_trades(kite)
            #for trade in st.session_state.paper_trades:
              #normalize_trade(trade)
              #manage_exit_papertrade(kite, trade)

            #st.write("Moniter")
             

 
   
          #---------------------------------------PAPER TRADE----------------------------------------------------   
              # Compute time to expiry (in years)
            days_to_exp = days_to_expiry(expiry)
            time_to_expiry = days_to_exp / 365 
            r=0.07
            r= 0.065  
            #st.write("spot_price, strike, time_to_expiry, r, ltp",spot_price, strike, time_to_expiry, r, ltp) 
            iv = implied_vol_call(spot_price, strike, time_to_expiry, r, ltp) 
            #st.write("IV  FOr (Option):CE")
            #st.write("IV (decimal):", iv)
            #st.write("IV (%):", iv * 100)    
            result = "Pass" if (iv is not None and 0.10 <= iv <= 0.35) else "Fail"
 
            #result = "Pass" if 0.10 <= iv <= 0.35 else "Fail"
            iv_result = result    
            #add_param_row("IV", round(iv, 2), "0.10 - 0.35", result)
             

#-----------------------------------IV Compute---------------------------------------------

        #spot_price = get_ltp(kite, "NSE:NIFTY 50")["ltp"]
        
         #iv_percent = compute_option_iv(nearest_itm, spot)
        
         #st.write("IV:", iv_percent)    
         
         #get_live_iv_nifty_option(kite, option_token: int, index_symbol="NSE:NIFTY 50"):        
            #st.write(nearest_itm)  

#----------------------------------IV----------------------------------------------

    
        
            iv_info = get_iv_rank0(kite, nearest_itm, lookback_days=250)
       
            #st.write("New Way Iv ",iv)  
            # Fix missing values
            if iv_info["iv"] is None:
                 iv_info["iv"] = 0
     
            if iv_info["iv_rank"] is None:
                iv_info["iv_rank"] = 0

         ##st.write("Current IV:", iv_info["iv"], "%")
         #st.write("IV Rank:", iv_info["iv_rank"], "%")
#-----------------------Add PARA----------------------------------------------
    # IV
            result = "Pass" if 0.10 <= iv_info["iv"] <= 0.35 else "Fail"
            iv_result = result    
            #add_param_row("IV", round(iv_info["iv"], 2), "0.10 - 0.35", result)

    # IV Rank
            result = "Pass" if 0.20 <= iv_info["iv_rank"] <= 0.70 else "Fail"
            iv_rank_result  = result    
            #add_param_row("IV Rank", round(iv_info["iv_rank"], 2), "0.20 - 0.70", result)
#--------------------------------------------------Getting New IV-----------& adding to para----------------------------
            #result = compute_option_iv_details(option, spot)
     
            #st.write(result)  
            option = get_live_option_details(kite, trending_symbol)
     
            #st.write(option)
     
     
            spot = option["strike"]
            #st.write("Spot",spot) 
            #spot = 25900.00  # live NIFTY spot
     
            result = compute_option_iv_details(option, spot)
            #st.write("IV new",result["iv"]) 
            new_iv_result= result["iv"]
            result = "Pass" if 0.10 <= new_iv_result <= 0.35 else "Fail" 
            add_param_row("IV ", round(new_iv_result, 2), "0.10 - 0.35", result) 
#-------------------------------------------------------------------------
            if(iv_info["iv"]=='None'):
             # Safely extract values
                  iv_value = iv_info.get("iv") or 0
                  iv_rank_value = iv_info.get("iv_rank") or 0
             
                  st.write("After None Current IV:", iv_value, "%")
                  st.write("After None IV Rank:", iv_rank_value, "%")
    
        

#--------------------------------VIX------------------------------------------------
         #vix_now =fetch_vix_from_fyers()
         
            vix_now = fetch_india_vix_kite(kite)
         #st.write("India VIX: kite", vix_now)
         #st.write("India VIX:", vix_now)
 #-----------------------Add PARA----------------------------------------------
    # VIX
            result = "Pass" if vix_now > 10 else "Fail"
            vix_result  = result     
            add_param_row("VIX", round(vix_now, 2), "> 10", result)

 #------------------------------------------------------------------------------   
    # Apply IV + VIX Filter
    # -------------------------
        #allowed, position_size = combined_filter(iv_info["iv"], iv_info["iv_rank"], vix_now)
    # Safely extract values
            iv_value = iv_info.get("iv") or 0
            iv_rank_value = iv_info.get("iv_rank") or 0
            allowed, position_size = combined_filter(iv_value, iv_rank_value, vix_now)
            #st.write("Allowed to Trade?", allowed)
            #st.write("Position Size:", position_size)
    #-----------------------------------------------------------------------------------------
    
    #---------------------------------tIME-----------------------------------------------
            import pytz
            
    # IST timezone
            ist = pytz.timezone("Asia/Kolkata")
            now_dt = datetime.now(ist)     # full datetime object
            now = now_dt.time()            # extract time only for comparisons

            tz = pytz.timezone("Asia/Kolkata")
            now = datetime.now(tz)
     #----------------------------------FUND-----------------------------------------------------
            #st.divider()

            funds = get_fund_status(kite)

            #st.subheader("💰 Zerodha Fund Status")
    
            if "error" in funds:
                st.error(funds["error"])
            else:
                  #st.write(f"**Net Balance:** ₹{funds['net']}")
                  #st.write(f"**Cash:** ₹{funds['cash']}")
                  #st.write(f"**Opening Balance:** ₹{funds['opening_balance']}")
                  #st.write(f"**Collateral:** ₹{funds['collateral']}")
                  #st.write(f"**Option Premium Used:** ₹{funds['option_premium']}")
                  #cash_balance = 73500
                  lots = get_lot_size(funds['cash'])
                  #st.write("Lot Size:", lots)
                  qty=65*lots
                  #st.divider()

   
    
    #------------------------------------PLACING ORDERS--------------------------------------------
             #st.write(f"Placing order for:", trending_symbol)
            if(position_size=='none'):
                  position_size=1;
        #st.write(f"Quantity: {qty}, LTP: {ltp}")
        #st.write(f"Quantity  order for:", qty)        
        #if st.button("🚀 PLACE BUY ORDER IN ZERODHA"):
        # Condition 1: Current time >= signal candle time
        # Trading window
            start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
            end_time   = now.replace(hour=14, minute=30, second=0, microsecond=0)
    #st.write("start_time", start_time)
    #st.write("end_time", end_time)
    #st.write("Now Time", now)
    #st.write("signal_time",signal_time)
    
    
    #-------------------------------------------------------------------------------

        # Convert to Python datetime (with timezone if needed)
            signal_time = pd.to_datetime(signal_time).to_pydatetime()
   
    # Optional: ensure same timezone as now
    #import pytz
            tz = pytz.timezone("Asia/Kolkata")
            signal_time = signal_time.replace(tzinfo=tz)
    #    st.write("signal_time",signal_time)
    #st.write("Now Time", now)
    #--------------------------------------------------------------------------------
     #-----------------------Add PARA----------------------------------------------
    # Define IST timezone
            ist = pytz.timezone("Asia/Kolkata")
    
    # Convert signal_time to IST
            signal_time_ist = signal_time.astimezone(ist)
            import datetime as dt

            start = dt.time(9, 30)
            end   = dt.time(14, 30)
    
            sig_t = signal_time_ist.time()
    
            result = "Pass" if start <= sig_t <= end else "Fail"
    
            add_param_row("Signal Time", str(signal_time_ist.time()),"09:30 - 14:30",result)
     #------------------------------------ADD PCR------------------------------------------ 
            pcr_value = get_nifty_pcr(kite)
            result = "Pass" if 0.80 <= pcr_value <= 1.30 else "Fail"
            pcr_result= result
            add_param_row("PCR", round(pcr_value, 2), "0.80 - 1.30", result)

#-------------------------------------lot ty------------------------------------------------
     # Default lot size
            qty = 1*65
     
     # Apply rule
            if iv_result == "Fail" or iv_rank_result == "Fail":
                   lot_qty = 2
            if iv_result == "Pass" and iv_rank_result == "Fail" and vix_result=="pass" and pcr_result=="pass":
                   lot_qty = 6    
            if vix_now < 10 :
                   lot_qty = 0 
                 
            add_param_row("LOT QTY", lot_qty, "0,1,2,4,6", "OK")
     #-----------------------------------------Display PARA-------------------------------------------
            if st.session_state.param_rows:
                  df = pd.DataFrame(st.session_state.param_rows)
                  st.table(df)
            else:
                  st.write("No parameters added yet.")
    #------------------------------------------------------------------------------------------------
#==============================================================================================================================

    with col6:
         days_to_exp = days_to_expiry(expiry)
         time_to_expiry = days_to_exp / 365 
         r=0.07
            #st.write("spot_price, strike, time_to_expiry, r, ltp",spot_price, strike, time_to_expiry, r, ltp) 
         #iv = implied_vol_call(spot_price, strike, time_to_expiry, r, ltp) 
         iv=new_iv_result
         st.subheader("Greeks Values")
         #greeks = option_greeks(S=spot_price,K=strike,T=time_to_expiry,r=r,sigma=iv,option_type=option_type)
         S=spot_price
         K=strike
         T=time_to_expiry
         r=r
         sigma=iv
         option_type=option_type
         st.session_state.S=S
         st.session_state.K=K
         st.session_state.T=T
         st.session_state.r=r
         st.session_state.sigma=sigma
         
         #st.write("Expiry value:", expiry)
         ##st.write("Expiry type:", type(expiry))
         expiry_dt = datetime.strptime(expiry, "%Y-%m-%d").replace(hour=15, minute=30)
 
         #greeks= safe_option_greeks(S, K, T, r, sigma, option_type="CALL")
         greeks= safe_option_greeks(S, K, expiry_dt, r, sigma, option_type="CALL")
         #if greeks:
              #st.subheader("Greeks Values")
          
              #col1, col2, col3, col4, col5 = st.columns(5)
              #col1.metric("Delta", round(greeks["Delta"], 3))
              #col2.metric("Gamma", round(greeks["Gamma"], 4))
              #col3.metric("Theta", round(greeks["Theta"], 2))
              #col4.metric("Vega", round(greeks["Vega"], 2))
              #col5.metric("IV %", round(greeks["IV"], 2))
         greeks_param_df = pd.DataFrame([
                   {
                       "Parameter": "NIFTY OPTION",
                       "Value": trending_symbol,
                       "Range": expiry,
                       "Result": "Valid"
                   },                  
         
    {
        "Parameter": "Delta",
        "Value": greeks["Delta"],
        "Range": "0.30 – 0.85",
        "Result": evaluate(greeks["Delta"], 0.30, 0.85)
    },
    {
        "Parameter": "Gamma",
        "Value": greeks["Gamma"],
        "Range": "≥ 0.0005",
        "Result": evaluate(greeks["Gamma"], 0.0005, None)
    },
    {
        "Parameter": "Theta",
        "Value": greeks["Theta"],
        "Range": "≥ -80",
        "Result": evaluate(greeks["Theta"], -80, None)
    },
    {
        "Parameter": "Vega",
        "Value": greeks["Vega"],
        "Range": "≥ 3.0",
        "Result": evaluate(greeks["Vega"], 3.0, None)
    },
    {
        "Parameter": "IV %",
        "Value": greeks["IV%"],
        "Range": "0.10 – 0.35",
        "Result": evaluate(greeks["IV%"], 0.10, 0.35)
    }
])
         st.session_state.GREEKdelta=greeks["Delta"]
         st.session_state.GREEKgamma=greeks["Gamma"]
         st.session_state.GREEKtheta=greeks["Theta"]
         st.session_state.GREEKvega=greeks["Vega"]
         
         st.dataframe(
         greeks_param_df.style.applymap(
            lambda x: "color: green; font-weight: bold"
            if x == "Pass"
            else "color: red; font-weight: bold"
            if x == "Fail"
            else ""
         ),
         use_container_width=True,
         hide_index=True
     )
#-----------------------------------------------------NEW GREEKS--------------------------------

         greeks = OptionGreeks(S, K, T, r, sigma, "put")
         #greeks= safe_option_greeks(S, K, T, r, sigma, option_type="CALL")
         greek_values = greeks.summary()
          
         #for greek, value in greek_values.items():
              #st.write(f"{greek}: {value:.4f}")
         #---------------------------------tIME-----------------------------------------------
         import pytz
            
    # IST timezone
         ist = pytz.timezone("Asia/Kolkata")
         now_dt = datetime.now(ist)     # full datetime object
         now = now_dt.time()            # extract time only for comparisons

         tz = pytz.timezone("Asia/Kolkata")
         now = datetime.now(tz)
     #----------------------------------FUND-----------------------------------------------------
            #st.divider()

         funds = get_fund_status(kite)

            #st.subheader("💰 Zerodha Fund Status")
    
         if "error" in funds:
                st.error(funds["error"])
         else:
                  #st.write(f"**Net Balance:** ₹{funds['net']}")
                  #st.write(f"**Cash:** ₹{funds['cash']}")
                  #st.write(f"**Opening Balance:** ₹{funds['opening_balance']}")
                  #st.write(f"**Collateral:** ₹{funds['collateral']}")
                  #st.write(f"**Option Premium Used:** ₹{funds['option_premium']}")
                  #cash_balance = 73500
                  lots = get_lot_size(funds['cash'])
                  #st.write("Lot Size:", lots)
                  qty=65*lots
                  #st.divider()

   
    
    #------------------------------------PLACING ORDERS--------------------------------------------
             #st.write(f"Placing order for:", trending_symbol)
         if(position_size=='none'):
                  position_size=1;
        #st.write(f"Quantity: {qty}, LTP: {ltp}")
        #st.write(f"Quantity  order for:", qty)        
        #if st.button("🚀 PLACE BUY ORDER IN ZERODHA"):
        # Condition 1: Current time >= signal candle time
        # Trading window
         start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
         end_time   = now.replace(hour=14, minute=30, second=0, microsecond=0)
    #st.wite("start_time", start_time)
    #st.write("end_time", end_time)
    #st.write("Now Time", now)
    #st.write("signal_time",signal_time)
    
    
    #-------------------------------------------------------------------------------

        # Convert to Python datetime (with timezone if needed)
         signal_time = pd.to_datetime(signal_time).to_pydatetime()
   
    # Optional: ensure same timezone as now
    #import pytz
         tz = pytz.timezone("Asia/Kolkata")
         signal_time = signal_time.replace(tzinfo=tz)
    #    st.write("signal_time",signal_time)
    #st.write("Now Time", now)
    #--------------------------------------------------------------------------------
     #-----------------------Add PARA----------------------------------------------
    # Define IST timezone
         ist = pytz.timezone("Asia/Kolkata")
    
    # Convert signal_time to IST
         signal_time_ist = signal_time.astimezone(ist)
         import datetime as dt

         start = dt.time(9, 30)
         end   = dt.time(14, 30)
    
         sig_t = signal_time_ist.time()
    
         result = "Pass" if start <= sig_t <= end else "Fail"
    
         add_param_row("Signal Time", str(signal_time_ist.time()),"09:30 - 14:30",result)
     #------------------------------------ADD PCR------------------------------------------ 
         pcr_value = get_nifty_pcr(kite)
         result = "Pass" if 0.80 <= pcr_value <= 1.30 else "Fail"
         pcr_result= result
         add_param_row("PCR", round(pcr_value, 2), "0.80 - 1.30", result)

#-------------------------------------lot ty------------------------------------------------
     # Default lot size
         qty = 1*65
            
                 
     
     # Apply rule
         if iv_result == "Fail" or iv_rank_result == "Fail":
                   lot_qty = 2
         if iv_result == "Pass" and iv_rank_result == "Fail" and vix_result=="pass" and pcr_result=="pass":
                   lot_qty = 6    
         if vix_now < 10 :
                   lot_qty = 1 
         if 10< vix_now < 15 :
                   lot_qty = 2
         if 15< vix_now < 20 :
                   lot_qty = 4
         if vix_now > 20 :
                   lot_qty = 1     
         add_param_row("LOT QTY", lot_qty, "0,1,2,4,6", "OK")
     #-----------------------------------------Display PARA-------------------------------------------
         if st.session_state.param_rows:
                  df = pd.DataFrame(st.session_state.param_rows)
                  #st.table(df)
         else:
                  st.write("No parameters added yet.")
    #------------------------------------------------------------------------------------------------
         qty=qty*lot_qty
            #qty=0
            #st.subheader("Session State Debug")
            #st.write(st.session_state)
            #st.subheader("Session State (Detailed)")
            #for key, value in st.session_state.items():
                #st.write(f"{key} :", value)

         #st.subheader("Trade State")
         keys_to_show = [
                   "trade_status",
                   "signal_time",
                   "signal_price",
                   "entry_time",
                   "exit_time",
                   "order_id",
                   "symbol"
               ]
               
         #for k in keys_to_show:
                   #if k in st.session_state:
                       #st.write(f"{k} :", st.session_state[k])

 
 
                # Check 1: Only run if current time is within trading window
         if is_valid_signal_time(entry_time):
                 st.warning("Signal time  match today's date .") 
                 if start_time <= now <= end_time:
                 
                 # Check 2: Signal time reached
                    #if now >= entry_time:
                    last_signal_price=st.session_state.signal_price  
                    last_executed_signal_time=st.session_state.last_executed_signal_time  
                      
                    st.write("Signal Price= ", last_signal_price )  
                    currnt_price=get_option_ltp(trending_symbol)  
                    st.write("Current Price =",currnt_price)  

                    lower = last_signal_price * 0.97
                    upper = last_signal_price * 1.03
                    
                                   
                    price_diff_pct = abs(currnt_price - last_signal_price) / last_signal_price * 100 
                    st.write("Current Price Difference=",price_diff_pct)  
                    if (lower <= currnt_price <= upper):
                        st.warning("Price within  ±3% execution range")
                        st.write("Allowed:", lower, "to", upper)
                        st.write("Current:", currnt_price)    
                    #if abs((now - entry_time).total_seconds()) < 50:  
                        st.info("Execution window In .") 
                        st.write("entry_time-",last_executed_signal_time)
                        st.write("Now Time-", now)
                      # Check 3: Order placed only once
                        if lot_qty>0: 
                              if has_open_position(kite):
                                  st.warning("⚠️ Open position exists. New trade not allowed.")                                  
                              else:
                                    if not st.session_state.order_executed:
                                        try:
                                            order_id = kite.place_order(
                                                    tradingsymbol=trending_symbol,
                                                    exchange=kite.EXCHANGE_NFO,
                                                    transaction_type=kite.TRANSACTION_TYPE_BUY,
                                                    quantity=qty,
                                                    order_type=kite.ORDER_TYPE_MARKET,
                                                    variety=kite.VARIETY_REGULAR,
                                                    product=kite.PRODUCT_MIS
                                                )                                
                                            st.session_state.order_executed = True   # Mark executed
                                            #st.session_state.order_executed = True
                                            st.session_state.last_order_id = order_id                                   
                                           # ✅ Mark trade active
                                            st.session_state.trade_active = True
                                            st.session_state.entry_price = ltp
                                            st.session_state.entry_time = datetime.now()
                                            st.session_state.qty = qty
                                            st.session_state.tradingsymbol = trending_symbol 
                                            st.success(f"Order Placed Successfully! Order ID: {order_id}")
                                            st.session_state["last_order_id"] = order_id
                                
                                        except Exception as e:
                                            st.error(f"Order Failed: {e}")                                        
                        else:
                               st.info("Trade Not Allowed Qty=0.")  
                    else:
                         st.info("Order already executed for this signal.")
                 
                 else:
                       st.warning("Trading window closed. Orders allowed only between 9:30 AM and 2:30 PM.")
         else:
                   st.warning("Signal time does not match today's date or is outside trading hours. Order not placed.")     
              
    st.divider()

    # ===== ROW 4 =====
    col7, col8 = st.columns(2)
#==============================================================================================================================

    with col7:
        st.subheader("Order Book")
        if "last_order_id" in st.session_state:
                  order_id = st.session_state["last_order_id"]
                  order = kite.order_history(order_id)[-1]
                  st.write("### 🔄 Live Order Update")
                  #st.write(order)


#------------------------------------ORDERS--------------------------------------------
        show_kite_orders(kite)
         #===========================================OPEN POSITION--------------------------------------
        st.divider()

        open_pnl = show_open_positions(kite)
        closed_pnl = show_closed_positions(kite)
               
        st.divider()
        st.metric(
                   "💰 TOTAL DAY P&L",
                   f"₹ {open_pnl + closed_pnl:,.2f}"
             )

#==============================================================================================================================

    with col8:
        st.subheader("Monitoring Trade / Positions")
        #---------------------------------Exit Logic-----------------------------------------------
        if "trade_active" not in st.session_state:
                   st.session_state.trade_active = False
                   st.session_state.entry_price = 0.0
                   st.session_state.entry_time = None
                   st.session_state.highest_price = 0.0
                   st.session_state.partial_exit_done = False
                   st.session_state.final_exit_done = False
#--------------------------------------Manage Order--------------------------------------------------------

        last_order1 = get_last_active_order(kite)

        st.subheader("🟢 Active Trade")
               
        if last_order1:
                   #st.write({"Symbol": last_order["tradingsymbol"],"Qty": last_order["quantity"],"Entry Price": last_order["average_price"],"Order Time": last_order["order_timestamp"] })
                   st.write("Last Order")
        else:
                   st.info("No active trade found.")

#--------------------------------------Exit Logix=-----------------------------------------------------------        
        pos = False 
        import time   
        last_order = get_last_buy_order(kite)
            #st.write("Last Order",last_order)   
        if last_order:
              pos = get_open_position_for_symbol(
                  kite,
                  last_order["tradingsymbol"]
              )
              #st.write("POS",pos)
        else:
                 st.write("No Open Position Active")
          
        if pos:
                  st.subheader("🟢 Active Position")
                  st.table(pd.DataFrame([{
                      "Symbol": pos["tradingsymbol"],
                      "Qty": pos["quantity"],
                      "Avg Price": pos["average_price"],
                      "PnL": pos["pnl"]
                  }]))
          
                 
        df_plot1 = fetch_nifty_daily_last_7_days(kite)

        
        if pos:
                        if df_plot1 is not None and not df_plot1.empty:
                             monitor_and_exit_last_position(kite, df_plot1)
                             time.sleep(5)
                        else:
                             print("❌ No NIFTY daily data available")
                        #monitor_and_exit_last_position(kite,df_plot)
                        
  #==============================================================================================================================
        
          
          
           
              
          
              
              


    
#####################################################################################################################

elif MENU=="Paper Trade":
    with st.sidebar:
         if st.button("🧹 Clear Paper Trades"):
             st.session_state.paper_trades = []
             st.success("All paper trades cleared")
             st.rerun()
 
    st.title("🔴 LIVE Paper  TRADE")
    #st.title("🔴 Live Nifty 15-Minute Chart + Signal Engine")
    if not is_kite_connected(kite):
        st.warning("Please login first to access LIVE trade.")
        st.stop()     # Stop page execution safely

    #st.success("You are logged in.")
     
    st.session_state.param_rows = []
    from streamlit_autorefresh import st_autorefresh
    import time             # Python's time module
    from datetime import time  # datetime.time (conflict!)
    # Initialize Kite in session_state
    if "kite" not in st.session_state:
        st.session_state.kite = None
    else:
        kite = st.session_state.get("kite")
    # --- SESSION STATE INIT ---
    if "order_executed" not in st.session_state:
        st.session_state.order_executed = False
        
    
    if "signal_time" not in st.session_state:
        st.session_state.signal_time = None
    # Add after data processing:
    def is_kite_connected(kite):
        try:
            kite.profile()
            return True
        except:
            return False

    if is_kite_connected(kite):
        st.success("Kite connection active")
    else:
        st.error("Kite session expired. Please login again.")

    st.set_page_config(layout="wide")
    # Place at the very top of your script (or just before plotting)
    #st_autorefresh(interval=60000, limit=None, key="refresh")
    # Current time in IST
    #----------------------------------------------------------------------
    #if is_kite_connected(kite):
    funds = get_fund_status(kite)
    cash = (funds['cash'])
    cash = (funds['net'])
    #iv_value = 0.26
    result = "Pass" if 75000 <= cash <= 25000 else "Fail"
    add_param_row("CASH", cash, "25K - 100K", result)


    #---------------------------------------------------------------------
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    
    # Market hours condition
    start = time(9, 15)   # 9:30 AM
    end = time(15, 25)    # 3:25 PM
    
    # Refresh only between 9:30–3:25
    if start <= now <= end:
        #st_autorefresh(interval=60000, key="refresh")  # 1 minute refresh
        st_autorefresh(interval=60000, key="refresh_live3")
    else:
        st.info("Auto-refresh is paused — Outside market hours (9:30 AM to 3:25 PM).")

    st.title("Nifty 15-min Chart")
    
    # Select date input (default today)
    selected_date = st.date_input("Select date", value=datetime.today())
    
    # Calculate date range to download (7 days before selected_date to day after selected_date)
    start_date = selected_date - timedelta(days=7)
    end_date = selected_date + timedelta(days=1)
    
    # Download data for ^NSEI from start_date to end_date
    df = yf.download("^NSEI", start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="15m")
    
    if df.empty:
        st.warning("No data downloaded for the selected range.")
        st.stop()
    df.reset_index(inplace=True)
    
    if 'Datetime_' in df.columns:
        df.rename(columns={'Datetime_': 'Datetime'}, inplace=True)
    elif 'Date' in df.columns:
        df.rename(columns={'Date': 'Datetime'}, inplace=True)
    # Add any other detected name if needed
    
    
    #st.write(df.columns)
    #st.write(df.head(10))
    # Flatten columns if MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
    
    # Rename datetime column if needed
    if 'Datetime' not in df.columns and 'datetime' in df.columns:
        df.rename(columns={'datetime': 'Datetime'}, inplace=True)
    #st.write(df.columns)
    #st.write(df.columns)
    # Convert to datetime & timezone aware
    #df['Datetime'] = pd.to_datetime(df['Datetime'])
    if df['Datetime_'].dt.tz is None:
        df['Datetime'] = df['Datetime_'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    else:
        df['Datetime'] = df['Datetime_'].dt.tz_convert('Asia/Kolkata')
    
    #st.write(df.columns)
    #st.write(df.head(10))
    
    # Filter for last two trading days to plot
    unique_days = df['Datetime'].dt.date.unique()
    if len(unique_days) < 2:
        st.warning("Not enough data for two trading days")
    else:
        last_day = unique_days[-2]
        today = unique_days[-1]
    
        df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
    
        # Get last day 3PM candle open and close
        candle_3pm = df_plot[(df_plot['Datetime'].dt.date == last_day) &
                             (df_plot['Datetime'].dt.hour == 15) &
                             (df_plot['Datetime'].dt.minute == 0)]
    
        if not candle_3pm.empty:
            open_3pm = candle_3pm.iloc[0]['Open_^NSEI']
            close_3pm = candle_3pm.iloc[0]['Close_^NSEI']
        else:
            open_3pm = None
            close_3pm = None
            st.warning("No 3:00 PM candle found for last trading day.")

         #-----------------------------Marking 9.15 Candle---------------------------------
        # Get today's 9:15 AM candle
        candle_915 = df_plot[(df_plot['Datetime'].dt.date == today) &
                          (df_plot['Datetime'].dt.hour == 9) &
                          (df_plot['Datetime'].dt.minute == 15)]
     
        if not candle_915.empty:
              o_915 = candle_915.iloc[0]['Open_^NSEI']
              h_915 = candle_915.iloc[0]['High_^NSEI']
              l_915 = candle_915.iloc[0]['Low_^NSEI']
              c_915 = candle_915.iloc[0]['Close_^NSEI']
              t_915 = candle_915.iloc[0]['Datetime']
        else:
              o_915 = h_915 = l_915 = c_915 = t_915 = None
              st.warning("No 9:15 AM candle found for today.")    
         
         #---------------------------------------------------------------------------------
         # Plot candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=df_plot['Datetime'],
            open=df_plot['Open_^NSEI'],
            high=df_plot['High_^NSEI'],
            low=df_plot['Low_^NSEI'],
            close=df_plot['Close_^NSEI']
        )])
     
        if t_915 is not None:
              fig.add_vrect(
                  x0=t_915,
                  x1=t_915 + pd.Timedelta(minutes=15),
                  fillcolor="orange",
                  opacity=0.25,
                  layer="below",
                  line_width=0,
                  annotation_text="9:15 Candle",
                  annotation_position="top left"
              )
        if open_3pm and close_3pm:
            fig.add_hline(y=open_3pm, line_dash="dot", line_color="blue", annotation_text="3PM Open")
            fig.add_hline(y=close_3pm, line_dash="dot", line_color="red", annotation_text="3PM Close")

        if o_915 is not None and c_915 is not None:
              fig.add_hline(y=o_915, line_dash="solid", line_color="green",
                            annotation_text="9:15 Open")
              fig.add_hline(y=c_915, line_dash="solid", line_color="orange",
                            annotation_text="9:15 Close")
 
       
        
    
    
    
        # Draw horizontal lines as line segments only between 3PM last day and 3PM next day
    
        
        fig.update_layout(title="Nifty 15-min candles - Last Day & Today", xaxis_rangeslider_visible=False)
        fig.update_layout(
        xaxis=dict(
            rangebreaks=[
                # Hide weekends (Saturday and Sunday)
                dict(bounds=["sat", "mon"]),
                # Hide hours outside of trading hours (NSE trading hours 9:15 to 15:30)
                dict(bounds=[15.5, 9.25], pattern="hour"),
            ]
        )
    )
    
    
        st.plotly_chart(fig, use_container_width=True)
        #----------------------------------------------------------------------
        df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
        #signal = trading_signal_all_conditions(df_plot)
        signal = trading_signal_all_conditions_final(df_plot)
        if signal is None:
            st.warning("⚠ No signal yet (conditions not met).")
        else:
            st.success(f"✅ SIGNAL GENERATED: {signal['message']}")
            df_sig1 = pd.DataFrame([signal])
            signal_time = df_plot["Datetime"].iloc[-1]   # last candle timestamp
            signal["signal_time"] = signal_time
  
 
                
                # Display as table
            st.table(df_sig1) 
             
            entry_time = signal['entry_time']
            #st.write("entry_time",entry_time) 
            #st.write("Signal Time only:", entry_time.strftime("%H:%M:%S"))  # HH:MM:SS
            signal_time=entry_time.strftime("%H:%M:%S")
            #st.write("Signal Time only:-", signal_time)  # HH:MM:SS
            #            st.write(signal)
#--------------------------------------------------------------------------------

        def generate_signals_stepwise(df):
            all_signals = []
            
            # We run strategy for each candle progressively
            for i in range(40, len(df)):   # start after enough candles
                sub_df = df.iloc[:i].copy()
                sig = trading_signal_all_conditions(sub_df)
                if sig is not None:
                    all_signals.append((sub_df.iloc[-1]["Datetime"], sig))
        
            return all_signals
#-------------------------------------Total signals-------------------------------------------

        step_signals = generate_signals_stepwise(df_plot)
        if step_signals:
                #st.info(f"Total signals detected so far: {len(step_signals)}")
            
                latest_time, latest_sig = step_signals[-1]
                
                st.success(f"🟢 Latest Candle Signal ({latest_time}):")
                #st.write(latest_sig)
                # Convert to DataFrame
                df_sig = pd.DataFrame([latest_sig])
                
                # Display as table
                #st.table(df_sig)
        else:
                st.warning("No signal triggered in any candle yet.")
   

#-----------------------------------Nearest ITM Option ---------------------------------------------

        if signal is not None:
            #signal_time = df["Datetime"].iloc[-1].time()   # last candle time
            option_type = signal["option_type"]     # CALL / PUT
            #st.write("Option type ",option_type)
            spot = signal["spot_price"]
            #st.write("Option spot ",spot)
            try:
                nearest_itm = find_nearest_itm_option(kite, spot, option_type)
                
                st.success("Nearest ITM Option Found")
                #                st.write(nearest_itm)
                nearest_itm1 = pd.DataFrame([nearest_itm])
                
                # Display as table
                st.table(nearest_itm1)
                trending_symbol=nearest_itm['tradingsymbol']
                #st.write("tradingsymbol-",trending_symbol)
        
            except Exception as e:
                st.error(f"Failed to fetch option: {e}")

    
#######################---------------------IV-NEW !-------------------------------------------------
             
            option_dict = get_live_option_details(kite, trending_symbol)
            spot_price=26046.00 
            ltp = option_dict.get("ltp")
            strike = option_dict.get("strike")
            expiry = option_dict.get("expiry")
            is_call = option_dict.get("option_type") == "CALL"
          #------------------------------------------PAPER TRADE-------------------------------------------------
            if signal is not None:

              signal_time = signal["signal_time"]
          
              # 🔒 ENTRY LOCK — THIS PREVENTS RE-ENTRY ON REFRESH
              if st.session_state.last_executed_signal_time == signal_time:
                  pass  # already traded this signal
          
              else:
                  option_type = signal["option_type"]
                  spot = signal["spot_price"]
          
                  nearest_itm = find_nearest_itm_option(kite, spot, option_type)
                  trending_symbol = nearest_itm["tradingsymbol"]
                  option_symbol = f"NFO:{trending_symbol}"
          
                  entry_price = kite.ltp(option_symbol)[option_symbol]["last_price"]
          
                  
                  trade = {
                        "signal_time": signal_time,
                        "entry_time": pd.Timestamp.now(),
                        "symbol": trending_symbol,
                        "option_type": option_type,
                        "entry_price": entry_price,
                        "quantity": 75,
                        "remaining_qty": 75,
                        "highest_price": entry_price,
                        "partial_exit_done": False,
                        "final_exit_done": False,
                        "status": "OPEN"
                    }
          
                  st.session_state.paper_trades.append(trade)
          
                  # 🔐 LOCK THE SIGNAL
                  st.session_state.last_executed_signal_time = signal_time
          
                  #st.success(f"Paper trade entered @ {entry_price}")

            #monitor_paper_trades(kite)
            #for trade in st.session_state.paper_trades:
              #normalize_trade(trade)
              #manage_exit_papertrade(kite, trade)

            st.write("Moniter")
             

 
   
          #---------------------------------------PAPER TRADE----------------------------------------------------   
              # Compute time to expiry (in years)
            days_to_exp = days_to_expiry(expiry)
            time_to_expiry = days_to_exp / 365 
            r=0.07
            #st.write("spot_price, strike, time_to_expiry, r, ltp",spot_price, strike, time_to_expiry, r, ltp) 
            iv = implied_vol_call(spot_price, strike, time_to_expiry, r, ltp) 
            #st.write("IV  FOr (Option):CE")
            #st.write("IV (decimal):", iv)
            #st.write("IV (%):", iv * 100)    
            result = "Pass" if (iv is not None and 0.10 <= iv <= 0.35) else "Fail"
 
            #result = "Pass" if 0.10 <= iv <= 0.35 else "Fail"
            iv_result = result    
            #add_param_row("IV", round(iv, 2), "0.10 - 0.35", result)
             

#-----------------------------------IV Compute---------------------------------------------

        #spot_price = get_ltp(kite, "NSE:NIFTY 50")["ltp"]
        
         #iv_percent = compute_option_iv(nearest_itm, spot)
        
         #st.write("IV:", iv_percent)    
         
         #get_live_iv_nifty_option(kite, option_token: int, index_symbol="NSE:NIFTY 50"):        
            #st.write(nearest_itm)  

#----------------------------------IV----------------------------------------------

    
        
            iv_info = get_iv_rank0(kite, nearest_itm, lookback_days=250)
       
            #st.write("New Way Iv ",iv)  
            # Fix missing values
            if iv_info["iv"] is None:
                 iv_info["iv"] = 0
     
            if iv_info["iv_rank"] is None:
                iv_info["iv_rank"] = 0

         ##st.write("Current IV:", iv_info["iv"], "%")
         #st.write("IV Rank:", iv_info["iv_rank"], "%")
#-----------------------Add PARA----------------------------------------------
    # IV
            result = "Pass" if 0.10 <= iv_info["iv"] <= 0.35 else "Fail"
            iv_result = result    
            #add_param_row("IV", round(iv_info["iv"], 2), "0.10 - 0.35", result)

    # IV Rank
            result = "Pass" if 0.20 <= iv_info["iv_rank"] <= 0.70 else "Fail"
            iv_rank_result  = result    
            add_param_row("IV Rank", round(iv_info["iv_rank"], 2), "0.20 - 0.70", result)
#--------------------------------------------------Getting New IV-----------& adding to para----------------------------
            #result = compute_option_iv_details(option, spot)
     
            #st.write(result)  
            option = get_live_option_details(kite, trending_symbol)
     
            #st.write(option)
     
     
            spot = option["strike"]
            #st.write("Spot",spot) 
            #spot = 25900.00  # live NIFTY spot
     
            result = compute_option_iv_details(option, spot)
            #st.write("IV new",result["iv"]) 
            new_iv_result= result["iv"]
            result = "Pass" if 0.10 <= new_iv_result <= 0.35 else "Fail" 
            add_param_row("IV ", round(new_iv_result, 2), "0.10 - 0.35", result) 
#-------------------------------------------------------------------------
            if(iv_info["iv"]=='None'):
             # Safely extract values
                  iv_value = iv_info.get("iv") or 0
                  iv_rank_value = iv_info.get("iv_rank") or 0
             
                  st.write("After None Current IV:", iv_value, "%")
                  st.write("After None IV Rank:", iv_rank_value, "%")
    
        

#--------------------------------VIX------------------------------------------------
         #vix_now =fetch_vix_from_fyers()
         
            vix_now = fetch_india_vix_kite(kite)
         #st.write("India VIX: kite", vix_now)
         #st.write("India VIX:", vix_now)
 #-----------------------Add PARA----------------------------------------------
    # VIX
            result = "Pass" if vix_now < 15 else "Fail"
            vix_result  = result     
            add_param_row("VIX", round(vix_now, 2), "< 15", result)

 #------------------------------------------------------------------------------   
    # Apply IV + VIX Filter
    # -------------------------
        #allowed, position_size = combined_filter(iv_info["iv"], iv_info["iv_rank"], vix_now)
    # Safely extract values
            iv_value = iv_info.get("iv") or 0
            iv_rank_value = iv_info.get("iv_rank") or 0
            allowed, position_size = combined_filter(iv_value, iv_rank_value, vix_now)
            #st.write("Allowed to Trade?", allowed)
            #st.write("Position Size:", position_size)
    #-----------------------------------------------------------------------------------------
    
    #---------------------------------tIME-----------------------------------------------
            import pytz
            
    # IST timezone
            ist = pytz.timezone("Asia/Kolkata")
            now_dt = datetime.now(ist)     # full datetime object
            now = now_dt.time()            # extract time only for comparisons

            tz = pytz.timezone("Asia/Kolkata")
            now = datetime.now(tz)
     #----------------------------------FUND-----------------------------------------------------
            #st.divider()

            funds = get_fund_status(kite)

            #st.subheader("💰 Zerodha Fund Status")
    
            if "error" in funds:
                st.error(funds["error"])
            else:
                  #st.write(f"**Net Balance:** ₹{funds['net']}")
                  #st.write(f"**Cash:** ₹{funds['cash']}")
                  #st.write(f"**Opening Balance:** ₹{funds['opening_balance']}")
                  #st.write(f"**Collateral:** ₹{funds['collateral']}")
                  #st.write(f"**Option Premium Used:** ₹{funds['option_premium']}")
                  #cash_balance = 73500
                  lots = get_lot_size(funds['cash'])
                  #st.write("Lot Size:", lots)
                  qty=65*lots
                  #st.divider()

   
    
    #------------------------------------PLACING ORDERS--------------------------------------------
             #st.write(f"Placing order for:", trending_symbol)
            if(position_size=='none'):
                  position_size=1;
        #st.write(f"Quantity: {qty}, LTP: {ltp}")
        #st.write(f"Quantity  order for:", qty)        
        #if st.button("🚀 PLACE BUY ORDER IN ZERODHA"):
        # Condition 1: Current time >= signal candle time
        # Trading window
            start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
            end_time   = now.replace(hour=14, minute=30, second=0, microsecond=0)
    #st.write("start_time", start_time)
    #st.write("end_time", end_time)
    #st.write("Now Time", now)
    #st.write("signal_time",signal_time)
    
    
    #-------------------------------------------------------------------------------

        # Convert to Python datetime (with timezone if needed)
            signal_time = pd.to_datetime(signal_time).to_pydatetime()
   
    # Optional: ensure same timezone as now
    #import pytz
            tz = pytz.timezone("Asia/Kolkata")
            signal_time = signal_time.replace(tzinfo=tz)
    #    st.write("signal_time",signal_time)
    #st.write("Now Time", now)
    #--------------------------------------------------------------------------------
     #-----------------------Add PARA----------------------------------------------
    # Define IST timezone
            ist = pytz.timezone("Asia/Kolkata")
    
    # Convert signal_time to IST
            signal_time_ist = signal_time.astimezone(ist)
            import datetime as dt

            start = dt.time(9, 30)
            end   = dt.time(14, 30)
    
            sig_t = signal_time_ist.time()
    
            result = "Pass" if start <= sig_t <= end else "Fail"
    
            add_param_row("Signal Time", str(signal_time_ist.time()),"09:30 - 14:30",result)
     #------------------------------------ADD PCR------------------------------------------ 
            pcr_value = get_nifty_pcr(kite)
            result = "Pass" if 0.80 <= pcr_value <= 1.30 else "Fail"
            pcr_result= result
            add_param_row("PCR", round(pcr_value, 2), "0.80 - 1.30", result)

#-------------------------------------lot ty------------------------------------------------
     # Default lot size
            qty = 1*65
     
     # Apply rule
            if iv_result == "Fail" or iv_rank_result == "Fail":
                   lot_qty = 2
            if iv_result == "Pass" and iv_rank_result == "Fail" and vix_result=="pass" and pcr_result=="pass":
                   lot_qty = 6    
            if vix_now < 10 :
                   lot_qty = 0 
            add_param_row("LOT QTY", lot_qty, "0,1,2,4,6", "OK")
     #-----------------------------------------Display PARA-------------------------------------------
            if st.session_state.param_rows:
                  df = pd.DataFrame(st.session_state.param_rows)
                  st.table(df)
            else:
                  st.write("No parameters added yet.")
    
            qty=qty*lot_qty
            
                # Check 1: Only run if current time is within trading window
            if is_valid_signal_time(entry_time):
                 st.warning("Signal time  match today's date .") 
                 if start_time <= now <= end_time:
                 
                 # Check 2: Signal time reached
                    if now >= signal_time:
                      
                      # Check 3: Order placed only once
                         if lot_qty>0: 
                               if not st.session_state.order_executed:
                                   try:
                                       order_id = kite.place_order(
                                               tradingsymbol=trending_symbol,
                                               exchange=kite.EXCHANGE_NFO,
                                               transaction_type=kite.TRANSACTION_TYPE_BUY,
                                               quantity=qty,
                                               order_type=kite.ORDER_TYPE_MARKET,
                                               variety=kite.VARIETY_REGULAR,
                                               product=kite.PRODUCT_MIS
                                           )
                           
                                       st.session_state.order_executed = True   # Mark executed
                                       st.success(f"Order Placed Successfully! Order ID: {order_id}")
                                       st.session_state["last_order_id"] = order_id
                           
                                   except Exception as e:
                                       st.error(f"Order Failed: {e}")
                         else:
                               st.info("Trade Not Allowed Qty=0.")  
                    else:
                         st.info("Order already executed for this signal.")
                 
                 else:
                       st.warning("Trading window closed. Orders allowed only between 9:30 AM and 2:30 PM.")
            else:
                   st.warning("Signal time does not match today's date or is outside trading hours. Order not placed.")     
          
#--------------------------------ORDERS------------------------------------------------
            st.divider()
         #st.autorefresh(interval=5000)  # refresh every 5 seconds
    
            if "last_order_id" in st.session_state:
                  order_id = st.session_state["last_order_id"]
                  order = kite.order_history(order_id)[-1]
                  st.write("### 🔄 Live Order Update")
                  #st.write(order)


#------------------------------------ORDERS--------------------------------------------
            show_kite_orders(kite)

#---------------------------------Exit Logic-----------------------------------------------
            if "trade_active" not in st.session_state:
                   st.session_state.trade_active = False
                   st.session_state.entry_price = 0.0
                   st.session_state.entry_time = None
                   st.session_state.highest_price = 0.0
                   st.session_state.partial_exit_done = False
                   st.session_state.final_exit_done = False
 

            if "trade_active" not in st.session_state:
                st.session_state.trade_active = False
          
            if "entry_price" not in st.session_state:
                st.session_state.entry_price = None
          
            if "highest_price" not in st.session_state:
                st.session_state.highest_price = None
          
            if "entry_time" not in st.session_state:
                st.session_state.entry_time = None
          
            if "partial_exit_done" not in st.session_state:
                st.session_state.partial_exit_done = False
          
            if "final_exit_done" not in st.session_state:
                st.session_state.final_exit_done = False
               #-------------------------------
            st.session_state.trade_active = True
            st.session_state.entry_price = ltp   # from trade average price
            st.session_state.highest_price = ltp
            st.session_state.entry_time = datetime.now()
            st.session_state.partial_exit_done = False
            st.session_state.final_exit_done = False
            st.session_state.qty = lot_qty
            st.session_state.tradingsymbol = trending_symbol
#-------------------------------Exit Order-----------------------------------------------

            last_order = get_last_active_order(kite)

            st.subheader("🟢 Active Trade")
               
            if last_order:
                   st.write({
                       "Symbol": last_order["tradingsymbol"],
                       "Qty": last_order["quantity"],
                       "Entry Price": last_order["average_price"],
                       "Order Time": last_order["order_timestamp"]
                   })
            else:
                   st.info("No active trade found.")




#--------------------------------EXIT------------------------------------------------
            # ---------------- EXIT MANAGEMENT ----------------
            if st.session_state.trade_active:
                   manage_exit(
                       kite=kite,
                       tradingsymbol=st.session_state.tradingsymbol,
                       qty=st.session_state.qty
                   )


#--------------------------------------------------------------------------------


elif MENU == "Telegram":
    st.title("📱 Telegram") 
    
    load_dotenv()
    
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    ##st.write(TELEGRAM_BOT_TOKEN)
    ##st.write(TELEGRAM_CHAT_ID) 
    #send_telegram_message("✅ Telegram bot is working!")

       

  #--------------------------------------------------------------------   
      
#-------------------------------------
elif MENU == "Logout":
        st.title("Logout")
    
        if st.button("Logout from All Brokers"):
            # Clear broker connections
            st.session_state.connected_broker = None
            st.session_state.api_status = {
                "Zerodha": False,
                "Fyers": False,
                "AliceBlue": False
            }
    
            # Remove Zerodha kite object if present
            if "kite" in st.session_state:
                st.session_state.kite = None
    
            st.success("You have been logged out successfully.")
            st.info("Please reconnect your broker from the 'Zerodha Broker API' menu.")
    
        st.write("---")
        st.caption("Your session is now cleared. Safe exit 👋")    

#--------------------------------------------------------------------------
elif MENU == "My Account":
        st.title("My Account")
        st.set_page_config(page_title="Zerodha Dashboard", layout="wide")
        #st.title("📊 Zerodha Orders & Holdings Dashboard")
     
        if not is_kite_connected(kite):
             st.warning("Please login first to access your account details.")
             st.stop()     # Stop page execution safely

        st.success("You are logged in.")
        # ---------------------------
        # Session State
        # ---------------------------
        if st.session_state.api_status.get("Zerodha"):
            kite = st.session_state.kite 
            def fetch_zerodha_data():
                kite = st.session_state.kite
                # IMPORTANT: make kite available everywhere below
     
            
                try:
                    funds = kite.margins()["equity"]["available"]["cash"]
                    holdings = kite.holdings()
                    positions = kite.positions()["net"]
                    orders = kite.orders()
            
                    return funds, holdings, positions, orders
            
                except Exception as e:
                    st.error(f"Error fetching Zerodha data: {e}")
                    return 0, [], [], []

            funds, holdings, positions, orders = fetch_zerodha_data()
        
            st.subheader("Zerodha Account Overview")
        
            #colA, colB = st.columns(2)
        
            #with colA:
                #st.metric("Total Funds", f"₹{funds:,.0f}")
        
            #with colB:
                #st.metric("Open Positions", len(positions))
        
            #st.markdown("### Holdings")
            #st.dataframe(holdings, use_container_width=True, height=200)
        
            #st.markdown("### Positions")
            #st.dataframe(positions, use_container_width=True, height=200)
        
            #st.markdown("### Orders")
            #st.dataframe(orders, use_container_width=True, height=200)
            #---------------------------------------------------------------------------

            # Tabs
            tab1, tab2, tab3,tab4,tab5,tab6 = st.tabs(["👤 Account Details", "📁 Holdings", "📘 Orders","💵 Funds","📈 Positions","Session"])
        
            # -----------------------------------------------------------
            # TAB 1 — ACCOUNT HOLDER DETAILS
            # -----------------------------------------------------------
            with tab1:
                st.subheader("👤 Account Holder Details")
        
                try:
                    profile = kite.profile()  # <-- Fetch user details
        
                    df_profile = pd.DataFrame({
                        "Field": ["User ID", "User Name", "Email", "Broker", "Products", "Exchanges"],
                        "Value": [
                            profile.get("user_id"),
                            profile.get("user_name"),
                            profile.get("email"),
                            profile.get("broker"),
                            ", ".join(profile.get("products")) if isinstance(profile.get("products"), list) else profile.get("products"),
                            ", ".join(profile.get("exchanges")) if isinstance(profile.get("exchanges"), list) else profile.get("exchanges")
                        ]
                    })
        
                    st.table(df_profile)
        
                except Exception as e:
                    st.error(f"Error fetching account details: {e}")
        
            # -----------------------------------------------------------
            # TAB 2 — HOLDINGS
            # -----------------------------------------------------------
            with tab2:
                st.subheader("📁 Your Holdings")
        
                try:
                    holdings = kite.holdings()
                    df_hold = pd.DataFrame(holdings)
        
                    if not df_hold.empty:
                        st.dataframe(df_hold, use_container_width=True)
                    else:
                        st.info("No holdings found.")
        
                except Exception as e:
                    st.error(f"Error fetching holdings: {e}")
        
            # -----------------------------------------------------------
            # TAB 3 — ORDERS
            # -----------------------------------------------------------
            with tab3:
                st.subheader("📘 Order History")
        
                try:
                    orders = kite.orders()
                    df_orders = pd.DataFrame(orders)
        
                    if not df_orders.empty:
                        st.dataframe(df_orders, use_container_width=True)
                    else:
                        st.info("No orders found.")
        
                except Exception as e:
                    st.error(f"Error fetching orders: {e}")

            with tab4:   # replace tabX with your actual tab variable
                   st.subheader("💰 Fund Status")
               
                   try:
                       margins = kite.margins()   # Fetch account margins
               
                       # Convert to DataFrame for display
                       df_funds = pd.DataFrame([{
                           "Available Cash": margins["equity"]["available"]["cash"],
                           #"Opening Balance": margins["equity"]["opening_balance"],
                           "Utilised Margin": margins["equity"]["utilised"]["debits"],
                           "Exposure": margins["equity"]["utilised"]["exposure"],
                           "SPAN": margins["equity"]["utilised"]["span"],
                           "Option Premium": margins["equity"]["utilised"]["option_premium"],
                           #"Collateral": margins["equity"]["collateral"],
                           "Total Equity": margins["equity"]["net"]
                       }])
               
                       st.dataframe(df_funds, use_container_width=True)
               
                   except Exception as e:
                       st.error(f"Error fetching fund status: {e}")

            with tab5:
                   st.subheader("📊 Open Positions")
               
                   try:
                       positions = kite.positions()
               
                       # Combine day + net positions
                       df_positions = pd.DataFrame(
                           positions.get("net", [])
                       )
               
                       if not df_positions.empty:
                           # Optional: select useful columns only
                           display_cols = [
                               "tradingsymbol",
                               "exchange",
                               "product",
                               "quantity",
                               "average_price",
                               "last_price",
                               "pnl",
                               "unrealised",
                               "realised"
                           ]
               
                           df_positions = df_positions[display_cols]
               
                           st.dataframe(
                               df_positions,
                               use_container_width=True
                           )
                       else:
                           st.info("No open positions.")
               
                   except Exception as e:
                       st.error(f"Error fetching positions: {e}")

            with tab6:    
                    st.subheader("🧠 Session State Debug (Clean View)")

                    rows = []
                    for key, value in st.session_state.items():
                        if isinstance(value, pd.DataFrame):
                            display_value = f"DataFrame shape={value.shape}"
                        elif isinstance(value, dict):
                            display_value = str(value)
                        elif isinstance(value, list):
                            display_value = f"List (len={len(value)})"
                        else:
                            display_value = value
                    
                        rows.append({
                            "Key": key,
                            "Value": display_value,
                            "Type": type(value).__name__
                        })
                    
                    df_debug = pd.DataFrame(rows)
                    
                    st.dataframe(
                        df_debug,
                        use_container_width=True,
                        hide_index=True                    
                    )
                    if isinstance(st.session_state.get("trades_signals"), pd.DataFrame):
                        st.subheader("📊 trades_signals Logs")
                        st.dataframe(st.session_state.trades_signals, use_container_width=True)
                         
                    if isinstance(st.session_state.get("trade_logs"), pd.DataFrame):
                        st.subheader("📊 Trade Logs")
                        st.dataframe(st.session_state.paper_trades, use_container_width=True)
                    
                    st.subheader("📌 Active Trade State")

                    trade_keys = [
                        "trade_active",
                        "tradingsymbol",
                        "entry_price",
                        "qty",
                        "entry_time",
                        "partial_exit_done",
                        "final_exit_done",
                        "order_executed"
                    ]
                    
                    trade_rows = [
                        {"Key": k, "Value": st.session_state.get(k)}
                        for k in trade_keys
                    ]
                    
                    st.table(pd.DataFrame(trade_rows))



                                
               


#-------------------------------------
elif MENU == "10.10 Strategy":
    st.title("Live Trade BANK NIFTY 10.10 Strategy")        
#-------------------------------------------------------------------------------------------
    from streamlit_autorefresh import st_autorefresh
    import time             # Python's time module
    from datetime import time  # datetime.time (conflict!)
    # Initialize Kite in session_state
    if "kite" not in st.session_state:
        st.session_state.kite = None
    else:
        kite = st.session_state.get("kite")
    # --- SESSION STATE INIT ---
    if "order_executed" not in st.session_state:
        st.session_state.order_executed = False
    
    if "signal_time" not in st.session_state:
        st.session_state.signal_time = None
    # Add after data processing:
    def is_kite_connected(kite):
        try:
            kite.profile()
            return True
        except:
            return False

    if is_kite_connected(kite):
        st.success("Kite connection active")
    else:
        st.error("Kite session expired. Please login again.")

    st.set_page_config(layout="wide")
    # Place at the very top of your script (or just before plotting)
    #st_autorefresh(interval=60000, limit=None, key="refresh")
    # Current time in IST
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    
    # Market hours condition
    start = time(9, 30)   # 9:30 AM
    end = time(15, 25)    # 3:25 PM
    
    # Refresh only between 9:30–3:25
    if start <= now <= end:
        st_autorefresh(interval=60000, key="refresh")  # 1 minute refresh
    else:
        st.info("Auto-refresh is paused — Outside market hours (9:30 AM to 3:25 PM).")

    st.title("Nifty 15-min Chart")
    
    # Select date input (default today)
    selected_date = st.date_input("Select date", value=datetime.today())
    
    # Calculate date range to download (7 days before selected_date to day after selected_date)
    start_date = selected_date - timedelta(days=7)
    end_date = selected_date + timedelta(days=1)
    
    # Download data for ^NSEI from start_date to end_date
    df = yf.download("^NSEI", start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="15m")
    
    if df.empty:
        st.warning("No data downloaded for the selected range.")
        st.stop()
    df.reset_index(inplace=True)
    
    if 'Datetime_' in df.columns:
        df.rename(columns={'Datetime_': 'Datetime'}, inplace=True)
    elif 'Date' in df.columns:
        df.rename(columns={'Date': 'Datetime'}, inplace=True)
    # Add any other detected name if needed
    
    
    #st.write(df.columns)
    #st.write(df.head(10))
    # Flatten columns if MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
    
    # Rename datetime column if needed
    if 'Datetime' not in df.columns and 'datetime' in df.columns:
        df.rename(columns={'datetime': 'Datetime'}, inplace=True)
    #st.write(df.columns)
    #st.write(df.columns)
    # Convert to datetime & timezone aware
    #df['Datetime'] = pd.to_datetime(df['Datetime'])
    if df['Datetime_'].dt.tz is None:
        df['Datetime'] = df['Datetime_'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    else:
        df['Datetime'] = df['Datetime_'].dt.tz_convert('Asia/Kolkata')
    
    #st.write(df.columns)
    #st.write(df.head(10))
    
    # Filter for last two trading days to plot
    unique_days = df['Datetime'].dt.date.unique()
    if len(unique_days) < 2:
        st.warning("Not enough data for two trading days")
    else:
        last_day = unique_days[-2]
        today = unique_days[-1]
    
        df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
    
        # Get last day 3PM candle open and close
        candle_3pm = df_plot[(df_plot['Datetime'].dt.date == last_day) &
                             (df_plot['Datetime'].dt.hour == 15) &
                             (df_plot['Datetime'].dt.minute == 0)]
    
        if not candle_3pm.empty:
            open_3pm = candle_3pm.iloc[0]['Open_^NSEI']
            close_3pm = candle_3pm.iloc[0]['Close_^NSEI']
        else:
            open_3pm = None
            close_3pm = None
            st.warning("No 3:00 PM candle found for last trading day.")
    
        # Plot candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=df_plot['Datetime'],
            open=df_plot['Open_^NSEI'],
            high=df_plot['High_^NSEI'],
            low=df_plot['Low_^NSEI'],
            close=df_plot['Close_^NSEI']
        )])
    
        if open_3pm and close_3pm:
            fig.add_hline(y=open_3pm, line_dash="dot", line_color="blue", annotation_text="3PM Open")
            fig.add_hline(y=close_3pm, line_dash="dot", line_color="red", annotation_text="3PM Close")
    
    
    
    
        # Draw horizontal lines as line segments only between 3PM last day and 3PM next day
    
        
        fig.update_layout(title="Nifty 15-min candles - Last Day & Today", xaxis_rangeslider_visible=False)
        fig.update_layout(
        xaxis=dict(
            rangebreaks=[
                # Hide weekends (Saturday and Sunday)
                dict(bounds=["sat", "mon"]),
                # Hide hours outside of trading hours (NSE trading hours 9:15 to 15:30)
                dict(bounds=[15.5, 9.25], pattern="hour"),
            ]
        )
    )
    
    
        st.plotly_chart(fig, use_container_width=True)     



#------------------------------------------------------------------------------------------------

elif MENU == "Test1":
    st.title("Live Trade Test1")
    if "kite" not in st.session_state:
        st.session_state.kite = None
    else:
        kite = st.session_state.get("kite")


    load_dotenv()
    
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    st.write(TELEGRAM_BOT_TOKEN)
    st.write(TELEGRAM_CHAT_ID)  

    #NIFTY_SYMBOL="NIFTY25D0926200CE"
    # ---------- helper: get underlying spot ----------
    def get_nifty_spot():
        #NIFTY_SYMBOL="NIFTY25D0926200CE"
        NIFTY_SYMBOL="NIFTY 50"
        quote = kite.ltp(f"NSE:{NIFTY_SYMBOL}")
        return quote[f"NSE:{NIFTY_SYMBOL}"]["last_price"]
    
    # ---------- helper: get option quote ----------
    def get_option_ltp(tradingsymbol):
        EXCHANGE = "NFO"
        q = kite.ltp(f"{EXCHANGE}:{tradingsymbol}")
        return q[f"{EXCHANGE}:{tradingsymbol}"]["last_price"]
    
    # ---------- helper: days to expiry ----------
    def days_to_expiry0(expiry_str):
        # expiry_str like '2025-12-25'
        expiry = parser.parse(expiry_str).date()
        today = datetime.now().date()
        return max((expiry - today).days, 0)

    def days_to_expiry11(expiry):
        """
        expiry: datetime.datetime object
        returns number of days until expiry (integer)
        """
        today = date.today()
        expiry_date = expiry.date() if isinstance(expiry, datetime) else expiry
        return max((expiry_date - today).days, 0)
    
    # ---------- compute current IV ----------
    def compute_current_iv_1(underlying_price, option_price, strike, expiry_str, option_type):
        """
        option_type: 'c' for CE, 'p' for PE (py_vollib convention)
        """
        T_days = days_to_expiry(expiry_str)
        if T_days == 0:
            return np.nan
        T = T_days / 365.0
    
        try:
            iv = implied_volatility(
                option_price,
                underlying_price,
                strike,
                T,
                R,
                option_type
            )
            return iv * 100.0  # convert to %
        except Exception:
            return np.nan
    
    # ---------- fetch 1-year IV history ----------
    def get_iv_history_for_option(tradingsymbol, strike, expiry_str, option_type):
        """
        Simple approximation: use daily option close + underlying close
        to recompute IV for each day with py_vollib.
        """
    
        # 1 year back
        to_date = datetime.now()
        from_date = to_date - timedelta(days=365)
    
        # Zerodha historical data for the option
        EXCHANGE="NFO"
        hist_opt = kite.historical_data(
            instrument_token=kite.ltp(f"{EXCHANGE}:{tradingsymbol}")[f"{EXCHANGE}:{tradingsymbol}"]["instrument_token"],
            from_date=from_date,
            to_date=to_date,
            interval="day",
            continuous=False,
            oi=True
        )
        opt_df = pd.DataFrame(hist_opt)
        if opt_df.empty:
            return pd.Series(dtype=float)
    
        # Historical NIFTY data (spot) – using index token via Kite
        NIFTY_SYMBOL="NIFTY 50"
        nifty_token = kite.ltp(f"NSE:{NIFTY_SYMBOL}")[f"NSE:{NIFTY_SYMBOL}"]["instrument_token"]
        hist_nifty = kite.historical_data(
            instrument_token=nifty_token,
            from_date=from_date,
            to_date=to_date,
            interval="day",
            continuous=False,
            oi=False
        )
        spot_df = pd.DataFrame(hist_nifty)
    
        # Merge by date
        opt_df["date"] = opt_df["date"].dt.date
        spot_df["date"] = spot_df["date"].dt.date
        df = pd.merge(opt_df[["date", "close"]], spot_df[["date", "close"]], on="date", suffixes=("_opt", "_spot"))
    
        iv_list = []
        for _, row in df.iterrows():
            # for history, use remaining days as if expiry is fixed
            T_days = (parser.parse(expiry_str).date() - row["date"]).days
            if T_days <= 0:
                iv_list.append(np.nan)
                continue
            T = T_days / 365.0
    
            try:
                iv = implied_volatility(
                    row["close_opt"],      # option close
                    row["close_spot"],     # spot close
                    strike,
                    T,
                    R,
                    option_type
                )
                iv_list.append(iv * 100.0)
            except Exception:
                iv_list.append(np.nan)
    
        df["iv"] = iv_list
        df = df.dropna(subset=["iv"])
        return df["iv"]
    
    # ---------- compute IV Rank ----------
   
    
   
        
        

elif MENU == "Setting":
    st.title("Live Trade Setting")
    # -----------------------------------------------------------
    # AVAILABLE FUNDS + DIY SETTINGS
    # -----------------------------------------------------------
    if st.session_state.api_status.get("Zerodha"):
            kite = st.session_state.kite 
    st.markdown("### 💰 Available Funds")
    
    try:
        funds = kite.margins()["equity"]["available"]["cash"]
        st.metric("Available Cash", f"₹{funds:,.0f}")
    except:
        st.error("Unable to fetch funds.")
    
    # ---------------- SAFE DIY SETTINGS BLOCK ----------------
    st.markdown("### ⚙️ DIY Trading Settings")

    colA, colB = st.columns(2)
    
    with colA:
        risk_per_trade = st.number_input(
            "Risk % Per Trade",
            min_value=1.0,
            max_value=10.0,
            value=st.session_state.get("diy_settings", {}).get("risk_per_trade", 2.0),
            step=0.5,
            format="%.2f"
        )
    
    with colB:
        max_trades = st.number_input(
            "Max Trades Per Day",
            min_value=1,
            max_value=20,
            value=st.session_state.get("diy_settings", {}).get("max_trades", 5)
        )
    
    # ---- MANUAL LOT SIZE (SAFE DEFAULT) ----
    st.markdown("### ✋ Manual Lot Size")
    
    saved_lot = st.session_state.get("diy_settings", {}).get("lot_size", 1)
    
    # ensure valid default
    if saved_lot is None or saved_lot < 1:
        saved_lot = 1
    
    manual_lot_size = st.number_input(
        "Lot Size (1–100)",
        min_value=1,
        max_value=100,
        value=saved_lot,
        step=1
    )

    st.metric("Final Lot Size Used", manual_lot_size)
    
    # Save settings
    st.session_state["diy_settings"] = {
        "risk_per_trade": float(risk_per_trade),
        "max_trades": int(max_trades),
        "lot_size": int(manual_lot_size)
    }

#========================================================================================================
elif MENU =="LIVE TRADE 3":
    with st.sidebar:
         if st.button("🧹 Clear Paper Trades"):
             st.session_state.paper_trades = []
             st.success("All paper trades cleared")
             st.rerun()
 
    #st.title("🔴 LIVE TRADE 3")
    #st.title("🔴 Live Nifty 15-Minute Chart + Signal Engine")
    with st.expander("📘 Base Zone Multi-Condition Options Strategy (Click to Expand)"):
         st.markdown("""
     ### 🔷 What this strategy does
     This is a **rule-based NIFTY options strategy** that uses:
     - Previous day **3:00 PM candle**
     - Current day **9:15–9:30 range**
     - **Price behavior after market open**
     
     It detects whether the market is:
     - Trending bullish
     - Trending bearish
     - Or reversing after a gap
     
     and trades accordingly.
     
     ---
     
     ## 🧱 1️⃣ Base Zone (Previous Day)
     From **yesterday’s 3:00 PM candle**:
     - `Base High` = max(Open, Close)
     - `Base Low` = min(Open, Close)
     
     This zone represents **institutional positioning**.
     
     ---
     
     ## ⏰ 2️⃣ Today’s First 15-Minute Range (9:15 – 9:30)
     From today’s **9:30 candle**:
     - `H1` = High
     - `L1` = Low
     - `C1` = Close
     
     This tells us how price reacts to the Base Zone.
     
     ---
     
     ## 📈 3️⃣ Trading Conditions
     
     ### 🔹 Condition 1 – Normal Breakout
     If price opens inside Base Zone and  
     **closes above Base High → Buy CALL**
     
     ---
     
     ### 🔹 Condition 2 – Gap Down
     If market opens **below Base Low**
     - Break below L1 → Buy PUT  
     - If price later recovers above Base High → Flip to CALL
     
     ---
     
     ### 🔹 Condition 3 – Gap Up
     If market opens **above Base High**
     - Break above H1 → Buy CALL  
     - If price later falls below Base Low → Flip to PUT
     
     ---
     
     ### 🔹 Condition 4 – Breakdown
     If market opens inside Base Zone and  
     **closes below Base Low → Buy PUT**
     
     ---
     
     ## 🛑 4️⃣ Smart Stop Loss (Swing Based)
     Stop loss is not fixed.
     
     It uses:
     > **Last 10 candles swing high & swing low**
     
     • CALL → Stoploss = recent swing low  
     • PUT → Stoploss = recent swing high  
     
     And it **trails automatically** as price moves.
     
     ---
     
     ## ⏳ 5️⃣ Time Exit
     If neither stoploss nor trailing SL hits:
     > Exit automatically after **16 minutes**
     
     This avoids chop and theta decay.
     
     ---
     
     ## 💰 6️⃣ What P&L Is Based On
     Your function uses: 
     These are **NIFTY spot prices**.

     Option P&L is **mapped from spot movement**.
     
     ---
     
     ## 🧠 7️⃣ Why This Works
     This captures:
     - Gap traps
     - Institutional breakout
     - Trend continuation
     - Smart trailing exits
     
     It avoids:
     - Random trades
     - Over-trading
     - Long holding during chop
     
     ---
     
     ### ✅ In simple words:
     > This is a **professional gap-and-base breakout strategy** with **dynamic trailing SL and time-based exits** — built for intraday NIFTY options trading.
     """)
    
    # STEP 1: Check kite object existence
    kite = st.session_state.get("kite")
     
    if kite is None:
         st.warning("Please login to access Algo Trading.")
         st.stop()
     
     # STEP 2: Check kite session validity
    if not is_kite_connected(kite):
         st.warning("Kite session not active. Please login again.")
         st.stop()
     
     # ✅ SAFE TO CONTINUE LIVE TRADING BELOW


     # --- --------------------------------------------------------------------------------        
    # --- HARD BLOCK: Do not trade if position already exists ---
    #if has_open_position(kite):
         #st.info("Open position exists → New signal ignored")
         #return
    #else:
         #st.info("Not Open  position exists →")
      # --- --------------------------------------------------------------------------------    
    #st.success("You are logged in.")
     
    st.session_state.param_rows = []
    from streamlit_autorefresh import st_autorefresh
    import time             # Python's time module
    from datetime import time  # datetime.time (conflict!)
    # Initialize Kite in session_state
    if "kite" not in st.session_state:
        st.session_state.kite = None
    else:
        kite = st.session_state.get("kite")
    # --- SESSION STATE INIT ---
    if "order_executed" not in st.session_state:
        st.session_state.order_executed = False
        
    
    if "signal_time" not in st.session_state:
        st.session_state.signal_time = None
    # Add after data processing:
    def is_kite_connected(kite):
        try:
            kite.profile()
            return True
        except:
            return False

    
    st.set_page_config(layout="wide")
    # Place at the very top of your script (or just before plotting)
    #st_autorefresh(interval=60000, limit=None, key="refresh")
    # Current time in IST
    #----------------------------------------------------------------------
    #if is_kite_connected(kite):
    funds = get_fund_status(kite)
    #st.write(funds) 
    cash = (funds['cash'])
    cash = (funds['net']) 
    #iv_value = 0.26
    result = "Fail" if 75000 <= cash <= 25000 else "Pass"
    add_param_row("CASH", cash, "25K - 100K", result)
    st.session_state.capital=cash

    #---------------------------------------------------------------------
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    
    # Market hours condition
    start = time(9, 30)   # 9:30 AM
    end = time(15, 25)    # 3:25 PM
    
    # Refresh only between 9:30–3:25
    if start <= now <= end:
        #st_autorefresh(interval=60000, key="refresh")  # 1 minute refresh
        st_autorefresh(interval=60000, key="refresh_live3")
    #else:
        #st.info("Auto-refresh is paused — Outside market hours (9:30 AM to 3:25 PM).")

    #st.title("Nifty 15-min Chart")
    
    # Select date input (default today)
    selected_date = st.date_input("Select date", value=datetime.today())
    
    # Calculate date range to download (7 days before selected_date to day after selected_date)
    start_date = selected_date - timedelta(days=7)
    end_date = selected_date + timedelta(days=1)
    
    # Download data for ^NSEI from start_date to end_date
    df = yf.download("^NSEI", start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="15m")
    
    if df.empty:
        st.warning("No data downloaded for the selected range.")
        st.stop()
    df.reset_index(inplace=True)
    
    if 'Datetime_' in df.columns:
        df.rename(columns={'Datetime_': 'Datetime'}, inplace=True)
    elif 'Date' in df.columns:
        df.rename(columns={'Date': 'Datetime'}, inplace=True)
    # Add any other detected name if needed
    
    
    #st.write(df.columns)
    #st.write(df.head(10))
    # Flatten columns if MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
    
    # Rename datetime column if needed
    if 'Datetime' not in df.columns and 'datetime' in df.columns:
        df.rename(columns={'datetime': 'Datetime'}, inplace=True)
    #st.write(df.columns)
    #st.write(df.columns)
    # Convert to datetime & timezone aware
    #df['Datetime'] = pd.to_datetime(df['Datetime'])
    if df['Datetime_'].dt.tz is None:
        df['Datetime'] = df['Datetime_'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    else:
        df['Datetime'] = df['Datetime_'].dt.tz_convert('Asia/Kolkata')
    
    #st.write(df.columns)
    #st.write(df.head(10))
    
    # Filter for last two trading days to plot
    unique_days = df['Datetime'].dt.date.unique()
    if len(unique_days) < 2:
        st.warning("Not enough data for two trading days")
    else:
        last_day = unique_days[-2]
        today = unique_days[-1]
    
        df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
    
        # Get last day 3PM candle open and close
        candle_3pm = df_plot[(df_plot['Datetime'].dt.date == last_day) &
                             (df_plot['Datetime'].dt.hour == 15) &
                             (df_plot['Datetime'].dt.minute == 0)]
    
        if not candle_3pm.empty:
            open_3pm = candle_3pm.iloc[0]['Open_^NSEI']
            close_3pm = candle_3pm.iloc[0]['Close_^NSEI']
        else:
            open_3pm = None
            close_3pm = None
            st.warning("No 3:00 PM candle found for last trading day.")
        #-----------------------------Marking 9.15 Candle---------------------------------
        # Get today's 9:15 AM candle
        candle_915 = df_plot[(df_plot['Datetime'].dt.date == today) &
                          (df_plot['Datetime'].dt.hour == 9) &
                          (df_plot['Datetime'].dt.minute == 15)]
     
        if not candle_915.empty:
              o_915 = candle_915.iloc[0]['Open_^NSEI']
              h_915 = candle_915.iloc[0]['High_^NSEI']
              l_915 = candle_915.iloc[0]['Low_^NSEI']
              c_915 = candle_915.iloc[0]['Close_^NSEI']
              t_915 = candle_915.iloc[0]['Datetime']
        else:
              o_915 = h_915 = l_915 = c_915 = t_915 = None
              st.warning("No 9:15 AM candle found for today.")    
         
         #---------------------------------------------------------------------------------
    
         
    
        # Plot candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=df_plot['Datetime'],
            open=df_plot['Open_^NSEI'],
            high=df_plot['High_^NSEI'],
            low=df_plot['Low_^NSEI'],
            close=df_plot['Close_^NSEI']
        )])
        if t_915 is not None:
              fig.add_vrect(
                  x0=t_915,
                  x1=t_915 + pd.Timedelta(minutes=15),
                  fillcolor="orange",
                  opacity=0.25,
                  layer="below",
                  line_width=0,
                  annotation_text="9:15 Candle",
                  annotation_position="top left"
              )
        
        

        if o_915 is not None and c_915 is not None:
              fig.add_hline(y=o_915, line_dash="solid", line_color="green",
                            annotation_text="9:15 Open")
              fig.add_hline(y=c_915, line_dash="solid", line_color="orange",
                            annotation_text="9:15 Close") 
        if open_3pm and close_3pm:
            fig.add_hline(y=open_3pm, line_dash="dot", line_color="blue", annotation_text="3PM Open")
            fig.add_hline(y=close_3pm, line_dash="dot", line_color="red", annotation_text="3PM Close")
    
    
    
    
        # Draw horizontal lines as line segments only between 3PM last day and 3PM next day
    
        
        fig.update_layout(title="Nifty 15-min candles - Last Day & Today", xaxis_rangeslider_visible=False)
        fig.update_layout(
        xaxis=dict(
            rangebreaks=[
                # Hide weekends (Saturday and Sunday)
                dict(bounds=["sat", "mon"]),
                # Hide hours outside of trading hours (NSE trading hours 9:15 to 15:30)
                dict(bounds=[15.5, 9.25], pattern="hour"),
            ]
        )
    )
        chart_slot = st.empty() 
        import time
        if "last_chart_refresh" not in st.session_state:
              st.session_state.last_chart_refresh = 0
        now = time.time()

        if now - st.session_state.last_chart_refresh >= 1:
              with chart_slot:
                  st.plotly_chart(fig, use_container_width=True)
          
              st.session_state.last_chart_refresh = now 
        #st.plotly_chart(fig, use_container_width=True)
        #----------------------------------------------------------------------
        df_plot1 = df[df['Datetime'].dt.date.isin([last_day, today])]
        #signal = trading_signal_all_conditions(df_plot)
         #trading_multi2_signal_all_conditions_5min
        #================================================5min DTAT=====================================================
        # 1️⃣ Download 5m data
        #df = yf.download("^NSEI", start=..., end=..., interval="5m")
        df = yf.download("^NSEI", start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="5m")
         
        # ---- ENSURE NSEI COLUMN NAMES ----
        required_cols = ["Open_^NSEI", "High_^NSEI", "Low_^NSEI", "Close_^NSEI"]
          
        if not all(col in df.columns for col in required_cols):
              df.rename(columns={
                  "Open": "Open_^NSEI",
                  "High": "High_^NSEI",
                  "Low": "Low_^NSEI",
                  "Close": "Close_^NSEI",
              }, inplace=True)

        
          
          # 3️⃣ Timezone fix
        df.reset_index(inplace=True)
        #df["Datetime"] = df["Datetime"].dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
        if df["Datetime"].dt.tz is None:
              df["Datetime"] = df["Datetime"].dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
        else:
              df["Datetime"] = df["Datetime"].dt.tz_convert("Asia/Kolkata")
        # ===== FORCE FLATTEN MULTIINDEX COLUMNS =====
        if isinstance(df.columns, pd.MultiIndex):
              df.columns = [
                  col[0] if col[0] != "Volume" else "Volume"
                  for col in df.columns
              ]

          # 4️⃣ Filter last 2 days
        df_plot = df[df["Datetime"].dt.date.isin([last_day, today])]
        #st.write("COLUMNS:", df_plot.columns)
        df_plot = normalize_nsei_columns(df_plot)

        #st.write("CLEAN COLUMNS:", df_plot.columns.tolist())
         
        #st.write("15 MIn Data")
        #st.write(df_plot1)
         
          # 5️⃣ Call strategy  
        #==================================================================================================== 
        #signal = trading_signal_all_conditions_final(df_plot) 
        #signal = trading_multi2_signal_all_conditions_5min(df_plot)  
        #signal = trading_multi2_signal_all_conditions_5min(df_plot1)   
        #signal = trading_multi1_signal_all_conditions(df_plot1)
        #signal = trading_multi2_signal_all_conditions(df_plot1)  
         
        #
        signal =trading_signal_all_conditions_final(df_plot1) 
         
        #signal =trading_signal_all_conditions_new(df_plot1)  
         
        #signal =trading_multi2_signal_all_conditions(df_plot1)  

        #signal =trading_multi1_signal_all_conditions (df_plot1)  
         
        #st.write("DEBUG signal:", signal)
        #st.write("Type:", type(signal))

        if signal and isinstance(signal, list):
              last_signal = signal[-1]
              st.success(f"✅ SIGNAL GENERATED: {last_signal['message']}")
 
        if signal is None:
            st.warning("⚠ No signal yet (conditions not met).")
        else:
            #st.success(f"✅ SIGNAL GENERATED: {signal['message']}")
            last_signal = signal[-1]  
            #df_sig1 = pd.DataFrame([signal])
            df_sig1 = pd.DataFrame(signal)  
            signal_time = df_plot["Datetime"].iloc[-1]   # last candle timestamp
            last_signal["signal_time"] = signal_time
            signal_time1=last_signal["signal_time"] 
            S=last_signal["buy_price"]              
            signal_entry_time=last_signal["entry_time"] 
                
                # Display as table
            #st.table(df_sig1) 
            #st.write(df_sig1) 
            colA, colB = st.columns(2)
            st.divider()
            with colA:
                 
                 st.subheader("📊 Signal Log")
                 #st.write(df_sig1) 
                 #st.dataframe(df_sig1, use_container_width=True, hide_index=True)
                 cols = ["option_type", "buy_price", "entry_time"]
                 st.dataframe(
                        df_sig1[cols],
                        use_container_width=True,
                        hide_index=True
                    )
                                
#======================================================================================================================


            
#========================================================================================================================             

             
            entry_time = last_signal['entry_time']
            #st.write("entry_time",entry_time) 
            #st.write("Signal Time only:", entry_time.strftime("%H:%M:%S"))  # HH:MM:SS
            signal_time=entry_time.strftime("%H:%M:%S")
            #st.write("Signal Time only:-", signal_time)  # HH:MM:SS
            #            st.write(signal)
#--------------------------------------------------------------------------------

        def generate_signals_stepwise(df):
            all_signals = []
            
            # We run strategy for each candle progressively
            for i in range(40, len(df)):   # start after enough candles
                sub_df = df.iloc[:i].copy()
                sig = trading_multi2_signal_all_conditions_5min(sub_df)
                if sig is not None:
                    all_signals.append((sub_df.iloc[-1]["Datetime"], sig))
        
            return all_signals
#-------------------------------------Total signals-------------------------------------------

        step_signals = generate_signals_stepwise(df_plot)
        if step_signals:
                #st.info(f"Total signals detected so far: {len(step_signals)}")
            
                latest_time, latest_sig = step_signals[-1]
                
                st.success(f"🟢 Latest Candle Signal ({latest_time}):")
                #st.write(latest_sig)
                # Convert to DataFrame
                df_sig = pd.DataFrame([latest_sig])
                
                # Display as table
                #st.table(df_sig)
        else:
                st.warning("No signal triggered in any candle yet.")
   

#-----------------------------------Nearest ITM Option ---------------------------------------------

        if signal is not None:
            #signal_time = df["Datetime"].iloc[-1].time()   # last candle time
            option_type = last_signal["option_type"]     # CALL / PUT
            #st.write("Option type ",option_type)
            spot = last_signal["buy_price"]
            #st.write("Option spot ",spot)
            try:
                nearest_itm = find_nearest_itm_option(kite, spot, option_type)
                nearest_itm1 = pd.DataFrame([nearest_itm]) 
                with colB:
                     st.subheader("📊 Option Log")
                     st.table(nearest_itm1)
                     #st.write(df[["tradingsymbol", "ltp", "expiry", "spot", "strike"]])

                #S=nearest_itm1["ltp"]
                K=nearest_itm1["strike"] 
                #st.write("S, K=",S,K)  
                # Display as table
                st.table(nearest_itm1)
                #trending_symbol=nearest_itm1["tradingsymbol"]
                trending_symbol = nearest_itm1["tradingsymbol"].iloc[0]
 
                #st.write("tradingsymbol-",trending_symbol)
             #====================================================FLAG SIGNAL================================
                st.session_state.trade_status = "SIGNAL"
                st.session_state.signal_time = signal_time
                st.session_state.signal_price = nearest_itm['ltp']   # LTP at signal candle
                st.session_state.symbol = trending_symbol 
                st.session_state.expiry = nearest_itm['expiry']
             #==================================================================================================
        
            except Exception as e:
                st.error(f"Failed to fetch option: {e}")

    
#######################---------------------IV-NEW !-------------------------------------------------
            #st.write("trending_symbol ",trending_symbol) 
             
            option_dict = get_live_option_details(kite, trending_symbol)
            if option_dict is None:
                   st.info("Running in safe mode. Live data access is unavailable.")
                   st.stop() #return  # or st.stop()
                
           # st.write(option_dict) 
            #spot_price=26046.00 
            spot_price=option_dict.get("strike") 
            ltp = option_dict.get("ltp")
            #S=ltp
            #K=spot_price 
            
            strike = option_dict.get("strike")
            #expiry = option_dict.get("expiry")
            is_call = option_dict.get("option_type") == "CALL"
            #st.write("ltp ", st.session_state.expiry)  
          #------------------------------------------PAPER TRADE-------------------------------------------------
            if signal is not None:

              signal_time = last_signal["signal_time"]
          
              # 🔒 ENTRY LOCK — THIS PREVENTS RE-ENTRY ON REFRESH
              if st.session_state.last_executed_signal_time == signal_time:
                  pass  # already traded this signal
                  st.write("st.session_state.last_executed_signal_time=",st.session_state.last_executed_signal_time)
                  st.write("System generated last_executed Signal time=",signal_time)
              else:
                  option_type = last_signal["option_type"]
                  spot = last_signal["buy_price"]
          
                  nearest_itm = find_nearest_itm_option(kite, spot, option_type)
                  trending_symbol = nearest_itm["tradingsymbol"]
                  option_symbol = f"NFO:{trending_symbol}"
          
                  entry_price = kite.ltp(option_symbol)[option_symbol]["last_price"]
                  ist = pytz.timezone("Asia/Kolkata")
                  now = datetime.now(ist)  
                  entry_time1=last_signal["entry_time"]
                  diff_minutes = (now - signal_time1).total_seconds() / 60
                  st.write("diff_minutes==",diff_minutes) 
                  if diff_minutes < 2: 
                           st.session_state.symbol_entry_ltp=entry_price
                  trade = {
                        "signal_time": signal_time,
                        "entry_time": pd.Timestamp.now(),
                        "symbol": trending_symbol,
                        "option_type": option_type,
                        "entry_price": entry_price,
                        "quantity": 65,
                        "remaining_qty": 65,
                        "highest_price": entry_price,
                        "partial_exit_done": False,
                        "final_exit_done": False,
                        "status": "OPEN"
                    }
          
                  st.session_state.paper_trades.append(trade)
          
                  # 🔐 LOCK THE SIGNAL
                  
                  #st.success(f"Paper trade entered @ {entry_price}")

            #monitor_paper_trades(kite)
            #for trade in st.session_state.paper_trades:
              #normalize_trade(trade)
              #manage_exit_papertrade(kite, trade)
            option_symbol=trending_symbol
            option_type = last_signal["option_type"]
            spot = last_signal["buy_price"] 
             
            expiry =st.session_state.expiry
            st.write("Moniter")
            st.write("Expiry",expiry) 
          #---------------------------------------PAPER TRADE----------------------------------------------------   
              # Compute time to expiry (in years)
            days_to_exp = days_to_expiry(expiry)
            time_to_expiry = days_to_exp / 365 
            r=0.07
            
             

#-----------------------------------IV Compute---------------------------------------------

#----------------------------------IV----------------------------------------------

    
#-----------------------Add PARA----------------------------------------------
  
#--------------------------------------------------Getting New IV-----------& adding to para----------------------------
            #result = compute_option_iv_details(option, spot)
     
            #st.write(result)  
            #
            #option = get_live_option_details(kite, trending_symbol)
     
            #st.write("option",option)
            #st.write("nearest_itm option",nearest_itm)
            spot=ltp
            #spot = option["last_price"]
            #st.write("Spot",spot) 
            #spot = 25900.00  # live NIFTY spot
            #st.write("nearest_itm",nearest_itm)
            #st.write("spot",spot) 
            result = compute_option_iv_details(nearest_itm, spot)
            #st.write("Result IV new",result) 
            new_iv_result= result["iv"]
            #st.session_state.GREEKtheta=new_iv_result 
            st.session_state.option_iv=new_iv_result 
            iv_result=new_iv_result 
            #st.write("new_iv_result",new_iv_result) 
            result = "Pass" if 0.10 <= new_iv_result <= 0.35 else "Fail" 
            add_param_row("IV ", round(new_iv_result, 2), "0.10 - 0.35", result) 
#-------------------------------------------------------------------------
           
        

#--------------------------------VIX------------------------------------------------
         #vix_now =fetch_vix_from_fyers()
         
            vix_now = fetch_india_vix_kite(kite)
         #st.write("India VIX: kite", vix_now)
         #st.write("India VIX:", vix_now)
 #-----------------------Add PARA----------------------------------------------
    # VIX
            result = "Pass" if vix_now > 10 else "Fail"
            vix_result  = result     
            add_param_row("VIX", round(vix_now, 2), " > 10", result)

 #------------------------------------------------------------------------------   
 
    #---------------------------------tIME-----------------------------------------------
            import pytz
            
    # IST timezone
            ist = pytz.timezone("Asia/Kolkata")
            now_dt = datetime.now(ist)     # full datetime object
            now = now_dt.time()            # extract time only for comparisons

            tz = pytz.timezone("Asia/Kolkata")
            now = datetime.now(tz)
     #----------------------------------FUND-----------------------------------------------------
            #st.divider()

            funds = get_fund_status(kite)

            #st.subheader("💰 Zerodha Fund Status")
    
            if "error" in funds:
                st.error(funds["error"])
            else:
                  #st.write(f"**Net Balance:** ₹{funds['net']}")
                  #st.write(f"**Cash:** ₹{funds['cash']}")
                  #st.write(f"**Opening Balance:** ₹{funds['opening_balance']}")
                  #st.write(f"**Collateral:** ₹{funds['collateral']}")
                  #st.write(f"**Option Premium Used:** ₹{funds['option_premium']}")
                  #cash_balance = 73500
                  lots = get_lot_size(funds['cash'])
                  #st.write("Lot Size:", lots)
                  #lot_qty=65*lots
                  #st.divider()

   
    
    #------------------------------------PLACING ORDERS--------------------------------------------
             #st.write(f"Placing order for:", trending_symbol)
            #if "position_size" not in st.session_state:
            position_size= st.session_state.position_size
            if(position_size=='none'):
                  position_size=1;
        #st.write(f"Quantity: {qty}, LTP: {ltp}")
        #st.write(f"Quantity  order for:", qty)        
        #if st.button("🚀 PLACE BUY ORDER IN ZERODHA"):
        # Condition 1: Current time >= signal candle time
        # Trading window
            start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
            end_time   = now.replace(hour=14, minute=30, second=0, microsecond=0)
    #st.write("start_time", start_time)
    #st.write("end_time", end_time)
    #st.write("Now Time", now)
    #st.write("signal_time",signal_time)
    
    
    #-------------------------------------------------------------------------------

        # Convert to Python datetime (with timezone if needed)
            signal_time = pd.to_datetime(signal_time).to_pydatetime()
   
    # Optional: ensure same timezone as now
    #import pytz
            tz = pytz.timezone("Asia/Kolkata")
            signal_time = signal_time.replace(tzinfo=tz)
    #    st.write("signal_time",signal_time)
    #st.write("Now Time", now)
    #--------------------------------------------------------------------------------
     #-----------------------Add PARA----------------------------------------------
    # Define IST timezone
            ist = pytz.timezone("Asia/Kolkata")
    
    # Convert signal_time to IST
            signal_time_ist = signal_time.astimezone(ist)
            import datetime as dt

            start = dt.time(9, 30)
            end   = dt.time(14, 30)
    
            sig_t = signal_time_ist.time()
    
            result = "Pass" if start <= sig_t <= end else "Fail"
    
            add_param_row("Signal Time", str(signal_time_ist.time()),"09:30 - 14:30",result)
     #------------------------------------ADD PCR------------------------------------------ 
            pcr_value = get_nifty_pcr(kite)
            result = "Pass" if 0.80 <= pcr_value <= 1.30 else "Fail"
            pcr_result= result
            add_param_row("PCR", round(pcr_value, 2), "0.80 - 1.30", result)

#-------------------------------------lot ty------------------------------------------------

             # Apply rule
            if new_iv_result == "Fail" : #or iv_rank_result == "Fail":
                   lot_qty = 2
            if new_iv_result == "Pass"  and vix_result=="pass" and pcr_result=="pass":
                   lot_qty = 6    
            if vix_now < 10 :
                   lot_qty = 1 
            if 10< vix_now < 15 :
                   lot_qty = 2
            if 15< vix_now < 20 :
                   lot_qty = 4
            if vix_now > 20 :
                   lot_qty = 1 
                 
            add_param_row("LOT QTY", lot_qty, "0,1,2,4,6", "OK") 
    
     #-----------------------------------------Display PARA-------------------------------------------
            if st.session_state.param_rows:
                df = pd.DataFrame(st.session_state.param_rows)
            
                col1, col2, col3 = st.columns(3)
            
                # ---------------- COL 1 ----------------
                with col1:
                    st.subheader("🚦 Parameters")
                    st.table(df)
            
                # ---------------- COL 2 ----------------
                with col2:
                    days_to_exp = days_to_expiry(expiry)
                    time_to_expiry = days_to_exp / 365
                    r = 0.07
            
                    iv = new_iv_result
                    st.subheader("🧮 Greeks Values")
            
                    T = time_to_expiry
                    sigma = iv
            
                    st.session_state.S = S
                    st.session_state.K = K
                    st.session_state.T = T
                    st.session_state.r = r
                    st.session_state.sigma = sigma
            
                    if isinstance(expiry, str):
                        expiry_dt = datetime.strptime(expiry, "%Y-%m-%d").replace(hour=15, minute=30)
                    elif isinstance(expiry, (datetime, pd.Timestamp)):
                        expiry_dt = expiry.to_pydatetime().replace(hour=15, minute=30)
                    else:
                        st.write("DEBUG expiry value:", expiry)
                        st.write("DEBUG expiry type:", type(expiry))
                        st.stop()
            
                    K = float(K)
            
                    greeks = safe_option_greeks(
                        S, K, expiry_dt, r, sigma, option_type="CALL"
                    )
            
                    greeks_param_df = pd.DataFrame([
                        {
                            "Parameter": "NIFTY OPTION",
                            "Value": trending_symbol,
                            "Range": expiry,
                            "Result": "Valid"
                        },
                        {
                            "Parameter": "Delta",
                            "Value": greeks["Delta"],
                            "Range": "0.30 – 0.85",
                            "Result": evaluate(greeks["Delta"], 0.30, 0.85)
                        },
                        {
                            "Parameter": "Gamma",
                            "Value": greeks["Gamma"],
                            "Range": "≥ 0.0005",
                            "Result": evaluate(greeks["Gamma"], 0.0005, None)
                        },
                        {
                            "Parameter": "Theta",
                            "Value": greeks["Theta"],
                            "Range": "≥ -80",
                            "Result": evaluate(greeks["Theta"], -80, None)
                        },
                        {
                            "Parameter": "Vega",
                            "Value": greeks["Vega"],
                            "Range": "≥ 3.0",
                            "Result": evaluate(greeks["Vega"], 3.0, None)
                        },
                        {
                            "Parameter": "IV %",
                            "Value": greeks["IV%"],
                            "Range": "0.10 – 0.35",
                            "Result": evaluate(greeks["IV%"], 0.10, 0.35)
                        }
                    ])
            
                    st.session_state.GREEKdelta = greeks["Delta"]
                    st.session_state.GREEKgamma = greeks["Gamma"]
                    st.session_state.GREEKtheta = greeks["Theta"]
                    st.session_state.GREEKvega = greeks["Vega"]
            
                    st.dataframe(
                        greeks_param_df.style.applymap(
                            lambda x: "color: green; font-weight: bold"
                            if x == "Pass"
                            else "color: red; font-weight: bold"
                            if x == "Fail"
                            else ""
                        ),
                        use_container_width=True,
                        hide_index=True
                    )
            
                # ---------------- COL 3 ----------------
                with col3:
                    st.subheader("✅ Trade Validation")
                    qty = get_lot_qty(new_iv_result, vix_now, vix_result, pcr_result)
                    qty = qty * QTY_PER_LOT
                    strike = spot
            
                    qty=trade_validation(
                        kite,
                        trending_symbol,
                        qty,
                        entry_price,
                        strike,
                        expiry,
                        option_type="CALL"
                    )
            
            else:
                st.write("No parameters added yet.")
                        
            

                   
    #------------------------------------------------------------------------------------------------
            #
            #qty=65*lot_qty
             
            #qty=0
            
            #st.subheader("Session State Debug")
            #st.write(st.session_state)
            #st.subheader("Session State (Detailed)")
            #for key, value in st.session_state.items():
                #st.write(f"{key} :", value)

            #st.subheader("Trade State")
            keys_to_show = [
                   "trade_status",
                   "signal_time",
                   "signal_price",
                   "entry_time",
                   "exit_time",
                   "order_id",
                   "symbol"
               ]
               
            #for k in keys_to_show:
                   #if k in st.session_state:
                       #st.write(f"{k} :", st.session_state[k])

 
           
                # Check 1: Only run if current time is within trading window
            st.write("entry_time",entry_time) 
            if is_valid_signal_time(entry_time):
                 st.warning("Signal time  match today's date .") 
                 if start_time <= now <= end_time:
                 
                 # Check 2: Signal time reached
                    #if now >= entry_time:
                    last_signal_price=st.session_state.signal_price  
                    last_executed_signal_time=st.session_state.last_executed_signal_time  
                      
                    st.write("Signal Price= ", last_signal_price )  
                    currnt_price=get_option_ltp(trending_symbol)  
                    st.write("Current Price =",currnt_price)  

                    lower = last_signal_price * 0.97
                    upper = last_signal_price * 1.03
                    
                                   
                    price_diff_pct = abs(currnt_price - last_signal_price) / last_signal_price * 100 
                    st.write("Current Price Difference=",price_diff_pct) 
                    st.write("Current TIIME=",now)
                    st.write("Signal TIIME=",signal_entry_time)  
                    diff_minutes = (now - signal_time).total_seconds() / 60
                    st.write("diff_minutes=",diff_minutes)    
                    MAX_DELAY_MINUTES = 5   # or 10 if you want

                    
                        #return None   # ❌ DO NOT PLACE ORDER  
                                          
                    if (lower <= currnt_price <= upper):
                        st.warning("Price within  ±3% execution range")
                        st.write("Allowed:", lower, "to", upper)
                        st.write("Current:", currnt_price)   
                    #if abs((now - entry_time).total_seconds()) < 60:  
                        st.info("Execution window In .") 
                        st.write("entry_time-",last_executed_signal_time)
                        st.write("Now Time-", now)
                        st.write("Qty*LOT=", qty) 
                    if diff_minutes > MAX_DELAY_MINUTES:
                        st.warning(
                            f"⏰ Old Signal Skipped | Signal Age: {diff_minutes:.1f} min"
                        )
                        st.stop()     
                      # Check 3: Order placed only once
                        if lot_qty>0: 
                              if has_open_position(kite):

                                  st.warning("⚠️ Open position exists. New trade not allowed.")
                                  
                              else:
                                    if not st.session_state.order_executed:
                                        try:
                                            st.write("Placing Trade-") 
                                            order_id = kite.place_order(
                                                    tradingsymbol=trending_symbol,
                                                    exchange=kite.EXCHANGE_NFO,
                                                    transaction_type=kite.TRANSACTION_TYPE_BUY,
                                                    quantity=qty,
                                                    order_type=kite.ORDER_TYPE_MARKET,
                                                    variety=kite.VARIETY_REGULAR,
                                                    product=kite.PRODUCT_MIS
                                                )
                                
                                            st.session_state.order_executed = True   # Mark executed
                                            #st.session_state.order_executed = True
                                            st.session_state.last_order_id = order_id
                                   
                                           # ✅ Mark trade active
                                            st.session_state.trade_active = True
                                            st.session_state.entry_price = ltp
                                            st.session_state.entry_time = datetime.now()
                                            st.session_state.qty = qty
                                            st.session_state.tradingsymbol = trending_symbol 
                                            st.success(f"Order Placed Successfully! Order ID: {order_id}")
                                            st.session_state["last_order_id"] = order_id
                                            st.session_state.last_executed_signal_time = signal_time
                                            st.session_state.last_option_entry_price = entry_price     
                                        except Exception as e:
                                            st.error(f"Order Failed: {e}")
                                        
                        else:
                               st.info("Trade Not Allowed Qty=0.")  
                    else:
                         st.info("Order already executed for this signal.")
                 
                 else:
                       st.warning("Trading window closed. Orders allowed only between 9:30 AM and 2:30 PM.")
            else:
                   st.warning("Signal time does not match today's date or is outside trading hours. Order not placed.")     
          
#--------------------------------ORDERS------------------------------------------------
            st.divider()
         #st.autorefresh(interval=5000)  # refresh every 5 seconds
    
            if "last_order_id" in st.session_state:
                  order_id = st.session_state["last_order_id"]
                  order = kite.order_history(order_id)[-1]
                  st.write("### 🔄 Live Order Update")
                  #st.write(order)


#------------------------------------ORDERS--------------------------------------------
            show_kite_orders(kite)
#===========================================OPEN POSITION--------------------------------------
            st.divider()

            open_pnl = show_open_positions(kite)
            closed_pnl = show_closed_positions(kite)
               
            st.divider()
            st.metric(
                   "💰 TOTAL DAY P&L",
                   f"₹ {open_pnl + closed_pnl:,.2f}"
             )

#---------------------------------Exit Logic-----------------------------------------------
            if "trade_active" not in st.session_state:
                   st.session_state.trade_active = False
                   st.session_state.entry_price = 0.0
                   st.session_state.entry_time = None
                   st.session_state.highest_price = 0.0
                   st.session_state.partial_exit_done = False
                   st.session_state.final_exit_done = False
 
#--------------------------------------Manage Order--------------------------------------------------------

            last_order1 = get_last_active_order(kite)

            st.subheader("🟢 Active Trade")
               
            active_trade_box = st.empty()

            #last_order1 = get_last_active_order(kite)

            if last_order1:
                active_trade_box.success("Last Order Found")
            else:
                active_trade_box.info("No active trade found.")

#--------------------------------------Exit Logix=-----------------------------------------------------------        
            pos = False 
            import time   
            last_order = get_last_buy_order(kite)
            #st.write("Last Order",last_order)   
            if last_order:
              pos = get_open_position_for_symbol(
                  kite,
                  last_order["tradingsymbol"]
              )
              #st.write("POS",pos)
            else:
                 st.write("No Open Position Active")
                 symbol=trending_symbol
                 #symbol="NIFTY26JAN25150PE" 
                 #qty=65  
                 #entry_price=127.15
                 #strike=25200
                 #expiry_date=date(2026,1,27)

                 #monitor_position_live_with_theta_table_and_exit(kite,symbol,qty,entry_price,strike,expiry,option_type="CALL")
               
          
            if pos:
                  st.subheader("🟢 Active Position")
                  
                  monitor_position_live_with_theta_table_and_exit(kite,symbol,qty,entry_price,strike,expiry,option_type="CALL")
                  st.table(pd.DataFrame([{
                      "Symbol": pos["tradingsymbol"],
                      "Qty": pos["quantity"],
                      "Avg Price": pos["average_price"],
                      "PnL": pos["pnl"]
                  }]))
          
                 

            df_plot1 = fetch_nifty_daily_last_7_days(kite)
             
            #monitor_position_live_with_theta_table(kite,symbol,qty,entry_price,strike,expiry_date,option_type="CALL")   
            #monitor_all_open_positions_live(kite)
            #while True:
                        #if df_plot1 is not None and not df_plot1.empty:
                             #monitor_and_exit_last_position(kite, df_plot1)
                             #time.sleep(5)
                        #else:
                            # print("❌ No NIFTY daily data available")
                        #monitor_and_exit_last_position(kite,df_plot)

           



#--------------------------------EXIT------------------------------------------------
          
#==========================================NIFTY 3:20 PM Intraday Strategy==============================================================
elif MENU =="NIFTY 3:20 PM Intraday Strategy":
    with st.sidebar:
         if st.button("🧹 Clear Paper Trades"):
             st.session_state.paper_trades = []
             st.success("All paper trades cleared")
             st.rerun()
 
    st.title("🔴 LIVE TRADE NIFTY 3:20 PM Intraday Strategy")
    with st.expander("📈 NIFTY 3:20 PM Intraday Breakout Options Strategy - Click to expand"):
         st.markdown("""
          1️⃣ **Market Preparation**  
          - The strategy is applied on NIFTY index only.  
          - The 3:15 PM to 3:20 PM candle is used as the reference candle.  
          
          **Box High** = High of 3:20 PM candle  
          **Box Low** = Low of 3:20 PM candle  
          
          This candle represents where institutional traders have positioned themselves.
          
          ---
          
          2️⃣ **Trading Time**  
          - The strategy becomes active from 3:20 PM to 3:29 PM only.  
          - Only one trade is allowed per day.
          
          ---
          
          3️⃣ **Entry Rules**  
          
          **Bullish Breakout (CALL Option):**  
          If NIFTY price breaks above the 3:20 PM candle high, buy ATM CALL option.
          
          **Bearish Breakout (PUT Option):**  
          If NIFTY price breaks below the 3:20 PM candle low, buy ATM PUT option.
          
          ---
          
          4️⃣ **Stop Loss**  
          
          - For CALL trade: Stop Loss = 3:20 PM candle low  
          - For PUT trade: Stop Loss = 3:20 PM candle high
          
          ---
          
          5️⃣ **Target**  
          
          - Risk = Box High − Box Low  
          - Target = Entry Price ± (1.5 × Risk)  
          
          This ensures positive risk-reward.
          
          ---
          
          6️⃣ **Time Exit**  
          
          - If target or stop loss is not hit, the trade is exited at 3:29 PM at market price.
          
          ---
          
          7️⃣ **Risk Management**  
          
          - Only one trade per day  
          - Fixed stop loss  
          - Fixed target  
          - Very short holding time
          
          ---
          
          8️⃣ **Why this strategy works**  
          
          After 3:20 PM, large traders and institutions adjust hedges.  
          This creates a strong directional move in NIFTY options which this strategy captures.
          """)
 
    #st.title("🔴 Live Nifty 15-Minute Chart + Signal Engine")
    if not is_kite_connected(kite):
        st.warning("Please login first to access LIVE trade.")
        st.stop()     # Stop page execution safely
     # --- --------------------------------------------------------------------------------        
    # --- HARD BLOCK: Do not trade if position already exists ---
    if has_open_position(kite):
         st.info("Open position exists → New signal ignored")
         #return
    else:
         st.info("Open Not position exists →")
      # --- --------------------------------------------------------------------------------    
    #st.success("You are logged in.")
     
    st.session_state.param_rows = []
    from streamlit_autorefresh import st_autorefresh
    import time             # Python's time module
    from datetime import time  # datetime.time (conflict!)
    # Initialize Kite in session_state
    if "kite" not in st.session_state:
        st.session_state.kite = None
    else:
        kite = st.session_state.get("kite")
    # --- SESSION STATE INIT ---
    if "order_executed" not in st.session_state:
        st.session_state.order_executed = False
        
    
    if "signal_time" not in st.session_state:
        st.session_state.signal_time = None
    # Add after data processing:
    def is_kite_connected(kite):
        try:
            kite.profile()
            return True
        except:
            return False

    if is_kite_connected(kite):
        st.success("Kite connection active")
    else:
        st.error("Kite session expired. Please login again.")

    st.set_page_config(layout="wide")
    # Place at the very top of your script (or just before plotting)
    #st_autorefresh(interval=60000, limit=None, key="refresh")
    # Current time in IST
    #----------------------------------------------------------------------
    #if is_kite_connected(kite):
    funds = get_fund_status(kite)
    #st.write(funds) 
    cash = (funds['cash'])
    cash = (funds['net']) 
    #iv_value = 0.26
    result = "Fail" if 75000 <= cash <= 25000 else "Pass"
    add_param_row("CASH", cash, "25K - 100K", result)


    #---------------------------------------------------------------------
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    
    # Market hours condition
    start = time(9, 15)   # 9:30 AM
    end = time(15, 25)    # 3:25 PM
    
    # Refresh only between 9:30–3:25
    if start <= now <= end:
        #st_autorefresh(interval=60000, key="refresh")  # 1 minute refresh
        st_autorefresh(interval=60000, key="refresh_live3")
    else:
        st.info("Auto-refresh is paused — Outside market hours (9:30 AM to 3:25 PM).")

    st.title("Nifty 5-min Chart")
    
    # Select date input (default today)
    selected_date = st.date_input("Select date", value=datetime.today())
    
    # Calculate date range to download (7 days before selected_date to day after selected_date)
    start_date = selected_date - timedelta(days=7)
    end_date = selected_date + timedelta(days=1)
    
    # Download data for ^NSEI from start_date to end_date
    df = yf.download("^NSEI", start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="5m")
    
    if df.empty:
        st.warning("No data downloaded for the selected range.")
        st.stop()
    df.reset_index(inplace=True)
    
    if 'Datetime_' in df.columns:
        df.rename(columns={'Datetime_': 'Datetime'}, inplace=True)
    elif 'Date' in df.columns:
        df.rename(columns={'Date': 'Datetime'}, inplace=True)
    # Add any other detected name if needed
    
    
    #st.write(df.columns)
    #st.write(df.head(10))
    # Flatten columns if MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
    
    # Rename datetime column if needed
    if 'Datetime' not in df.columns and 'datetime' in df.columns:
        df.rename(columns={'datetime': 'Datetime'}, inplace=True)
    #st.write(df.columns)
    #st.write(df.columns)
    # Convert to datetime & timezone aware
    #df['Datetime'] = pd.to_datetime(df['Datetime'])
    if df['Datetime_'].dt.tz is None:
        df['Datetime'] = df['Datetime_'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    else:
        df['Datetime'] = df['Datetime_'].dt.tz_convert('Asia/Kolkata')
    
    #st.write(df.columns)
    #st.write(df.head(10))
    
    # Filter for last two trading days to plot
    unique_days = df['Datetime'].dt.date.unique()
    if len(unique_days) < 2:
        st.warning("Not enough data for two trading days")
    else:
        last_day = unique_days[-2]
        today = unique_days[-1]
    
        df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
    
        # Get last day 3PM candle open and close
        candle_3pm = df_plot[(df_plot['Datetime'].dt.date == last_day) &
                             (df_plot['Datetime'].dt.hour == 15) &
                             (df_plot['Datetime'].dt.minute == 0)]
    
        if not candle_3pm.empty:
            open_3pm = candle_3pm.iloc[0]['Open_^NSEI']
            close_3pm = candle_3pm.iloc[0]['Close_^NSEI']
        else:
            open_3pm = None
            close_3pm = None
            st.warning("No 3:00 PM candle found for last trading day.")
        #-----------------------------Marking 9.15 Candle---------------------------------
        # Get today's 9:15 AM candle
        candle_915 = df_plot[(df_plot['Datetime'].dt.date == today) &
                          (df_plot['Datetime'].dt.hour == 9) &
                          (df_plot['Datetime'].dt.minute == 15)]
     
        if not candle_915.empty:
              o_915 = candle_915.iloc[0]['Open_^NSEI']
              h_915 = candle_915.iloc[0]['High_^NSEI']
              l_915 = candle_915.iloc[0]['Low_^NSEI']
              c_915 = candle_915.iloc[0]['Close_^NSEI']
              t_915 = candle_915.iloc[0]['Datetime']
        else:
              o_915 = h_915 = l_915 = c_915 = t_915 = None
              st.warning("No 9:15 AM candle found for today.")    
         
         #---------------------------------------------------------------------------------
    
         
    
        # Plot candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=df_plot['Datetime'],
            open=df_plot['Open_^NSEI'],
            high=df_plot['High_^NSEI'],
            low=df_plot['Low_^NSEI'],
            close=df_plot['Close_^NSEI']
        )])
        if t_915 is not None:
              fig.add_vrect(
                  x0=t_915,
                  x1=t_915 + pd.Timedelta(minutes=15),
                  fillcolor="orange",
                  opacity=0.25,
                  layer="below",
                  line_width=0,
                  annotation_text="9:15 Candle",
                  annotation_position="top left"
              )
        
        

        if o_915 is not None and c_915 is not None:
              fig.add_hline(y=o_915, line_dash="solid", line_color="green",
                            annotation_text="9:15 Open")
              fig.add_hline(y=c_915, line_dash="solid", line_color="orange",
                            annotation_text="9:15 Close") 
        if open_3pm and close_3pm:
            fig.add_hline(y=open_3pm, line_dash="dot", line_color="blue", annotation_text="3PM Open")
            fig.add_hline(y=close_3pm, line_dash="dot", line_color="red", annotation_text="3PM Close")
    
    
    
    
        # Draw horizontal lines as line segments only between 3PM last day and 3PM next day
    
        
        fig.update_layout(title="Nifty 15-min candles - Last Day & Today", xaxis_rangeslider_visible=False)
        fig.update_layout(
        xaxis=dict(
            rangebreaks=[
                # Hide weekends (Saturday and Sunday)
                dict(bounds=["sat", "mon"]),
                # Hide hours outside of trading hours (NSE trading hours 9:15 to 15:30)
                dict(bounds=[15.5, 9.25], pattern="hour"),
            ]
        )
    )
    
    
        st.plotly_chart(fig, use_container_width=True)
        #----------------------------------------------------------------------
        df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
        #signal = trading_signal_all_conditions(df_plot)
        signal = nifty_320_breakout_strategy(df_plot) 
        #st.write(signal)  
        if signal is None:
            st.warning("⚠ No signal yet (conditions not met).")
        else:
            st.success(f"✅ SIGNAL GENERATED: {signal['option_type']}")
            df_sig1 = pd.DataFrame([signal])
            signal_time = df_plot["Datetime"].iloc[-1]   # last candle timestamp
            signal["signal_time"] = signal_time
            signal_time1=signal["signal_time"] 
 
                
                # Display as table
            #st.table(df_sig1) 
            st.write(df_sig1) 
            entry_time = signal['entry_time']
            #st.write("entry_time",entry_time) 
            #st.write("Signal Time only:", entry_time.strftime("%H:%M:%S"))  # HH:MM:SS
            signal_time=entry_time.strftime("%H:%M:%S")
            #st.write("Signal Time only:-", signal_time)  # HH:MM:SS
            #            st.write(signal)
#--------------------------------------------------------------------------------

        def generate_signals_stepwise(df):
            all_signals = []
            
            # We run strategy for each candle progressively
            for i in range(40, len(df)):   # start after enough candles
                sub_df = df.iloc[:i].copy()
                sig = trading_signal_all_conditions(sub_df)
                if sig is not None:
                    all_signals.append((sub_df.iloc[-1]["Datetime"], sig))
        
            return all_signals
#-------------------------------------Total signals-------------------------------------------

        step_signals = generate_signals_stepwise(df_plot)
        if step_signals:
                #st.info(f"Total signals detected so far: {len(step_signals)}")
            
                latest_time, latest_sig = step_signals[-1]
                
                st.success(f"🟢 Latest Candle Signal ({latest_time}):")
                #st.write(latest_sig)
                # Convert to DataFrame
                df_sig = pd.DataFrame([latest_sig])
                
                # Display as table
                #st.table(df_sig)
        else:
                st.warning("No signal triggered in any candle yet.")
   

#-----------------------------------Nearest ITM Option ---------------------------------------------

        if signal is not None:
            #signal_time = df["Datetime"].iloc[-1].time()   # last candle time
            option_type = signal["option_type"]     # CALL / PUT
            #st.write("Option type ",option_type)
            spot = signal["spot_price"]
            #st.write("Option spot ",spot)
            try:
                nearest_itm = find_nearest_itm_option(kite, spot, option_type)
                
                st.success("Nearest ITM Option Found")
                #                st.write(nearest_itm)
                nearest_itm1 = pd.DataFrame([nearest_itm])
                
                # Display as table
                st.table(nearest_itm1)
                trending_symbol=nearest_itm['tradingsymbol']
                #st.write("tradingsymbol-",trending_symbol)
        
            except Exception as e:
                st.error(f"Failed to fetch option: {e}")

    
#######################---------------------IV-NEW !-------------------------------------------------
             
            option_dict = get_live_option_details(kite, trending_symbol)
            #spot_price=26046.00 
            ltp = option_dict.get("ltp")
            strike = option_dict.get("strike")
            expiry = option_dict.get("expiry")
            is_call = option_dict.get("option_type") == "CALL"
          #------------------------------------------PAPER TRADE-------------------------------------------------
            if signal is not None:

              signal_time = signal["signal_time"]
          
              # 🔒 ENTRY LOCK — THIS PREVENTS RE-ENTRY ON REFRESH
              if st.session_state.last_executed_signal_time == signal_time:
                  pass  # already traded this signal
          
              else:
                  option_type = signal["option_type"]
                  spot = signal["spot_price"]
          
                  nearest_itm = find_nearest_itm_option(kite, spot, option_type)
                  trending_symbol = nearest_itm["tradingsymbol"]
                  option_symbol = f"NFO:{trending_symbol}"
          
                  entry_price = kite.ltp(option_symbol)[option_symbol]["last_price"]
          
                  
                  trade = {
                        "signal_time": signal_time,
                        "entry_time": pd.Timestamp.now(),
                        "symbol": trending_symbol,
                        "option_type": option_type,
                        "entry_price": entry_price,
                        "quantity": 65,
                        "remaining_qty": 65,
                        "highest_price": entry_price,
                        "partial_exit_done": False,
                        "final_exit_done": False,
                        "status": "OPEN"
                    }
          
                  st.session_state.paper_trades.append(trade)
          
                  # 🔐 LOCK THE SIGNAL
                  st.session_state.last_executed_signal_time = signal_time
          
                  #st.success(f"Paper trade entered @ {entry_price}")

            #monitor_paper_trades(kite)
            #for trade in st.session_state.paper_trades:
              #normalize_trade(trade)
              #manage_exit_papertrade(kite, trade)

            st.write("Moniter")
             

 
   
          #---------------------------------------PAPER TRADE----------------------------------------------------   
              # Compute time to expiry (in years)
            days_to_exp = days_to_expiry(expiry)
            time_to_expiry = days_to_exp / 365 
            r=0.07
            #st.write("spot_price, strike, time_to_expiry, r, ltp",spot_price, strike, time_to_expiry, r, ltp) 
            iv = implied_vol_call(spot_price, strike, time_to_expiry, r, ltp) 
            #st.write("IV  FOr (Option):CE")
            #st.write("IV (decimal):", iv)
            #st.write("IV (%):", iv * 100)    
            result = "Pass" if (iv is not None and 0.10 <= iv <= 0.35) else "Fail"
 
            #result = "Pass" if 0.10 <= iv <= 0.35 else "Fail"
            iv_result = result    
            #add_param_row("IV", round(iv, 2), "0.10 - 0.35", result)
             

#-----------------------------------IV Compute---------------------------------------------

        #spot_price = get_ltp(kite, "NSE:NIFTY 50")["ltp"]
        
         #iv_percent = compute_option_iv(nearest_itm, spot)
        
         #st.write("IV:", iv_percent)    
         
         #get_live_iv_nifty_option(kite, option_token: int, index_symbol="NSE:NIFTY 50"):        
            #st.write(nearest_itm)  

#----------------------------------IV----------------------------------------------

    
        
            iv_info = get_iv_rank0(kite, nearest_itm, lookback_days=250)
       
            #st.write("New Way Iv ",iv)  
            # Fix missing values
            if iv_info["iv"] is None:
                 iv_info["iv"] = 0
     
            if iv_info["iv_rank"] is None:
                iv_info["iv_rank"] = 0

         ##st.write("Current IV:", iv_info["iv"], "%")
         #st.write("IV Rank:", iv_info["iv_rank"], "%")
#-----------------------Add PARA----------------------------------------------
    # IV
            result = "Pass" if 0.10 <= iv_info["iv"] <= 0.35 else "Fail"
            iv_result = result    
            #add_param_row("IV", round(iv_info["iv"], 2), "0.10 - 0.35", result)

    # IV Rank
            result = "Pass" if 0.20 <= iv_info["iv_rank"] <= 0.70 else "Fail"
            iv_rank_result  = result    
            #add_param_row("IV Rank", round(iv_info["iv_rank"], 2), "0.20 - 0.70", result)
#--------------------------------------------------Getting New IV-----------& adding to para----------------------------
            #result = compute_option_iv_details(option, spot)
     
            #st.write(result)  
            option = get_live_option_details(kite, trending_symbol)
     
            #st.write(option)
     
     
            spot = option["strike"]
            #st.write("Spot",spot) 
            #spot = 25900.00  # live NIFTY spot
     
            result = compute_option_iv_details(option, spot)
            #st.write("IV new",result["iv"]) 
            new_iv_result= result["iv"]
            result = "Pass" if 0.10 <= new_iv_result <= 0.35 else "Fail" 
            add_param_row("IV ", round(new_iv_result, 2), "0.10 - 0.35", result) 
#-------------------------------------------------------------------------
            if(iv_info["iv"]=='None'):
             # Safely extract values
                  iv_value = iv_info.get("iv") or 0
                  iv_rank_value = iv_info.get("iv_rank") or 0
             
                  st.write("After None Current IV:", iv_value, "%")
                  st.write("After None IV Rank:", iv_rank_value, "%")
    
        

#--------------------------------VIX------------------------------------------------
         #vix_now =fetch_vix_from_fyers()
         
            vix_now = fetch_india_vix_kite(kite)
         #st.write("India VIX: kite", vix_now)
         #st.write("India VIX:", vix_now)
 #-----------------------Add PARA----------------------------------------------
    # VIX
            result = "Pass" if vix_now > 10 else "Fail"
            vix_result  = result     
            add_param_row("VIX", round(vix_now, 2), "> 10", result)

 #------------------------------------------------------------------------------   
    # Apply IV + VIX Filter
    # -------------------------
        #allowed, position_size = combined_filter(iv_info["iv"], iv_info["iv_rank"], vix_now)
    # Safely extract values
            iv_value = iv_info.get("iv") or 0
            iv_rank_value = iv_info.get("iv_rank") or 0
            allowed, position_size = combined_filter(iv_value, iv_rank_value, vix_now)
            #st.write("Allowed to Trade?", allowed)
            #st.write("Position Size:", position_size)
    #-----------------------------------------------------------------------------------------
    
    #---------------------------------tIME-----------------------------------------------
            import pytz
            
    # IST timezone
            ist = pytz.timezone("Asia/Kolkata")
            now_dt = datetime.now(ist)     # full datetime object
            now = now_dt.time()            # extract time only for comparisons

            tz = pytz.timezone("Asia/Kolkata")
            now = datetime.now(tz)
     #----------------------------------FUND-----------------------------------------------------
            #st.divider()

            funds = get_fund_status(kite)

            #st.subheader("💰 Zerodha Fund Status")
    
            if "error" in funds:
                st.error(funds["error"])
            else:
                  #st.write(f"**Net Balance:** ₹{funds['net']}")
                  #st.write(f"**Cash:** ₹{funds['cash']}")
                  #st.write(f"**Opening Balance:** ₹{funds['opening_balance']}")
                  #st.write(f"**Collateral:** ₹{funds['collateral']}")
                  #st.write(f"**Option Premium Used:** ₹{funds['option_premium']}")
                  #cash_balance = 73500
                  lots = get_lot_size(funds['cash'])
                  #st.write("Lot Size:", lots)
                  #qty=65*lots
                  #st.divider()

   
    
    #------------------------------------PLACING ORDERS--------------------------------------------
             #st.write(f"Placing order for:", trending_symbol)
            if(position_size=='none'):
                  position_size=1;
        #st.write(f"Quantity: {qty}, LTP: {ltp}")
        #st.write(f"Quantity  order for:", qty)        
        #if st.button("🚀 PLACE BUY ORDER IN ZERODHA"):
        # Condition 1: Current time >= signal candle time
        # Trading window
            start_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
            end_time   = now.replace(hour=14, minute=30, second=0, microsecond=0)
    #st.write("start_time", start_time)
    #st.write("end_time", end_time)
    #st.write("Now Time", now)
    #st.write("signal_time",signal_time)
    
    
    #-------------------------------------------------------------------------------

        # Convert to Python datetime (with timezone if needed)
            signal_time = pd.to_datetime(signal_time).to_pydatetime()
   
    # Optional: ensure same timezone as now
    #import pytz
            tz = pytz.timezone("Asia/Kolkata")
            signal_time = signal_time.replace(tzinfo=tz)
    #    st.write("signal_time",signal_time)
    #st.write("Now Time", now)
    #--------------------------------------------------------------------------------
     #-----------------------Add PARA----------------------------------------------
    # Define IST timezone
            ist = pytz.timezone("Asia/Kolkata")
    
    # Convert signal_time to IST
            signal_time_ist = signal_time.astimezone(ist)
            import datetime as dt

            start = dt.time(9, 30)
            end   = dt.time(14, 30)
    
            sig_t = signal_time_ist.time()
    
            result = "Pass" if start <= sig_t <= end else "Fail"
    
            add_param_row("Signal Time", str(signal_time_ist.time()),"09:30 - 14:30",result)
     #------------------------------------ADD PCR------------------------------------------ 
            pcr_value = get_nifty_pcr(kite)
            result = "Pass" if 0.80 <= pcr_value <= 1.30 else "Fail"
            pcr_result= result
            add_param_row("PCR", round(pcr_value, 2), "0.80 - 1.30", result)

#-------------------------------------lot ty------------------------------------------------
     # Default lot size
            qty = 1*65
     
     # Apply rule
            if iv_result == "Fail" or iv_rank_result == "Fail":
                   lot_qty = 2
            if iv_result == "Pass" and iv_rank_result == "Fail" and vix_result=="pass" and pcr_result=="pass":
                   lot_qty = 6    
            if vix_now < 10 :
                   lot_qty = 0 
            add_param_row("LOT QTY", lot_qty, "0,1,2,4,6", "OK")
     #-----------------------------------------Display PARA-------------------------------------------
            if st.session_state.param_rows:
                  df = pd.DataFrame(st.session_state.param_rows)
                  st.table(df)
            else:
                  st.write("No parameters added yet.")
    #------------------------------------------------------------------------------------------------
            #qty=qty*lot_qty
            #qty=0
                # Check 1: Only run if current time is within trading window
            if is_valid_signal_time(entry_time):
                 st.warning("Signal time  match today's date .") 
                 if start_time <= now <= end_time:
                 
                 # Check 2: Signal time reached
                    #if now >= entry_time:
                      
                    if abs((now - entry_time).total_seconds()) < 30:  
                         st.info("Execution window In (30 seconds).") 
                         st.write("entry_time-",entry_time)
                         st.write("Now Time-", now)
                      # Check 3: Order placed only once
                         if lot_qty>0: 
                              if has_open_position(kite):

                                  st.warning("⚠️ Open position exists. New trade not allowed.")
                                  
                              else:
                                    if not st.session_state.order_executed:
                                        try:
                                            order_id = kite.place_order(
                                                    tradingsymbol=trending_symbol,
                                                    exchange=kite.EXCHANGE_NFO,
                                                    transaction_type=kite.TRANSACTION_TYPE_BUY,
                                                    quantity=qty,
                                                    order_type=kite.ORDER_TYPE_MARKET,
                                                    variety=kite.VARIETY_REGULAR,
                                                    product=kite.PRODUCT_MIS
                                                )
                                
                                            st.session_state.order_executed = True   # Mark executed
                                            st.session_state.order_executed = True
                                            st.session_state.last_order_id = order_id
                                   
                                           # ✅ Mark trade active
                                            st.session_state.trade_active = True
                                            st.session_state.entry_price = ltp
                                            st.session_state.entry_time = datetime.now()
                                            st.session_state.qty = qty
                                            st.session_state.tradingsymbol = trending_symbol 
                                            st.success(f"Order Placed Successfully! Order ID: {order_id}")
                                            st.session_state["last_order_id"] = order_id
                                
                                        except Exception as e:
                                            st.error(f"Order Failed: {e}")
                                        
                         else:
                               st.info("Trade Not Allowed Qty=0.")  
                    else:
                         st.info("Order already executed for this signal.")
                 
                 else:
                       st.warning("Trading window closed. Orders allowed only between 9:30 AM and 2:30 PM.")
            else:
                   st.warning("Signal time does not match today's date or is outside trading hours. Order not placed.")     
          
#--------------------------------ORDERS------------------------------------------------
            st.divider()
         #st.autorefresh(interval=5000)  # refresh every 5 seconds
    
            if "last_order_id" in st.session_state:
                  order_id = st.session_state["last_order_id"]
                  order = kite.order_history(order_id)[-1]
                  st.write("### 🔄 Live Order Update")
                  #st.write(order)


#------------------------------------ORDERS--------------------------------------------
            show_kite_orders(kite)
#===========================================OPEN POSITION--------------------------------------
            st.divider()

            open_pnl = show_open_positions(kite)
            closed_pnl = show_closed_positions(kite)
               
            st.divider()
            st.metric(
                   "💰 TOTAL DAY P&L",
                   f"₹ {open_pnl + closed_pnl:,.2f}"
             )

#---------------------------------Exit Logic-----------------------------------------------
            if "trade_active" not in st.session_state:
                   st.session_state.trade_active = False
                   st.session_state.entry_price = 0.0
                   st.session_state.entry_time = None
                   st.session_state.highest_price = 0.0
                   st.session_state.partial_exit_done = False
                   st.session_state.final_exit_done = False
 
#--------------------------------------Manage Order--------------------------------------------------------

            last_order1 = get_last_active_order(kite)

            st.subheader("🟢 Active Trade")
               
            if last_order1:
                   #st.write({"Symbol": last_order["tradingsymbol"],"Qty": last_order["quantity"],"Entry Price": last_order["average_price"],"Order Time": last_order["order_timestamp"] })
                   st.write("Last Order")
            else:
                   st.info("No active trade found.")

#--------------------------------------Exit Logix=-----------------------------------------------------------        

            import time   
            last_order = get_last_buy_order(kite)
            #st.write("Last Order",last_order)   
            if last_order:
              pos = get_open_position_for_symbol(
                  kite,
                  last_order["tradingsymbol"]
              )
              #st.write("POS",pos)
            else:
                 st.write("No Open Position Active")
          
            if pos:
                  st.subheader("🟢 Active Position")
                  st.table(pd.DataFrame([{
                      "Symbol": pos["tradingsymbol"],
                      "Qty": pos["quantity"],
                      "Avg Price": pos["average_price"],
                      "PnL": pos["pnl"]
                  }]))
          
                 

                  while True:
                        monitor_and_exit_last_position(kite)
                        time.sleep(5)


           



#--------------------------------EXIT------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

#--------------------------------------------------------------------------------

elif MENU=="Live IV/RANK":
    st.title("Live IV/RANK")
    if not is_kite_connected(kite):
        st.warning("Please login first to access your account details.")
        st.stop()     # Stop page execution safely

    #st.success("You are logged in.") 
    
    from math import log, sqrt, exp
    from scipy.stats import norm
     
    
   
         
    tradingsymbol = "NIFTY20J2726200PE"
     
    option = get_live_option_details(kite, tradingsymbol)
     
    st.write(option)
     
     
    spot = option["strike"]
    st.write("Spot",spot) 
    #spot = 25900.00  # live NIFTY spot
     
    result = compute_option_iv_details(option, spot)
    st.write("IV",result["iv"]) 
    st.write(result)
 #-------------------------------------------------------------------

    import math

     # Black-Scholes call price
    def bs_call_price(S, K, T, r, sigma):
         if sigma <= 0:
             return 0.0
         d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
         d2 = d1 - sigma * math.sqrt(T)
         Nd1 = 0.5 * (1.0 + math.erf(d1 / math.sqrt(2.0)))
         Nd2 = 0.5 * (1.0 + math.erf(d2 / math.sqrt(2.0)))
         return S * Nd1 - K * math.exp(-r * T) * Nd2
     
     # Implied volatility via simple bisection
    def implied_vol_call(S, K, T, r, C_mkt, tol=1e-6, max_iter=100):
         low, high = 1e-6, 5.0      # 0.0001% to 500% vol range
         for _ in range(max_iter):
             mid = 0.5 * (low + high)
             price = bs_call_price(S, K, T, r, mid)
             if abs(price - C_mkt) < tol:
                 return mid
             if price > C_mkt:
                 high = mid
             else:
                 low = mid
         return mid  # best guess if not converged
     
     # Your inputs
    S0   = 26046.0
    K    = 26000.0
    T    = 0.010958904109589
    C_mk = 112.60
    r    = 0.07   # 7% risk-free

    st.write("spot_price, strike, time_to_expiry, r, ltp",S0, K, T, r, C_mk)  
    iv = implied_vol_call(S0, K, T, r, C_mk)
    st.write("IV  FOr (26000):CE")
    st.write("IV (decimal):", iv)
    st.write("IV (%):", iv * 100)
    st.title("📊 NIFTY Option Input")

    tradingsymbol = st.text_input(
         "Trading Symbol",
         value=""
     )
     
    pattern = r"^NIFTY\d{2}[A-Z]\d{2}\d{5}(CE|PE)$"
     
    if tradingsymbol:
         if re.match(pattern, tradingsymbol):
             st.success("✅ Valid NIFTY Option Symbol")
         else:
             st.error("❌ Invalid format (Example: NIFTY25D1626000CE)") 
    #tradingsymbol="NIFTY25D1626000CE" 
    option_dict = get_live_option_details(kite, tradingsymbol)
    spot_price=26136.00 
    ltp = option_dict.get("ltp")
    strike = option_dict.get("strike")
    expiry = option_dict.get("expiry")
    is_call = option_dict.get("option_type") == "CALL"
     
         # Compute time to expiry (in years)
    days_to_exp = days_to_expiry(expiry)
    time_to_expiry = days_to_exp / 365 
    r=0.07
    st.write("spot_price, strike, time_to_expiry, r, ltp",spot_price, strike, time_to_expiry, r, ltp) 
    iv = implied_vol_call(spot_price, strike, time_to_expiry, r, ltp) 
    st.write("IV  FOr Option:CE")
    st.write("IV (decimal):", iv)
    st.write("IV (%):", iv * 100)      

    #------------------------------------------------New RANK IV----------------------------------------------------------
    
elif MENU=="Strategy Signals":
    with st.sidebar:
         if st.button("🧹 Clear Paper Trades"):
             st.session_state.paper_trades = []
             st.success("All paper trades cleared")
             st.rerun()
 
    st.title("🔴 Strategy Signals")
    #st.title("🔴 Live Nifty 15-Minute Chart + Signal Engine")
    if not is_kite_connected(kite):
        st.warning("Please login first to access LIVE trade.")
        st.stop()     # Stop page execution safely

    #st.success("You are logged in.")
     
    st.session_state.param_rows = []
    from streamlit_autorefresh import st_autorefresh
    import time             # Python's time module
    from datetime import time  # datetime.time (conflict!)
    # Initialize Kite in session_state
    if "kite" not in st.session_state:
        st.session_state.kite = None
    else:
        kite = st.session_state.get("kite")
    # --- SESSION STATE INIT ---
    if "order_executed" not in st.session_state:
        st.session_state.order_executed = False
        
    
    if "signal_time" not in st.session_state:
        st.session_state.signal_time = None
   

    if is_kite_connected(kite):
        st.success("Kite connection active")
    else:
        st.error("Kite session expired. Please login again.")

    st.set_page_config(layout="wide")
    # Place at the very top of your script (or just before plotting)
    #st_autorefresh(interval=60000, limit=None, key="refresh")
    # Current time in IST
    #----------------------------------------------------------------------
    #if is_kite_connected(kite):
    funds = get_fund_status(kite)
    cash = (funds['cash'])
    st.write(cash) 
    #iv_value = 0.26
    result = "Pass" if 75000 <= cash <= 25000 else "Fail"
    add_param_row("CASH", cash, "25K - 100K", result)


    #---------------------------------------------------------------------
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    
    # Market hours condition
    start = time(9, 15)   # 9:30 AM
    end = time(15, 25)    # 3:25 PM
    
    # Refresh only between 9:30–3:25
    if start <= now <= end:
        #st_autorefresh(interval=60000, key="refresh")  # 1 minute refresh
        st_autorefresh(interval=60000, key="refresh_live3")
    else:
        st.info("Auto-refresh is paused — Outside market hours (9:30 AM to 3:25 PM).")

    st.title("Nifty 15-min Chart")
    
    # Select date input (default today)
    selected_date = st.date_input("Select date", value=datetime.today())
    
    # Calculate date range to download (7 days before selected_date to day after selected_date)
    start_date = selected_date - timedelta(days=7)
    end_date = selected_date + timedelta(days=1)
    
    # Download data for ^NSEI from start_date to end_date
    df = yf.download("^NSEI", start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="15m")
    
    if df.empty:
        st.warning("No data downloaded for the selected range.")
        st.stop()
    df.reset_index(inplace=True)
    
    if 'Datetime_' in df.columns:
        df.rename(columns={'Datetime_': 'Datetime'}, inplace=True)
    elif 'Date' in df.columns:
        df.rename(columns={'Date': 'Datetime'}, inplace=True)
    # Add any other detected name if needed
    
    
    #st.write(df.columns)
    #st.write(df.head(10))
    # Flatten columns if MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
    
    # Rename datetime column if needed
    if 'Datetime' not in df.columns and 'datetime' in df.columns:
        df.rename(columns={'datetime': 'Datetime'}, inplace=True)
    #st.write(df.columns)
    #st.write(df.columns)
    # Convert to datetime & timezone aware
    #df['Datetime'] = pd.to_datetime(df['Datetime'])
    if df['Datetime_'].dt.tz is None:
        df['Datetime'] = df['Datetime_'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    else:
        df['Datetime'] = df['Datetime_'].dt.tz_convert('Asia/Kolkata')
    
    #st.write(df.columns)
    #st.write(df.head(10))
    
    # Filter for last two trading days to plot
    unique_days = df['Datetime'].dt.date.unique()
    if len(unique_days) < 2:
        st.warning("Not enough data for two trading days")
    else:
        last_day = unique_days[-2]
        today = unique_days[-1]
    
        df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
    
        # Get last day 3PM candle open and close
        candle_3pm = df_plot[(df_plot['Datetime'].dt.date == last_day) &
                             (df_plot['Datetime'].dt.hour == 15) &
                             (df_plot['Datetime'].dt.minute == 0)]
    
        if not candle_3pm.empty:
            open_3pm = candle_3pm.iloc[0]['Open_^NSEI']
            close_3pm = candle_3pm.iloc[0]['Close_^NSEI']
        else:
            open_3pm = None
            close_3pm = None
            st.warning("No 3:00 PM candle found for last trading day.")

         #-----------------------------Marking 9.15 Candle---------------------------------
        # Get today's 9:15 AM candle
        candle_915 = df_plot[(df_plot['Datetime'].dt.date == today) &
                          (df_plot['Datetime'].dt.hour == 9) &
                          (df_plot['Datetime'].dt.minute == 15)]
     
        if not candle_915.empty:
              o_915 = candle_915.iloc[0]['Open_^NSEI']
              h_915 = candle_915.iloc[0]['High_^NSEI']
              l_915 = candle_915.iloc[0]['Low_^NSEI']
              c_915 = candle_915.iloc[0]['Close_^NSEI']
              t_915 = candle_915.iloc[0]['Datetime']
        else:
              o_915 = h_915 = l_915 = c_915 = t_915 = None
              st.warning("No 9:15 AM candle found for today.")    
         
         #---------------------------------------------------------------------------------
    
        # Plot candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=df_plot['Datetime'],
            open=df_plot['Open_^NSEI'],
            high=df_plot['High_^NSEI'],
            low=df_plot['Low_^NSEI'],
            close=df_plot['Close_^NSEI']
        )])
        if t_915 is not None:
              fig.add_vrect(
                  x0=t_915,
                  x1=t_915 + pd.Timedelta(minutes=15),
                  fillcolor="orange",
                  opacity=0.25,
                  layer="below",
                  line_width=0,
                  annotation_text="9:15 Candle",
                  annotation_position="top left"
              )
        
        if open_3pm and close_3pm:
            fig.add_hline(y=open_3pm, line_dash="dot", line_color="blue", annotation_text="3PM Open")
            fig.add_hline(y=close_3pm, line_dash="dot", line_color="red", annotation_text="3PM Close")

        if o_915 is not None and c_915 is not None:
              fig.add_hline(y=o_915, line_dash="solid", line_color="green",
                            annotation_text="9:15 Open")
              fig.add_hline(y=c_915, line_dash="solid", line_color="orange",
                            annotation_text="9:15 Close")
 
    
    
    
    
        # Draw horizontal lines as line segments only between 3PM last day and 3PM next day
    
        
        fig.update_layout(title="Nifty 15-min candles - Last Day & Today", xaxis_rangeslider_visible=False)
        fig.update_layout(
        xaxis=dict(
            rangebreaks=[
                # Hide weekends (Saturday and Sunday)
                dict(bounds=["sat", "mon"]),
                # Hide hours outside of trading hours (NSE trading hours 9:15 to 15:30)
                dict(bounds=[15.5, 9.25], pattern="hour"),
            ]
        )
    )
    
    
        st.plotly_chart(fig, use_container_width=True)
        #----------------------------------------------------------------------
        #----------------------------------------------------------------------
        df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
        #signal = trading_multi1_signal_all_conditions(df_plot)
        #signals = trading_multi1_signal_all_conditions(df)
        signals = trading_multi2_signal_all_conditions(df) 
        def calculate_pnl(row):
                   # Swing SL PnL
                   if row['option_type'] == 'CALL':
                       pnl_swing = (row['exit_price'] - row['buy_price']) * row['quantity']
                       pnl_fixed = (row['initial_sl'] - row['buy_price']) * row['quantity']
                   else:  # PUT
                       pnl_swing = (row['buy_price'] - row['exit_price']) * row['quantity']
                       pnl_fixed = (row['buy_price'] - row['initial_sl']) * row['quantity']
               
                   return pd.Series([pnl_swing, pnl_fixed, pnl_swing - pnl_fixed])

        if signals:
                   signals_df = pd.DataFrame(signals)
             
                   #st.write("Signals columns:", list(signals_df.columns))
 
                   
                   
              
                   st.subheader("📊 Generated Trading Signals")
                   st.dataframe(signals_df, use_container_width=True)
        else:
              st.info("No signal generated today")


#-----------------------------------------------Multi Signal------------------------------------
elif MENU=="Strategy Multi Signals":
    with st.sidebar:
         if st.button("🧹 Clear Paper Trades"):
             st.session_state.paper_trades = []
             st.success("All paper trades cleared")
             st.rerun()
 
    st.title("🔴 Strategy Signals")
    #st.title("🔴 Live Nifty 15-Minute Chart + Signal Engine")
    if not is_kite_connected(kite):
        st.warning("Please login first to access LIVE trade.")
        st.stop()     # Stop page execution safely

    #st.success("You are logged in.")
     
    st.session_state.param_rows = []
    from streamlit_autorefresh import st_autorefresh
    import time             # Python's time module
    from datetime import time  # datetime.time (conflict!)
    # Initialize Kite in session_state
    if "kite" not in st.session_state:
        st.session_state.kite = None
    else:
        kite = st.session_state.get("kite")
    # --- SESSION STATE INIT ---
    if "order_executed" not in st.session_state:
        st.session_state.order_executed = False
        
    
    if "signal_time" not in st.session_state:
        st.session_state.signal_time = None
   

    if is_kite_connected(kite):
        st.success("Kite connection active")
    else:
        st.error("Kite session expired. Please login again.")

    st.set_page_config(layout="wide")
    # Place at the very top of your script (or just before plotting)
    #st_autorefresh(interval=60000, limit=None, key="refresh")
    # Current time in IST
    #----------------------------------------------------------------------
    #if is_kite_connected(kite):
    funds = get_fund_status(kite)
    cash = (funds['cash'])
    st.write(cash) 
    #iv_value = 0.26
    result = "Pass" if 75000 <= cash <= 25000 else "Fail"
    add_param_row("CASH", cash, "25K - 100K", result)


    #---------------------------------------------------------------------
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    
    # Market hours condition
    start = time(9, 15)   # 9:30 AM
    end = time(15, 25)    # 3:25 PM
    
    # Refresh only between 9:30–3:25
    if start <= now <= end:
        #st_autorefresh(interval=60000, key="refresh")  # 1 minute refresh
        st_autorefresh(interval=60000, key="refresh_live3")
    else:
        st.info("Auto-refresh is paused — Outside market hours (9:30 AM to 3:25 PM).")

    st.title("Nifty 15-min Chart")
    
    # Select date input (default today)
    selected_date = st.date_input("Select date", value=datetime.today())
    
    # Calculate date range to download (7 days before selected_date to day after selected_date)
    start_date = selected_date - timedelta(days=7)
    end_date = selected_date + timedelta(days=1)
    
    # Download data for ^NSEI from start_date to end_date
    df = yf.download("^NSEI", start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="15m")
    
    if df.empty:
        st.warning("No data downloaded for the selected range.")
        st.stop()
    df.reset_index(inplace=True)
    
    if 'Datetime_' in df.columns:
        df.rename(columns={'Datetime_': 'Datetime'}, inplace=True)
    elif 'Date' in df.columns:
        df.rename(columns={'Date': 'Datetime'}, inplace=True)
    # Add any other detected name if needed
    
    
    #st.write(df.columns)
    #st.write(df.head(10))
    # Flatten columns if MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]
    
    # Rename datetime column if needed
    if 'Datetime' not in df.columns and 'datetime' in df.columns:
        df.rename(columns={'datetime': 'Datetime'}, inplace=True)
    #st.write(df.columns)
    #st.write(df.columns)
    # Convert to datetime & timezone aware
    #df['Datetime'] = pd.to_datetime(df['Datetime'])
    if df['Datetime_'].dt.tz is None:
        df['Datetime'] = df['Datetime_'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    else:
        df['Datetime'] = df['Datetime_'].dt.tz_convert('Asia/Kolkata')
    
    #st.write(df.columns)
    #st.write(df.head(10))
    
    # Filter for last two trading days to plot
    unique_days = df['Datetime'].dt.date.unique()
    if len(unique_days) < 2:
        st.warning("Not enough data for two trading days")
    else:
        last_day = unique_days[-2]
        today = unique_days[-1]
    
        df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
    
        # Get last day 3PM candle open and close
        candle_3pm = df_plot[(df_plot['Datetime'].dt.date == last_day) &
                             (df_plot['Datetime'].dt.hour == 15) &
                             (df_plot['Datetime'].dt.minute == 0)]
    
        if not candle_3pm.empty:
            open_3pm = candle_3pm.iloc[0]['Open_^NSEI']
            close_3pm = candle_3pm.iloc[0]['Close_^NSEI']
        else:
            open_3pm = None
            close_3pm = None
            st.warning("No 3:00 PM candle found for last trading day.")

         #-----------------------------Marking 9.15 Candle---------------------------------
        # Get today's 9:15 AM candle
        candle_915 = df_plot[(df_plot['Datetime'].dt.date == today) &
                          (df_plot['Datetime'].dt.hour == 9) &
                          (df_plot['Datetime'].dt.minute == 15)]
     
        if not candle_915.empty:
              o_915 = candle_915.iloc[0]['Open_^NSEI']
              h_915 = candle_915.iloc[0]['High_^NSEI']
              l_915 = candle_915.iloc[0]['Low_^NSEI']
              c_915 = candle_915.iloc[0]['Close_^NSEI']
              t_915 = candle_915.iloc[0]['Datetime']
        else:
              o_915 = h_915 = l_915 = c_915 = t_915 = None
              st.warning("No 9:15 AM candle found for today.")    
         
         #---------------------------------------------------------------------------------
    
        # Plot candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=df_plot['Datetime'],
            open=df_plot['Open_^NSEI'],
            high=df_plot['High_^NSEI'],
            low=df_plot['Low_^NSEI'],
            close=df_plot['Close_^NSEI']
        )])
        if t_915 is not None:
              fig.add_vrect(
                  x0=t_915,
                  x1=t_915 + pd.Timedelta(minutes=15),
                  fillcolor="orange",
                  opacity=0.25,
                  layer="below",
                  line_width=0,
                  annotation_text="9:15 Candle",
                  annotation_position="top left"
              )
        
        if open_3pm and close_3pm:
            fig.add_hline(y=open_3pm, line_dash="dot", line_color="blue", annotation_text="3PM Open")
            fig.add_hline(y=close_3pm, line_dash="dot", line_color="red", annotation_text="3PM Close")

        if o_915 is not None and c_915 is not None:
              fig.add_hline(y=o_915, line_dash="solid", line_color="green",
                            annotation_text="9:15 Open")
              fig.add_hline(y=c_915, line_dash="solid", line_color="orange",
                            annotation_text="9:15 Close")
 
    
    
    
    
        # Draw horizontal lines as line segments only between 3PM last day and 3PM next day
    
        
        fig.update_layout(title="Nifty 15-min candles - Last Day & Today", xaxis_rangeslider_visible=False)
        fig.update_layout(
        xaxis=dict(
            rangebreaks=[
                # Hide weekends (Saturday and Sunday)
                dict(bounds=["sat", "mon"]),
                # Hide hours outside of trading hours (NSE trading hours 9:15 to 15:30)
                dict(bounds=[15.5, 9.25], pattern="hour"),
            ]
        )
    )
    
    
        st.plotly_chart(fig, use_container_width=True)
        #----------------------------------------------------------------------
        #----------------------------------------------------------------------
        df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]
        #signal = trading_multi1_signal_all_conditions(df_plot)
        signals = trading_multi1_signal_all_conditions(df)
        #signals = trading_multi2_signal_all_conditions(df) 
        def calculate_pnl(row):
                   # Swing SL PnL
                   if row['option_type'] == 'CALL':
                       pnl_swing = (row['exit_price'] - row['buy_price']) * row['quantity']
                       pnl_fixed = (row['initial_sl'] - row['buy_price']) * row['quantity']
                   else:  # PUT
                       pnl_swing = (row['buy_price'] - row['exit_price']) * row['quantity']
                       pnl_fixed = (row['buy_price'] - row['initial_sl']) * row['quantity']
               
                   return pd.Series([pnl_swing, pnl_fixed, pnl_swing - pnl_fixed])

        if signals:
                   signals_df = pd.DataFrame(signals)
             
                   #st.write("Signals columns:", list(signals_df.columns))
 
                   
                   
              
                   st.subheader("📊 Generated Trading Signals")
                   st.dataframe(signals_df, use_container_width=True)
        else:
              st.info("No signal generated today")

   

elif MENU=="Download Instrument":
     st.title("Zerodha Instruments Downloader")

     if st.button("Download Instruments"):
         instruments_df = download_zerodha_instruments()
         
         st.success(f"Downloaded {len(instruments_df)} instruments")
         st.dataframe(instruments_df.head(50))
     
         # Save locally
         today = datetime.now().strftime("%Y-%m-%d")
         file_name = f"zerodha_instruments_{today}.csv"
         instruments_df.to_csv(file_name, index=False)
     
         st.success(f"Saved as {file_name}")
     
         # Download button
         st.download_button(
             label="Download CSV",
             data=instruments_df.to_csv(index=False),
             file_name=file_name,
             mime="text/csv"
         )

elif MENU=="Upload Instrument":
    # ---------------- CONFIG ----------------
    import os, base64, requests, json
    import pandas as pd
    import streamlit as st

    # ---------------- CONFIG ----------------
    #GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    OWNER = "malusareabhi1"
    REPO = "algobot"
    BRANCH = "main"
    FILE_PATH = "data/instruments.csv"
    COMMIT_MESSAGE = "Update Zerodha instruments file"
    # ----------------------------------------------------------------------------------------------

    #GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
 
    if not GITHUB_TOKEN:
         st.error("Token not found")
         st.stop()
     
    headers = {
         "Authorization": f"token {GITHUB_TOKEN}",
         "Accept": "application/vnd.github.v3+json"
     }
     
    r = requests.get("https://api.github.com/user", headers=headers)
     
    st.write("Status code:", r.status_code)
    st.json(r.json())




    #------------------------------------------------------------------------------------------------ 

    if not GITHUB_TOKEN:
        st.error("❌ GITHUB_TOKEN set केलेला नाही")
        st.stop()

    def upload_instruments_to_github():
        # 1. Download Zerodha instruments
        df = pd.read_csv("https://api.kite.trade/instruments")
        content = base64.b64encode(
            df.to_csv(index=False).encode()
        ).decode()

        url = f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{FILE_PATH}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }

        # 2. Check if file exists
        r = requests.get(url, headers=headers)
        sha = r.json().get("sha") if r.status_code == 200 else None

        payload = {
            "message": COMMIT_MESSAGE,
            "content": content,
            "branch": BRANCH
        }

        if sha:
            payload["sha"] = sha

        # 3. Upload / Update
        res = requests.put(url, headers=headers, json=payload)

        if res.status_code in (200, 201):
            st.success("✅ instruments.csv GitHub वर upload झाला")
        else:
            st.error("❌ GitHub upload failed")
            st.code(res.status_code)
            st.code(res.text)
            st.stop()

    # 🔴 VERY IMPORTANT: Button trigger
    if st.button("Upload Instruments to GitHub"):
        upload_instruments_to_github()

# ------------------------------------------------------------
# Footer
# ------------------------------------------------------------
st.markdown("---")
st.caption("© 2025 Shree Software • This is a colorful demo UI. Replace demo handlers with your live logic, APIs, and secure storage.")
