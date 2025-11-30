"""
Streamlit single-file app for NIFTY Base-Zone Option Strategy (Zerodha KiteConnect)

Features:
- Upload instruments.csv
- Enter Kite API_KEY and ACCESS_TOKEN
- Start/Stop strategy
- Uses 15-min candles and previous session 15:00-15:15 as Base Zone
- Implements Conditions 1-4 from user's spec
- Selects nearest weekly ITM option (CALL/PUT)
- Places Market entry, separate SL (SL order), optional TP (limit) and trailing SL via swing lows/highs
- Forced exit after 16 minutes if no exit
- Single active trade enforcement
- Basic logging and UI

IMPORTANT: Test on paper / small size first. This code is provided as-is and requires
live credentials + instruments.csv from Kite. Use paper trading mode to avoid real orders.

"""

import streamlit as st
from kiteconnect import KiteConnect
import pandas as pd
import threading
import time
import datetime as dt
import math
import io
import logging

# ----------------- CONFIG & HELPERS -----------------
st.set_page_config(page_title="Doctor Strategy Streamlit - Single File", layout="wide")
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

LOT_SIZE = 75       # change if your NIFTY lot size differs
NUM_LOTS = 10
QUANTITY = LOT_SIZE * NUM_LOTS  # 750
STRIKE_STEP = 50
POLL_INTERVAL = 5   # seconds
FORCE_EXIT_SECONDS = 16 * 60  # 16 minutes -> seconds

# ----------------- Utility functions -----------------
@st.cache_data
def load_instruments_csv(buf):
    df = pd.read_csv(buf)
    # Ensure consistent column names
    cols = [c.lower() for c in df.columns]
    df.columns = cols
    return df

def round_down_to_strike(price):
    return int(math.floor(price / STRIKE_STEP) * STRIKE_STEP)

def round_up_to_strike(price):
    return int(math.ceil(price / STRIKE_STEP) * STRIKE_STEP)

# helper to search instruments DataFrame
def find_option_row(df, strike, opt_type, expiry_date):
    # expiry_date is date object
    # common file has columns: tradingsymbol, instrument_token, expiry, strike, name, segment, exchange
    dfc = df.copy()
    # normalize expiry column
    if 'expiry' in dfc.columns:
        dfc['expiry'] = pd.to_datetime(dfc['expiry']).dt.date
    # filter name contains NIFTY or tradingsymbol contains NIFTY
    dfc = dfc[dfc['tradingsymbol'].str.contains('NIFTY', case=False, na=False)]
    mask = (dfc['strike'] == strike) & (dfc['tradingsymbol'].str.upper().str.contains(opt_type))
    if 'expiry' in dfc.columns:
        mask = mask & (dfc['expiry'] == expiry_date)
    res = dfc[mask]
    if not res.empty:
        return res.iloc[0].to_dict()
    # fallback: try to match without expiry
    res = dfc[(dfc['strike'] == strike) & (dfc['tradingsymbol'].str.upper().str.contains(opt_type))]
    if not res.empty:
        return res.iloc[0].to_dict()
    return None

def nearest_weekly_expiry(today=None):
    if not today:
        today = dt.date.today()
    weekday = today.weekday()  # Monday=0 ... Sunday=6
    if weekday == 4:  # Friday
        return today
    days_ahead = (4 - weekday) % 7
    if days_ahead == 0:
        days_ahead = 7
    expiry = today + dt.timedelta(days=days_ahead)
    return expiry

