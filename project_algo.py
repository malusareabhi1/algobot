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
        "Dashboard", "Get Stock Data", "Doctor Strategy","Doctor1.0 Strategy","Doctor2.0 Strategy","Doctor3.0 Strategy", "Swing Trade Strategy", "Swing SMA44 Strategy","New Nifty Strategy",
        "Intraday Stock Finder","ORB Strategy","ORB Screener", "Trade Log", "Account Info", "Candle Chart", "Strategy Detail","Strategy2.0 Detail", "Project Detail", "KITE API", "API","Alpha Vantage API","Live Algo Trading","Paper Trade","Volatility Scanner","TradingView","Telegram Demo","NIFTY PCR"
    ],
    icons=[
        "bar-chart", "search", "cpu", "cpu","cpu", "cpu","cpu","cpu","cpu", "arrow-repeat",
        "search", "clipboard-data", "wallet2", "graph-up", "info-circle", "search","file-earmark","file-earmark", "code-slash", "code-slash", "code-slash","journal-text","search", "bar-chart", "bar-chart","file-earmark", "bar-chart"
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


if selected == "Dashboard":
    st.subheader("📊 Dashboard - Zerodha Account Overview")       
    # Get current time in UTC
    #utc_now = datetime.datetime.utcnow()
    
    # Define the Indian time zone
    #ist_timezone = pytz.timezone('Asia/Kolkata')
    
    # Localize the UTC time to IST
    #ist_now = utc_now.replace(tzinfo=pytz.utc).astimezone(ist_timezone)
    
    # Display the time in Streamlit
    #st.write("Current time in IST:", ist_now.strftime("%Y-%m-%d %H:%M:%S %Z%z"))
    if "kite" in st.session_state and st.session_state.kite is not None:
        kite = st.session_state.kite

        # ✅ Funds
        try:
            funds = kite.margins(segment="equity")
            available_cash = funds['available']['cash']
            st.metric("💰 Available Fund", f"₹ {available_cash:,.2f}")
        except Exception as e:
            st.error(f"Failed to fetch funds: {e}")

        # ✅ Holdings
        try:
            holdings = kite.holdings()
            if holdings:
                df_holdings = pd.DataFrame(holdings)
                df_holdings = df_holdings[["tradingsymbol", "quantity", "average_price", "last_price", "pnl"]]
                df_holdings["holding_value"] = df_holdings["quantity"] * df_holdings["last_price"]

                total_holding_value = df_holdings["holding_value"].sum()
                total_pnl = df_holdings["pnl"].sum()

                st.metric("📦 Total Holding Value", f"₹ {total_holding_value:,.2f}")
                st.metric("📈 Total P&L", f"₹ {total_pnl:,.2f}", delta_color="normal")

                st.write("📄 Your Holdings:")
                st.dataframe(
                    df_holdings.style.format({
                        "average_price": "₹{:.2f}",
                        "last_price": "₹{:.2f}",
                        "pnl": "₹{:.2f}",
                        "holding_value": "₹{:.2f}"
                    }),
                    use_container_width=True
                )
            else:
                st.info("No holdings available.")
        except Exception as e:
            st.error(f"Failed to fetch holdings: {e}")
            # ✅ Orders
        try:
            st.subheader("🧾 Recent Orders")
            orders = kite.orders()
            if orders:
                df_orders = pd.DataFrame(orders)
                df_orders = df_orders[["order_id", "tradingsymbol", "transaction_type", "quantity", "price", "status", "order_timestamp"]]
                df_orders = df_orders.sort_values(by="order_timestamp", ascending=False)
                st.dataframe(df_orders.head(10), use_container_width=True)
            else:
                st.info("No recent orders found.")
        except Exception as e:
            st.error(f"Failed to fetch orders: {e}")

        # ✅ Positions
        try:
            st.subheader("📌 Net Positions")
            positions = kite.positions()
            net_positions = positions['net']
            if net_positions:
                df_positions = pd.DataFrame(net_positions)
                df_positions = df_positions[["tradingsymbol", "quantity", "average_price", "last_price", "pnl"]]
                st.dataframe(
                    df_positions.style.format({
                        "average_price": "₹{:.2f}",
                        "last_price": "₹{:.2f}",
                        "pnl": "₹{:.2f}"
                    }),
                    use_container_width=True
                )
            else:
                st.info("No open positions.")
        except Exception as e:
            st.error(f"Failed to fetch positions: {e}")

                    # 📈 Live NIFTY 50 Price Chart
        st.subheader("📈 Live NIFTY 50 Chart")

       

        # Setup live prices tracking
        if 'live_prices' not in st.session_state:
            st.session_state.live_prices = []

        if 'ws_started' not in st.session_state:
            def start_websocket():
                try:
                    kws = KiteTicker(api_key, st.session_state.access_token)
                    
                    def on_ticks(ws, ticks):
                        for tick in ticks:
                            price = tick['last_price']
                            timestamp = datetime.now()
                            st.session_state.live_prices.append((timestamp, price))
                            if len(st.session_state.live_prices) > 100:
                                st.session_state.live_prices.pop(0)

                    def on_connect(ws, response):
                        ws.subscribe([256265])  # Token for NIFTY 50 spot

                    def on_close(ws, code, reason):
                        print("WebSocket closed:", reason)

                    kws.on_ticks = on_ticks
                    kws.on_connect = on_connect
                    kws.on_close = on_close
                    kws.connect(threaded=True)
                except Exception as e:
                    print("WebSocket Error:", e)

            thread = threading.Thread(target=start_websocket, daemon=True)
            thread.start()
            st.session_state.ws_started = True

        # Display the chart
        def show_chart():
            if st.session_state.live_prices:
                df = pd.DataFrame(st.session_state.live_prices, columns=["Time", "Price"])
                fig = go.Figure(data=[go.Scatter(x=df["Time"], y=df["Price"], mode="lines+markers")])
                fig.update_layout(title="NIFTY 50 Live Price", xaxis_title="Time", yaxis_title="Price", height=400)
                st.plotly_chart(fig, use_container_width=True)

        show_chart()


    else:
        st.warning("Please login to Kite Connect first.")

elif selected == "NIFTY PCR":
        # Fetch last 30 trading days of NIFTY data
    nifty = yf.download("^NSEI", period="1mo", interval="1d")
    nifty = nifty[["Close"]].dropna().reset_index()
    nifty.rename(columns={"Date": "date", "Close": "nifty_close"}, inplace=True)
    
    # Simulate PCR data (in real case, fetch from NSE or data vendor)
    np.random.seed(42)
    pcr_values = np.round(np.random.uniform(0.8, 1.3, size=len(nifty)), 2)
    nifty["pcr"] = pcr_values
    
    # Plot
    fig, ax1 = plt.subplots(figsize=(10, 5))
    
    # Nifty line
    ax1.set_xlabel("Date")
    ax1.set_ylabel("NIFTY Close", color="tab:blue")
    ax1.plot(nifty["date"], nifty["nifty_close"], color="tab:blue", label="NIFTY Close")
    ax1.tick_params(axis="y", labelcolor="tab:blue")
    
    # PCR on secondary y-axis
    ax2 = ax1.twinx()
    ax2.set_ylabel("PCR", color="tab:red")
    ax2.plot(nifty["date"], nifty["pcr"], color="tab:red", linestyle="--", label="PCR")
    ax2.tick_params(axis="y", labelcolor="tab:red")
    ax2.axhline(1, color='gray', linestyle='--', linewidth=0.7)
    
    # Title and legend
    fig.suptitle("📅 NIFTY Closing Price vs PCR (Simulated for 1 Month)")
    fig.tight_layout()
    st.pyplot(fig)
    
    # Show data
    with st.expander("📋 View Data Table"):
        st.dataframe(nifty)


    
    

    

elif selected == "Telegram Demo":
    # --- Streamlit App ---
    #st.set_page_config(page_title="Indian Market Dashboard", layout="centered")
    st.write("📈 Indian Market Dashboard")
    st.write("Live stock/index prices + Telegram update")
    
    # Load environment variables
    load_dotenv()
    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN_demo")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID_demo")
    
    # Function to send a Telegram message
    def send_telegram_message(message):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
        r = requests.post(url, data=payload)
        return r.ok
    
    # Get stock/index data using yfinance
    def get_market_data():
        indices = {
            'NIFTY 50': '^NSEI',
            'BANK NIFTY': '^NSEBANK',
            'SENSEX': '^BSESN',
            'ADANIENT': 'ADANIENT.NS',
            'ADANIPORTS': 'ADANIPORTS.NS',
            'ASIANPAINT': 'ASIANPAINT.NS',
            'AXISBANK': 'AXISBANK.NS',
            'BAJAJ-AUTO': 'BAJAJ-AUTO.NS',
            'BAJFINANCE': 'BAJFINANCE.NS',
            'BAJAJFINSV': 'BAJAJFINSV.NS',
            'BPCL': 'BPCL.NS',
            'BHARTIARTL': 'BHARTIARTL.NS',
            'BRITANNIA': 'BRITANNIA.NS',
            'CIPLA': 'CIPLA.NS',
            'COALINDIA': 'COALINDIA.NS',
            'DIVISLAB': 'DIVISLAB.NS',
            'DRREDDY': 'DRREDDY.NS',
            'EICHERMOT': 'EICHERMOT.NS',
            'GRASIM': 'GRASIM.NS',
            'HCLTECH': 'HCLTECH.NS',
            'HDFCBANK': 'HDFCBANK.NS',
            'HDFCLIFE': 'HDFCLIFE.NS',
            'HEROMOTOCO': 'HEROMOTOCO.NS',
            'HINDALCO': 'HINDALCO.NS',
            'HINDUNILVR': 'HINDUNILVR.NS',
            'ICICIBANK': 'ICICIBANK.NS',
            'ITC': 'ITC.NS',
            'INDUSINDBK': 'INDUSINDBK.NS',
            'INFY': 'INFY.NS',
            'JSWSTEEL': 'JSWSTEEL.NS',
            'KOTAKBANK': 'KOTAKBANK.NS',
            'LT': 'LT.NS',
            'M&M': 'M&M.NS',
            'MARUTI': 'MARUTI.NS',
            'NTPC': 'NTPC.NS',
            'NESTLEIND': 'NESTLEIND.NS',
            'ONGC': 'ONGC.NS',
            'POWERGRID': 'POWERGRID.NS',
            'RELIANCE': 'RELIANCE.NS',
            'SBILIFE': 'SBILIFE.NS',
            'SBIN': 'SBIN.NS',
            'SUNPHARMA': 'SUNPHARMA.NS',
            'TCS': 'TCS.NS',
            'TATACONSUM': 'TATACONSUM.NS',
            'TATAMOTORS': 'TATAMOTORS.NS',
            'TATASTEEL': 'TATASTEEL.NS',
            'TECHM': 'TECHM.NS',
            'TITAN': 'TITAN.NS',
            'UPL': 'UPL.NS',
            'ULTRACEMCO': 'ULTRACEMCO.NS',
            'WIPRO': 'WIPRO.NS'
        }
    
        message = "*📊 Indian Market Snapshot 📈*\n\n"
        market_list = []
    
        for name, symbol in indices.items():
            ticker = yf.Ticker(symbol)
            info = ticker.info
    
            price = info.get("regularMarketPrice")
            change = info.get("regularMarketChange")
            percent = info.get("regularMarketChangePercent")
            volume = info.get("volume")
    
            if price is not None and percent is not None:
                row = {
                    "Name": name,
                    "Price (₹)": round(price, 2),
                    "Change": f"{change:+.2f}",
                    "Change %": f"{percent:+.2f}%",
                    "Volume": volume if volume is not None else "N/A",
                    "percent_numeric": percent
                }
                market_list.append(row)
    
        # Sort by Change % numeric descending
        market_list.sort(key=lambda x: x["percent_numeric"], reverse=True)
    
        # Build Telegram message from sorted data
        message = "*📊 Indian Market Snapshot 📈*\n\n"
        for row in market_list:
            emoji = "🟢" if row["percent_numeric"] >= 0 else "🔴"
            message += (f"{emoji} *{row['Name']}*: ₹{row['Price (₹)']:.2f} "
                        f"({row['Change']}, {row['Change %']}), Vol: {row['Volume']}\n")
    
        # Remove helper key before returning data for DataFrame
        for row in market_list:
            del row["percent_numeric"]
    
        return market_list, message
    # Fetch data
    market_data, message = get_market_data()
    
    # Convert to DataFrame
    df = pd.DataFrame(market_data)
    
    # Convert 'Change %' to float for sorting (strip % sign)
    df["Change % (numeric)"] = df["Change %"].str.replace('%', '').astype(float)
    
    # Sort by Change % descending (highest first)
    df = df.sort_values(by="Change % (numeric)", ascending=False)
    
    # Drop the helper column before display (optional)
    df = df.drop(columns=["Change % (numeric)"])
    
    # Color formatting: red for negative, green for positive
    def highlight_change(val):
        try:
            val_float = float(val.strip('%'))
            return 'color: green;' if val_float > 0 else 'color: red;'
        except:
            return ''
    
    # Display styled dataframe
    #st.dataframe(
       # df.style.applymap(highlight_change, subset=["Change", "Change %"])
    #)
    # Convert to DataFrame
    df = pd.DataFrame(market_data)
    
    # Convert 'Change %' to float for sorting (strip % sign and convert)
    df["Change % (numeric)"] = df["Change %"].str.replace('%', '', regex=False).astype(float)
    
    # Sort by % change descending
    df = df.sort_values(by="Change % (numeric)", ascending=False)
    
    # Drop the helper column before display
    df_display = df.drop(columns=["Change % (numeric)"])
    
    # Apply text color formatting
    def text_color(row):
        color = 'color: green' if row["Change %"].startswith('+') else 'color: red'
        return [color] * len(row)
    
    # Display styled table
    #st.dataframe(df_display.style.apply(row_color, axis=1))
    # Display styled dataframe in Streamlit with colored text
    st.dataframe(df_display.style.apply(text_color, axis=1))
    
    # Refresh every 5 minutes
    st_autorefresh(interval=5 * 60 * 1000, key="datarefresh")
    # Send update to Telegram
    send_telegram_message(message)
    # Display in Streamlit
    #st.table(market_data)
    
    # Manual send button
    if st.button("📤 Send Market Data to Telegram"):
        success = send_telegram_message(message)
        if success:
            st.success("Message sent to Telegram successfully!")
        else:
            st.error("Failed to send message. Check bot token and chat ID.")

