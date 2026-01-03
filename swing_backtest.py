import yfinance as yf
import pandas as pd
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator

CAPITAL = 200000
RISK_PER_TRADE = 0.01

symbols = [
    "NTPC.NS","GAIL.NS","RAILTEL.NS","IRFC.NS",
    "POWERGRID.NS","COALINDIA.NS","IOC.NS"
]

trades = []

for sym in symbols:
    df = yf.download(sym, period="3y", interval="1d")
    df.dropna(inplace=True)

    df["ema20"] = EMAIndicator(df["Close"], 20).ema_indicator()
    df["ema50"] = EMAIndicator(df["Close"], 50).ema_indicator()
    df["rsi"] = RSIIndicator(df["Close"], 14).rsi()
    df["avg_vol"] = df["Volume"].rolling(20).mean()

    for i in range(60, len(df)-1):
        row = df.iloc[i]

        if (
            row["Close"] > row["ema50"]
            and row["ema20"] > row["ema50"]
            and abs(row["Close"] - row["ema20"]) / row["ema20"] < 0.01
            and 45 < row["rsi"] < 60
            and row["Volume"] > 1.2 * row["avg_vol"]
        ):
            entry = df.iloc[i+1]["Open"]
            sl = df["Low"].iloc[i-5:i].min()
            risk = entry - sl

            if risk <= 0:
                continue

            qty = int((CAPITAL * RISK_PER_TRADE) / risk)
            target = entry + 2 * risk

            exit_price = None
            exit_date = None
            result = None

            for j in range(i+1, len(df)):
                low = df.iloc[j]["Low"]
                high = df.iloc[j]["High"]

                if low <= sl:
                    exit_price = sl
                    result = "LOSS"
                    exit_date = df.index[j]
                    break
                elif high >= target:
                    exit_price = target
                    result = "WIN"
                    exit_date = df.index[j]
                    break

            pnl = (exit_price - entry) * qty if exit_price else 0

            trades.append({
                "Stock": sym.replace(".NS",""),
                "Entry": entry,
                "Exit": exit_price,
                "Qty": qty,
                "PnL": pnl,
                "Result": result
            })