# -------------- Kite wrapper (light) -----------------
class KiteClient:
    def __init__(self, api_key, access_token):
        self.api_key = api_key
        self.access_token = access_token
        self.kite = None
        try:
            self.kite = KiteConnect(api_key=api_key)
            self.kite.set_access_token(access_token)
        except Exception as e:
            st.error(f"Kite init error: {e}")
            raise

    def ltp(self, symbol):
        return self.kite.ltp(symbol)

    def historical(self, symbol, from_dt, to_dt, interval="15minute"):
        return self.kite.historical_data(symbol, from_dt, to_dt, interval)

    def place_order_market(self, tradingsymbol, exchange, transaction_type, qty, product="MIS"):
        return self.kite.place_order(
            variety=self.kite.VARIETY_REGULAR,
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            transaction_type=transaction_type,
            quantity=qty,
            order_type=self.kite.ORDER_TYPE_MARKET,
            product=product
        )

    def place_order_sl(self, tradingsymbol, exchange, transaction_type, qty, trigger_price, product="MIS"):
        return self.kite.place_order(
            variety=self.kite.VARIETY_REGULAR,
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            transaction_type=transaction_type,
            quantity=qty,
            order_type=self.kite.ORDER_TYPE_SL,
            product=product,
            trigger_price=round(trigger_price, 2)
        )

    def place_limit(self, tradingsymbol, exchange, transaction_type, qty, price, product="MIS"):
        return self.kite.place_order(
            variety=self.kite.VARIETY_REGULAR,
            exchange=exchange,
            tradingsymbol=tradingsymbol,
            transaction_type=transaction_type,
            quantity=qty,
            order_type=self.kite.ORDER_TYPE_LIMIT,
            product=product,
            price=round(price, 2)
        )

    def cancel_order(self, order_id):
        try:
            return self.kite.cancel_order(variety=self.kite.VARIETY_REGULAR, order_id=order_id)
        except Exception as e:
            logging.warning(f"Cancel failed {order_id}: {e}")

    def orders(self):
        return self.kite.orders()