elif selected == "Swing SMA44 Strategy":
    def scan_bhanushali_strategy(stock):
        # Download historical stock data
        df = yf.download(stock, period='90d', interval='1d')
        if df.empty:
            return None  # Skip if no data returned
    
        # Calculate the 44-period SMA
        df['SMA44'] = df['Close'].rolling(window=44).mean()
    
        # Drop rows with NaN values (if any)
        df.dropna(inplace=True)
    
        if len(df) < 2:
            return None  # Not enough data
    
        last_candle = df.iloc[-1]  # Get the most recent candle (row)
        prev_candle = df.iloc[-2]  # Get the previous candle (row)
    
        # Ensure you're working with scalar values
        low = last_candle['Low']
        close = last_candle['Close']
        sma44 = last_candle['SMA44']
    
        # Ensure values are scalar (individual numbers)
        if isinstance(low, pd.Series): low = low.values[0]
        if isinstance(close, pd.Series): close = close.values[0]
        if isinstance(sma44, pd.Series): sma44 = sma44.values[0]
    
        # Condition: low < SMA44 < close (candle near rising 44 SMA)
        if low < sma44 < close:
            # Buy above the high of the candle, stoploss below the low of the candle
            #entry = last_candle['High']
            #stoploss = low
            entry = float(last_candle['High'])       # entry as scalar
            stoploss = float(last_candle['Low'])     # stoploss as scalar
    
    
            # Calculate targets based on a 1:2 and 1:3 risk-reward ratio
            target1 = entry + (entry - stoploss) * 2
            target2 = entry + (entry - stoploss) * 3
    
            # Return a dictionary with the results
            return {
                'symbol': stock,
                'entry': round(entry, 2),
                'stoploss': round(stoploss, 2),
                'target_1_2': round(target1, 2),
                'target_1_3': round(target2, 2)
            }
    
        return None
    
    # Example usage with a list of NIFTY 100 stocks
    #nifty_100 = [
        
    nifty_100 = [
    '360ONE.NS',
    '3MINDIA.NS',
    'ABB.NS',
    'ACC.NS',
    'ACMESOLAR.NS',
    'AIAENG.NS',
    'APLAPOLLO.NS',
    'AUBANK.NS',
    'AWL.NS',
    'AADHARHFC.NS',
    'AARTIIND.NS',
    'AAVAS.NS',
    'ABBOTINDIA.NS',
    'ACE.NS',
    'ADANIENSOL.NS',
    'ADANIENT.NS',
    'ADANIGREEN.NS',
    'ADANIPORTS.NS',
    'ADANIPOWER.NS',
    'ATGL.NS',
    'ABCAPITAL.NS',
    'ABFRL.NS',
    'ABREL.NS',
    'ABSLAMC.NS',
    'AEGISLOG.NS',
    'AFCONS.NS',
    'AFFLE.NS',
    'AJANTPHARM.NS',
    'AKUMS.NS',
    'APLLTD.NS',
    'ALIVUS.NS',
    'ALKEM.NS',
    'ALKYLAMINE.NS',
    'ALOKINDS.NS',
    'ARE&M.NS',
    'AMBER.NS',
    'AMBUJACEM.NS',
    'ANANDRATHI.NS',
    'ANANTRAJ.NS',
    'ANGELONE.NS',
    'APARINDS.NS',
    'APOLLOHOSP.NS',
    'APOLLOTYRE.NS',
    'APTUS.NS',
    'ASAHIINDIA.NS',
    'ASHOKLEY.NS',
    'ASIANPAINT.NS',
    'ASTERDM.NS',
    'ASTRAZEN.NS',
    'ASTRAL.NS',
    'ATUL.NS',
    'AUROPHARMA.NS',
    'AIIL.NS',
    'DMART.NS',
    'AXISBANK.NS',
    'BASF.NS',
    'BEML.NS',
    'BLS.NS',
    'BSE.NS',
    'BAJAJ-AUTO.NS',
    'BAJFINANCE.NS',
    'BAJAJFINSV.NS',
    'BAJAJHLDNG.NS',
    'BAJAJHFL.NS',
    'BALKRISIND.NS',
    'BALRAMCHIN.NS',
    'BANDHANBNK.NS',
    'BANKBARODA.NS',
    'BANKINDIA.NS',
    'MAHABANK.NS',
    'BATAINDIA.NS',
    'BAYERCROP.NS',
    'BERGEPAINT.NS',
    'BDL.NS',
    'BEL.NS',
    'BHARATFORG.NS',
    'BHEL.NS',
    'BPCL.NS',
    'BHARTIARTL.NS',
    'BHARTIHEXA.NS',
    'BIKAJI.NS',
    'BIOCON.NS',
    'BSOFT.NS',
    'BLUEDART.NS',
    'BLUESTARCO.NS',
    'BBTC.NS',
    'BOSCHLTD.NS',
    'FIRSTCRY.NS',
    'BRIGADE.NS',
    'BRITANNIA.NS',
    'MAPMYINDIA.NS',
    'CCL.NS',
    'CESC.NS',
    'CGPOWER.NS',
    'CRISIL.NS',
    'CAMPUS.NS',
    'CANFINHOME.NS',
    'CANBK.NS',
    'CAPLIPOINT.NS',
    'CGCL.NS',
    'CARBORUNIV.NS',
    'CASTROLIND.NS',
    'CEATLTD.NS',
    'CENTRALBK.NS',
    'CDSL.NS',
    'CENTURYPLY.NS',
    'CERA.NS',
    'CHALET.NS',
    'CHAMBLFERT.NS',
    'CHENNPETRO.NS',
    'CHOLAHLDNG.NS',
    'CHOLAFIN.NS',
    'CIPLA.NS',
    'CUB.NS',
    'CLEAN.NS',
    'COALINDIA.NS',
    'COCHINSHIP.NS',
    'COFORGE.NS',
    'COHANCE.NS',
    'COLPAL.NS',
    'CAMS.NS',
    'CONCORDBIO.NS',
    'CONCOR.NS',
    'COROMANDEL.NS',
    'CRAFTSMAN.NS',
    'CREDITACC.NS',
    'CROMPTON.NS',
    'CUMMINSIND.NS',
    'CYIENT.NS',
    'DCMSHRIRAM.NS',
    'DLF.NS',
    'DOMS.NS',
    'DABUR.NS',
    'DALBHARAT.NS',
    'DATAPATTNS.NS',
    'DEEPAKFERT.NS',
    'DEEPAKNTR.NS',
    'DELHIVERY.NS',
    'DEVYANI.NS',
    'DIVISLAB.NS',
    'DIXON.NS',
    'LALPATHLAB.NS',
    'DRREDDY.NS',
    'DUMMYABFRL.NS',
    'DUMMYSIEMS.NS',
    'DUMMYRAYMN.NS',
    'EIDPARRY.NS',
    'EIHOTEL.NS',
    'EICHERMOT.NS',
    'ELECON.NS',
    'ELGIEQUIP.NS',
    'EMAMILTD.NS',
    'EMCURE.NS',
    'ENDURANCE.NS',
    'ENGINERSIN.NS',
    'ERIS.NS',
    'ESCORTS.NS',
    'ETERNAL.NS',
    'EXIDEIND.NS',
    'NYKAA.NS',
    'FEDERALBNK.NS',
    'FACT.NS',
    'FINCABLES.NS',
    'FINPIPE.NS',
    'FSL.NS',
    'FIVESTAR.NS',
    'FORTIS.NS',
    'GAIL.NS',
    'GVT&D.NS',
    'GMRAIRPORT.NS',
    'GRSE.NS',
    'GICRE.NS',
    'GILLETTE.NS',
    'GLAND.NS',
    'GLAXO.NS',
    'GLENMARK.NS',
    'MEDANTA.NS',
    'GODIGIT.NS',
    'GPIL.NS',
    'GODFRYPHLP.NS',
    'GODREJAGRO.NS',
    'GODREJCP.NS',
    'GODREJIND.NS',
    'GODREJPROP.NS',
    'GRANULES.NS',
    'GRAPHITE.NS',
    'GRASIM.NS',
    'GRAVITA.NS',
    'GESHIP.NS',
    'FLUOROCHEM.NS',
    'GUJGASLTD.NS',
    'GMDCLTD.NS',
    'GNFC.NS',
    'GPPL.NS',
    'GSPL.NS',
    'HEG.NS',
    'HBLENGINE.NS',
    'HCLTECH.NS',
    'HDFCAMC.NS',
    'HDFCBANK.NS',
    'HDFCLIFE.NS',
    'HFCL.NS',
    'HAPPSTMNDS.NS',
    'HAVELLS.NS',
    'HEROMOTOCO.NS',
    'HSCL.NS',
    'HINDALCO.NS',
    'HAL.NS',
    'HINDCOPPER.NS',
    'HINDPETRO.NS',
    'HINDUNILVR.NS',
    'HINDZINC.NS',
    'POWERINDIA.NS',
    'HOMEFIRST.NS',
    'HONASA.NS',
    'HONAUT.NS',
    'HUDCO.NS',
    'HYUNDAI.NS',
    'ICICIBANK.NS',
    'ICICIGI.NS',
    'ICICIPRULI.NS',
    'IDBI.NS',
    'IDFCFIRSTB.NS',
    'IFCI.NS',
    'IIFL.NS',
    'INOXINDIA.NS',
    'IRB.NS',
    'IRCON.NS',
    'ITC.NS',
    'ITI.NS',
    'INDGN.NS',
    'INDIACEM.NS',
    'INDIAMART.NS',
    'INDIANB.NS',
    'IEX.NS',
    'INDHOTEL.NS',
    'IOC.NS',
    'IOB.NS',
    'IRCTC.NS',
    'IRFC.NS',
    'IREDA.NS',
    'IGL.NS',
    'INDUSTOWER.NS',
    'INDUSINDBK.NS',
    'NAUKRI.NS',
    'INFY.NS',
    'INOXWIND.NS',
    'INTELLECT.NS',
    'INDIGO.NS',
    'IGIL.NS',
    'IKS.NS',
    'IPCALAB.NS',
    'JBCHEPHARM.NS',
    'JKCEMENT.NS',
    'JBMA.NS',
    'JKTYRE.NS',
    'JMFINANCIL.NS',
    'JSWENERGY.NS',
    'JSWHL.NS',
    'JSWINFRA.NS',
    'JSWSTEEL.NS',
    'JPPOWER.NS',
    'J&KBANK.NS',
    'JINDALSAW.NS',
    'JSL.NS',
    'JINDALSTEL.NS',
    'JIOFIN.NS',
    'JUBLFOOD.NS',
    'JUBLINGREA.NS',
    'JUBLPHARMA.NS',
    'JWL.NS',
    'JUSTDIAL.NS',
    'JYOTHYLAB.NS',
    'JYOTICNC.NS',
    'KPRMILL.NS',
    'KEI.NS',
    'KNRCON.NS',
    'KPITTECH.NS',
    'KAJARIACER.NS',
    'KPIL.NS',
    'KALYANKJIL.NS',
    'KANSAINER.NS',
    'KARURVYSYA.NS',
    'KAYNES.NS',
    'KEC.NS',
    'KFINTECH.NS',
    'KIRLOSBROS.NS',
    'KIRLOSENG.NS',
    'KOTAKBANK.NS',
    'KIMS.NS',
    'LTF.NS',
    'LTTS.NS',
    'LICHSGFIN.NS',
    'LTFOODS.NS',
    'LTIM.NS',
    'LT.NS',
    'LATENTVIEW.NS',
    'LAURUSLABS.NS',
    'LEMONTREE.NS',
    'LICI.NS',
    'LINDEINDIA.NS',
    'LLOYDSME.NS',
    'LUPIN.NS',
    'MMTC.NS',
    'MRF.NS',
    'LODHA.NS',
    'MGL.NS',
    'MAHSEAMLES.NS',
    'M&MFIN.NS',
    'M&M.NS',
    'MANAPPURAM.NS',
    'MRPL.NS',
    'MANKIND.NS',
    'MARICO.NS',
    'MARUTI.NS',
    'MASTEK.NS',
    'MFSL.NS',
    'MAXHEALTH.NS',
    'MAZDOCK.NS',
    'METROPOLIS.NS',
    'MINDACORP.NS',
    'MSUMI.NS',
    'MOTILALOFS.NS',
    'MPHASIS.NS',
    'MCX.NS',
    'MUTHOOTFIN.NS',
    'NATCOPHARM.NS',
    'NBCC.NS',
    'NCC.NS',
    'NHPC.NS',
    'NLCINDIA.NS',
    'NMDC.NS',
    'NSLNISP.NS',
    'NTPCGREEN.NS',
    'NTPC.NS',
    'NH.NS',
    'NATIONALUM.NS',
    'NAVA.NS',
    'NAVINFLUOR.NS',
    'NESTLEIND.NS',
    'NETWEB.NS',
    'NETWORK18.NS',
    'NEULANDLAB.NS',
    'NEWGEN.NS',
    'NAM-INDIA.NS',
    'NIVABUPA.NS',
    'NUVAMA.NS',
    'OBEROIRLTY.NS',
    'ONGC.NS',
    'OIL.NS',
    'OLAELEC.NS',
    'OLECTRA.NS',
    'PAYTM.NS',
    'OFSS.NS',
    'POLICYBZR.NS',
    'PCBL.NS',
    'PGEL.NS',
    'PIIND.NS',
    'PNBHOUSING.NS',
    'PNCINFRA.NS',
    'PTCIL.NS',
    'PVRINOX.NS',
    'PAGEIND.NS',
    'PATANJALI.NS',
    'PERSISTENT.NS',
    'PETRONET.NS',
    'PFIZER.NS',
    'PHOENIXLTD.NS',
    'PIDILITIND.NS',
    'PEL.NS',
    'PPLPHARMA.NS',
    'POLYMED.NS',
    'POLYCAB.NS',
    'POONAWALLA.NS',
    'PFC.NS',
    'POWERGRID.NS',
    'PRAJIND.NS',
    'PREMIERENE.NS',
    'PRESTIGE.NS',
    'PNB.NS',
    'RRKABEL.NS',
    'RBLBANK.NS',
    'RECLTD.NS',
    'RHIM.NS',
    'RITES.NS',
    'RADICO.NS',
    'RVNL.NS',
    'RAILTEL.NS',
    'RAINBOW.NS',
    'RKFORGE.NS',
    'RCF.NS',
    'RTNINDIA.NS',
    'RAYMONDLSL.NS',
    'RAYMOND.NS',
    'REDINGTON.NS',
    'RELIANCE.NS',
    'RPOWER.NS',
    'ROUTE.NS',
    'SBFC.NS',
    'SBICARD.NS',
    'SBILIFE.NS',
    'SJVN.NS',
    'SKFINDIA.NS',
    'SRF.NS',
    'SAGILITY.NS',
    'SAILIFE.NS',
    'SAMMAANCAP.NS',
    'MOTHERSON.NS',
    'SAPPHIRE.NS',
    'SARDAEN.NS',
    'SAREGAMA.NS',
    'SCHAEFFLER.NS',
    'SCHNEIDER.NS',
    'SCI.NS',
    'SHREECEM.NS',
    'RENUKA.NS',
    'SHRIRAMFIN.NS',
    'SHYAMMETL.NS',
    'SIEMENS.NS',
    'SIGNATURE.NS',
    'SOBHA.NS',
    'SOLARINDS.NS',
    'SONACOMS.NS',
    'SONATSOFTW.NS',
    'STARHEALTH.NS',
    'SBIN.NS',
    'SAIL.NS',
    'SWSOLAR.NS',
    'SUMICHEM.NS',
    'SUNPHARMA.NS',
    'SUNTV.NS',
    'SUNDARMFIN.NS',
    'SUNDRMFAST.NS',
    'SUPREMEIND.NS',
    'SUZLON.NS',
    'SWANENERGY.NS',
    'SWIGGY.NS',
    'SYNGENE.NS',
    'SYRMA.NS',
    'TBOTEK.NS',
    'TVSMOTOR.NS',
    'TANLA.NS',
    'TATACHEM.NS',
    'TATACOMM.NS',
    'TCS.NS',
    'TATACONSUM.NS',
    'TATAELXSI.NS',
    'TATAINVEST.NS',
    'TATAMOTORS.NS',
    'TATAPOWER.NS',
    'TATASTEEL.NS',
    'TATATECH.NS',
    'TTML.NS',
    'TECHM.NS',
    'TECHNOE.NS',
    'TEJASNET.NS',
    'NIACL.NS',
    'RAMCOCEM.NS',
    'THERMAX.NS',
    'TIMKEN.NS',
    'TITAGARH.NS',
    'TITAN.NS',
    'TORNTPHARM.NS',
    'TORNTPOWER.NS',
    'TARIL.NS',
    'TRENT.NS',
    'TRIDENT.NS',
    'TRIVENI.NS',
    'TRITURBINE.NS',
    'TIINDIA.NS',
    'UCOBANK.NS',
    'UNOMINDA.NS',
    'UPL.NS',
    'UTIAMC.NS',
    'ULTRACEMCO.NS',
    'UNIONBANK.NS',
    'UBL.NS',
    'UNITDSPR.NS',
    'USHAMART.NS',
    'VGUARD.NS',
    'DBREALTY.NS',
    'VTL.NS',
    'VBL.NS',
    'MANYAVAR.NS',
    'VEDL.NS',
    'VIJAYA.NS',
    'VMM.NS',
    'IDEA.NS',
    'VOLTAS.NS',
    'WAAREEENER.NS',
    'WELCORP.NS',
    'WELSPUNLIV.NS',
    'WESTLIFE.NS',
    'WHIRLPOOL.NS',
    'WIPRO.NS',
    'WOCKPHARMA.NS',
    'YESBANK.NS',
    'ZFCVINDIA.NS',
    'ZEEL.NS',
    'ZENTEC.NS',
    'ZENSARTECH.NS',
    'ZYDUSLIFE.NS',
    'ECLERX.NS',
]

    
    # Scan and collect results
    results = []
    for stock in nifty_100:
        try:
            res = scan_bhanushali_strategy(stock)
            if res:
                results.append(res)
        except Exception as e:
            st.write(f"Error with {stock}: {e}")
    
    # Create a DataFrame to display the results in table format
    
    
    # Display results
    if results:
        df_results = pd.DataFrame(results)
        st.dataframe(df_results)
        #st.write(df_results)
    
        # Selection box
        selected_stock = st.selectbox("Select a stock to view chart:", df_results['symbol'].tolist())
    
        # If a stock is selected, fetch its data and plot chart
        if selected_stock:
            stock_data = yf.download(selected_stock, period='60d', interval='1d')
            if isinstance(stock_data.columns, pd.MultiIndex):
                stock_data.columns = stock_data.columns.get_level_values(0)
    
            if stock_data.index.tz is None:
                stock_data.index = stock_data.index.tz_localize("UTC").tz_convert("Asia/Kolkata")
            else:
                stock_data.index = stock_data.index.tz_convert("Asia/Kolkata")
            #stock_data.index = stock_data.index.tz_convert("Asia/Kolkata")
            stock_data.dropna(inplace=True)
            stock_data = stock_data[['Open', 'High', 'Low', 'Close']]  # Make sure required columns exist
            stock_data.reset_index(inplace=True)
            #st.write("Sample stock data:", stock_data.tail())
    
            #stock_data.reset_index(inplace=True)
    
            # Get entry/SL/target from result
            selected_row = df_results[df_results['symbol'] == selected_stock].iloc[0]
            entry = selected_row['entry']
            stoploss = selected_row['stoploss']
            target1 = selected_row['target_1_2']
            target2 = selected_row['target_1_3']
    
            # Create candlestick chart
            fig = go.Figure(data=[
                go.Candlestick(
                    x=stock_data['Date'],
                    open=stock_data['Open'],
                    high=stock_data['High'],
                    low=stock_data['Low'],
                    close=stock_data['Close'],
                    name='Candles'
                ),
                go.Scatter(x=stock_data['Date'], y=[entry]*len(stock_data), mode='lines', name='Entry', line=dict(color='blue', dash='dash')),
                go.Scatter(x=stock_data['Date'], y=[stoploss]*len(stock_data), mode='lines', name='Stoploss', line=dict(color='red', dash='dash')),
                go.Scatter(x=stock_data['Date'], y=[target1]*len(stock_data), mode='lines', name='Target 1:2', line=dict(color='green', dash='dot')),
                go.Scatter(x=stock_data['Date'], y=[target2]*len(stock_data), mode='lines', name='Target 1:3', line=dict(color='darkgreen', dash='dot'))
            ])
            stock_data['SMA44'] = stock_data['Close'].rolling(window=44).mean()
            fig.add_trace(go.Scatter(x=stock_data['Date'], y=stock_data['SMA44'], mode='lines', name='SMA44', line=dict(color='orange')))
    
    
            fig.update_layout(title=f"{selected_stock} Chart with Entry, SL & Targets", xaxis_title="Date", yaxis_title="Price", height=600)
            st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("No stocks meet the strategy criteria.")

    st.markdown("""📘 SMA44 Strategy (a.k.a. Bhanushali Strategy)
Objective:
To identify bullish setups where the price pulls back toward the rising 44-period Simple Moving Average (SMA44) and shows strength by closing above it, suggesting potential continuation of the uptrend.

📊 Core Criteria
SMA44 Rising:
The 44-day Simple Moving Average (SMA44) must be sloping upward, indicating an uptrend.

Current Candle Conditions:

The Low of the current candle is below SMA44.

The Close of the candle is above SMA44.
👉 This implies the price dipped below the SMA during the day but recovered and closed above it, showing buyer strength near support.

🎯 Trade Setup
Entry Price:
Above the High of the candle that met the criteria.

Stoploss:
Below the Low of the same candle.

Targets:

Target 1 (1:2 RR): Entry + 2 × (Entry − Stoploss)

Target 2 (1:3 RR): Entry + 3 × (Entry − Stoploss)

🧠 Why SMA44?
The 44-period SMA is a custom mid-range moving average that balances between shorter-term (e.g., 20 SMA) and long-term (e.g., 100/200 SMA) trends. It is often used by discretionary swing traders like Vivek Bhanushali for detecting pullback zones in trending markets.

📌 Best Practices
Works well in strong uptrending stocks.

Avoid in sideways or weakly trending stocks.

Preferably used with volume confirmation or sector strength.""")
#_______________________________________________________________________________________________________________________________________________________________________________________________________
elif selected == "Paper Trade":
    # ✅ MUST BE FIRST Streamlit command
    #st.set_page_config(page_title="Doctor Strategy Live", layout="wide")
    #st_autorefresh(interval=30_000, key="data_refresh")
    
    
    # ✅ Now safe to use any other Streamlit commands
    st.title("Doctor Strategy Live Signal Dashboard")
    # Configuration
    symbol = "^NSEI"  # NIFTY 50 index symbol for Yahoo Finance
    interval = "5m"
    lookback_minutes = 1000  # Lookback for 3-4 days for rolling SMA
    iv_threshold = 16  # Placeholder; replace with live IV if needed
    log_file = "doctor_signal_log.csv"
    
    # Load previous log if exists
    if os.path.exists(log_file):
        signal_log = pd.read_csv(log_file)
    else:
        signal_log = pd.DataFrame(columns=[
            "Date", "Close", "SMA_20", "Upper_BB", "Lower_BB",
            "Signal", "Entry_Price", "IV"
        ])
    
    def get_nifty_data():
        df = yf.download(tickers=symbol, interval=interval, period="1d", progress=False)
       
        if isinstance(df.columns, pd.MultiIndex):  # This checks if the columns are a MultiIndex
                df.columns = df.columns.get_level_values(0)
                 # Ensure datetime index is timezone-aware in UTC and then convert to IST
                df.index = df.index.tz_convert("Asia/Kolkata")
            # Reset index to bring datetime into a column
                df.reset_index(inplace=True)
                df.rename(columns={"index": "Date"}, inplace=True)  # Ensure column name is 'Date'
            
                for col in ["Open","High","Low","Close"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df.dropna(subset=["Open","High","Low","Close"], inplace=True)
        return df
    
    def doctor_strategy_signals(df, iv_threshold=16, capital=50000):
        """
        Applies Doctor Strategy on a 5-minute OHLC DataFrame and returns trades with signals and PnL.
    
        Parameters:
            df (pd.DataFrame): Must contain 'Date', 'Open', 'High', 'Low', 'Close'
            iv_threshold (float): IV threshold for trade confirmation
            capital (float): Capital allocated per trade
    
        Returns:
            pd.DataFrame: Original DataFrame with Signal column
            list of dicts: Trade log with entry/exit and PnL
        """
    
        # Ensure Date column is timezone-aware
        df['Date'] = pd.to_datetime(df['Date'])
        if df['Date'].dt.tz is None:
            df['Date'] = df['Date'].dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
        else:
            df['Date'] = df['Date'].dt.tz_convert("Asia/Kolkata")
    
        df = df[df['Date'].dt.time.between(pd.to_datetime('09:30:00').time(), pd.to_datetime('13:30:00').time())]
        df = df.sort_values('Date').reset_index(drop=True)
    
        # Bollinger Bands and SMA 20
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['Upper_BB'] = df['SMA_20'] + 2 * df['Close'].rolling(window=20).std()
        df['Lower_BB'] = df['SMA_20'] - 2 * df['Close'].rolling(window=20).std()
    
        # Entry Logic
        df['Crossed_SMA_Up'] = (df['Close'] > df['SMA_20']) & (df['Close'].shift(1) < df['SMA_20'].shift(1))
        df['Ref_Candle_Up'] = (df['Close'] > df['SMA_20']) & (df['Close'].shift(1) > df['SMA_20'].shift(1))
    
        df['Signal'] = None
        for i in range(1, len(df)):
            if df['Ref_Candle_Up'].iloc[i] and iv_threshold >= 16:
                if df['Close'].iloc[i] > df['Close'].iloc[i - 1]:
                    df.at[i, 'Signal'] = 'BUY'
    
        # Trade simulation
        trades = []
        for i in range(len(df)):
            if df['Signal'].iloc[i] == 'BUY':
                entry_time = df['Date'].iloc[i]
                entry_price = df['Close'].iloc[i]
                stop_loss = entry_price * 0.90
                profit_target = entry_price * 1.05
                exit_time = None
                exit_price = None
                exit_reason = None
                pnl = None
    
                for j in range(i + 1, min(i + 12, len(df))):  # 10-minute window after entry
                    price = df['Close'].iloc[j]
                    if price >= profit_target:
                        exit_time = df['Date'].iloc[j]
                        exit_price = profit_target
                        exit_reason = "Target Hit"
                        break
                    elif price <= stop_loss:
                        exit_time = df['Date'].iloc[j]
                        exit_price = stop_loss
                        exit_reason = "Stop Loss Hit"
                        break
                else:
                    # Time-based exit
                    if i + 10 < len(df):
                        exit_time = df['Date'].iloc[i + 10]
                        exit_price = df['Close'].iloc[i + 10]
                        exit_reason = "Time Exit"
    
                if exit_price:
                    turnover = entry_price + exit_price
                    pnl = (exit_price - entry_price) * (capital // entry_price) - 20  # ₹20 brokerage
                    trades.append({
                        "Entry_Time": entry_time,
                        "Entry_Price": entry_price,
                        "Exit_Time": exit_time,
                        "Exit_Price": exit_price,
                        "Stop_Loss": stop_loss,
                        "Profit_Target": profit_target,
                        "Exit_Reason": exit_reason,
                        "Brokerage": 20,
                        "PnL": round(pnl, 2),
                        "Turnover": round(turnover, 2)
                    })
    
        return df, trades
    
    def plot_candles(df):
            fig = go.Figure(data=[go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
            )])
            fig.update_layout(
                title="NIFTY 5‑Minute Candles (Today)",
                xaxis_title="Time",
                yaxis_title="Price",
                xaxis_rangeslider_visible=False
            )
            return fig
    
    # Function to plot candlesticks with 20-SMA
    def plot_candles_with_sma(df):
            # Calculate the 20-period SMA
            df['20-SMA'] = df['Close'].rolling(window=20).mean()
        
            # Create the candlestick chart
            fig = go.Figure(data=[go.Candlestick(
                x=df.index,
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="Candlesticks"
            )])
        
            # Add the 20-period SMA as a line on top of the chart
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df['20-SMA'],
                mode='lines',
                name='20-SMA',
                line=dict(color='orange', width=2)
            ))
        
            # Update the layout of the chart
            fig.update_layout(
                title="NIFTY 5‑Minute Candles with 20-SMA (Today)",
                xaxis_title="Time",
                yaxis_title="Price",
                xaxis_rangeslider_visible=False
            )
        
            return fig
        
    
    
    
        
        
    if __name__ == "__main__":
        df = get_nifty_data()
        df.rename(columns={df.columns[0]: "Date"}, inplace=True)
        df.reset_index(drop=True, inplace=True)  # 🔴 This removes the numbering column
        st.write("DATA")
        st.dataframe(df.head(), use_container_width=True, hide_index=True)
        #st.write(df.head(5))
        if df.empty:
            st.warning("No data available for today’s 5‑min bars.")
        else:
            st.plotly_chart(plot_candles_with_sma(df), use_container_width=True)
        #st.write(df.columns)
        # Assuming your df_5min has 'Date', 'Open', 'High', 'Low', 'Close'
        df_result, trade_log = doctor_strategy_signals(df)
        
        # Show signals on chart
        st.dataframe(df_result[['Date', 'Close', 'SMA_20', 'Signal']].dropna(subset=['Signal']))
        
        # Show trade summary
        st.dataframe(pd.DataFrame(trade_log))
        #st.write(df)
        st.write("Tradelog")
        st_autorefresh(interval=30000, key="refresh")
        #st.sleep(60)
        #st.write(trade_log.head(5))
        # =====================
        # Streamlit Dashboard
        # =====================

