def apply_strategy(df):
    df = df.copy()
    df.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'], inplace=True)

    # Skip processing if not enough candles
    if df['Close'].isnull().sum() > 0 or len(df['Close']) < 50:
        df['buy'] = False
        return df

    # Calculate Indicators
    df['20ema'] = df['Close'].ewm(span=20).mean()
    df['50ema'] = df['Close'].ewm(span=50).mean()
    df['200sma'] = df['Close'].rolling(window=200).mean()
    df['bb_mid'] = df['Close'].rolling(window=20).mean()
    df['bb_std'] = df['Close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']

    # Safe RSI
    try:
        rsi = RSIIndicator(close=df['Close'].astype(float), window=14)
        df['rsi'] = rsi.rsi()
    except Exception as e:
        df['rsi'] = pd.Series([None] * len(df), index=df.index)

    # Safe MACD
    try:
        macd = MACD(close=df['Close'].astype(float))
        df['macd'] = macd.macd()
        df['signal'] = macd.macd_signal()
    except Exception as e:
        df['macd'] = df['signal'] = pd.Series([None] * len(df), index=df.index)

    # Signal logic
    df['buy'] = (
        (df['Close'] > df['bb_upper']) &
        (df['Close'] > df['20ema']) &
        (df['20ema'] > df['50ema']) &
        (df['50ema'] > df['200sma']) &
        (df['macd'] > df['signal']) &
        (df['rsi'] > 55) & (df['rsi'] < 70)
    )

    df['buy'] = df['buy'].fillna(False)
    return df