# -------------- Strategy / Trade Manager -----------------
class TradeManager:
    def __init__(self, kite_client, instruments_df, paper_trade=True):
        self.kc = kite_client
        self.instruments = instruments_df
        self.paper = paper_trade
        self.active = None
        self.lock = threading.Lock()
        self.log = []

    def log_add(self, msg):
        timestamp = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log.append({'ts': timestamp, 'msg': msg})
        logging.info(msg)

    def select_nearest_itm(self, is_call=True):
        spot = get_nifty_spot_ltp_wrapper(self.kc)
        if is_call:
            strike = round_down_to_strike(spot)
            opt_type = 'CE'
        else:
            strike = round_up_to_strike(spot)
            opt_type = 'PE'
        expiry = nearest_weekly_expiry(dt.date.today())
        row = find_option_row(self.instruments, strike, opt_type, expiry)
        if not row:
            # try +/- one step
            row = find_option_row(self.instruments, strike - STRIKE_STEP, opt_type, expiry) or find_option_row(self.instruments, strike + STRIKE_STEP, opt_type, expiry)
        if not row:
            raise RuntimeError(f"No instrument found for {strike}{opt_type} expiry {expiry}")
        return row

    def start_trade(self, direction, opt_row, entry_spot, sl_trigger=None, tp_price=None):
        with self.lock:
            if self.active:
                self.log_add("Active trade exists. Skipping new trade.")
                return False
            tradingsymbol = opt_row['tradingsymbol']
            exchange = opt_row.get('exchange', 'NFO')
            # Place market entry (BUY)
            if self.paper:
                entry_order_id = f"PAPER-{int(time.time())}"
                self.log_add(f"PAPER: Placed MARKET BUY {tradingsymbol} qty {QUANTITY} id {entry_order_id}")
            else:
                entry_order_id = self.kc.place_order_market(tradingsymbol, exchange, "BUY", QUANTITY)
                self.log_add(f"ENTRY order id {entry_order_id}")
            # Place SL as separate order (SELL)
            sl_order_id = None
            if sl_trigger:
                if self.paper:
                    sl_order_id = f"PAPER-SL-{int(time.time())}"
                    self.log_add(f"PAPER: Placed SL SELL {tradingsymbol} qty {QUANTITY} trigger {sl_trigger} id {sl_order_id}")
                else:
                    sl_order_id = self.kc.place_order_sl(tradingsymbol, exchange, "SELL", QUANTITY, sl_trigger)
                    self.log_add(f"SL order id {sl_order_id}")
            # Place TP if provided
            tp_order_id = None
            if tp_price:
                if self.paper:
                    tp_order_id = f"PAPER-TP-{int(time.time())}"
                    self.log_add(f"PAPER: Placed TP SELL {tradingsymbol} qty {QUANTITY} price {tp_price} id {tp_order_id}")
                else:
                    tp_order_id = self.kc.place_limit(tradingsymbol, exchange, "SELL", QUANTITY, tp_price)
                    self.log_add(f"TP order id {tp_order_id}")
            self.active = {
                'direction': direction,
                'instrument': opt_row,
                'entry_id': entry_order_id,
                'sl_id': sl_order_id,
                'tp_id': tp_order_id,
                'entry_time': dt.datetime.now(),
                'entry_spot': entry_spot,
                'last_trail': None
            }
            # Start monitor thread
            t = threading.Thread(target=self._monitor_active_trade, args=(self.active,), daemon=True)
            t.start()
            return True

    def _monitor_active_trade(self, trade):
        self.log_add(f"Monitoring trade {trade['entry_id']}")
        forced_exit_at = trade['entry_time'] + dt.timedelta(seconds=FORCE_EXIT_SECONDS)
        tradingsymbol = trade['instrument']['tradingsymbol']
        exchange = trade['instrument'].get('exchange', 'NFO')
        while True:
            with self.lock:
                if not self.active or self.active['entry_id'] != trade['entry_id']:
                    self.log_add('Trade cleared externally; monitor exit.')
                    return
            now = dt.datetime.now()
            # Check orders status if live
            try:
                if not self.paper:
                    orders = self.kc.orders()
                    # scan statuses
                    for o in orders:
                        if str(o.get('order_id')) == str(trade.get('sl_id')):
                            stt = o.get('status')
                            if stt and stt.upper() in ("COMPLETE", "TRIGGERED", "CANCELLED", "FILLED"):
                                self.log_add(f"SL order status: {stt}. Exiting and cancelling TP if any.")
                                if trade.get('tp_id'):
                                    self.kc.cancel_order(trade['tp_id'])
                                self._clear_active()
                                return
                        if str(o.get('order_id')) == str(trade.get('tp_id')):
                            stt = o.get('status')
                            if stt and stt.upper() in ("COMPLETE", "FILLED"):
                                self.log_add(f"TP hit: {stt}. Cancelling SL and exiting.")
                                if trade.get('sl_id'):
                                    self.kc.cancel_order(trade['sl_id'])
                                self._clear_active()
                                return
            except Exception as e:
                logging.debug(f"Order status check error: {e}")
            # trailing SL: use recent swing low/high on index to move SL
            try:
                if trade['direction'] == 'BUY_CALL':
                    swing_low = recent_swing_low_15m_wrapper(self.kc, dt.datetime.now(), lookback_candles=3)
                    if swing_low:
                        new_trigger = swing_low - 0.5
                        if trade['sl_id'] and (trade['last_trail'] is None or new_trigger > trade['last_trail']):
                            if self.paper:
                                self.log_add(f"PAPER: Trail SL -> {new_trigger} for {tradingsymbol}")
                                trade['last_trail'] = new_trigger
                            else:
                                try:
                                    self.kc.kite.modify_order(variety=self.kc.kite.VARIETY_REGULAR, order_id=trade['sl_id'], trigger_price=round(new_trigger,2))
                                    self.log_add(f"Modified SL to {new_trigger}")
                                    trade['last_trail'] = new_trigger
                                except Exception as e:
                                    logging.debug(f"Modify SL error: {e}")
                else:
                    swing_high = recent_swing_high_15m_wrapper(self.kc, dt.datetime.now(), lookback_candles=3)
                    if swing_high:
                        new_trigger = swing_high + 0.5
                        if trade['sl_id'] and (trade['last_trail'] is None or new_trigger < trade['last_trail']):
                            if self.paper:
                                self.log_add(f"PAPER: Trail SL -> {new_trigger} for {tradingsymbol}")
                                trade['last_trail'] = new_trigger
                            else:
                                try:
                                    self.kc.kite.modify_order(variety=self.kc.kite.VARIETY_REGULAR, order_id=trade['sl_id'], trigger_price=round(new_trigger,2))
                                    self.log_add(f"Modified SL to {new_trigger}")
                                    trade['last_trail'] = new_trigger
                                except Exception as e:
                                    logging.debug(f"Modify SL error: {e}")
            except Exception as e:
                logging.debug(f"Trailing computation error: {e}")

            # Force exit after 16 minutes
            if now >= forced_exit_at:
                self.log_add("Force exit after 16 minutes: selling at market")
                if self.paper:
                    self.log_add(f"PAPER: MARKET SELL {tradingsymbol} qty {QUANTITY}")
                else:
                    try:
                        self.kc.place_order_market(tradingsymbol, exchange, "SELL", QUANTITY)
                    except Exception as e:
                        logging.warning(f"Force exit market order failed: {e}")
                if trade.get('sl_id'):
                    if not self.paper:
                        self.kc.cancel_order(trade['sl_id'])
                if trade.get('tp_id'):
                    if not self.paper:
                        self.kc.cancel_order(trade['tp_id'])
                self._clear_active()
                return

            time.sleep(POLL_INTERVAL)

    def _clear_active(self):
        with self.lock:
            self.log_add('Clearing active trade state')
            self.active = None