elif selected == "TradingView":
    #import datetime
    #from datetime import datetime, timedelta
    nifty_50_stocks = [
        "TCS.NS","ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE",
        "BAJAJFINSV", "BPCL", "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY",
        "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR",
        "ICICIBANK", "ITC", "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LT", "M&M", "MARUTI", "NTPC",
        "NESTLEIND", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TCS", "TATACONSUM",
        "TATAMOTORS", "TATASTEEL", "TECHM", "TITAN", "UPL", "ULTRACEMCO", "WIPRO","YESBANK",# Additional Large/Mid Cap Stocks
    "ABB", "ADANIGREEN", "ADANIPOWER", "AMBUJACEM", "AUROPHARMA", "BANDHANBNK", "BANKBARODA", 
    "BERGEPAINT", "BHEL", "BIOCON", "BOSCHLTD", "CANBK", "CHOLAFIN", "COLPAL", 
    "DLF", "DABUR", "ESCORTS", "GAIL", "GODREJCP", "HAL", "HAVELLS", "ICICIPRULI", 
    "IDFCFIRSTB", "INDIGO", "L&TFH", "LICI", "MUTHOOTFIN", "NAUKRI", "PAGEIND", 
    "PEL", "PIDILITIND", "PNB", "RECLTD", "SAIL", "SHREECEM", "SRF", "SIEMENS", 
    "TATACHEM", "TRENT", "TVSMOTOR", "TORNTPHARM", "UBL", "VOLTAS", "ZYDUSLIFE", 
    "IRCTC", "INDIACEM", "IOC", "MPHASIS", "COFORGE", "CROMPTON","IDEA",# Nifty Next 50 and other liquid stocks
    "ABB", "ADANIGREEN", "ADANIPOWER", "AMBUJACEM", "AUROPHARMA", "BANDHANBNK",
    "BANKBARODA", "BERGEPAINT", "BHEL", "BIOCON", "BOSCHLTD", "CANBK", "CHOLAFIN",
    "COLPAL", "DABUR", "DLF", "ESCORTS", "GAIL", "GODREJCP", "HAVELLS", "HAL",
    "ICICIGI", "ICICIPRULI", "IDFCFIRSTB", "INDIGO", "IRCTC", "JSPL", "LICI", "MCDOWELL-N",
    "MPHASIS", "MUTHOOTFIN", "NAUKRI", "PAGEIND", "PEL", "PIDILITIND", "PNB", "RECLTD",
    "SAIL", "SHREECEM", "SIEMENS", "SRF", "TATACHEM", "TORNTPHARM", "TRENT", "TVSMOTOR",
    "UBL", "VOLTAS", "ZYDUSLIFE", "COFORGE", "CROMPTON", "AARTIIND", "ABFRL", "ACC",
    "ALOKINDS", "AMARAJABAT", "ASTRAL", "BALRAMCHIN", "BEL", "BEML", "CAMLINFINE",
    "CENTURYTEX", "CONCOR", "COROMANDEL", "DEEPAKNTR", "EIDPARRY", "EXIDEIND", "FEDERALBNK",
    "FINCABLES", "FORTIS", "GLENMARK", "GRINDWELL", "GUJGASLTD", "HEG", "IDBI",
    "IIFL", "INDHOTEL", "INDIAMART", "IRFC", "JINDALSTEL", "JUBLFOOD", "KAJARIACER",
    "LALPATHLAB", "LTI", "LTTS", "MAHLOG", "MANAPPURAM", "MCX", "METROPOLIS", "NATIONALUM",
    "NHPC", "NMDC", "OBEROIRLTY", "PFC", "POLYCAB", "RADICO", "RAJESHEXPO", "RAMCOCEM",
    "RBLBANK", "SANOFI", "SCHAEFFLER", "SUPREMEIND", "SUNTV", "SYNGENE", "TATACOMM",
    "THERMAX", "UNIONBANK", "UJJIVANSFB", "VINATIORGA", "WHIRLPOOL", "YESBANK"
    ]
    st.sidebar.title("📊 TradingView-style Stock Dashboard")
    #symbol = st.selectbox("Select NIFTY 50 stock or Index (^NSEI)", options=nifty_50_stocks, index=nifty_50_stocks.index("TCS.NS"))
    selected_stock = st.selectbox("Select a NIFTY 50 Stock", sorted(nifty_50_stocks))
    symbol = selected_stock + ".NS"
    start_date = st.date_input("From Date", datetime(2025, 1, 1))
    end_date = st.date_input("To Date", datetime.today())
    interval = st.selectbox("Select Interval", ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"], index=5)
    
    
    def plot_candles_with_sma(df):
        df['20-SMA'] = df['Close'].rolling(window=20).mean()
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Candlesticks"
        )])
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['20-SMA'],
            mode='lines',
            name='20-SMA',
            line=dict(color='orange', width=2)
        ))
        fig.update_layout(
            title=f"{symbol} 5‑Minute Candles with 20-SMA (Today)",
            xaxis_title="Time",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False
        )
        return fig
    
    # Fetch data
    #df = yf.download(symbol, start=start_date, end=end_date)
    df = yf.download(symbol, start=start_date, end=end_date, interval=interval)
    # Flatten MultiIndex columns (e.g., ('Open', 'BHARTIARTL.NS') → 'Open')
    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    
    
    if df.empty:
        st.error("No data found. Please check symbol or date.")
        st.stop()
    
    #st.write(df.head())
    # Technical Indicators
    df['20_SMA'] = df['Close'].rolling(window=20).mean()
    df['BB_std'] = df['Close'].rolling(window=20).std()
    df['BB_upper'] = df['20_SMA'] + 2 * df['BB_std']
    df['BB_lower'] = df['20_SMA'] - 2 * df['BB_std']
    
    # RSI Calculation
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Drop NaNs from indicators
    df.dropna(inplace=True)
    
    # Plot Candlestick with Bollinger Bands
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name='Candlestick'
    ))
    fig.add_trace(go.Scatter(x=df.index, y=df['20_SMA'], name='20 SMA', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_upper'], name='BB Upper', line=dict(color='lightblue')))
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_lower'], name='BB Lower', line=dict(color='lightblue')))
    
    fig.update_layout(title=f"{symbol} Price Chart", xaxis_title='Date', yaxis_title='Price', xaxis_rangeslider_visible=False, height=700)
    st.plotly_chart(fig, use_container_width=True)
    # Display candlestick chart
    #st.plotly_chart(plot_candles_with_sma(df), use_container_width=True)
    #st.divider()
    # RSI Plot
    
    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple'), name='RSI'))
    rsi_fig.update_layout(yaxis=dict(range=[0, 100]), height=300)
    st.plotly_chart(rsi_fig, use_container_width=True)
    st.subheader("📉 RSI Indicator")

elif selected == "ORB Strategy":
    st.title("📈 Intraday Opening Range Breakout Strategy")
    st.title("📊 Live 5‑Minute Candle Analysis")
    
    # -------------------------------------------------------------------------------------------------
    # Stock Selector
    #default_symbol = "RELIANCE.NS"  # You can change this to any default
    #symbol = st.text_input("Enter NSE Stock Symbol (e.g., RELIANCE.NS, TCS.NS, INFY.NS):", default_symbol).upper()
    # NIFTY 50 Stock List
    
    nifty50_stocks = [
        "TCS.NS","ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE",
        "BAJAJFINSV", "BPCL", "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY",
        "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR",
        "ICICIBANK", "ITC", "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LT", "M&M", "MARUTI", "NTPC",
        "NESTLEIND", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TCS", "TATACONSUM",
        "TATAMOTORS", "TATASTEEL", "TECHM", "TITAN", "UPL", "ULTRACEMCO", "WIPRO","YESBANK",# Additional Large/Mid Cap Stocks
    "ABB", "ADANIGREEN", "ADANIPOWER", "AMBUJACEM", "AUROPHARMA", "BANDHANBNK", "BANKBARODA", 
    "BERGEPAINT", "BHEL", "BIOCON", "BOSCHLTD", "CANBK", "CHOLAFIN", "COLPAL", 
    "DLF", "DABUR", "ESCORTS", "GAIL", "GODREJCP", "HAL", "HAVELLS", "ICICIPRULI", 
    "IDFCFIRSTB", "INDIGO", "L&TFH", "LICI", "MUTHOOTFIN", "NAUKRI", "PAGEIND", 
    "PEL", "PIDILITIND", "PNB", "RECLTD", "SAIL", "SHREECEM", "SRF", "SIEMENS", 
    "TATACHEM", "TRENT", "TVSMOTOR", "TORNTPHARM", "UBL", "VOLTAS", "ZYDUSLIFE", 
    "IRCTC", "INDIACEM", "IOC", "MPHASIS", "COFORGE", "CROMPTON","IDEA",# Nifty Next 50 and other liquid stocks
    "ABB", "ADANIGREEN", "ADANIPOWER", "AMBUJACEM", "AUROPHARMA", "BANDHANBNK",
    "BANKBARODA", "BERGEPAINT", "BHEL", "BIOCON", "BOSCHLTD", "CANBK", "CHOLAFIN",
    "COLPAL", "DABUR", "DLF", "ESCORTS", "GAIL", "GODREJCP", "HAVELLS", "HAL",
    "ICICIGI", "ICICIPRULI", "IDFCFIRSTB", "INDIGO", "IRCTC", "JSPL", "LICI", "MCDOWELL-N",
    "MPHASIS", "MUTHOOTFIN", "NAUKRI", "PAGEIND", "PEL", "PIDILITIND", "PNB", "RECLTD",
    "SAIL", "SHREECEM", "SIEMENS", "SRF", "TATACHEM", "TORNTPHARM", "TRENT", "TVSMOTOR",
    "UBL", "VOLTAS", "ZYDUSLIFE", "COFORGE", "CROMPTON", "AARTIIND", "ABFRL", "ACC",
    "ALOKINDS", "AMARAJABAT", "ASTRAL", "BALRAMCHIN", "BEL", "BEML", "CAMLINFINE",
    "CENTURYTEX", "CONCOR", "COROMANDEL", "DEEPAKNTR", "EIDPARRY", "EXIDEIND", "FEDERALBNK",
    "FINCABLES", "FORTIS", "GLENMARK", "GRINDWELL", "GUJGASLTD", "HEG", "IDBI",
    "IIFL", "INDHOTEL", "INDIAMART", "IRFC", "JINDALSTEL", "JUBLFOOD", "KAJARIACER",
    "LALPATHLAB", "LTI", "LTTS", "MAHLOG", "MANAPPURAM", "MCX", "METROPOLIS", "NATIONALUM",
    "NHPC", "NMDC", "OBEROIRLTY", "PFC", "POLYCAB", "RADICO", "RAJESHEXPO", "RAMCOCEM",
    "RBLBANK", "SANOFI", "SCHAEFFLER", "SUPREMEIND", "SUNTV", "SYNGENE", "TATACOMM",
    "THERMAX", "UNIONBANK", "UJJIVANSFB", "VINATIORGA", "WHIRLPOOL", "YESBANK"
    ]
    selected_stock = st.selectbox("Select a NIFTY 50 Stock", sorted(nifty50_stocks))
    symbol = selected_stock + ".NS"
    
    # -------------------------------------------------------------------------------------------------
    # Opening Range Breakout
    
    # Trend Calculation
    def get_trend(df):
        df["EMA5"] = df["Close"].ewm(span=5, adjust=False).mean()
        df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
        if df["EMA5"].iloc[-1] > df["EMA20"].iloc[-1]:
            return "🔼 Uptrend"
        elif df["EMA5"].iloc[-1] < df["EMA20"].iloc[-1]:
            return "🔻 Downtrend"
        else:
            return "➡️ Sideways"
    
    # Fetch 5-minute data
    def fetch_5min_data(symbol):
        df = yf.download(tickers=symbol, interval="5m", period="1d", progress=False)
        if df.empty:
            return df
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_convert("Asia/Kolkata")
        for col in ["Open", "High", "Low", "Close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)
        return df
    
    # Plot candlestick chart with 20-SMA
    def plot_candles_with_sma(df):
        df['20-SMA'] = df['Close'].rolling(window=20).mean()
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Candlesticks"
        )])
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['20-SMA'],
            mode='lines',
            name='20-SMA',
            line=dict(color='orange', width=2)
        ))
        fig.update_layout(
            title=f"{symbol} 5‑Minute Candles with 20-SMA (Today)",
            xaxis_title="Time",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False
        )
        return fig
    
    # -------------------------------------------------------------------------------------------------
    # Main Execution

    df = fetch_5min_data(symbol)
    opening_range = df.between_time("09:15", "09:30")
    if len(opening_range) < 3:
        st.warning("Not enough data yet for Opening Range (need 3 candles).")
    else:
        or_high = opening_range["High"].max()
        or_low = opening_range["Low"].min()
        or_close_time = opening_range.index[-1]
    
        # Identify breakout after 9:30
        post_or = df[df.index > or_close_time]
        breakout_signal = ""
        for idx, row in post_or.iterrows():
            if row["Close"] > or_high and row["Volume"] > opening_range["Volume"].mean():
                breakout_signal = f"🔼 Long Signal at {idx.time()} (Price: {row['Close']:.2f})"
                break
            elif row["Close"] < or_low and row["Volume"] > opening_range["Volume"].mean():
                breakout_signal = f"🔽 Short Signal at {idx.time()} (Price: {row['Close']:.2f})"
                break
    
        st.subheader("📊 Opening Range Breakout (ORB)")
        st.write(f"Opening Range High: {or_high:.2f} | Low: {or_low:.2f}")
        st.success(breakout_signal if breakout_signal else "❌ No breakout detected yet.")

    
    if df.empty:
        st.warning(f"No data available for symbol: {symbol}")
    else:
        trend = get_trend(df)
        current_price = float(df["Close"].iloc[-1])
        high = float(df["High"].max())
        low = float(df["Low"].min())
    
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📈 Trend", trend)
        col2.metric("💰 Price", f"{current_price:.2f} ₹")
        col3.metric("🔺 High", f"{high:.2f} ₹")
        col4.metric("🔻 Low", f"{low:.2f} ₹")
    
        # Display candlestick chart
        st.plotly_chart(plot_candles_with_sma(df), use_container_width=True)
        st.divider()
    
        
    
        time.sleep(30)

