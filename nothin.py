# app.py
# Streamlit Cloud: Multi-ticker stock screener that trains an XGBoost model on-the-fly

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import re
from bs4 import BeautifulSoup
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- CONFIG ---
NUM_TICKERS = 50
POP_THRESHOLD = 0.05
LOOKBACK_MINUTES = 120
LABEL_HORIZON = 30

st.set_page_config("Real-Time Stock Pop Screener", layout="wide")
st.title("📈 Real-Time Stock Pop Screener")

now_et = datetime.utcnow() - timedelta(hours=5)
if now_et.hour < 4 or now_et.hour > 20:
    st.warning("⚠️ Market is currently closed. 1-minute data may be unavailable until pre-market opens (~4:00 AM ET).")

# --- SCRAPE TICKERS ---
@st.cache_data(ttl=600)
def scrape_tickers():
    tickers = set()
    try:
        pages = [
            ("https://finance.yahoo.com/gainers", r"/quote/"),
            ("https://finance.yahoo.com/most-active", r"/quote/"),
            ("https://finviz.com/screener.ashx?v=111&o=-volume", r"quote\.ashx\?t=")
        ]
        headers = {"User-Agent": "Mozilla/5.0"}
        for url, pattern in pages:
            html = requests.get(url, headers=headers).text
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=re.compile(pattern)):
                t = a.text.strip().upper() if "finviz" in url else a.get("href").split("/")[-1]
                if t.isalpha() and 1 <= len(t) <= 5:
                    tickers.add(t)
    except Exception as e:
        st.error(f"Failed to scrape tickers: {e}")
    return sorted(tickers)[:NUM_TICKERS]

# --- FETCH DATA ---
def fetch_data(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False)
        if df.empty or df.isna().all().any():
            return None
        df = df.tail(LOOKBACK_MINUTES)
        df.dropna(subset=["Close", "High", "Low"], inplace=True)
        df["ticker"] = ticker
        return df
    except:
        return None

# --- FEATURE ENGINEERING ---
def compute_features(df):
    df = df.copy()
    if df.empty or "Close" not in df.columns:
        return pd.DataFrame()
    df["ret_1"] = df["Close"].pct_change(1)
    df["ret_5"] = df["Close"].pct_change(5)
    df["ret_10"] = df["Close"].pct_change(10)
    df["vol_10"] = df["Close"].pct_change().rolling(10).std()
    df["vwap"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["dev_vwap"] = (df["Close"] - df["vwap"]) / df["vwap"]
    df["minute_of_day"] = df.index.hour * 60 + df.index.minute
    return df

# --- LABELING FUNCTION ---
def add_labels(df):
    df = df.copy()
    if df.empty or "Close" not in df.columns:
        return pd.DataFrame()
    future_max = df["Close"].shift(-1).iloc[::-1].rolling(LABEL_HORIZON).max().iloc[::-1]
    df["label"] = ((future_max - df["Close"]) / df["Close"] >= POP_THRESHOLD).astype(int)
    return df

# --- LOAD AND PREP DATA ---
st.info("Fetching and preparing data for ~50 tickers...")
ticker_list = scrape_tickers()
raw_data = [fetch_data(t) for t in ticker_list]
valid_data = [d for d in raw_data if d is not None and not d.empty]

if not valid_data:
    st.warning("⚠️ No live data found. Using fallback demo tickers: TSLA, NVDA, AAPL")
    fallback = ["TSLA", "NVDA", "AAPL"]
    valid_data = [fetch_data(t) for t in fallback if fetch_data(t) is not None and not fetch_data(t).empty]

if not valid_data:
    st.error("Still no data available. Try again during market hours.")
    st.stop()

# --- PREPARE DATA ---
frames = []
for df in valid_data:
    feats = compute_features(df)
    if not feats.empty:
        feats = add_labels(feats)
        frames.append(feats)

if not frames:
    st.error("Failed to generate valid feature data.")
    st.stop()

all_data = pd.concat(frames).dropna(subset=["ret_1", "ret_5", "ret_10", "label"]).reset_index(drop=True)

# --- TRAIN MODEL ---
st.success("Training model...")
features = ["ret_1", "ret_5", "ret_10", "vol_10", "dev_vwap", "minute_of_day"]
X = all_data[features].values
y = all_data["label"].values

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
model = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.07, use_label_encoder=False, eval_metric='logloss')
model.fit(X_scaled, y)

# --- PREDICT POPS ---
latest = all_data.groupby("ticker", group_keys=False).tail(1)
X_latest = scaler.transform(latest[features])
preds = model.predict_proba(X_latest)[:, 1]
latest["p_pop"] = preds

# --- DISPLAY RESULTS ---
st.subheader("Predicted Pop Candidates (Next 30 min)")
top_hits = latest.sort_values("p_pop", ascending=False).head(20)

for _, row in top_hits.iterrows():
    col1, col2 = st.columns([1, 4])
    with col1:
        st.metric(label=row["ticker"], value=f"{row['p_pop']:.2f}", delta=f"{row['ret_1'] * 100:.2f}% 1m")
    with col2:
        hist = all_data[all_data["ticker"] == row["ticker"]].tail(LOOKBACK_MINUTES)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], mode="lines", line=dict(width=2)))
        fig.update_layout(height=150, margin=dict(l=20, r=20, t=10, b=10), xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True)

st.caption("This demo trains an XGBoost model on-the-fly using recent price/volume behavior across ~50 tickers.")
