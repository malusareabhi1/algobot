import pandas as pd
import matplotlib.pyplot as plt

def load_data(file):
    df = pd.read_csv(file)
    df['Datetime'] = pd.to_datetime(df['Datetime'])
    df.set_index('Datetime', inplace=True)
    return df

def run_backtest(df):
    buy_signals = []
    sell_signals = []
    for i in range(20, len(df)):
        if df['Close'][i] > df['Close'][i-20:i].mean():  # simple 20 SMA breakout
            buy_signals.append(df['Close'][i])
            sell_signals.append(None)
        else:
            buy_signals.append(None)
            sell_signals.append(df['Close'][i])
    df['Buy'] = buy_signals
    df['Sell'] = sell_signals

    fig, ax = plt.subplots()
    ax.plot(df['Close'], label="Close Price")
    ax.plot(df['Buy'], marker="^", color="g", label="Buy", linestyle="None")
    ax.plot(df['Sell'], marker="v", color="r", label="Sell", linestyle="None")
    ax.legend()

    return {"metrics": {"Trades": df['Buy'].count()}, "chart": fig}

def run_live_trade():
    # To be integrated with Zerodha or paper trade engine
    pass