# --------- Index & candle helper wrappers (use kc.historical) ----------

def get_nifty_spot_ltp_wrapper(kc: KiteClient):
    # try common symbols; uses kite.ltp
    candidates = ["NSE:NIFTY 50", "NSE:NIFTY", "NSE:NIFTY50"]
    for s in candidates:
        try:
            d = kc.ltp(s)
            val = list(d.values())[0]['last_price']
            return float(val)
        except Exception:
            continue
    # fallback raise
    raise RuntimeError("Unable to fetch NIFTY spot LTP from Kite. Ensure symbol mapping or instruments csv present.")


def fetch_15m_candles_wrapper(kc: KiteClient, from_dt, to_dt):
    # symbol string for index
    sym = "NSE:NIFTY 50"
    return kc.historical(sym, from_dt, to_dt, "15minute")


def recent_swing_low_15m_wrapper(kc: KiteClient, reference_time, lookback_candles=3):
    end = reference_time - dt.timedelta(seconds=1)
    start = end - dt.timedelta(minutes=15 * lookback_candles)
    candles = fetch_15m_candles_wrapper(kc, start, end)
    lows = [c['low'] for c in candles] if candles else []
    return min(lows) if lows else None


def recent_swing_high_15m_wrapper(kc: KiteClient, reference_time, lookback_candles=3):
    end = reference_time - dt.timedelta(seconds=1)
    start = end - dt.timedelta(minutes=15 * lookback_candles)
    candles = fetch_15m_candles_wrapper(kc, start, end)
    highs = [c['high'] for c in candles] if candles else []
    return max(highs) if highs else None

# -------------- Streamlit UI -----------------
st.title("Doctor Strategy  - Single-file Streamlit (NIFTY Options)")
st.markdown("**Instructions:** Upload `instruments.csv` from Kite, enter API Key & Access Token. Use PAPER mode for testing.")

col1, col2 = st.columns([1, 1])
with col1:
    instruments_file = st.file_uploader("Upload instruments.csv (Kite)", type=['csv'])
    api_key = st.text_input("Kite API Key", type="password")
    access_token = st.text_input("Kite Access Token", type="password")
    paper_trade = st.checkbox("Paper Trading (no live orders)", value=True)
    start_btn = st.button("Start Strategy")
    stop_btn = st.button("Stop Strategy")

with col2:
    st.write("**Strategy settings**")
    st.write(f"Lot size: {LOT_SIZE}, Lots: {NUM_LOTS}, Quantity: {QUANTITY}")
    st.write(f"Strike step: {STRIKE_STEP}")
    st.write("Trading window: 09:30 - 15:00 IST; Single active trade; 16-minute forced exit")

# Status and logs
status_placeholder = st.empty()
log_df_placeholder = st.empty()

# Global state holder
if 'engine' not in st.session_state:
    st.session_state['engine'] = None

if instruments_file:
    ins_df = load_instruments_csv(instruments_file)
    st.session_state['instruments_df'] = ins_df
    st.success(f"Loaded instruments.csv with {len(ins_df)} rows")
else:
    ins_df = None

if start_btn:
    if not api_key or not access_token:
        st.error("Provide API Key and Access Token before starting (or enable paper trading).")
    elif not instruments_file:
        st.error("Upload instruments.csv first.")
    else:
        try:
            kc = KiteClient(api_key, access_token) if not paper_trade else None
            tm = TradeManager(kc, ins_df, paper_trade=paper_trade)
            st.session_state['engine'] = tm
            status_placeholder.info("Engine started. Monitoring for Day-1 first candle and triggers.")

            # Start evaluator thread (runs strategy detection & watchers)
            def evaluator_runner():
                try:
                    run_evaluate_and_watch(tm, kc)
                except Exception as e:
                    tm.log_add(f"Evaluator error: {e}")
            t = threading.Thread(target=evaluator_runner, daemon=True)
            t.start()
        except Exception as e:
            st.error(f"Failed to start engine: {e}")

if stop_btn:
    if st.session_state.get('engine'):
        eng = st.session_state['engine']
        eng._clear_active()
        st.session_state['engine'] = None
        status_placeholder.warning("Engine stopped by user.")
    else:
        st.warning("Engine not running.")

# show logs
if st.session_state.get('engine'):
    eng = st.session_state['engine']
    logs = pd.DataFrame(eng.log)
    if not logs.empty:
        log_df_placeholder.dataframe(logs.tail(200))