elif selected == "ORB Screener":
    st.title("📊 Intraday Opening Range Breakout - NIFTY 50 Screener")

    # List of NIFTY 50 symbols
    nifty50_stocks = [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE",
        "BAJAJFINSV", "BPCL", "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY",
        "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR",
        "ICICIBANK", "ITC", "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LT", "M&M", "MARUTI", "NTPC",
        "NESTLEIND", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TCS", "TATACONSUM",
        "TATAMOTORS", "TATASTEEL", "TECHM", "TITAN", "UPL", "ULTRACEMCO", "WIPRO","ABB", "ADANIGREEN", "ADANIPOWER", "AMBUJACEM", "AUROPHARMA", "BANDHANBNK", "BANKBARODA", 
    "BERGEPAINT", "BHEL", "BIOCON", "BOSCHLTD", "CANBK", "CHOLAFIN", "COLPAL", 
    "DLF", "DABUR", "ESCORTS", "GAIL", "GODREJCP", "HAL", "HAVELLS", "ICICIPRULI", 
    "IDFCFIRSTB", "INDIGO", "L&TFH", "LICI", "MUTHOOTFIN", "NAUKRI", "PAGEIND", 
    "PEL", "PIDILITIND", "PNB", "RECLTD", "SAIL", "SHREECEM", "SRF", "SIEMENS", 
    "TATACHEM", "TRENT", "TVSMOTOR", "TORNTPHARM", "UBL", "VOLTAS", "ZYDUSLIFE", 
    "IRCTC", "INDIACEM", "IOC", "MPHASIS", "COFORGE", "CROMPTON","IDEA",# Nifty Next 50 and other liquid stocks
    "ABB", "ADANIGREEN", "ADANIPOWER", "AMBUJACEM", "AUROPHARMA", "BANDHANBNK",
    "BANKBARODA", "BERGEPAINT", "BHEL", "BIOCON", "BOSCHLTD", "CANBK", "CHOLAFIN",
    "COLPAL", "DABUR", "DLF", "ESCORTS", "GAIL", "GODREJCP", "HAVELLS", "HAL",
    "ICICIGI", "ICICIPRULI", "IDFCFIRSTB", "INDIGO", "IRCTC", "JSPL", "LICI", "MCDOWELL-N",
    "MPHASIS", "MUTHOOTFIN", "NAUKRI", "PAGEIND", "PEL", "PIDILITIND", "PNB", "RECLTD",
    "SAIL", "SHREECEM", "SIEMENS", "SRF", "TATACHEM", "TORNTPHARM", "TRENT", "TVSMOTOR",
    "UBL", "VOLTAS", "ZYDUSLIFE", "COFORGE", "CROMPTON", "AARTIIND", "ABFRL", "ACC",
    "ALOKINDS", "AMARAJABAT", "ASTRAL", "BALRAMCHIN", "BEL", "BEML", "CAMLINFINE",
    "CENTURYTEX", "CONCOR", "COROMANDEL", "DEEPAKNTR", "EIDPARRY", "EXIDEIND", "FEDERALBNK",
    "FINCABLES", "FORTIS", "GLENMARK", "GRINDWELL", "GUJGASLTD", "HEG", "IDBI",
    "IIFL", "INDHOTEL", "INDIAMART", "IRFC", "JINDALSTEL", "JUBLFOOD", "KAJARIACER",
    "LALPATHLAB", "LTI", "LTTS", "MAHLOG", "MANAPPURAM", "MCX", "METROPOLIS", "NATIONALUM",
    "NHPC", "NMDC", "OBEROIRLTY", "PFC", "POLYCAB", "RADICO", "RAJESHEXPO", "RAMCOCEM",
    "RBLBANK", "SANOFI", "SCHAEFFLER", "SUPREMEIND", "SUNTV", "SYNGENE", "TATACOMM",
    "THERMAX", "UNIONBANK", "UJJIVANSFB", "VINATIORGA", "WHIRLPOOL", "YESBANK"
    ]
    # Fetch 5-minute data
    def fetch_5min_data(symbol):
        df = yf.download(tickers=symbol, interval="5m", period="1d", progress=False)
        if df.empty:
            return df
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_convert("Asia/Kolkata")
        for col in ["Open", "High", "Low", "Close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)
        return df
    
    # Function to fetch and process data
    def detect_orb(symbol):
        try:
            df = yf.download(tickers=symbol + ".NS", interval="5m", period="1d", progress=False)
            if df.empty:
                return None
            df.index = df.index.tz_convert("Asia/Kolkata")
            df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
            
            opening_range = df.between_time("09:15", "09:30")
            if len(opening_range) < 3:
                return None
            
            or_high = opening_range["High"].max()
            or_low = opening_range["Low"].min()
            or_close_time = opening_range.index[-1]
            avg_volume = opening_range["Volume"].mean()
            
            post_or = df[df.index > or_close_time]
    
            for idx, row in post_or.iterrows():
                if row["Close"] > or_high and row["Volume"] > avg_volume:
                    return {"Stock": symbol, "Signal": "🔼 Long", "Time": idx.time(), "Price": row["Close"]}
                elif row["Close"] < or_low and row["Volume"] > avg_volume:
                    return {"Stock": symbol, "Signal": "🔽 Short", "Time": idx.time(), "Price": row["Close"]}
            return None
        except Exception:
            return None
    
    # Progress and detection
    # Create trade log table
    trade_log = []
    
    for stock in nifty50_stocks:
        symbol = stock + ".NS"
        df = fetch_5min_data(symbol)
        if df.empty:
            continue
    
        opening_range = df.between_time("09:15", "09:30")
        if len(opening_range) < 3:
            continue
    
        or_high = opening_range["High"].max()
        or_low = opening_range["Low"].min()
        or_close_time = opening_range.index[-1]
        post_or = df[df.index > or_close_time]
    
        for idx, row in post_or.iterrows():
            if row["Close"] > or_high and row["Volume"] > opening_range["Volume"].mean():
                trade_log.append({
                    "Stock": stock,
                    "Signal": "🔼 Long",
                    "Time": idx.strftime("%H:%M"),
                    "Price": row["Close"],
                    "OR High": or_high,
                    "OR Low": or_low
                })
                break
            elif row["Close"] < or_low and row["Volume"] > opening_range["Volume"].mean():
                trade_log.append({
                    "Stock": stock,
                    "Signal": "🔽 Short",
                    "Time": idx.strftime("%H:%M"),
                    "Price": row["Close"],
                    "OR High": or_high,
                    "OR Low": or_low
                })
                break
    
    # Display table
    st.subheader("📋 ORB Trade Log (Live Signals)")
    if trade_log:
        st.dataframe(pd.DataFrame(trade_log))
    else:
        st.info("No breakout signals found yet.")

    st.markdown(""" 🧠 Concept of ORB
Opening Range (OR):

Defined as the high and low of the first N minutes after the market opens (commonly 15 minutes, i.e., 9:15 AM to 9:30 AM in India).

OR High = max(High) in this period

OR Low = min(Low) in this period

Breakout Conditions (Post OR period):

Long Entry: When price closes above OR High with confirming volume.

Short Entry: When price closes below OR Low with confirming volume.

Volume Confirmation (optional but improves accuracy):

The breakout candle should have higher-than-average volume (e.g., > mean volume of OR candles).

Trend Filter (optional):

Use EMAs (e.g., EMA 5/20) to trade only in the direction of the prevailing trend.

""")

elif selected == "Volatility Scanner":
    st.title("📈 NIFTY 50 Volatility Scanner (Last 14 Days)")
    st.markdown("""A Volatility Scanner is a tool used to identify which stocks (or assets) are experiencing the most price movement—how "volatile" they are—over a given period.

        🔍 What is Volatility?
        Volatility measures how much the price of a stock fluctuates. More technically, it’s often calculated as the standard deviation of returns.
        
        High volatility means the stock's price moves up and down a lot — this can offer more trading opportunities, but also more risk.
        
        Low volatility means the price is more stable.
        
        📊 What Your Volatility Scanner Does:
        Your Streamlit app:
        
        Downloads 15 days of daily price data for NIFTY 50 stocks.
        
        Calculates daily returns (percentage changes in closing price).
        
        Computes the standard deviation of those returns for each stock.
        
        Sorts the list to show the top 5 most volatile stocks.
        
        🧠 Why Use a Volatility Scanner?
        Traders use it to find stocks with high price movement for intraday or swing trading.
        
        Investors might use it to avoid risky (high-volatility) stocks.
        
        Option traders especially care about volatility, as it affects premiums.
                
            
            
                """)

    # Nifty 50 stock symbols (add ".NS" for NSE)
    nifty_50 = [
        'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'LT.NS',
        'SBIN.NS', 'HINDUNILVR.NS', 'ITC.NS', 'KOTAKBANK.NS', 'AXISBANK.NS',
        'BAJFINANCE.NS', 'BHARTIARTL.NS', 'MARUTI.NS', 'SUNPHARMA.NS',
        'NESTLEIND.NS', 'ULTRACEMCO.NS', 'TITAN.NS', 'ASIANPAINT.NS', 'WIPRO.NS',
        'HCLTECH.NS', 'NTPC.NS', 'POWERGRID.NS', 'ADANIENT.NS', 'TATASTEEL.NS',
        'TECHM.NS', 'COALINDIA.NS', 'ONGC.NS', 'UPL.NS', 'JSWSTEEL.NS',
        'BPCL.NS', 'GRASIM.NS', 'DRREDDY.NS', 'DIVISLAB.NS', 'BAJAJFINSV.NS',
        'HDFCLIFE.NS', 'SBILIFE.NS', 'EICHERMOT.NS', 'INDUSINDBK.NS', 'HEROMOTOCO.NS',
        'BAJAJ-AUTO.NS', 'CIPLA.NS', 'BRITANNIA.NS', 'APOLLOHOSP.NS', 'HINDALCO.NS',
        'ADANIPORTS.NS', 'SHREECEM.NS', 'M&M.NS','ABB.NS', 'ADANIGREEN.NS', 'ADANIPOWER.NS', 'AMBUJACEM.NS', 'AUROPHARMA.NS', 'BANDHANBNK.NS', 'BANKBARODA.NS', 
    'BERGEPAINT.NS', 'BHEL.NS', 'BIOCON.NS', 'BOSCHLTD.NS', 'CANBK.NS', 'CHOLAFIN.NS', 'COLPAL.NS', 
    'DLF.NS', 'DABUR.NS', 'ESCORTS.NS', 'GAIL.NS', 'GODREJCP.NS', 'HAL.NS', 'HAVELLS.NS', 'ICICIPRULI.NS', 
    'IDFCFIRSTB.NS', 'INDIGO.NS', 'L&TFH.NS', 'LICI.NS', 'MUTHOOTFIN.NS', 'NAUKRI.NS', 'PAGEIND.NS', 
    'PEL.NS', 'PIDILITIND.NS', 'PNB.NS', 'RECLTD.NS', 'SAIL.NS', 'SHREECEM.NS', 'SRF.NS', 'SIEMENS.NS', 
    'TATACHEM.NS', 'TRENT.NS', 'TVSMOTOR.NS', 'TORNTPHARM.NS', 'UBL.NS', 'VOLTAS.NS', 'ZYDUSLIFE.NS', 
    'IRCTC.NS', 'INDIACEM.NS', 'IOC.NS', 'MPHASIS.NS', 'COFORGE.NS', 'CROMPTON.NS','IDEA',# Nifty Next 50 and other liquid stocks
    'ABB.NS', 'ADANIGREEN.NS', 'ADANIPOWER.NS', 'AMBUJACEM.NS', 'AUROPHARMA.NS', 'BANDHANBNK.NS',
    'BANKBARODA.NS', 'BERGEPAINT.NS', 'BHEL.NS', 'BIOCON.NS', 'BOSCHLTD.NS', 'CANBK.NS', 'CHOLAFIN.NS',
    'COLPAL.NS', 'DABUR.NS', 'DLF.NS', 'ESCORTS.NS', 'GAIL.NS', 'GODREJCP.NS', 'HAVELLS.NS', 'HAL.NS',
    'ICICIGI.NS', 'ICICIPRULI.NS', 'IDFCFIRSTB.NS', 'INDIGO.NS', 'IRCTC.NS', 'JSPL.NS', 'LICI.NS', 'MCDOWELL-N.NS',
    'MPHASIS.NS', 'MUTHOOTFIN.NS', 'NAUKRI.NS', 'PAGEIND.NS', 'PEL.NS', 'PIDILITIND.NS', 'PNB.NS', 'RECLTD.NS',
    'SAIL.NS', 'SHREECEM.NS', 'SIEMENS.NS', 'SRF.NS', 'TATACHEM.NS', 'TORNTPHARM.NS', 'TRENT.NS', 'TVSMOTOR.NS',
    'UBL.NS', 'VOLTAS.NS', 'ZYDUSLIFE.NS', 'COFORGE.NS', 'CROMPTON.NS', 'AARTIIND.NS', 'ABFRL.NS', 'ACC.NS',
    'ALOKINDS.NS', 'AMARAJABAT.NS', 'ASTRAL.NS', 'BALRAMCHIN.NS', 'BEL.NS', 'BEML.NS', 'CAMLINFINE.NS',
    'CENTURYTEX.NS', 'CONCOR.NS', 'COROMANDEL.NS', 'DEEPAKNTR.NS', 'EIDPARRY.NS', 'EXIDEIND.NS', 'FEDERALBNK.NS',
    'FINCABLES.NS', 'FORTIS.NS', 'GLENMARK.NS', 'GRINDWELL.NS', 'GUJGASLTD.NS', 'HEG.NS', 'IDBI.NS',
    'IIFL.NS', 'INDHOTEL.NS', 'INDIAMART.NS', 'IRFC.NS', 'JINDALSTEL.NS', 'JUBLFOOD.NS', 'KAJARIACER.NS',
    'LALPATHLAB.NS', 'LTI.NS', 'LTTS.NS', 'MAHLOG.NS', 'MANAPPURAM.NS', 'MCX.NS', 'METROPOLIS.NS', 'NATIONALUM.NS',
    'NHPC.NS', 'NMDC.NS', 'OBEROIRLTY.NS', 'PFC.NS', 'POLYCAB.NS', 'RADICO.NS', 'RAJESHEXPO.NS', 'RAMCOCEM.NS',
    'RBLBANK.NS', 'SANOFI.NS', 'SCHAEFFLER.NS', 'SUPREMEIND.NS', 'SUNTV.NS', 'SYNGENE.NS', 'TATACOMM.NS',
    'THERMAX.NS', 'UNIONBANK.NS', 'UJJIVANSFB.NS', 'VINATIORGA.NS', 'WHIRLPOOL.NS', 'YESBANK.NS'
    ]
    
    volatilities = []
    
    with st.spinner("📊 Fetching data and calculating volatility..."):
        for symbol in nifty_50:
            try:
                df = yf.download(symbol, period='15d', interval='1d', progress=False)
                if not df.empty and 'Close' in df.columns:
                    df['returns'] = df['Close'].pct_change()
                    volatility = df['returns'].std()
                    volatilities.append((symbol, volatility))
                else:
                    st.warning(f"No data for {symbol}")
            except Exception as e:
                st.exception(f"Error fetching {symbol}: {e}")
    
    if volatilities:
        # Sort by highest volatility
        vol_df = pd.DataFrame(volatilities, columns=['Symbol', 'Volatility'])
        vol_df = vol_df.sort_values(by='Volatility', ascending=False)
    
        st.subheader("🔍 Top 15 Most Volatile NIFTY 50 Stocks (Last 14 Days)")
        st.dataframe(vol_df.head(15), use_container_width=True)
    else:
        st.error("No volatility data could be calculated.")
        
        


            
    

  
        
elif selected == "API":

    st.subheader("🔐 Fyers API Integration")

    from fyers_apiv3 import fyersModel
    from fyers_apiv3.FyersWebsocket import data_ws

    # --- User Inputs (you can also store these securely or load from .env)
    app_id = st.text_input("📌 App ID", type="password")
    access_token = st.text_input("🔑 Access Token", type="password")

    if app_id and access_token:
        try:
            # --- Initialize session
            fyers = fyersModel.FyersModel(client_id=app_id, token=access_token, log_path="")

            # --- Fetch Profile
            profile = fyers.get_profile()
            st.success("✅ Connected to Fyers!")
            st.json(profile)

            # --- Optional: Fetch Holdings
            holdings = fyers.holdings()
            st.subheader("📁 Holdings")
            st.json(holdings)

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

    else:
        st.info("ℹ️ Please enter App ID and Access Token to continue.")


elif selected == "Get Stock Data":
    st.title("📈 Get Stock Data from NSE")

    nifty_50_stocks = [
        "^NSEI","SUZLON.NS","WIPRO.NS", "ADANIENT.NS", "ASIANPAINT.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS",
        "BAJAJFINSV.NS", "BPCL.NS", "BHARTIARTL.NS", "BRITANNIA.NS", "CIPLA.NS", "COALINDIA.NS",
        "DRREDDY.NS", "EICHERMOT.NS", "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFC.NS",
        "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS",
        "INDUSINDBK.NS", "INFY.NS", "ITC.NS", "JSWSTEEL.NS", "KOTAKBANK.NS", "LT.NS", "M&M.NS",
        "MARUTI.NS", "NESTLEIND.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "RELIANCE.NS",
        "SBIN.NS", "SHREECEM.NS", "SUNPHARMA.NS", "TATACONSUM.NS", "TATAMOTORS.NS",
        "TATASTEEL.NS", "TCS.NS", "TECHM.NS", "TITAN.NS", "ULTRACEMCO.NS", "UPL.NS", "WIPRO.NS","ABB.NS", "ADANIGREEN.NS", "ADANIPOWER.NS", "AMBUJACEM.NS", "AUROPHARMA.NS", "BANDHANBNK.NS", "BANKBARODA.NS", 
    "BERGEPAINT.NS", "BHEL.NS", "BIOCON.NS", "BOSCHLTD.NS", "CANBK.NS", "CHOLAFIN.NS", "COLPAL.NS", 
    "DLF.NS", "DABUR.NS", "ESCORTS.NS", "GAIL.NS", "GODREJCP.NS", "HAL.NS", "HAVELLS.NS", "ICICIPRULI.NS", 
    "IDFCFIRSTB.NS", "INDIGO.NS", "L&TFH.NS", "LICI.NS", "MUTHOOTFIN.NS", "NAUKRI.NS", "PAGEIND.NS", 
    "PEL.NS", "PIDILITIND.NS", "PNB.NS", "RECLTD.NS", "SAIL.NS", "SHREECEM.NS", "SRF.NS", "SIEMENS.NS", 
    "TATACHEM.NS", "TRENT.NS", "TVSMOTOR.NS", "TORNTPHARM.NS", "UBL.NS", "VOLTAS.NS", "ZYDUSLIFE.NS", 
    "IRCTC.NS", "INDIACEM.NS", "IOC.NS", "MPHASIS.NS", "COFORGE.NS", "CROMPTON.NS","IDEA",# Nifty Next 50 and other liquid stocks
    "ABB.NS", "ADANIGREEN.NS", "ADANIPOWER.NS", "AMBUJACEM.NS", "AUROPHARMA.NS", "BANDHANBNK.NS",
    "BANKBARODA.NS", "BERGEPAINT.NS", "BHEL.NS", "BIOCON.NS", "BOSCHLTD.NS", "CANBK.NS", "CHOLAFIN.NS",
    "COLPAL.NS", "DABUR.NS", "DLF.NS", "ESCORTS.NS", "GAIL.NS", "GODREJCP.NS", "HAVELLS.NS", "HAL.NS",
    "ICICIGI.NS", "ICICIPRULI.NS", "IDFCFIRSTB.NS", "INDIGO.NS", "IRCTC.NS", "JSPL.NS", "LICI.NS", "MCDOWELL-N.NS",
    "MPHASIS.NS", "MUTHOOTFIN.NS", "NAUKRI.NS", "PAGEIND.NS", "PEL.NS", "PIDILITIND.NS", "PNB.NS", "RECLTD.NS",
    "SAIL.NS", "SHREECEM.NS", "SIEMENS.NS", "SRF.NS", "TATACHEM.NS", "TORNTPHARM.NS", "TRENT.NS", "TVSMOTOR.NS",
    "UBL.NS", "VOLTAS.NS", "ZYDUSLIFE.NS", "COFORGE.NS", "CROMPTON.NS", "AARTIIND.NS", "ABFRL.NS", "ACC.NS",
    "ALOKINDS.NS", "AMARAJABAT.NS", "ASTRAL.NS", "BALRAMCHIN.NS", "BEL.NS", "BEML.NS", "CAMLINFINE.NS",
    "CENTURYTEX.NS", "CONCOR.NS", "COROMANDEL.NS", "DEEPAKNTR.NS", "EIDPARRY.NS", "EXIDEIND.NS", "FEDERALBNK.NS",
    "FINCABLES.NS", "FORTIS.NS", "GLENMARK.NS", "GRINDWELL.NS", "GUJGASLTD.NS", "HEG.NS", "IDBI.NS",
    "IIFL.NS", "INDHOTEL.NS", "INDIAMART.NS", "IRFC.NS", "JINDALSTEL.NS", "JUBLFOOD.NS", "KAJARIACER.NS",
    "LALPATHLAB.NS", "LTI.NS", "LTTS.NS", "MAHLOG.NS", "MANAPPURAM.NS", "MCX.NS", "METROPOLIS.NS", "NATIONALUM.NS",
    "NHPC.NS", "NMDC.NS", "OBEROIRLTY.NS", "PFC.NS", "POLYCAB.NS", "RADICO.NS", "RAJESHEXPO.NS", "RAMCOCEM.NS",
    "RBLBANK.NS", "SANOFI.NS", "SCHAEFFLER.NS", "SUPREMEIND.NS", "SUNTV.NS", "SYNGENE.NS", "TATACOMM.NS",
    "THERMAX.NS", "UNIONBANK.NS", "UJJIVANSFB.NS", "VINATIORGA.NS", "WHIRLPOOL.NS", "YESBANK.NS"
    ]

    stock = st.selectbox("Select NIFTY 50 stock or Index (^NSEI)", options=nifty_50_stocks, index=nifty_50_stocks.index("TCS.NS"))
    from_date = st.date_input("From Date", datetime(2025, 1, 1))
    to_date = st.date_input("To Date", datetime.today())
    interval = st.selectbox("Select Interval", ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"], index=5)

    if st.button("Fetch Data"):
        st.info(f"Fetching data for {stock.upper()} from {from_date} to {to_date} at interval {interval}")
        try:
            df = yf.download(stock, start=from_date, end=to_date, interval=interval)
    
            if df.empty:
                st.warning("No data returned. Check symbol or market hours for intraday intervals.")
            else:
                # Reset index to get 'Date' column
                df.reset_index(inplace=True)
                # Ensure proper column names and date
                if 'Datetime' in df.columns:
                    df.rename(columns={'Datetime': 'Date'}, inplace=True)
                elif 'Date' not in df.columns:
                    df.insert(0, 'Date', df.index)  # fallback
                
                # Rename OHLCV columns to match expected format
                df.rename(columns=lambda x: x.strip().capitalize(), inplace=True)  # e.g., "open" -> "Open"
    
                # Flatten multi-index columns if needed
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = ['_'.join(col).strip() if col[1] else col[0] for col in df.columns]
    
                # Show the raw column names to debug
                #st.write("📊 Columns:", df.columns.tolist())
    
                # Rename columns for consistency
                rename_map = {}
                for col in df.columns:
                    if "Open" in col and "Adj" not in col: rename_map[col] = "Open"
                    if "High" in col: rename_map[col] = "High"
                    if "Low" in col: rename_map[col] = "Low"
                    if "Close" in col and "Adj" not in col: rename_map[col] = "Close"
                    if "Volume" in col: rename_map[col] = "Volume"
                df.rename(columns=rename_map, inplace=True)
    
                # Show dataframe
                st.dataframe(df)
    
                # CSV download
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"{stock.upper()}_{interval}_data.csv",
                    mime="text/csv"
                )
    
                # Plot candlestick chart
                if {"Date", "Open", "High", "Low", "Close"}.issubset(df.columns):
                    fig = go.Figure(data=[
                        go.Candlestick(
                            x=df["Date"],
                            open=df["Open"],
                            high=df["High"],
                            low=df["Low"],
                            close=df["Close"],
                            increasing_line_color="green",
                            decreasing_line_color="red"
                        )
                    ])
                    fig.update_layout(
                        title=f"{stock.upper()} Candlestick Chart",
                        xaxis_title="Date",
                        yaxis_title="Price",
                        xaxis_rangeslider_visible=False,
                        template="plotly_dark"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                      st.warning("Could not find required columns to generate candlestick chart.")
                      # ✅ Add line chart for Close price
                      st.subheader("📈 Line Chart - Close Price")
                      st.line_chart(df.set_index("Date")["Close"])
    
        except Exception as e:
            st.error(f"❌ Error fetching data: {e}")

elif selected == "Doctor Strategy":
    st.title("⚙️ Test Doctor Trade Strategy")

    uploaded_file = st.file_uploader("Upload CSV file", type="csv")
    capital = st.number_input("Capital Allocation (₹)", value=50000)

    # Helper to ensure timezone consistency
    def align_timezone(dt):
        dt = pd.to_datetime(dt)  # Make sure it's a datetime object
        if dt.tzinfo is None:
            return dt.tz_localize("UTC").tz_convert("Asia/Kolkata")
        return dt.tz_convert("Asia/Kolkata")


    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.success("File uploaded successfully")

        # Convert 'Date' to datetime if it's not already
        df['Date'] = pd.to_datetime(df['Date'])

        # Check if the 'Date' column is timezone-aware
        if df['Date'].dt.tz is None:
            df['Date'] = df['Date'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
        else:
            df['Date'] = df['Date'].dt.tz_convert('Asia/Kolkata')

        # Filter times for 9:30 AM to 1:30 PM market hours
        df = df[df['Date'].dt.time.between(pd.to_datetime('09:30:00').time(), pd.to_datetime('13:30:00').time())]

        # Display the final DataFrame
        st.write(df.head())
        #st.write(df.columns)  # Display the columns in the uploaded file

        if "Close" not in df.columns:
            st.error("CSV must contain a 'Close' column")
        else:
            # Step 1: Time Frame (5-minute chart)
            if df['Date'].diff().dt.total_seconds().median() < 300:
                df = df.resample('5T', on='Date').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
            df.dropna(inplace=True)
            #df.set_index('Date', inplace=True)

            # Step 2: Center Line (20 SMA) and Bollinger Bands
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['Upper_BB'] = df['SMA_20'] + 2 * df['Close'].rolling(window=20).std()
            df['Lower_BB'] = df['SMA_20'] - 2 * df['Close'].rolling(window=20).std()

            # Step 3: Cross and Confirm Closing Above SMA
            df['Crossed_SMA_Up'] = (df['Close'] > df['SMA_20']) & (df['Close'].shift(1) < df['SMA_20'].shift(1))

            # Step 4: Reference Candle - Next Candle Close Above 20 SMA
            df['Ref_Candle_Up'] = (df['Close'] > df['SMA_20']) & (df['Close'].shift(1) > df['SMA_20'].shift(1))

            # Step 5: Check IV Condition (only if IV data available)
            # Note: You should fetch IV data externally (example: using API), this is just a placeholder
            iv_data = 16  # Placeholder value, replace with actual API fetch for IV

            # Step 6: Trade Execution Based on Cross and IV Condition
            df['Signal'] = None
            for idx in range(1, len(df)):
                if df['Ref_Candle_Up'].iloc[idx] and iv_data >= 16:
                    if df['Close'].iloc[idx] > df['Close'].iloc[idx - 1]:  # Confirm Next Candle Cross
                        df.at[idx, 'Signal'] = 'BUY'

            # Step 7: Stop Loss Logic (10% below entry price)
            df['Stop_Loss'] = df['Close'] * 0.90

            # Step 8: Profit Booking and Trailing Stop Loss
            df['Initial_Stop_Loss'] = df['Close'] * 0.90
            df['Profit_Target'] = df['Close'] * 1.05

           # For trailing stop loss and profit booking logic
            trades = []
            for idx in range(1, len(df)):
                if idx < len(df) and df['Signal'].iloc[idx] == 'BUY':
                    # Your code logic here
            
                    entry_price = df['Close'].iloc[idx]
                    stop_loss = entry_price * 0.90
                    profit_target = entry_price * 1.05
                    trade = {
                        #'Entry_Time': df.index[idx],
                        'Entry_Time': df['Date'].iloc[idx],
                        'Entry_Price': entry_price,
                        'Stop_Loss': stop_loss,
                        'Profit_Target': profit_target,
                        'Exit_Time': None,
                        'Exit_Price': None,
                        'Brokerage'     : 20 ,   # ₹20 per trade
                        'PnL': None,
                        'Turnover':None,
                        'Exit_Reason': None  # Add the Exit_Reason field
                    }
            
                    # Track the trade for 10-minute exit and trailing logic
                    trades.append(trade)
            
                    # Logic for trailing stop loss and profit booking
                    for trade in trades:
                        entry_time = trade['Entry_Time']
                        entry_price = trade['Entry_Price']
                        stop_loss = trade['Stop_Loss']
                        profit_target = trade['Profit_Target']
                        current_stop_loss = stop_loss
                        current_profit_target = profit_target
                        trailing_stop_loss_triggered = False
                        profit_booked = False
            
                        # Make sure Date is in the index and sorted
                        df = df.sort_values('Date').reset_index(drop=True)
            
                        # Find closest index to entry_time
                        entry_time = align_timezone(trade['Entry_Time'])
            
                        # Safely find the closest index
                        entry_idx = df['Date'].searchsorted(entry_time)
            
                        if entry_idx >= len(df):
                            continue  # Skip if entry time is beyond available data
            
                        # Now proceed
                        for idx in range(entry_idx + 1, len(df)):
                            current_time = df.at[idx, 'Date']
                            close_price = df.at[idx, 'Close']
            
                            # Check for profit booking
                            if close_price >= current_profit_target and not profit_booked:
                                trade['Exit_Time'] = current_time
                                trade['Exit_Price'] = current_profit_target
                                trade['Turnover'] = trade['Exit_Price'] + trade['Entry_Price']
                                trade['PnL'] = current_profit_target - entry_price
                                trade['PnL_After_Brokerage'] = trade['PnL'] - trade['Brokerage']
                                trade['Exit_Reason'] = 'Profit Booking'  # Add exit reason
                                profit_booked = True
                                break
            
                            # Check for trailing stop loss
                            if close_price >= entry_price * 1.04 and not trailing_stop_loss_triggered:
                                current_stop_loss = entry_price
                                trailing_stop_loss_triggered = True
            
                            if trailing_stop_loss_triggered:
                                if close_price >= entry_price * 1.10:
                                    current_stop_loss = entry_price * 1.04
                                elif close_price >= entry_price * 1.15:
                                    current_stop_loss = entry_price * 1.11
                                elif close_price >= entry_price * 1.20:
                                    trade['Exit_Time'] = current_time
                                    trade['Exit_Price'] = close_price
                                    trade['PnL'] = close_price - entry_price
                                    trade['Turnover'] = trade['Exit_Price'] + trade['Entry_Price']
                                    trade['PnL_After_Brokerage'] = trade['PnL'] - trade['Brokerage']
                                    trade['Exit_Reason'] = 'Profit Target Reached'  # Exit reason
                                    break
            
                            # Check for stop loss hit
                            if df.at[idx, 'Low'] <= current_stop_loss:
                                trade['Exit_Time'] = current_time
                                trade['Exit_Price'] = current_stop_loss
                                trade['PnL'] = current_stop_loss - entry_price
                                trade['Turnover'] = trade['Exit_Price'] + trade['Entry_Price']
                                trade['PnL_After_Brokerage'] = trade['PnL'] - trade['Brokerage']
                                trade['Exit_Reason'] = 'Stop Loss Hit'  # Exit reason
                                break
            
                        # Step 9: Time-Based Exit (after 10 minutes)
                        if not trade.get('Exit_Time'):
                            # Ensure 'Date' column is in datetime format, force errors to NaT if conversion fails
                            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            
                            # Ensure 'entry_time' is also in datetime format, force errors to NaT if conversion fails
                            entry_time = pd.to_datetime(trade['Entry_Time'], errors='coerce')
            
                            # Check if the 'Date' column has any NaT (invalid) values and handle accordingly
                            if df['Date'].isnull().any():
                                print("Warning: Some 'Date' values are invalid (NaT). They will be excluded.")
                                df = df.dropna(subset=['Date'])
            
                            # Localize to 'Asia/Kolkata' timezone only if the column is naive (no timezone)
                            df['Date'] = df['Date'].apply(lambda x: x.tz_localize('Asia/Kolkata', ambiguous='NaT') if x.tzinfo is None else x)
            
                            # Ensure entry_time is timezone-aware, localize it if it's naive
                            if entry_time.tzinfo is None:
                                entry_time = entry_time.tz_localize('Asia/Kolkata', ambiguous='NaT')
            
                            # Now both df['Date'] and entry_time are timezone-aware, so we can safely use searchsorted()
                            entry_idx = df['Date'].searchsorted(entry_time)
            
                            # Ensure we don't go out of bounds
                            if entry_idx < len(df):
                                closest_entry = df.iloc[entry_idx]
                            else:
                                closest_entry = df.iloc[-1]  # If it's out of bounds, take the last available
            
                            # Time-based exit logic (after 10 minutes)
                            for idx in range(entry_idx + 1, len(df)):
                                current_time = df.at[idx, 'Date']
                                close_price = df.at[idx, 'Close']
                                if (current_time - entry_time).seconds >= 600:  # 600 seconds = 10 minutes
                                    trade['Exit_Time'] = current_time
                                    trade['Exit_Price'] = df.at[idx, 'Close']
                                    trade['PnL'] = df.at[idx, 'Close'] - entry_price
                                    trade['PnL_After_Brokerage'] = trade['PnL'] - trade['Brokerage']
                                    trade['Turnover'] = trade['Exit_Price'] + trade['Entry_Price']
                                    trade['Exit_Reason'] = 'Time-Based Exit'  # Exit reason
                                    break
                    # 2️⃣ If you didn't compute PnL_After_Brokerage per-trade, do it now:
                    #if 'PnL_After_Brokerage' not in trade_log.columns:
                        #trade_log['PnL_After_Brokerage'] = trade_log['PnL'] - trade_log['Brokerage']
                    # Add the trades to the DataFrame
                    #trade_log = pd.DataFrame(trades)
                    #total_net_pnl = trade_log['PnL_After_Brokerage'].sum()
                    #st.markdown(f"**Total Net P&L after Brokerage:** ₹{total_net_pnl:.2f}")
            
                     


                    

           
            
                    
            # Display chart with trade signals (optional)
            # Calculate the 20-period Simple Moving Average (SMA)
            df['20_SMA'] = df['Close'].rolling(window=20).mean()
            
            # Create the candlestick chart
            fig = go.Figure(data=[go.Candlestick(
                x=df['Date'],
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                increasing_line_color='green',
                decreasing_line_color='red',
            )])
            
            # Add buy signals
            buy_signals = df[df['Signal'] == 'BUY']
            fig.add_trace(go.Scatter(
                x=buy_signals['Date'],
                y=buy_signals['Close'],
                mode='markers',
                name='Buy Signal',
                marker=dict(symbol='triangle-up', color='green', size=12)
            ))
            
            # Add 20-period SMA to the chart
            fig.add_trace(go.Scatter(
                x=df['Date'],
                y=df['20_SMA'],
                mode='lines',
                name='20 SMA',
                line=dict(color='blue', width=2)
            ))
            
            # Display the chart
            st.subheader("Daily Chart")
            
            fig.update_layout(
                xaxis_title='Date',
                yaxis_title='Price (₹)',
                xaxis_rangeslider_visible=False,
                template='plotly_dark',
                hovermode='x unified',
            )
            
            st.plotly_chart(fig)
            # Display the trade log
             # Display the chart
            st.subheader("Trade Log ")
            st.dataframe(trades)

            # Create a DataFrame
            trade_log_df = pd.DataFrame(trades)
            
            # Ensure the CSV string is generated correctly
            csv = trade_log_df.to_csv(index=False)  # `csv` should hold the CSV data as a string
            #print(csv)  # This will print the CSV content in the console for debugging
            
            # Download Button
            st.download_button(
                label="📥 Download Trade Log",
                data=csv,  # Make sure `csv` is correctly defined here
                file_name="trade_log.csv",
                mime="text/csv",
                key="download_button"
            )
            # ── assume you already have: trade_log_df = pd.DataFrame(trades) ──

            # 1️⃣ Compute summary stats
            total_trades = len(trade_log_df)
            wins        = trade_log_df[trade_log_df['PnL_After_Brokerage'] > 0]
            losses      = trade_log_df[trade_log_df['PnL_After_Brokerage'] < 0]
            
            num_wins    = len(wins)
            num_losses  = len(losses)
            win_rate    = (num_wins / total_trades * 100) if total_trades else 0
            
            gross_profit = wins['PnL_After_Brokerage'].sum()
            gross_loss   = losses['PnL_After_Brokerage'].sum()  # negative number
            profit_factor = (gross_profit / abs(gross_loss)) if gross_loss < 0 else float("inf")
            
            avg_win   = wins['PnL_After_Brokerage'].mean()  if num_wins   else 0
            avg_loss  = losses['PnL_After_Brokerage'].mean() if num_losses else 0

            # Total Turnover & Brokerage
            total_turnover = trade_log_df['Turnover'].sum()
            total_brokerage = trade_log_df['Brokerage'].sum()
            
            # Expectancy per trade
            expectancy = (win_rate/100) * avg_win + (1 - win_rate/100) * avg_loss
            
            # 2️⃣ Display in Streamlit
            st.markdown("## 📊 Performance Summary")
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Trades", total_trades)
            c2.metric("Winning Trades", num_wins, f"{win_rate:.1f}%")
            c3.metric("Losing Trades", num_losses)
            
            c4, c5, c6 = st.columns(3)
            c4.metric("Gross Profit", f"₹{gross_profit:.2f}")
            c5.metric("Gross Loss",   f"₹{gross_loss:.2f}")
            c6.metric("Profit Factor", f"{profit_factor:.2f}")
            
            c7, c8, c9 = st.columns(3)
            c7.metric("Avg. Win",   f"₹{avg_win:.2f}")
            c8.metric("Avg. Loss",  f"₹{avg_loss:.2f}")
            c9.metric("Expectancy", f"₹{expectancy:.2f}")

            c10, c11, c12 = st.columns(3)
            c10.metric("Total Turnover",   f"₹{total_turnover:.2f}")
            c11.metric("Total Brokerage",  f"₹{total_brokerage:.2f}")
            c12.metric("Expectancy", f"₹{expectancy:.2f}")
        
            # 3️⃣ (Optional) Equity curve
            st.markdown("### 📈 Equity Curve")
            st.line_chart(trade_log_df['PnL_After_Brokerage'].cumsum())
            
            # 4️⃣ Download full log
            csv = trade_log_df.to_csv(index=False)
            st.download_button(
                "📥 Download Trade Log",
                data=csv,
                file_name="trade_log_with_summary.csv",
                mime="text/csv",
                key="download_with_summary"
            )


  
    


elif selected == "Doctor1.0 Strategy":
    st.title("⚙️ Test Doctor1.0 Strategy ")

    uploaded_file = st.file_uploader("Upload CSV file", type="csv")
    capital = st.number_input("Capital Allocation (₹)", value=50000)

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)

        required_columns = {'Date', 'Open', 'High', 'Low', 'Close', 'Volume'}
        if not required_columns.issubset(df.columns):
            st.error(f"CSV must contain the following columns: {required_columns}")
        else:
            st.success("File uploaded successfully")

            df['Signal'] = df['Close'].diff().apply(lambda x: 'BUY' if x > 5 else 'SELL' if x < -5 else None)
            df.dropna(subset=['Signal'], inplace=True)

            trade_log = pd.DataFrame({
                "Date": df['Date'],
                "Stock": "TEST-STOCK",
                "Action": df['Signal'],
                "Price": df['Close'],
                "Qty": 10,
                "PnL": df['Close'].diff().fillna(0) * 10
            })

            net_pnl = trade_log["PnL"].sum()
            win_trades = trade_log[trade_log["PnL"] > 0].shape[0]
            lose_trades = trade_log[trade_log["PnL"] < 0].shape[0]
            last_order = f"{trade_log.iloc[-1]['Action']} - TEST-STOCK - 10 shares @ {trade_log.iloc[-1]['Price']}"

            st.session_state['net_pnl'] = float(net_pnl)
            st.session_state['used_capital'] = capital
            st.session_state['open_positions'] = {"TEST-STOCK": {"Qty": 10, "Avg Price": round(df['Close'].iloc[-1], 2)}}
            st.session_state['last_order'] = last_order

            st.metric("Net PnL", f"₹{net_pnl:.2f}")
            st.metric("Winning Trades", win_trades)
            st.metric("Losing Trades", lose_trades)
            st.dataframe(trade_log)

            csv = trade_log.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Trade Log", data=csv, file_name="trade_log.csv", mime="text/csv")
            st.session_state['trade_log_df'] = trade_log

            fig = go.Figure(data=[go.Candlestick(
                x=df['Date'],
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                increasing_line_color='green',
                decreasing_line_color='red',
            )])

            buy_signals = df[df['Signal'] == 'BUY']
            sell_signals = df[df['Signal'] == 'SELL']

            fig.add_trace(go.Scatter(
                x=buy_signals['Date'],
                y=buy_signals['Close'],
                mode='markers',
                name='Buy Signal',
                marker=dict(symbol='triangle-up', color='green', size=12)
            ))

            fig.add_trace(go.Scatter(
                x=sell_signals['Date'],
                y=sell_signals['Close'],
                mode='markers',
                name='Sell Signal',
                marker=dict(symbol='triangle-down', color='red', size=12)
            ))

            fig.update_layout(
                xaxis_title='Date',
                yaxis_title='Price (₹)',
                xaxis_rangeslider_visible=False,
                template='plotly_dark',
                hovermode='x unified',
            )

            st.plotly_chart(fig)

            df['Signal_Code'] = df['Signal'].map({'BUY': 1, 'SELL': -1})
            csv_with_signal = df[["Date", "Open", "High", "Low", "Close", "Signal_Code"]]
            csv_data = csv_with_signal.rename(columns={"Signal_Code": "Signal"}).to_csv(index=False).encode("utf-8")

            st.download_button(
                label="📥 Download CSV with Signals",
                data=csv_data,
                file_name="signal_output.csv",
                mime="text/csv"
            )

            
elif selected == "Trade Log":
    st.title("📘 Trade Log")

    # Check if trade_log_df exists
    if 'trade_log_df' in st.session_state and not st.session_state['trade_log_df'].empty:
        trade_log = st.session_state['trade_log_df']
        
        st.subheader("Trade Log Table")
        st.dataframe(trade_log)
        df=trade_log
         # ✅ Show key metrics
        if "PnL" in df.columns:
            total_pnl = df["PnL"].sum()
            win_trades = df[df["PnL"] > 0].shape[0]
            lose_trades = df[df["PnL"] < 0].shape[0]
    
            st.metric("💰 Net PnL", f"₹{total_pnl:.2f}")
            st.metric("✅ Winning Trades", win_trades)
            st.metric("❌ Losing Trades", lose_trades)
    
            # 📉 Line chart - PnL over time
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df.sort_values("Date", inplace=True)
                df["Cumulative PnL"] = df["PnL"].cumsum()
                st.subheader("📈 Cumulative PnL Over Time")
                st.line_chart(df.set_index("Date")["Cumulative PnL"])
    
            # 🥧 Pie chart - Win vs Loss
            st.subheader("📊 Win/Loss Distribution")
            win_loss_df = pd.DataFrame({
                "Result": ["Win", "Loss"],
                "Count": [win_trades, lose_trades]
            })
            fig = px.pie(win_loss_df, names="Result", values="Count", title="Win vs Loss")
            st.plotly_chart(fig, use_container_width=True)
    
            # 📤 Download button
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Clean Trade Log", csv, "clean_trade_log.csv", "text/csv")
        else:
            st.warning("No 'PnL' column found in CSV.")
    else:
        st.info("Upload a CSV file to view trade log.")
   
       
      

elif selected == "Account Info":
    st.title("💼 Account Information")

    # Get session values
    starting_capital = 100000
    net_pnl = st.session_state.get('net_pnl', 0)
    used_capital = st.session_state.get('used_capital', 0)
    available_capital = starting_capital + net_pnl

    open_positions = st.session_state.get('open_positions', {})
    last_order = st.session_state.get('last_order', "No order placed yet")

    # 📊 Display Funds Summary
    st.subheader("Funds Summary")
    funds_df = pd.DataFrame({
        "Metric": ["Available Capital", "Used Capital", "Net PnL"],
        "Value (₹)": [round(available_capital, 2), round(used_capital, 2), round(net_pnl, 2)],
    })
    st.table(funds_df)

    st.subheader("Open Positions")
    if open_positions:
        for stock, details in open_positions.items():
            st.write(f"{stock}: {details['Qty']} shares @ ₹{details['Avg Price']}")
    else:
        st.info("No open positions")

    st.subheader("Last Order")
    st.write(last_order)

elif selected == "Doctor3.0  Strategy":
    st.title("⚙️ Test Doctor3.0 Strategy")

    st.markdown("""
    ### 📋 Doctor 3.0 स्ट्रॅटेजी प्लॅन:

    ✅ **चार्ट सेटअप**: 5 मिनिटांचा कँडलस्टिक चार्ट + Bollinger Band (20 SMA). 

    ✅ **20 SMA क्रॉसिंग:**
    - कँडलने 20 SMA लाईन खालून वर क्रॉस करून क्लोज केली पाहिजे.
    - नंतरची कँडल ही 20 SMA ला touch न करता वर क्लोज झाली पाहिजे.

    ✅ **Reference Candle Setup:**
    - क्रॉस करणारी कँडल = Reference Candle
    - त्याच्या अगोदरची कँडल महत्त्वाची: तिचा High/Close दोन्हीपैकी जास्त किंमत मार्क करा.
    - नंतरची कँडल ह्या किमतीला खालून वर ब्रेक करत असल्यास ट्रेड एंटर करा.

    ✅ **Entry Condition:**
    - Reference candle नंतरच्या कँडलने prior candle चा High/Close cross केलं पाहिजे.
    - आणि IV > 16% असेल तर, त्या वेळी In the Money Call Option खरेदी करा.

    ✅ **Risk Management:**
    - Entry नंतर Stop Loss: Buy Price - 10%
    - Profit Target: 5%
    - Profit > 4% झाल्यावर Stop Loss ला Entry Price ला ट्रेल करा (No Loss Zone).
    - Profit > 10% = SL @ 4%, Profit > 15% = SL @ 11%, Profit > 20% = Book full profit

    ✅ **Time Based Exit:**
    - Trade घेतल्यावर 10 मिनिटात काहीही हिट न झाल्यास, नफा/तोटा न पाहता एक्झिट करा.

    ✅ **Trade Time:**
    - सकाळी 9:30 ते दुपारी 3:00 पर्यंतच ट्रेड सुरू करा.
    """)

    uploaded_file = st.file_uploader("Upload CSV file with OHLCV data", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip()

        if {'Open', 'High', 'Low', 'Close', 'Volume', 'Date'}.issubset(df.columns):
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values("Date")
            st.success("✅ Data loaded successfully!")
            st.dataframe(df.tail())

            # Calculate 20 SMA and Bollinger Bands
            df['SMA20'] = df['Close'].rolling(window=20).mean()
            df['Upper'] = df['SMA20'] + 2 * df['Close'].rolling(window=20).std()
            df['Lower'] = df['SMA20'] - 2 * df['Close'].rolling(window=20).std()

            # Detect breakout condition
            breakout_signals = []
            entry_price = None
            sl_price = None
            tp_price = None

            for i in range(21, len(df) - 1):
                prev = df.iloc[i - 1]
                curr = df.iloc[i]
                next_candle = df.iloc[i + 1]
                iv = 18  # simulated implied volatility

                if (prev['Close'] < prev['SMA20']) and (curr['Close'] > curr['SMA20']) and (curr['Low'] > curr['SMA20']):
                    ref_price = max(prev['High'], prev['Close'])
                    if next_candle['Close'] > ref_price and iv > 16:
                        entry_price = next_candle['Close']
                        sl_price = entry_price * 0.90
                        tp_price = entry_price * 1.05
                        breakout_signals.append({
                            'Time': df.iloc[i + 1]['Date'],
                            'Entry': entry_price,
                            'SL': sl_price,
                            'TP': tp_price,
                            'IV': iv,
                            'Result': None
                        })

            # Paper Trading Simulation
            results = []
            for signal in breakout_signals:
                trade_open = False
                entry = signal['Entry']
                sl = signal['SL']
                tp = signal['TP']
                entry_time = signal['Time']
                exit_time = entry_time + pd.Timedelta(minutes=10)

                for idx, row in df.iterrows():
                    if row['Date'] < entry_time:
                        continue
                    if row['Date'] > exit_time:
                        results.append({**signal, 'Exit': row['Close'], 'Reason': 'Time Exit'})
                        break
                    if row['Low'] <= sl:
                        results.append({**signal, 'Exit': sl, 'Reason': 'Stop Loss Hit'})
                        break
                    if row['High'] >= tp:
                        results.append({**signal, 'Exit': tp, 'Reason': 'Profit Target Hit'})
                        break

            if results:
                result_df = pd.DataFrame(results)
                st.subheader("📊 Paper Trading Results")
                st.dataframe(result_df)
            else:
                st.info("🚫 No trades detected.")

        else:
            st.error("CSV must contain the following columns: Date, Open, High, Low, Close, Volume")



elif selected == "Strategy Detail":
    st.title("ℹ️ Strategy Details")

    st.markdown("""
    **Objective:** Implement a simple strategy based on basic moving averages and volatility.
    
    **Strategy Highlights:**
    - Buy when the price crosses above the moving average and volatility is low.
    - Sell when the price falls below the moving average and volatility is high.
    ✅ Doctor Algo-BOT Strategy – English Version
    1. Chart Setup
    Use Bollinger Bands (20 SMA, 2 SD) on the chart.
    
    Use Candlestick pattern, not line or Heikin-Ashi.
    
    Timeframe: 5-minute chart.
    
    Only take trades after 9:30 AM.
    
    2. Center Line (20 SMA) Crossing Logic
    The middle line of the Bollinger Band (20 SMA) should be crossed from below to above by Nifty or Bank Nifty.
    
    The candle that crosses the 20 SMA must also close above it.
    
    The next candle after the crossover should also close above the 20 SMA, without touching it.
    
    This second candle is marked as the "Reference Candle".
    
    The candle before the Reference Candle is called the "Pre-Reference Candle".
    
    3. Breakout and Trade Execution
    Identify:
    
    High of the Pre-Reference Candle
    
    Close of the Reference Candle
    
    Take the maximum of these two values = breakout_level
    
    Trade Trigger: If a future 5-minute candle crosses breakout_level from below, execute the trade (Call Option Buy).
    
    Stop Loss (SL): 10% below the entry price.
    
    4. Implied Volatility (IV) Check
    At the time of trade, Nifty/Bank Nifty IV should be ≥ 16.
    
    Only then the trade is valid.
    
    5. Option Selection
    On breakout, buy the nearest In-The-Money (ITM) Call Option for Nifty/Bank Nifty.
    
    6. Risk Management – SL and Trailing Logic
    
    Profit Reached	Trailing Stop Loss Moves To
    5%	Entry Price (No-Loss Zone)
    10%	Trail SL to 4% profit
    15%	Trail SL to 11% profit
    20%	Book full profit
    7. Time-Based Exit
    If none of SL or Target is hit within 10 minutes of trade initiation,
    
    Then exit the trade immediately, regardless of PnL.


    """)
    
elif selected == "Project Detail":
    st.title("📋 Project Details")

    st.markdown("""
    **Project Name:** Trade Strategy Automation System
    **Goal:** Automate strategy testing, risk management, and trade execution.
    
    **Components:**
    - Data Collection
    - Backtesting Framework
    - Trade Simulation
    - Capital & Risk Management
    """)
elif selected == "Candle Chart":
    st.title("📉 Candle Chart Viewer")

    st.title("📊 Live NIFTY 5‑Minute Candle")

    # Trend Calculation
    def get_trend(df):
        df["EMA5"] = df["Close"].ewm(span=5, adjust=False).mean()
        df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
        if df["EMA5"].iloc[-1] > df["EMA20"].iloc[-1]:
            return "🔼 Uptrend"
        elif df["EMA5"].iloc[-1] < df["EMA20"].iloc[-1]:
            return "🔻 Downtrend"
        else:
            return "➡️ Sideways"
    
    def fetch_5min_data(symbol):
        df = yf.download(tickers=symbol, interval="5m", period="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):  # This checks if the columns are a MultiIndex
            df.columns = df.columns.get_level_values(0)
         # Ensure datetime index is timezone-aware in UTC and then convert to IST
        df.index = df.index.tz_convert("Asia/Kolkata")
        # Reset index and rename it to "Date"
        df = df.reset_index().rename(columns={"index": "Date", "Datetime": "Date"})
        for col in ["Open","High","Low","Close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.dropna(subset=["Open","High","Low","Close"], inplace=True)
        return df
    
    def plot_candles(df):
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
        )])
        fig.update_layout(
            title="NIFTY 5‑Minute Candles (Today)",
            xaxis_title="Time",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False
        )
        return fig
    
    # Function to plot candlesticks with 20-SMA
    def plot_candles_with_sma(df):
        # Calculate the 20-period SMA
        df['20-SMA'] = df['Close'].rolling(window=20).mean()
    
        # Create the candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Candlesticks"
        )])
    
        # Add the 20-period SMA as a line on top of the chart
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['20-SMA'],
            mode='lines',
            name='20-SMA',
            line=dict(color='orange', width=2)
        ))
    
        # Update the layout of the chart
        fig.update_layout(
            title="NIFTY 5‑Minute Candles with 20-SMA (Today)",
            xaxis_title="Time",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False
        )
    
        return fig
    

    def doctor_strategy_signals(df, iv_threshold=16, capital=50000):
        """
        Applies Doctor Strategy on a 5-minute OHLC DataFrame and returns trades with signals and PnL.
    
        Parameters:
            df (pd.DataFrame): Must contain 'Date', 'Open', 'High', 'Low', 'Close'
            iv_threshold (float): IV threshold for trade confirmation
            capital (float): Capital allocated per trade
    
        Returns:
            pd.DataFrame: Original DataFrame with Signal column
            list of dicts: Trade log with entry/exit and PnL
        """
    
        # Ensure Date column is timezone-aware
        df['Date'] = pd.to_datetime(df['Date'])
        if df['Date'].dt.tz is None:
            df['Date'] = df['Date'].dt.tz_localize("UTC").dt.tz_convert("Asia/Kolkata")
        else:
            df['Date'] = df['Date'].dt.tz_convert("Asia/Kolkata")
    
        df = df[df['Date'].dt.time.between(pd.to_datetime('09:30:00').time(), pd.to_datetime('13:30:00').time())]
        df = df.sort_values('Date').reset_index(drop=True)
    
        # Bollinger Bands and SMA 20
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['Upper_BB'] = df['SMA_20'] + 2 * df['Close'].rolling(window=20).std()
        df['Lower_BB'] = df['SMA_20'] - 2 * df['Close'].rolling(window=20).std()
    
        # Entry Logic
        df['Crossed_SMA_Up'] = (df['Close'] > df['SMA_20']) & (df['Close'].shift(1) < df['SMA_20'].shift(1))
        df['Ref_Candle_Up'] = (df['Close'] > df['SMA_20']) & (df['Close'].shift(1) > df['SMA_20'].shift(1))
    
        df['Signal'] = None
        for i in range(1, len(df)):
            if df['Ref_Candle_Up'].iloc[i] and iv_threshold >= 16:
                if df['Close'].iloc[i] > df['Close'].iloc[i - 1]:
                    df.at[i, 'Signal'] = 'BUY'
    
        # Trade simulation
        trades = []
        for i in range(len(df)):
            if df['Signal'].iloc[i] == 'BUY':
                entry_time = df['Date'].iloc[i]
                entry_price = df['Close'].iloc[i]
                stop_loss = entry_price * 0.90
                profit_target = entry_price * 1.05
                exit_time = None
                exit_price = None
                exit_reason = None
                pnl = None
    
                for j in range(i + 1, min(i + 12, len(df))):  # 10-minute window after entry
                    price = df['Close'].iloc[j]
                    if price >= profit_target:
                        exit_time = df['Date'].iloc[j]
                        exit_price = profit_target
                        exit_reason = "Target Hit"
                        break
                    elif price <= stop_loss:
                        exit_time = df['Date'].iloc[j]
                        exit_price = stop_loss
                        exit_reason = "Stop Loss Hit"
                        break
                else:
                    # Time-based exit
                    if i + 10 < len(df):
                        exit_time = df['Date'].iloc[i + 10]
                        exit_price = df['Close'].iloc[i + 10]
                        exit_reason = "Time Exit"
    
                if exit_price:
                    turnover = entry_price + exit_price
                    pnl = (exit_price - entry_price) * (capital // entry_price) - 20  # ₹20 brokerage
                    trades.append({
                        "Entry_Time": entry_time,
                        "Entry_Price": entry_price,
                        "Exit_Time": exit_time,
                        "Exit_Price": exit_price,
                        "Stop_Loss": stop_loss,
                        "Profit_Target": profit_target,
                        "Exit_Reason": exit_reason,
                        "Brokerage": 20,
                        "PnL": round(pnl, 2),
                        "Turnover": round(turnover, 2)
                    })
    
        return df, trades

    symbol = "^NSEI"
    df = fetch_5min_data(symbol)
    # Check actual column names
    st.write("Columns before rename:", df.columns.tolist())
    
    # Rename 'Datetime' to 'Date' so your function works
    if 'Datetime' in df.columns:
        df.rename(columns={"Datetime": "Date"}, inplace=True)

    trend = get_trend(df)
    current_price = float(df["Close"].iloc[-1])
    high = float(df["High"].max())
    low = float(df["Low"].min())
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📈 Trend", trend)
    
    if df.empty:
        st.warning("No data available for today’s 5‑min bars.")
    else:
        st.plotly_chart(plot_candles_with_sma(df), use_container_width=True)

    current_price = float(df["Close"].iloc[-1])
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📈 Trend", trend)
    col2.metric("💰 Price", f"{current_price:.2f} ₹")
    col3.metric("🔺 High", f"{high:.2f} ₹")
    col4.metric("🔻 Low", f"{low:.2f} ₹")
    st.divider()
    # Assuming your df_5min has 'Date', 'Open', 'High', 'Low', 'Close'
    st.write(df.head(5))
    df_result, trade_log = doctor_strategy_signals(df)
    
    # Show signals on chart
    st.dataframe(df_result[['Date', 'Close', 'SMA_20', 'Signal']].dropna(subset=['Signal']))
    time.sleep(30)
    
    
        

elif selected == "Swing Trade Strategy":
    # Title
    st.title("📈 Swing Trade Strategy")
    
    # Sidebar options
    capital = st.sidebar.number_input("Total Capital (₹)", value=100000)
    risk_percent = st.sidebar.slider("Risk per Trade (%)", 0.5, 5.0, 1.0)
    
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
    
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
    
        # Detect and set datetime index
        datetime_col = next((c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()), None)
        if not datetime_col:
            st.error("❌ No datetime column found.")
            st.stop()
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        df.set_index(datetime_col, inplace=True)
        st.success(f"✅ Using '{datetime_col}' as index.")
    
        # Ensure OHLC columns
        for col in ['Open','High','Low','Close']:
            if col not in df.columns:
                st.error(f"❌ '{col}' column missing.")
                st.stop()
    
        # Calculate indicators
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['SMA_50'] = df['Close'].rolling(50).mean()
        df['Signal'] = None
        df.loc[df['SMA_20'] > df['SMA_50'], 'Signal'] = 'BUY'
        df.loc[df['SMA_20'] < df['SMA_50'], 'Signal'] = 'SELL'
    
        # Build complete trade log with stoploss, target, quantity
        trades = []
        in_trade = False
        entry_time = entry_price = stop_loss = target1 = target2 = qty = None
        risk_per_trade = capital * (risk_percent / 100)
    
        for time, row in df.iterrows():
            sig = row['Signal']
            price = row['Close']
            low = row['Low']
    
            if sig == 'BUY' and not in_trade:
                entry_time = time
                entry_price = price
                stop_loss = low
                risk = entry_price - stop_loss
                if risk <= 0:
                    continue
                qty = floor(risk_per_trade / risk)
                target1 = entry_price + 1.5 * risk
                target2 = entry_price + 2.5 * risk
                in_trade = True
    
            elif in_trade:
                if price <= stop_loss:
                    # Stop loss hit
                    exit_time = time
                    exit_price = price
                    pnl = (exit_price - entry_price) * qty
                    trades.append({
                        'Entry Time': entry_time, 'Entry Price': entry_price,
                        'Exit Time': exit_time, 'Exit Price': exit_price,
                        'Qty': qty, 'Exit Type': 'Stop Loss', 'PnL': round(pnl, 2)
                    })
                    in_trade = False
    
                elif price >= target2:
                    # Target 2 hit
                    exit_time = time
                    exit_price = target2
                    pnl = (exit_price - entry_price) * qty
                    trades.append({
                        'Entry Time': entry_time, 'Entry Price': entry_price,
                        'Exit Time': exit_time, 'Exit Price': exit_price,
                        'Qty': qty, 'Exit Type': 'Target 2', 'PnL': round(pnl, 2)
                    })
                    in_trade = False
    
                elif sig == 'SELL':
                    # Manual exit
                    exit_time = time
                    exit_price = price
                    pnl = (exit_price - entry_price) * qty
                    trades.append({
                        'Entry Time': entry_time, 'Entry Price': entry_price,
                        'Exit Time': exit_time, 'Exit Price': exit_price,
                        'Qty': qty, 'Exit Type': 'SELL Signal', 'PnL': round(pnl, 2)
                    })
                    in_trade = False
    
        trade_log = pd.DataFrame(trades)
    
        # Summary metrics
        if not trade_log.empty:
            trade_log['Cumulative PnL'] = trade_log['PnL'].cumsum()
            total_pnl = trade_log['PnL'].sum()
            win_rate = (trade_log['PnL'] > 0).sum() / len(trade_log) * 100
            avg_pnl = trade_log['PnL'].mean()
    
            st.metric("Total PnL", f"₹{total_pnl:.2f}")
            st.metric("Win Rate", f"{win_rate:.2f}%")
            st.metric("Avg PnL per Trade", f"₹{avg_pnl:.2f}")
    
            st.dataframe(trade_log)
            st.line_chart(trade_log.set_index('Exit Time')['Cumulative PnL'])
    
            csv = trade_log.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Trade Log", data=csv, file_name="swing_trade_log.csv", mime="text/csv")
    
        # Candlestick chart + signals
        fig = go.Figure([go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']
        )])
        buys = df[df['Signal'] == 'BUY']
        sells = df[df['Signal'] == 'SELL']
        fig.add_trace(go.Scatter(x=buys.index, y=buys['Close'], mode='markers', marker=dict(symbol='triangle-up', color='green', size=12), name='BUY'))
        fig.add_trace(go.Scatter(x=sells.index, y=sells['Close'], mode='markers', marker=dict(symbol='triangle-down', color='red', size=12), name='SELL'))
        fig.update_layout(title="Swing Trade Chart", xaxis_rangeslider_visible=False, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)     


