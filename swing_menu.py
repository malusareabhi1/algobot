import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta import trend, momentum, volatility
from datetime import date, timedelta
from ta.momentum import RSIIndicator

# ========== STRATEGY DEFINITIONS ==========

def sma_crossover(df):
    df['SMA50'] = df['Close'].rolling(50).mean()
    df['SMA200'] = df['Close'].rolling(200).mean()
    df['Signal'] = np.where(df['SMA50'] > df['SMA200'], 1, 0)
    df['Signal'] = df['Signal'].fillna(0)  # Ensures no NaNs
    return df


def ema_crossover(df):
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['EMA50'] = df['Close'].ewm(span=50).mean()
    df['Signal'] = np.where(df['EMA20'] > df['EMA50'], 1, 0)
    return df

def rsi_strategy(df):
    # Ensure 'Close' is a 1D Series
    close_series = df['Close']

    # Compute RSI using 1D series
    rsi = RSIIndicator(close=close_series, window=14).rsi()
    df['RSI'] = rsi

    # Generate buy/sell signals
    df['Signal'] = np.where(df['RSI'] < 30, 1,
                    np.where(df['RSI'] > 70, 0, np.nan))

    # Fill missing signals forward, then default to no position
    df['Signal'] = df['Signal'].ffill().fillna(0)

    return df

def macd_strategy(df):
    macd = trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['Signal_Line'] = macd.macd_signal()
    df['Signal'] = np.where(df['MACD'] > df['Signal_Line'], 1, 0)
    return df

def bollinger_band_strategy(df):
    bb = volatility.BollingerBands(df['Close'])
    df['bb_low'] = bb.bollinger_lband()
    df['bb_high'] = bb.bollinger_hband()
    df['Signal'] = np.where(df['Close'] < df['bb_low'], 1, np.where(df['Close'] > df['bb_high'], 0, np.nan))
    df['Signal'] = df['Signal'].ffill()
    return df

def donchian_channel(df):
    df['DC_high'] = df['High'].rolling(20).max()
    df['DC_low'] = df['Low'].rolling(20).min()
    df['Signal'] = np.where(df['Close'] > df['DC_high'], 1, np.where(df['Close'] < df['DC_low'], 0, np.nan))
    df['Signal'] = df['Signal'].ffill()
    return df

def adx_strategy(df):
    adx = trend.ADXIndicator(df['High'], df['Low'], df['Close'])
    df['ADX'] = adx.adx()
    df['Signal'] = np.where(df['ADX'] > 25, 1, 0)
    return df

def stochastic_strategy(df):
    stoch = momentum.StochasticOscillator(df['High'], df['Low'], df['Close'])
    df['stoch'] = stoch.stoch()
    df['Signal'] = np.where(df['stoch'] < 20, 1, np.where(df['stoch'] > 80, 0, np.nan))
    df['Signal'] = df['Signal'].ffill()
    return df

def cci_strategy(df):
    cci = trend.CCIIndicator(df['High'], df['Low'], df['Close'])
    df['CCI'] = cci.cci()
    df['Signal'] = np.where(df['CCI'] < -100, 1, np.where(df['CCI'] > 100, 0, np.nan))
    df['Signal'] = df['Signal'].ffill()
    return df

def atr_trend_follow(df):
    atr = volatility.AverageTrueRange(df['High'], df['Low'], df['Close'])
    df['ATR'] = atr.average_true_range()
    df['Upper'] = df['Close'].rolling(10).mean() + 1.5 * df['ATR']
    df['Lower'] = df['Close'].rolling(10).mean() - 1.5 * df['ATR']
    df['Signal'] = np.where(df['Close'] > df['Upper'], 1, np.where(df['Close'] < df['Lower'], 0, np.nan))
    df['Signal'] = df['Signal'].ffill()
    return df

# ========== BACKTESTING FUNCTION ==========

def backtest(df):
    if 'Signal' not in df.columns:
        raise ValueError("No Signal column found.")
    df['Position'] = df['Signal'].shift(1).fillna(0)
    df['Return'] = df['Close'].pct_change().fillna(0)
    df['Strategy'] = df['Position'] * df['Return']
    df['Cumulative'] = (1 + df['Strategy']).cumprod()
    return df

# ========== STREAMLIT UI ==========

st.title("📈 Swing Trading Strategy Tester (Live Data)")
st.markdown("Test 10 swing trading strategies on selected stock with live Yahoo Finance data.")

symbol = st.text_input("Enter stock ticker (e.g., AAPL, INFY.NS):", "AAPL")
start_date = st.date_input("Start Date", date.today() - timedelta(days=365))
end_date = st.date_input("End Date", date.today())

if st.button("Run Backtests"):
    with st.spinner("Fetching data and running strategies..."):
        df = yf.download(symbol, start=start_date, end=end_date)
        results = {}
        strategies = {
            "SMA Crossover": sma_crossover,
            "EMA Crossover": ema_crossover,
            "RSI Strategy": rsi_strategy,
            "MACD Strategy": macd_strategy,
            "Bollinger Bands": bollinger_band_strategy,
            "Donchian Channel": donchian_channel,
            "ADX Strategy": adx_strategy,
            "Stochastic Oscillator": stochastic_strategy,
            "CCI Strategy": cci_strategy,
            "ATR Trend Follow": atr_trend_follow,
        }

        for name, func in strategies.items():
            df_copy = df.copy()
            try:
                strat_df = func(df_copy)
                strat_df = backtest(strat_df)
                final_return = strat_df['Cumulative'].iloc[-1] if 'Cumulative' in strat_df else 1
                results[name] = final_return
                if 'Cumulative' in strat_df.columns:
                    st.subheader(f"📉 {name}")
                    st.line_chart(strat_df['Cumulative'].dropna(), height=200, use_container_width=True)
                else:
                    st.warning(f"{name} did not return cumulative results.")
            except Exception as e:
                results[name] = np.nan
                st.error(f"{name} failed: {e}")


        result_df = pd.DataFrame.from_dict(results, orient='index', columns=['Cumulative Return'])
        result_df = result_df.sort_values(by='Cumulative Return', ascending=False)
        st.subheader("📊 Strategy Performance")
        st.dataframe(result_df.style.format("{:.2f}x"))