else:
    st.info("Engine not running. Logs will appear here when you start the strategy.")

# -------------- Evaluation & Trigger functions (core logic) -----------------

def get_base_zone_prev_day_wrapper(kc: KiteClient):
    # fetch previous trading day's 15:00-15:15 candle
    today = dt.date.today()
    prev = today - dt.timedelta(days=1)
    from_dt = dt.datetime.combine(prev, dt.time(15,0))
    to_dt = dt.datetime.combine(prev, dt.time(15,16))
    candles = fetch_15m_candles_wrapper(kc, from_dt, to_dt)
    if not candles:
        raise RuntimeError("No prev day 15:00-15:15 candle found")
    c = candles[0]
    return float(c['open']), float(c['close'])


def get_day1_first_candle_wrapper(kc: KiteClient, trading_day):
    from_dt = dt.datetime.combine(trading_day, dt.time(9,15))
    to_dt = dt.datetime.combine(trading_day, dt.time(9,31))
    candles = fetch_15m_candles_wrapper(kc, from_dt, to_dt)
    if not candles:
        raise RuntimeError("No first 15-min candle found for Day1")
    return candles[0]


def run_evaluate_and_watch(trade_manager: TradeManager, kc: KiteClient):
    # This function implements the Condition detection and spawns watchers
    if trade_manager.paper:
        # For paper mode we use a mock Kite client functionality using the instruments file
        # but some historical fetches require kite; so raise if not provided
        if kc is None:
            st.warning("Paper mode active: historical candle fetch requires Kite historicals to be available. For full testing, provide live credentials or prefetch candles separately.")
    if kc is None:
        # cannot fetch historical candles without Kite
        trade_manager.log_add("No Kite client: historical candle fetch disabled. Start with live credentials or use paper trading + precomputed candles.")
        return
    # compute base zone
    try:
        base_open, base_close = get_base_zone_prev_day_wrapper(kc)
    except Exception as e:
        trade_manager.log_add(f"Base zone fetch failed: {e}")
        return
    base_min = min(base_open, base_close)
    base_max = max(base_open, base_close)
    trade_manager.log_add(f"Base Zone {base_min} - {base_max}")

    # wait until the first 15-min candle (09:15-09:30) exists and has closed
    today = dt.date.today()
    trade_manager.log_add("Waiting for Day1 first 15-min candle (09:15-09:30) close...")
    # wait until after 09:31
    while True:
        now = dt.datetime.now()
        if now.time() > dt.time(9,31):
            break
        time.sleep(5)
    try:
        c1 = get_day1_first_candle_wrapper(kc, today)
    except Exception as e:
        trade_manager.log_add(f"Failed to fetch Day1 first candle: {e}")
        return
    H1 = float(c1['high']); L1 = float(c1['low']); C1 = float(c1['close']); O1 = float(c1['open'])
    trade_manager.log_add(f"Day1 first candle H1={H1}, L1={L1}, C1={C1}")

    # Condition 1
    crossed_from_below_to_above = ((float(c1['low']) < base_min and C1 > base_max) or (O1 < base_min and C1 > base_max))
    if crossed_from_below_to_above and C1 > base_max:
        trade_manager.log_add("Condition 1 detected: Candle 1 (break above base zone)")
        threading.Thread(target=watch_break_and_enter, args=(trade_manager, kc, True, H1), daemon=True).start()

    # Condition 2 - major gap down
    if C1 < base_min:
        trade_manager.log_add("Condition 2 detected: Major Gap Down (Ref Candle 2)")
        threading.Thread(target=watch_break_and_enter, args=(trade_manager, kc, False, L1), daemon=True).start()
        threading.Thread(target=monitor_for_zone_cut_and_flip, args=(trade_manager, kc, base_min, base_max, 'BULL_FLIP_AFTER_REF2'), daemon=True).start()

    # Condition 3 - major gap up
    if C1 > base_max:
        trade_manager.log_add("Condition 3 detected: Major Gap Up (Ref Candle 3)")
        threading.Thread(target=watch_break_and_enter, args=(trade_manager, kc, True, H1), daemon=True).start()
        threading.Thread(target=monitor_for_zone_cut_and_flip, args=(trade_manager, kc, base_min, base_max, 'BEAR_FLIP_AFTER_REF3'), daemon=True).start()

    # Condition 4 - break below base zone
    crossed_from_above_to_below = ((float(c1['high']) > base_max and C1 < base_min) or (O1 > base_max and C1 < base_min))
    if crossed_from_above_to_below and C1 < base_min:
        trade_manager.log_add("Condition 4 detected: Candle 4 (break below base zone)")
        threading.Thread(target=watch_break_and_enter, args=(trade_manager, kc, False, L1), daemon=True).start()