elif selected == "Intraday Stock Finder":
    st.subheader("📊 Intraday Stock Finder (Simulated on NIFTY 50)")

    # --- Mock NIFTY 50 stock data for simulation ---
    nifty50_stocks = [
        "ADANIENT", "ADANIPORTS", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV",
        "BPCL", "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT",
        "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK",
        "ITC", "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LT", "M&M", "MARUTI", "NTPC", "NESTLEIND",
        "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TCS", "TATACONSUM", "TATAMOTORS",
        "TATASTEEL", "TECHM", "TITAN", "UPL", "ULTRACEMCO", "WIPRO"
    ]

    # --- Generate mock stock data ---
    def generate_mock_data():
        mock_data = []
        for symbol in nifty50_stocks:
            open_price = random.uniform(100, 1500)
            price = open_price * random.uniform(0.98, 1.05)
            prev_close = open_price * random.uniform(0.97, 1.03)
            volume = random.randint(400000, 1200000)
            mock_data.append({
                "symbol": symbol,
                "price": round(price, 2),
                "volume": volume,
                "open_price": round(open_price, 2),
                "prev_close": round(prev_close, 2)
            })
        return mock_data

    # --- Scanner configuration ---
    MIN_VOLUME = 500000
    PRICE_RANGE = (50, 1500)
    PRICE_CHANGE_THRESHOLD = 0.015  # 1.5%

    # --- Simulate technical conditions ---
    def simulate_technical_conditions(stock):
        rsi = random.randint(25, 75)
        vwap = stock['open_price'] + random.uniform(-10, 10)
        above_vwap = stock['price'] > vwap
        breakout_15min = stock['price'] > stock['open_price'] * 1.015
        return rsi, above_vwap, breakout_15min

    # --- Scan logic ---
    def scan_intraday_stocks(stocks):
        shortlisted = []
        for stock in stocks:
            if PRICE_RANGE[0] <= stock['price'] <= PRICE_RANGE[1] and stock['volume'] >= MIN_VOLUME:
                price_change = (stock['price'] - stock['prev_close']) / stock['prev_close']
                if abs(price_change) >= PRICE_CHANGE_THRESHOLD:
                    rsi, above_vwap, breakout_15min = simulate_technical_conditions(stock)

                    if above_vwap and breakout_15min:
                        shortlisted.append({
                            "symbol": stock['symbol'],
                            "price": stock['price'],
                            "rsi": rsi,
                            "above_vwap": above_vwap,
                            "breakout": breakout_15min,
                            "volume": stock['volume']
                        })
        return shortlisted

    # --- Run scanner ---
    mock_stocks = generate_mock_data()
    result = scan_intraday_stocks(mock_stocks)

    # --- Display results ---
    if result:
        df = pd.DataFrame(result)
        st.success(f"{len(df)} stocks shortlisted for intraday trading")
        st.dataframe(df, use_container_width=True)

        # --- CSV Export ---
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", csv, "intraday_shortlist.csv", "text/csv")

        # --- Stock line chart selection ---
        selected_symbol = st.selectbox("📈 Select stock to view mock intraday chart", df["symbol"].unique())

        if selected_symbol:
            # Generate mock intraday line chart
            times = pd.date_range("09:15", "15:30", freq="15min").strftime("%H:%M")
            base_price = df[df["symbol"] == selected_symbol]["price"].values[0]
            prices = [base_price * random.uniform(0.98, 1.02) for _ in times]

            st.line_chart(pd.DataFrame({"Time": times, "Price": prices}).set_index("Time"))

    else:
        st.warning("No suitable intraday stocks found based on current filters.")


