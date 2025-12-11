from datetime import datetime
import pandas as pd
import streamlit as st
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
from math import log, sqrt, exp
from scipy.stats import norm

def black_scholes_call_iv(spot, strike, time_to_expiry, ltp, r=0.0, tol=1e-5, max_iter=100):
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
        r=0.0
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
option = {
    "tradingsymbol": "NIFTY25D1625850CE",
    "strike": 25850,
    "option_type": "CALL",
    "expiry": "Timestamp('2025-12-16 00:00:00')",   # your Pandas Timestamp
    "ltp": 138.65
}
option ={
"tradingsymbol":"NIFTY25D1625850CE"
"strike":25850
"instrument_token":12343810
"option_type":"CALL"
"expiry":"Timestamp('2025-12-16 00:00:00')"
"lot_size":75
"tick_size":0.05
"segment":"NFO-OPT"
"exchange":"NFO"
"name":"NIFTY"
"ltp":157
}

spot = 25820.40   # live NIFTY spot

result = compute_option_iv_details(option, spot)

st.write(result)