# watcher functions

def watch_break_and_enter(trade_manager: TradeManager, kc: KiteClient, is_call: bool, trigger_level: float):
    tag = 'CALL' if is_call else 'PUT'
    trade_manager.log_add(f"Watcher started for {tag} trigger {trigger_level}")
    start_allowed = dt.datetime.combine(dt.date.today(), dt.time(9,30))
    end_allowed = dt.datetime.combine(dt.date.today(), dt.time(15,0))
    while True:
        now = dt.datetime.now()
        if now < start_allowed:
            time.sleep(2)
            continue
        if now > end_allowed:
            trade_manager.log_add(f"{tag} watcher: entry window closed for day.")
            return
        try:
            spot = get_nifty_spot_ltp_wrapper(kc)
        except Exception as e:
            trade_manager.log_add(f"Failed to get spot LTP: {e}")
            time.sleep(POLL_INTERVAL)
            continue
        if is_call and spot >= trigger_level:
            trade_manager.log_add(f"Trigger hit for CALL (spot {spot} >= {trigger_level}). Selecting nearest ITM CALL and entering.")
            try:
                instr = trade_manager.select_nearest_itm(is_call=True)
                swing_low = recent_swing_low_15m_wrapper(kc, dt.datetime.now(), lookback_candles=3)
                sl_trigger = swing_low - 0.5 if swing_low else None
                trade_manager.start_trade('BUY_CALL', instr, entry_spot=spot, sl_trigger=sl_trigger, tp_price=None)
            except Exception as e:
                trade_manager.log_add(f"Entry error: {e}")
            return
        if (not is_call) and spot <= trigger_level:
            trade_manager.log_add(f"Trigger hit for PUT (spot {spot} <= {trigger_level}). Selecting nearest ITM PUT and entering.")
            try:
                instr = trade_manager.select_nearest_itm(is_call=False)
                swing_high = recent_swing_high_15m_wrapper(kc, dt.datetime.now(), lookback_candles=3)
                sl_trigger = swing_high + 0.5 if swing_high else None
                trade_manager.start_trade('BUY_PUT', instr, entry_spot=spot, sl_trigger=sl_trigger, tp_price=None)
            except Exception as e:
                trade_manager.log_add(f"Entry error: {e}")
            return
        time.sleep(POLL_INTERVAL)


def monitor_for_zone_cut_and_flip(trade_manager: TradeManager, kc: KiteClient, base_min, base_max, flip_tag):
    trade_manager.log_add(f"Flip monitor started {flip_tag}")
    end_allowed = dt.datetime.combine(dt.date.today(), dt.time(15,0))
    while dt.datetime.now() < end_allowed:
        time.sleep(10)
        try:
            now = dt.datetime.now()
            # fetch last closed 15-min candle
            minute = (now.minute // 15) * 15
            end = now.replace(minute=minute, second=0, microsecond=0)
            start = end - dt.timedelta(minutes=15)
            candles = fetch_15m_candles_wrapper(kc, start, end + dt.timedelta(minutes=1))
            if not candles:
                continue
            last = candles[-1]
            close_v = float(last['close'])
            if flip_tag.startswith('BULL') and close_v > base_max:
                Hc = float(last['high'])
                trade_manager.log_add('Bull flip detected: Candle closes above base zone. Watching for break above its high.')
                watch_break_and_enter(trade_manager, kc, True, Hc)
                return
            if flip_tag.startswith('BEAR') and close_v < base_min:
                Lc = float(last['low'])
                trade_manager.log_add('Bear flip detected: Candle closes below base zone. Watching for break below its low.')
                watch_break_and_enter(trade_manager, kc, False, Lc)
                return
        except Exception as e:
            trade_manager.log_add(f"Flip monitor error: {e}")
            time.sleep(5)
    trade_manager.log_add(f"Flip monitor {flip_tag} ended for day.")

# ----------------- End of app -----------------

st.markdown("---")
st.markdown("**Disclaimer:** Live trading with real money involves risk. Test thoroughly with paper trading. This script is a technical translation of your strategy and provided for educational/automation assistance only.")