elif selected == "Alpha Vantage API":
    st.subheader("📈 Stock Data from Alpha Vantage")

    # Input for API key and symbol 
    api_key = st.text_input("🔑 Enter your Alpha Vantage API Key- 10MY6CQY1UCYDAOB ")
    symbol = st.text_input("📌 Enter Stock Symbol (e.g., AAPL, MSFT, RELIANCE.BSE)")

    if st.button("Fetch Data") and api_key and symbol:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=15min&apikey={api_key}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()

            if "Time Series (15min)" in data:
                df = pd.DataFrame.from_dict(data["Time Series (15min)"], orient='index')
                df = df.astype(float)
                df.index = pd.to_datetime(df.index)
                df = df.sort_index()

                st.success(f"Showing intraday data for {symbol.upper()}")
                st.line_chart(df["4. close"])

                with st.expander("📋 Show Raw Data"):
                    st.dataframe(df)

                # CSV Export
                csv = df.to_csv().encode("utf-8")
                st.download_button("⬇️ Download CSV", csv, f"{symbol}_intraday.csv", "text/csv")
            else:
                st.warning("⚠️ No intraday data found. Check symbol or API limit.")
        else:
            st.error("❌ Failed to fetch data from Alpha Vantage.")


elif selected == "KITE API":
    st.subheader("🔐 Kite Connect API (Zerodha) Integration")

    api_key = st.text_input("Enter your API Key", type="password")
    api_secret = st.text_input("Enter your API Secret", type="password")

    if api_key and api_secret:
        try:
            kite = KiteConnect(api_key=api_key)
            login_url = kite.login_url()

            st.markdown(f"👉 [Click here to login with Zerodha and get your request token]({login_url})")
            request_token = st.text_input("🔑 Paste the Request Token after login")

            if request_token:
                try:
                    data = kite.generate_session(request_token, api_secret=api_secret)
                    kite.set_access_token(data["access_token"])

                    st.success("✅ Login successful!")
                    st.session_state.kite = kite

                    # Create tabs
                    tab1, tab2, tab3 = st.tabs(["👤 Profile", "📈 Holdings", "📝 Orders"])

                    # Tab 1: Profile
                    with tab1:
                        profile = kite.profile()
                        profile_flat = {
                            "User ID": profile.get("user_id"),
                            "User Name": profile.get("user_name"),
                            "Email": profile.get("email"),
                            "User Type": profile.get("user_type"),
                            "Broker": profile.get("broker"),
                            "Exchanges": ", ".join(profile.get("exchanges", [])),
                            "Products": ", ".join(profile.get("products", [])),
                            "Order Types": ", ".join(profile.get("order_types", [])),
                        }
                        df_profile = pd.DataFrame(profile_flat.items(), columns=["Field", "Value"])
                        st.table(df_profile)

                    # Tab 2: Holdings
                    with tab2:
                        holdings = kite.holdings()
                        if holdings:
                            df_holdings = pd.DataFrame(holdings)
                            st.dataframe(df_holdings, use_container_width=True)
                        else:
                            st.info("No holdings available.")

                    # Tab 3: Orders
                    with tab3:
                        orders = kite.orders()
                        if orders:
                            df_orders = pd.DataFrame(orders)
                            st.dataframe(df_orders, use_container_width=True)
                        else:
                            st.info("No orders found.")

                except Exception as e:
                    st.error(f"Login failed: {e}")
        except Exception as e:
            st.error(f"Error generating login URL: {e}")
    else:
        st.info("Please enter your API Key and Secret to continue.")
      
       
        #############################################################################################################################
