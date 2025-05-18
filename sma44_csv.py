import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def generate_signals(data):
    data['MA44'] = data['Close'].rolling(window=44).mean()
    data['RSI'] = calculate_rsi(data)
    data['Signal'] = np.nan
    data['Position'] = 0  # 1 for buy, -1 for sell

    for i in range(1, len(data)):
        curr_close = data['Close'].iloc[i]
        prev_close = data['Close'].iloc[i - 1]
        curr_ma = data['MA44'].iloc[i]
        prev_ma = data['MA44'].iloc[i - 1]
        curr_rsi = data['RSI'].iloc[i]

        if pd.notna(curr_ma) and pd.notna(prev_ma) and pd.notna(curr_rsi):
            if curr_close > curr_ma and curr_rsi > 50 and prev_close <= prev_ma:
                data.at[data.index[i], 'Signal'] = 'Buy'
                data.at[data.index[i], 'Position'] = 1

            elif curr_close < curr_ma and curr_rsi < 50 and prev_close >= prev_ma:
                data.at[data.index[i], 'Signal'] = 'Sell'
                data.at[data.index[i], 'Position'] = 0
            else:
                data.at[data.index[i], 'Position'] = data.at[data.index[i - 1], 'Position']
        else:
            data.at[data.index[i], 'Position'] = data.at[data.index[i - 1], 'Position']

    return data
def backtest_strategy(data, initial_capital=100000):
    data['Returns'] = data['Close'].pct_change()
    data['Strategy_Returns'] = data['Returns'] * data['Position'].shift(1)
    data['Equity_Curve'] = (1 + data['Strategy_Returns']).cumprod() * initial_capital
    data['Strategy_PnL'] = data['Equity_Curve'].diff().fillna(0)
    return data
st.title("MA44 + RSI Strategy Backtest")

uploaded_file = st.file_uploader("Upload your CSV", type=['csv'])
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, parse_dates=True, index_col=0)
    df = generate_signals(df)
    df = backtest_strategy(df)

    st.subheader("Sample Data with Signals")
    st.write(df.tail())

    st.subheader("Equity Curve")
    fig, ax = plt.subplots()
    ax.plot(df['Equity_Curve'], label='Equity Curve')
    ax.set_title('Equity Curve')
    ax.set_xlabel('Date')
    ax.set_ylabel('Portfolio Value')
    ax.legend()
    st.pyplot(fig)

    total_return = df['Equity_Curve'].iloc[-1] - df['Equity_Curve'].iloc[0]
    st.metric("Total Profit/Loss", f"₹ {total_return:,.2f}")
