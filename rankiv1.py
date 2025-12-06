# pip install kiteconnect py_vollib yfinance pandas numpy python-dateutil

from kiteconnect import KiteConnect
import pandas as pd
import streamlit as st
import numpy as np
from datetime import datetime, timedelta
from dateutil import parser
from py_vollib.black_scholes.implied_volatility import implied_volatility
from py_vollib.black_scholes import black_scholes
from py_vollib.black_scholes import black_scholes as bs
from py_vollib.black_scholes import black_scholes as bs_price

# ---------------- CONFIG ----------------
API_KEY = "your_api_key"
ACCESS_TOKEN = "your_access_token"  # after login flow
NIFTY_SYMBOL = "NIFTY"              # underlying index
EXCHANGE = "NFO"                    # options segment
OPTION_TRADINGSYMBOL = "NIFTY25DEC24500CE"  # example option symbol

# Risk-free rate (approx, annualized)
R = 0.07

# ------------- INIT KITE ---------------
kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# ---------- helper: get underlying spot ----------
def get_nifty_spot():
    quote = kite.ltp(f"NSE:{NIFTY_SYMBOL}")
    return quote[f"NSE:{NIFTY_SYMBOL}"]["last_price"]

# ---------- helper: get option quote ----------
def get_option_ltp(tradingsymbol):
    q = kite.ltp(f"{EXCHANGE}:{tradingsymbol}")
    return q[f"{EXCHANGE}:{tradingsymbol}"]["last_price"]

# ---------- helper: days to expiry ----------
def days_to_expiry(expiry_str):
    # expiry_str like '2025-12-25'
    expiry = parser.parse(expiry_str).date()
    today = datetime.now().date()
    return max((expiry - today).days, 0)

# ---------- compute current IV ----------
def compute_current_iv(underlying_price, option_price, strike, expiry_str, option_type):
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
def compute_iv_rank(iv_history, current_iv):
    if iv_history.empty or np.isnan(current_iv):
        return np.nan

    iv_low = iv_history.min()
    iv_high = iv_history.max()
    if iv_high == iv_low:
        return 0.0

    iv_rank = (current_iv - iv_low) / (iv_high - iv_low) * 100.0
    return max(0.0, min(100.0, iv_rank))  # clamp 0–100

# ------------- MAIN EXAMPLE -------------
if __name__ == "__main__":
    # you must know strike, expiry and type for the selected option
    STRIKE = 24500
    EXPIRY = "2025-12-25"
    OPTION_TYPE = "c"   # 'c' for CE, 'p' for PE

    spot = get_nifty_spot()
    opt_ltp = get_option_ltp(OPTION_TRADINGSYMBOL)
    current_iv = compute_current_iv(spot, opt_ltp, STRIKE, EXPIRY, OPTION_TYPE)
    st.write("Current IV (%):", current_iv)

    iv_hist = get_iv_history_for_option(OPTION_TRADINGSYMBOL, STRIKE, EXPIRY, OPTION_TYPE)
    st.write("History points:", len(iv_hist))

    iv_rank = compute_iv_rank(iv_hist, current_iv)
    st.write("IV Rank:", iv_rank)
