import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Candlestick pattern detection functions
def is_doji(df):
    body = abs(df['Close'] - df['Open'])
    range_ = df['High'] - df['Low']
    return (body <= 0.1 * range_)

def is_hammer(df):
    body = abs(df['Close'] - df['Open'])
    lower_shadow = np.minimum(df['Open'], df['Close']) - df['Low']
    upper_shadow = df['High'] - np.maximum(df['Open'], df['Close'])
    condition = (lower_shadow > 2 * body) & (upper_shadow < 0.5 * body)
    return condition

def is_bullish_engulfing(df):
    prev_open = df['Open'].shift(1)
    prev_close = df['Close'].shift(1)
    condition = (prev_close < prev_open) & \
                (df['Close'] > df['Open']) & \
                (df['Close'] > prev_open) & \
                (df['Open'] < prev_close)
    return condition

def is_bearish_engulfing(df):
    prev_open = df['Open'].shift(1)
    prev_close = df['Close'].shift(1)
    condition = (prev_close > prev_open) & \
                (df['Close'] < df['Open']) & \
                (df['Open'] > prev_close) & \
                (df['Close'] < prev_open)
    return condition

# Sample NIFTY 200 list (extend as needed)
nifty_200 = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'HINDUNILVR.NS', 'SBIN.NS', 'KOTAKBANK.NS', 'LT.NS', 'AXISBANK.NS'
]

st.title("NIFTY 200 Candlestick Pattern Detector")

selected_stocks = st.multiselect("Select Stocks (NIFTY 200)", nifty_200, default=nifty_200[:5])
start_date = st.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.date_input("End Date", pd.to_datetime("today"))
interval = st.selectbox("Data Interval", ['1d', '5m'], index=0)

if st.button("Run Pattern Detection"):
    all_results = []
    progress_bar = st.progress(0)
    total = len(selected_stocks)

    stock_data = {}  # Store df with patterns for each stock

    for i, symbol in enumerate(selected_stocks):
        try:
            df = yf.download(symbol, start=start_date, end=end_date, interval=interval, progress=False)
            if df.empty:
                st.warning(f"No data for {symbol}")
                continue
            
            df.reset_index(inplace=True)

            # Detect patterns
            df['Doji'] = is_doji(df)
            df['Hammer'] = is_hammer(df)
            df['Bullish_Engulfing'] = is_bullish_engulfing(df)
            df['Bearish_Engulfing'] = is_bearish_engulfing(df)

            stock_data[symbol] = df

            # Collect detected patterns
            for pattern in ['Doji', 'Hammer', 'Bullish_Engulfing', 'Bearish_Engulfing']:
                pattern_dates = df[df[pattern]][['Date', 'Open', 'High', 'Low', 'Close']]
                for idx, row in pattern_dates.iterrows():
                    all_results.append({
                        'Stock': symbol,
                        'Date': row['Date'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(row['Date'], pd.Timestamp) else str(row['Date']),
                        'Pattern': pattern,
                        'Open': row['Open'],
                        'High': row['High'],
                        'Low': row['Low'],
                        'Close': row['Close'],
                    })

        except Exception as e:
            st.error(f"Error processing {symbol}: {e}")

        progress_bar.progress((i + 1) / total)

    if all_results:
        result_df = pd.DataFrame(all_results)
        st.subheader("Detected Patterns Summary")
        st.dataframe(result_df.sort_values(by=['Date', 'Stock']))

    else:
        st.info("No patterns detected in selected stocks and date range.")

    # Show candle charts for each stock with pattern markers
    for symbol, df in stock_data.items():
        with st.expander(f"Candlestick Chart for {symbol}"):
            fig = go.Figure(data=[go.Candlestick(
                x=df['Date'],
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name=symbol
            )])

            # Add markers for patterns
            for pattern, color in zip(['Doji', 'Hammer', 'Bullish_Engulfing', 'Bearish_Engulfing'],
                                      ['yellow', 'lime', 'cyan', 'magenta']):
                pattern_dates = df.loc[df[pattern], 'Date']
                pattern_prices = df.loc[df[pattern], 'Close']
                fig.add_trace(go.Scatter(
                    x=pattern_dates,
                    y=pattern_prices,
                    mode='markers',
                    marker=dict(size=10, color=color, symbol='star'),
                    name=pattern
                ))

            fig.update_layout(title=f'Candlestick Chart with Patterns for {symbol}',
                              xaxis_title='Date',
                              yaxis_title='Price',
                              height=600)
            st.plotly_chart(fig, use_container_width=True)