elif selected == "PaperTrade":

    st.subheader("📊 Backtest + Paper Trading Simulator")

    st.markdown("Upload your stock data with `Date`, `Open`, `High`, `Low`, `Close`, and `Signal` columns.")
    
    uploaded_file = st.file_uploader("📁 Upload CSV File", type=["csv"])

    if uploaded_file:
        try:
            # Load and preprocess data
            df = pd.read_csv(uploaded_file, parse_dates=["Date"])
            df.set_index("Date", inplace=True)

            st.success("✅ File successfully uploaded and processed!")
            st.dataframe(df.head())

            # Initial balance input
            initial_balance = st.number_input("💰 Initial Capital (INR)", value=100000, step=1000)

            # Backtest logic
            def backtest_paper_trade(df, initial_balance=100000):
                balance = initial_balance
                position = 0
                trade_log = []

                for i in range(1, len(df)):
                    price = df['Close'].iloc[i]
                    signal = df['Signal'].iloc[i]
                    date = df.index[i]

                    if signal == 1 and position == 0:
                        shares = balance // price
                        cost = shares * price
                        position = shares
                        balance -= cost
                        trade_log.append({
                            'Date': date, 'Action': 'BUY', 'Shares': shares,
                            'Price': price, 'Balance': balance
                        })

                    elif signal == -1 and position > 0:
                        revenue = position * price
                        balance += revenue
                        trade_log.append({
                            'Date': date, 'Action': 'SELL', 'Shares': position,
                            'Price': price, 'Balance': balance
                        })
                        position = 0

                final_value = balance + (position * df['Close'].iloc[-1])
                returns = (final_value - initial_balance) / initial_balance * 100

                return pd.DataFrame(trade_log), final_value, returns

            # Run simulation
            trade_log, final_value, returns = backtest_paper_trade(df, initial_balance)

            # Display results
            st.subheader("📘 Trade Log")
            st.dataframe(trade_log)

            st.subheader("📈 Summary")
            st.write(f"**Final Portfolio Value**: ₹{final_value:,.2f}")
            st.write(f"**Total Return**: {returns:.2f}%")

        except Exception as e:
            st.error(f"❌ Error processing file: {e}")

    else:
        st.info("📌 Please upload a CSV file to begin the simulation.")
        st.subheader("🕯️ Live Chart (Candlestick + Buy/Sell Signals)")

        fig = go.Figure()
        
        # Candlestick chart
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Price'
        ))
        
        # Buy signals
        buy_signals = df[df['Signal'] == 1]
        fig.add_trace(go.Scatter(
            x=buy_signals.index,
            y=buy_signals['Close'],
            mode='markers',
            marker=dict(symbol='triangle-up', color='green', size=10),
            name='Buy Signal'
        ))
        
        # Sell signals
        sell_signals = df[df['Signal'] == -1]
        fig.add_trace(go.Scatter(
            x=sell_signals.index,
            y=sell_signals['Close'],
            mode='markers',
            marker=dict(symbol='triangle-down', color='red', size=10),
            name='Sell Signal'
        ))
        
        # Layout settings
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False,
            height=600,
            template="plotly_dark",
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)

elif selected == "Live Algo Trading":
    st.title("🤖 Live Algo Trading (Paper/Real Mode)")
    from dotenv import load_dotenv
    #_____________________________________________________________________________________________________________________________
    st.title("📊 Live NIFTY 5‑Minute Candle")

    # Trend Calculation
    def get_trend(df):
        df["EMA5"] = df["Close"].ewm(span=5, adjust=False).mean()
        df["EMA20"] = df["Close"].ewm(span=20, adjust=False).mean()
        if df["EMA5"].iloc[-1] > df["EMA20"].iloc[-1]:
            return "🔼 Uptrend"
        elif df["EMA5"].iloc[-1] < df["EMA20"].iloc[-1]:
            return "🔻 Downtrend"
        else:
            return "➡️ Sideways"
    
    def fetch_5min_data(symbol):
        df = yf.download(tickers=symbol, interval="5m", period="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):  # This checks if the columns are a MultiIndex
            df.columns = df.columns.get_level_values(0)
         # Ensure datetime index is timezone-aware in UTC and then convert to IST
        df.index = df.index.tz_convert("Asia/Kolkata")
        for col in ["Open","High","Low","Close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df.dropna(subset=["Open","High","Low","Close"], inplace=True)
        return df
    
    def plot_candles(df):
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
        )])
        fig.update_layout(
            title="NIFTY 5‑Minute Candles (Today)",
            xaxis_title="Time",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False
        )
        return fig
    
    # Function to plot candlesticks with 20-SMA
    def plot_candles_with_sma(df):
        # Calculate the 20-period SMA
        df['20-SMA'] = df['Close'].rolling(window=20).mean()
    
        # Create the candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Candlesticks"
        )])
    
        # Add the 20-period SMA as a line on top of the chart
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['20-SMA'],
            mode='lines',
            name='20-SMA',
            line=dict(color='orange', width=2)
        ))
    
        # Update the layout of the chart
        fig.update_layout(
            title="NIFTY 5‑Minute Candles with 20-SMA (Today)",
            xaxis_title="Time",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False
        )
    
        return fig
    
    
    symbol = "^NSEI"
    df = fetch_5min_data(symbol)
    #st.write(df.head(25))
    #trend = get_trend(df)
    trend = get_trend(df)
    current_price = float(df["Close"].iloc[-1])
    high = float(df["High"].max())
    low = float(df["Low"].min())
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📈 Trend", trend)
    
    if df.empty:
        st.warning("No data available for today’s 5‑min bars.")
    else:
        st.plotly_chart(plot_candles_with_sma(df), use_container_width=True)

    current_price = float(df["Close"].iloc[-1])
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📈 Trend", trend)
    col2.metric("💰 Price", f"{current_price:.2f} ₹")
    col3.metric("🔺 High", f"{high:.2f} ₹")
    col4.metric("🔻 Low", f"{low:.2f} ₹")
    st.divider()
    time.sleep(30)
    
    
        
    

    #_____________________________________________________________________________________________________________________________

    # ─── AUTO REFRESH ─────────────────────────────────────────────────────────────
    #st.markdown("⏱️ Auto-refresh every 30 seconds")
    #with st.spinner("⏳ Refreshing in 30 seconds..."):
        #time.sleep(30)
        #st.rerun()

   

