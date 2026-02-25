from fastapi import FastAPI
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

app = FastAPI()


# ===============================
# Helpers
# ===============================

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def atr(df, period=14):
    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def vwap(df):
    return (df["Close"] * df["Volume"]).cumsum() / df["Volume"].cumsum()


def safe(val):
    if val is None:
        return None
    if pd.isna(val):
        return None
    if np.isinf(val):
        return None
    return round(float(val), 2)


# ===============================
# API
# ===============================

@app.get("/nifty")
def get_nifty():

    try:

        ticker = yf.Ticker("^NSEI")

        # Fetch Data
        data_1m = ticker.history(period="1d", interval="1m")
        data_5m = ticker.history(period="5d", interval="5m")
        data_15m = ticker.history(period="5d", interval="15m")

        if data_1m.empty or data_5m.empty or data_15m.empty:
            return {"error": "Market data unavailable"}


        # ===============================
        # Price Info
        # ===============================

        price = data_1m["Close"].iloc[-1]

        high = data_1m["High"].max()
        low = data_1m["Low"].min()


        # ===============================
        # Indicators
        # ===============================

        ema9_1 = ema(data_1m["Close"], 9).iloc[-1]
        ema20_1 = ema(data_1m["Close"], 20).iloc[-1]

        ema9_5 = ema(data_5m["Close"], 9).iloc[-1]
        ema20_5 = ema(data_5m["Close"], 20).iloc[-1]

        ema9_15 = ema(data_15m["Close"], 9).iloc[-1]
        ema20_15 = ema(data_15m["Close"], 20).iloc[-1]

        vwap_val = vwap(data_1m).iloc[-1]

        atr_val = atr(data_5m).iloc[-1]


        # ===============================
        # Trend / Bias
        # ===============================

        if price > ema20_15 and price > ema20_5:
            bias = "Bullish"
        elif price < ema20_15 and price < ema20_5:
            bias = "Bearish"
        else:
            bias = "Sideways"


        # ===============================
        # Market Structure
        # ===============================

        last_high = data_5m["High"].rolling(10).max().iloc[-1]
        last_low = data_5m["Low"].rolling(10).min().iloc[-1]

        if price > last_high:
            structure = "Breakout"
        elif price < last_low:
            structure = "Breakdown"
        else:
            structure = "Range"


        # ===============================
        # Signal Engine
        # ===============================

        signal = "WAIT"
        reason = "No clear setup"

        stoploss = None
        target = None


        # Bullish Setup
        if (
            bias == "Bullish"
            and price > ema9_5
            and price > vwap_val
        ):
            signal = "CALL"
            reason = "Uptrend + Pullback above VWAP"

            stoploss = price - (atr_val * 1.2)
            target = price + (atr_val * 2)


        # Bearish Setup
        elif (
            bias == "Bearish"
            and price < ema9_5
            and price < vwap_val
        ):
            signal = "PUT"
            reason = "Downtrend + Pullback below VWAP"

            stoploss = price + (atr_val * 1.2)
            target = price - (atr_val * 2)


        # Range Market
        elif bias == "Sideways":
            signal = "WAIT"
            reason = "Market in range — avoid trading"


        # ===============================
        # Response
        # ===============================

        return {

            # Price
            "price": safe(price),
            "day_high": safe(high),
            "day_low": safe(low),

            # Indicators
            "vwap": safe(vwap_val),
            "atr": safe(atr_val),

            "ema9_15m": safe(ema9_15),
            "ema20_15m": safe(ema20_15),

            "ema9_5m": safe(ema9_5),
            "ema20_5m": safe(ema20_5),

            "ema9_1m": safe(ema9_1),
            "ema20_1m": safe(ema20_1),

            # Analysis
            "bias": bias,
            "structure": structure,

            # Trade
            "signal": signal,
            "reason": reason,
            "stoploss": safe(stoploss),
            "target": safe(target),

            # Time
            "time": str(datetime.now())
        }


    except Exception as e:

        return {
            "error": str(e),
            "time": str(datetime.now())
        }