elif selected == "Test Doctor2 Strategy":
    st.title("🤖 Test Doctor2 Strategy")
    # Trade log to store trade details
    trade_log = []
    import numpy as np
    
    def read_csv_data(uploaded_file):
        try:
            # Read CSV data into DataFrame
            data = pd.read_csv(uploaded_file)
            
            # Ensure the Date column is parsed as a datetime object
            data['Date'] = pd.to_datetime(data['Date'])
            data.set_index('Date', inplace=True)
    
            # Ensure correct column names for OHLCV
            expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            if not all(col in data.columns for col in expected_columns):
                raise ValueError("⚠️ Missing required columns in CSV. Ensure you have Open, High, Low, Close, and Volume columns.")
    
            data.dropna(inplace=True)  # Drop rows with missing data
            return data
    
        except Exception as e:
            st.error(f"⚠️ Error reading the CSV: {e}")
            return pd.DataFrame()
    
    def check_crossing(data):
        if 'Close' not in data.columns:
            raise KeyError("❌ 'Close' column is missing in the DataFrame!")
    
        # Calculate 20‑period SMA
        data['SMA_20'] = data['Close'].rolling(window=20).mean()
    
        # Drop rows where SMA is NaN (first 19 rows)
        data.dropna(subset=['SMA_20'], inplace=True)
    
        # Mark crossings
        data['crossed'] = (data['Close'] > data['SMA_20']).astype(int)
        return data
    
    def check_iv(data, iv_threshold=16):
        # Mock IV — replace with real API call if available
        data['IV'] = 17
        data['iv_check'] = np.where(data['IV'] >= iv_threshold, 1, 0)
        return data
    
    def execute_trade(data):
        for i in range(1, len(data)):
            if data['crossed'].iat[i] == 1 and data['iv_check'].iat[i] == 1:
                entry = data['Close'].iat[i]
                sl = entry * 0.90
                tg = entry * 1.05
                entry_time = data.index[i]
                
                # Log the trade details
                trade_log.append({
                    'Entry Time': entry_time,
                    'Entry Price': entry,
                    'Stop Loss': sl,
                    'Target Price': tg,
                    'Status': 'Open'
                })
                
                st.success(f"✅ Trade @ ₹{entry:.2f}  SL: ₹{sl:.2f}  TG: ₹{tg:.2f}")
                return entry, sl, tg, entry_time
        st.info("ℹ️ No trade signal.")
        return None, None, None, None
    
    def manage_risk(entry, sl, tg, data):
        for price in data['Close']:
            if price >= tg:
                st.success(f"🎯 Target hit @ ₹{price:.2f}")
                close_trade('Target Hit')
                return True
            if price <= sl:
                st.error(f"🛑 SL hit @ ₹{price:.2f}")
                close_trade('Stop Loss Hit')
                return True
        return False
    
    def close_trade(status):
        # Update the last trade in the log to "Closed"
        if trade_log:
            trade_log[-1]['Status'] = status
    
    # --- Streamlit UI ---
    st.title("📊 Doctor Trade Strategy")
    
    # Sidebar inputs
    uploaded_file = st.file_uploader("Upload OHLCV CSV File", type=["csv"])
    
    # Handle CSV file upload
    if uploaded_file is not None:
        # Read data from CSV
        df = read_csv_data(uploaded_file)
        if not df.empty:
            st.subheader("Raw Data")
            st.dataframe(df.tail(20))
    
            try:
                df = check_crossing(df)
                df = check_iv(df)
    
                # Plot
                fig = go.Figure([
                    go.Candlestick(x=df.index,
                                   open=df['Open'], high=df['High'],
                                   low=df['Low'],   close=df['Close']),
                    go.Scatter(     x=df.index,
                                   y=df['SMA_20'],
                                   mode='lines',
                                   name='20 SMA')
                ])
                fig.update_layout(title="OHLCV Data with 20 SMA", xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
    
                # Trade logic
                entry, sl, tg, t0 = execute_trade(df)
                if entry is not None:
                    if manage_risk(entry, sl, tg, df):
                        st.info("🔁 Trade Closed (SL/TG hit)")
    
            except Exception as e:
                st.error(f"❌ Strategy error: {e}")
    
            # Display trade log
            if trade_log:
                st.subheader("Trade Log")
                trade_df = pd.DataFrame(trade_log)
                st.dataframe(trade_df)
    
    else:
        st.warning("⚠️ Please upload a CSV file.")

elif selected == "Doctor2.0 Strategy":
    st.title("⚙️ Test Doctor2.0 Strategy")

    uploaded_file = st.file_uploader("Upload 5-minute Nifty/Bank Nifty CSV file", type=["csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file)

        # Convert and prepare datetime
        df['Date'] = pd.to_datetime(df['Date'])
        df = df.sort_values('Date')
        df.set_index('Date', inplace=True)

        # Calculate Bollinger Bands (20 SMA)
        df['20sma'] = df['Close'].rolling(window=20).mean()
        df['stddev'] = df['Close'].rolling(window=20).std()
        df['upper_band'] = df['20sma'] + 2 * df['stddev']
        df['lower_band'] = df['20sma'] - 2 * df['stddev']

        # Track trades
        trades = []

        for i in range(21, len(df)-2):
            candle = df.iloc[i]
            prev_candle = df.iloc[i-1]

            # Step 2-4: 20 SMA Cross & confirmation
            crossed_up = prev_candle['Close'] < prev_candle['20sma'] and candle['Close'] > candle['20sma']
            closed_above = candle['Close'] > candle['20sma'] and candle['Low'] > candle['20sma']

            if crossed_up and closed_above:
                reference_candle = candle
                prev2_candle = df.iloc[i-2]

                ref_level = max(prev2_candle['High'], prev2_candle['Close'])
                next_candle = df.iloc[i+1]

                if next_candle['High'] > ref_level:
                    entry_price = next_candle['Close']
                    sl_price = entry_price * 0.90
                    target1 = entry_price * 1.05
                    target2 = entry_price * 1.10
                    target3 = entry_price * 1.15
                    final_target = entry_price * 1.20

                    trades.append({
                        'Entry Time': next_candle.name,
                        'Entry Price': round(entry_price, 2),
                        'SL': round(sl_price, 2),
                        'T1': round(target1, 2),
                        'T2': round(target2, 2),
                        'T3': round(target3, 2),
                        'T4': round(final_target, 2),
                        'Reference High': round(ref_level, 2)
                    })

        # Display trades
        st.subheader("📈 Doctor2.0 Strategy Trades")
        if trades:
            trades_df = pd.DataFrame(trades)
            st.dataframe(trades_df)
        else:
            st.warning("No valid trades found based on strategy rules.")

elif selected == "Strategy2.0 Detail":
    st.title("📋 Project Details")

    st.markdown("""
        स्ट्रॅटेजीचा संपूर्ण प्लॅन खालील प्रमाणे आहे:

        📌 Step 1: चार्ट सेटअप
        चार्टवर बोलिंजर बँड (Bollinger Bands) वापरा.
        
        कँडलस्टिक पॅटर्न वापरा, लाईन/हायकन अश्यि नको.
        
        टाइम फ्रेम – ५ मिनिटांचा चार्ट.
        
        📌 Step 2: Center Line (20 SMA) क्रॉसिंग
        बोलिंजर बँडची मधली लाईन म्हणजेच 20 SMA.
        
        Nifty किंवा Bank Nifty ने ही लाईन खालून वर क्रॉस केली पाहिजे.
        
        📌 Step 3: क्रॉस झालेली कँडल त्याच कँडलमध्ये वर क्लोज झाली पाहिजे
        जेव्हा 20 SMA ला क्रॉस करणारी कँडल कॅन्डल उर्ध्वगामी क्लोज होते, तेव्हा त्याची खात्री करा.
        
        📌 Step 4: 20 SMA च्या वर कँडल क्लोज
        त्याच्या नंतरच्या कँडलने 20 SMA ला touch न करता, 20 SMA च्या वर क्लोज झाले पाहिजे.
        
        📌 Step 5: रेफरन्स कँडल मार्क करा
        20 SMA ला क्रॉस करणारी कँडल ही रेफरन्स कँडल म्हणून मार्क करा.
        
        📌 Step 6: रेफरन्स कँडलच्या अगोदरच्या कँडलचा हाय आणि क्लोज
        रेफरन्स कँडलच्या अगोदरच्या कँडलचा हाय आणि क्लोज दोन्हीमध्ये जे मोठे असेल, ते रेफरन्स कँडल नंतरच्या कँडलने खालून वर क्रॉस करत असताना ट्रेड एक्झिक्युट करा.
        
        स्टॉप लॉस त्याच्याखाली 10% असावा.
        
        📌 Step 7: रेफरन्स कँडलच्या अगोदरची कँडल
        रेफरन्स कँडलच्या अगोदरची कँडल ही 20 SMA ला क्रॉस करणारी कँडल म्हणून ओळखली जाईल.
        
        📌 Step 8: रेफरन्स कँडलच्या अगोदरच्या कँडलचा हाय किंवा क्लोज वरून ट्रेड एंटर करा
        रेफरन्स कँडल नंतरच्या कँडलने, त्याच्या अगोदरच्या कँडलचा हाय आणि क्लोज दोन्ही हिट केली पाहिजे.
        
        त्या स्थितीत In the Money Call Option खरेदी करा.
        
        📌 Step 9: प्रॉफिट बुकिंग आणि ट्रेलिंग स्टॉप लॉस
        ट्रेड घेतल्यावर:
        
        10% Stop Loss.
        
        5% Profit Target.
        
        जेव्हा Profit 4% पेक्षा जास्त जाईल, तेव्हा Stop Loss ला Buy Price पर्यंत ट्रेल करा (No Loss Zone).
        
        नंतर, प्रॉफिटमध्ये वाढ केल्यास:
        
        10% Profit वर Stop Loss ला 4% Profit वर ट्रेल करा.
        
        15% Profit वर Stop Loss ला 11% Profit वर ट्रेल करा.
        
        20% Profit झाल्यावर, संपूर्ण प्रॉफिट बुक करा.
        
        📌 Step 10: Implied Volatility चा तपास
        Nifty किंवा Bank Nifty चं Implied Volatility (IV) 16% किंवा त्याहून जास्त असावी, जेव्हा ट्रेड घेण्याचा निर्णय घेतला जातो.
        
        📌 Step 11: ब्रेकआउट आणि ट्रेड इनिशिएशन
        Reference Candle च्या High च्या वर जर पुढील कँडल गेली, तर लगेच त्या इंडेक्सचा सर्वात जवळचा In the Money Call Option खरेदी करा.
        
        📌 Step 12: Risk Management – Stop Loss आणि Profit Booking
        ट्रेड घेतल्यावर:
        
        10% Stop Loss.
        
        5% Profit Target.
        
        जेव्हा Profit 4% पेक्षा जास्त जाईल, तेव्हा Stop Loss ला Buy Price पर्यंत ट्रेल करा (No Loss Zone).
        
        नंतर 10% प्रॉफिट झाल्यावर Stop Loss ला 4% Profit वर ट्रेल करा.
        
        15% प्रॉफिट झाल्यावर Stop Loss ला 11% Profit वर ट्रेल करा.
        
        20% प्रॉफिट झाल्यावर, संपूर्ण प्रॉफिट बुक करा.
        
        📌 Step 13: Time-Based Exit
        ट्रेड इनिशिएट केल्यानंतर 10 मिनिटात, वरच्या पैकी कोणतीही Condition (Target/SL) हिट झाली नाही तर, त्या ट्रेडला तिथेच बुक करा, Profit Loss न पाहता.
        
        📌 Step 14: Trade Time from 9:30 AM to 3:00 PM
        ट्रेड फक्त 9:30 AM ते 3:00 PM दरम्यानच घेतला जावा.
        
        9:30 AM च्या आधी किंवा 3:00 PM नंतर ट्रेड सुरू होणार नाही.
        
        या स्टेप्समध्ये, प्रत्येक ट्रेडमध्ये तुम्ही सुरक्षितपणे आणि परिणामकारकपणे ट्रेड घेण्याचा प्रयत्न करू शकता. आपला Doctor Trade Strategy याप्रमाणे अधिक मजबूत आणि प्रॉफिटेबल होईल.

        ✅ Development Checklist:
        डेटा सोर्सिंग:
        
        5-minute candles for Nifty/Bank Nifty (live + historical).
        
        Bollinger Bands (20 SMA basis) calculation.
        
        IV value from NSE option chain or API.
        
        Reference Candle Logic:
        
        SMA cross check
        
        Close above 20 SMA without touching
        
        Identify reference and pre-reference candles
        
        Trigger check (next candle breaking pre-reference high/close)
        
        Trade Execution (Paper Trading / Live via Zerodha/Fyers API):
        
        ATM Call Option Buy
        
        SL/Target apply
        
        Trailing SL updates
        
        Time-based exit after 10 min if no SL/TP
        
        Trade Management Logic:
        
        Risk Management Module (as per Step 12)
        
        Trail logic:
        
        4% → No loss
        
        10% → SL @ 4%
        
        15% → SL @ 11%
        
        20% → Book full
        
        Streamlit Dashboard UI:
        
        Left Sidebar: Stock selection, Time range, Capital, Risk %, etc.
        
        Right Main: Chart view (candles + BB + markers), Live log, Trade Summary
        
        Telegram Alerts Integration:
        
        Entry/Exit alerts with levels
        
        IV alert (if below 16%, don’t trade)
                    """)

elif selected == "Doctor3.0 Strategy":
    st.title("⚙️ Test Doctor3.0 Strategy")

    st.markdown("""
    ### 📋 Doctor 3.0 स्ट्रॅटेजी प्लॅन:

    ✅ **चार्ट सेटअप**: 5 मिनिटांचा कँडलस्टिक चार्ट + Bollinger Band (20 SMA). 

    ✅ **20 SMA क्रॉसिंग:**
    - कँडलने 20 SMA लाईन खालून वर क्रॉस करून क्लोज केली पाहिजे.
    - नंतरची कँडल ही 20 SMA ला touch न करता वर क्लोज झाली पाहिजे.

    ✅ **Reference Candle Setup:**
    - क्रॉस करणारी कँडल = Reference Candle
    - त्याच्या अगोदरची कँडल महत्त्वाची: तिचा High/Close दोन्हीपैकी जास्त किंमत मार्क करा.
    - नंतरची कँडल ह्या किमतीला खालून वर ब्रेक करत असल्यास ट्रेड एंटर करा.

    ✅ **Entry Condition:**
    - Reference candle नंतरच्या कँडलने prior candle चा High/Close cross केलं पाहिजे.
    - आणि IV > 16% असेल तर, त्या वेळी In the Money Call Option खरेदी करा.

    ✅ **Risk Management:**
    - Entry नंतर Stop Loss: Buy Price - 10%
    - Profit Target: 5%
    - Profit > 4% झाल्यावर Stop Loss ला Entry Price ला ट्रेल करा (No Loss Zone).
    - Profit > 10% = SL @ 4%, Profit > 15% = SL @ 11%, Profit > 20% = Book full profit

    ✅ **Time Based Exit:**
    - Trade घेतल्यावर 10 मिनिटात काहीही हिट न झाल्यास, नफा/तोटा न पाहता एक्झिट करा.

    ✅ **Trade Time:**
    - सकाळी 9:30 ते दुपारी 3:00 पर्यंतच ट्रेड सुरू करा.
    """)

    uploaded_file = st.file_uploader("Upload CSV file with OHLCV data", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip()

        if {'Open', 'High', 'Low', 'Close', 'Volume', 'Date'}.issubset(df.columns):
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values("Date")
            st.success("✅ Data loaded successfully!")
            st.dataframe(df.tail())

            # Calculate 20 SMA and Bollinger Bands
            df['SMA20'] = df['Close'].rolling(window=20).mean()
            df['Upper'] = df['SMA20'] + 2 * df['Close'].rolling(window=20).std()
            df['Lower'] = df['SMA20'] - 2 * df['Close'].rolling(window=20).std()

            # Detect breakout condition
            breakout_signals = []
            entry_price = None
            sl_price = None
            tp_price = None

            for i in range(21, len(df) - 1):
                prev = df.iloc[i - 1]
                curr = df.iloc[i]
                next_candle = df.iloc[i + 1]
                iv = 18  # simulated implied volatility

                if (prev['Close'] < prev['SMA20']) and (curr['Close'] > curr['SMA20']) and (curr['Low'] > curr['SMA20']):
                    ref_price = max(prev['High'], prev['Close'])
                    if next_candle['Close'] > ref_price and iv > 16:
                        entry_price = next_candle['Close']
                        sl_price = entry_price * 0.90
                        tp_price = entry_price * 1.05
                        breakout_signals.append({
                            'Time': df.iloc[i + 1]['Date'],
                            'Entry': entry_price,
                            'SL': sl_price,
                            'TP': tp_price,
                            'IV': iv,
                            'Result': None
                        })

            # Paper Trading Simulation
            results = []
            for signal in breakout_signals:
                trade_open = False
                entry = signal['Entry']
                sl = signal['SL']
                tp = signal['TP']
                entry_time = signal['Time']
                exit_time = entry_time + pd.Timedelta(minutes=10)

                for idx, row in df.iterrows():
                    if row['Date'] < entry_time:
                        continue
                    if row['Date'] > exit_time:
                        results.append({**signal, 'Exit': row['Close'], 'Reason': 'Time Exit'})
                        break
                    if row['Low'] <= sl:
                        results.append({**signal, 'Exit': sl, 'Reason': 'Stop Loss Hit'})
                        break
                    if row['High'] >= tp:
                        results.append({**signal, 'Exit': tp, 'Reason': 'Profit Target Hit'})
                        break

            if results:
                result_df = pd.DataFrame(results)
                st.subheader("📊 Paper Trading Results")
                st.dataframe(result_df)
            else:
                st.info("🚫 No trades detected.")

        else:
            st.error("CSV must contain the following columns: Date, Open, High, Low, Close, Volume")

elif selected == "New Nifty Strategy":
    st.title("⚙️ Test New Nifty Strategy")
    # Step 1: Streamlit App Configuration
    #st.set_page_config("📊 New Nifty Strategy Backtest", layout="centered")
    #st.title("📊 New Nifty Strategy - Backtest")
    
    # Sidebar for Strategy Parameters
    st.header("🛠 Strategy Parameters")
    stop_loss_pct = st.slider("Stop Loss %", 1, 20, 10) / 100
    profit_target_pct = st.slider("Profit Target %", 1, 20, 5) / 100
    trailing_stop_pct = st.slider("Trailing Stop %", 1, 10, 4) / 100
    initial_capital = st.number_input("Initial Capital (₹)", value=50000)
    qty = st.number_input("Quantity per Trade", value=10)
    
    # Option to enable/disable time-based exit
    #enable_time_exit = st.checkbox("Enable Time-Based Exit", value=True)
    enable_time_exit = st.checkbox("Enable Time-Based Exit", value=True)
    exit_minutes = st.number_input("Exit After X Minutes", min_value=1, max_value=60, value=10)
    
    # Step 2: CSV Upload
    uploaded_file = st.file_uploader("📂 Upload CSV file", type="csv")
    
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("✅ Data loaded successfully")
    
        # Step 3: Data Preprocessing
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
    
        df['20_SMA'] = df['Close'].rolling(window=20).mean()
        df['Upper_Band'] = df['20_SMA'] + 2 * df['Close'].rolling(window=20).std()
        df['Lower_Band'] = df['20_SMA'] - 2 * df['Close'].rolling(window=20).std()
    
        st.dataframe(df.tail())
    
        # Strategy Execution
        trades = []
        capital = initial_capital
        position_open = False
        entry_price = 0
        trailing_stop = 0
        stop_loss_price = 0
        profit_target_price = 0
        entry_time = None
        reference_candle = None
        exit_reason = ""
        cumulative_pnl = []
    
        for idx, row in df.iterrows():
            current_time = idx.time()
    
            if datetime.strptime("09:30:00", "%H:%M:%S").time() <= current_time <= datetime.strptime("14:30:00", "%H:%M:%S").time():
                if position_open:
                    if row['Close'] <= stop_loss_price:
                        exit_reason = "Stop Loss Hit"
                    elif row['Close'] >= profit_target_price:
                        exit_reason = "Profit Target Hit"
                    elif row['Close'] < trailing_stop and trailing_stop > 0:
                        exit_reason = "Trailing Stop Hit"
                    #elif enable_time_exit and (idx - entry_time) > timedelta(minutes=10):
                    elif enable_time_exit and (idx - entry_time) > timedelta(minutes=exit_minutes):
                        exit_reason = "Time-Based Exit"
                    else:
                        if row['Close'] > entry_price * (1 + trailing_stop_pct):
                            trailing_stop = row['Close'] * (1 - trailing_stop_pct)
                        continue  # no exit yet
    
                    pnl = qty * (row['Close'] - entry_price)
                    capital += pnl
                    cumulative_pnl.append(capital)
                    trades.append({
                        'Action': 'SELL',
                        'Price': row['Close'],
                        'Exit Reason': exit_reason,
                        'Time': idx,
                        'Capital': capital,
                        'PnL': pnl
                    })
                    position_open = False
                    trailing_stop = 0
                    continue
    
                if row['Close'] > row['20_SMA'] and row['Close'] > row['Upper_Band']:
                    if reference_candle is not None and row['Close'] > reference_candle['Close']:
                        entry_price = row['Close']
                        stop_loss_price = entry_price * (1 - stop_loss_pct)
                        profit_target_price = entry_price * (1 + profit_target_pct)
                        trailing_stop = entry_price * (1 - trailing_stop_pct)
                        entry_time = idx
                        position_open = True
                        trades.append({
                            'Action': 'BUY',
                            'Price': entry_price,
                            'Time': idx,
                            'Capital': capital,
                            'PnL': 0,
                            'Exit Reason': ""
                        })
                    reference_candle = row
            else:
                continue
    
        final_capital = cumulative_pnl[-1] if cumulative_pnl else capital
        st.write(f"💰 Final Capital: ₹{final_capital:,.2f}")
    
        trade_df = pd.DataFrame(trades)
    
        if not trade_df.empty:
            st.subheader("📋 Trade Log")
            st.dataframe(trade_df)
    
            csv = trade_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Trade Log as CSV",
                data=csv,
                file_name='trade_log.csv',
                mime='text/csv',
            )
    
            # 📉 Strategy Execution Chart
            fig = go.Figure(data=[go.Candlestick(
                x=df.index,
                open=df['Open'],
                high=df['High'],
                low=df['Low'],
                close=df['Close'],
                name='Candlesticks'
            )])
    
            for trade in trades:
                color = 'green' if trade['Action'] == 'BUY' else 'red'
                symbol = 'triangle-up' if trade['Action'] == 'BUY' else 'triangle-down'
                fig.add_trace(go.Scatter(
                    x=[trade['Time']],
                    y=[trade['Price']],
                    mode='markers',
                    marker=dict(symbol=symbol, color=color, size=10),
                    name=trade['Action']
                ))
    
            fig.update_layout(
                title="📉 Strategy Execution Chart",
                xaxis_title="Date",
                yaxis_title="Price (₹)",
                template="plotly_dark",
                hovermode="x unified"
            )
            st.plotly_chart(fig)
    
            # 📈 Cumulative PnL Chart
            trade_df['Cumulative Capital'] = trade_df['Capital'].ffill()
            pnl_fig = go.Figure()
            pnl_fig.add_trace(go.Scatter(
                x=trade_df['Time'],
                y=trade_df['Cumulative Capital'],
                mode='lines+markers',
                line=dict(color='gold', width=2),
                name='Cumulative Capital'
            ))
            pnl_fig.update_layout(
                title="📈 Cumulative Capital Over Time",
                xaxis_title="Date",
                yaxis_title="Capital (₹)",
                template="plotly_dark"
            )
            st.plotly_chart(pnl_fig)
    
            # 📊 Performance Summary
            buy_trades = trade_df[trade_df['Action'] == 'BUY']
            sell_trades = trade_df[trade_df['Action'] == 'SELL']
    
            total_trades = len(sell_trades)
            winning_trades = sell_trades[sell_trades['PnL'] > 0].shape[0]
            losing_trades = sell_trades[sell_trades['PnL'] <= 0].shape[0]
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            max_drawdown = trade_df['Cumulative Capital'].cummax() - trade_df['Cumulative Capital']
            max_drawdown = max_drawdown.max() if not max_drawdown.empty else 0
    
            # Count exit reasons
            exit_reasons = sell_trades['Exit Reason'].value_counts().to_dict()
            time_based_exits = exit_reasons.get("Time-Based Exit", 0)
    
            summary_df = pd.DataFrame({
                "Metric": [
                    "Total Trades",
                    "Winning Trades",
                    "Losing Trades",
                    "Win Rate (%)",
                    "Max Drawdown (₹)",
                    "Time-Based Exits"
                ],
                "Value": [
                    total_trades,
                    winning_trades,
                    losing_trades,
                    f"{win_rate:.2f}",
                    f"{max_drawdown:,.2f}",
                    time_based_exits
                ]
            })
    
            st.subheader("📊 Performance Summary")
            st.table(summary_df)
    
            st.subheader("📌 Exit Reason Breakdown")
            exit_reason_df = pd.DataFrame(list(exit_reasons.items()), columns=["Exit Reason", "Count"])
            st.table(exit_reason_df)
    
        else:
            st.warning("🚫 No trades were executed based on the given conditions.")
    else:
        st.warning("📴 Please upload a valid CSV file to backtest the strategy.")  
   
