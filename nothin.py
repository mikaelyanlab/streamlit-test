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
LOOKBACK_MINUTES = 120  # last 2 hours
LABEL_HORIZON = 30  # future 30 minutes

st.set_page_config("Real-Time Stock Pop Screener", layout="wide")
st.title("📈 Real-Time Stock Pop Screener")

# --- SCRAPE TICKERS ---
@st.cache_data(ttl=600)
def scrape_tickers():
    tickers = set()
    try:
        # Yahoo: Top Gainers
        soup = BeautifulSoup(requests.get("https://finance.yahoo.com/gainers").text, "html.parser")
        for a in soup.find_all("a", href=re.compile(r"/quote/")):
            t = a.get("href").split("/")[-1]
            if t.isupper() and len(t) <= 5:
                tickers.add(t)
        # Yahoo: Most Active
        soup = BeautifulSoup(requests.get("https://finance.yahoo.com/most-active").text, "html.parser")
        for a in soup.find_all("a", href=re.compile(r"/quote/")):
            t = a.get("href").split("/")[-1]
            if t.isupper() and len(t) <= 5:
                tickers.add(t)
        # Finviz
        soup = BeautifulSoup(requests.get("https://finviz.com/screener.ashx?v=111&o=-volume", headers={"User-Agent": "Mozilla/5.0"}).text, "html.parser")
        for a in soup.find_all("a", href=re.compile(r"quote\.ashx\?t=")):
            t = a.text.strip()
            if t.isupper() and len(t) <= 5:
                tickers.add(t)
    except Exception as e:
        st.error(f"Failed to scrape tickers: {e}")
    return sorted(list(tickers))[:NUM_TICKERS]

# --- FETCH DATA ---
def fetch_data(ticker):
    try:
        df = yf.download(ticker, period="1d", interval="1m", progress=False)
        df = df.tail(LOOKBACK_MINUTES)
        df.dropna(inplace=True)
        df["ticker"] = ticker
        return df
    except:
        return pd.DataFrame()

# --- FEATURE ENGINEERING ---
def compute_features(df):
    df = df.copy()
    df["ret_1"] = df["close"].pct_change(1)
    df["ret_5"] = df["close"].pct_change(5)
    df["ret_10"] = df["close"].pct_change(10)
    df["vol_10"] = df["close"].pct_change().rolling(10).std()
    df["vwap"] = (df["high"] + df["low"] + df["close"]) / 3
    df["dev_vwap"] = (df["close"] - df["vwap"]) / df["vwap"]
    df["minute_of_day"] = df.index.hour * 60 + df.index.minute
    return df

# --- LABELING FUNCTION ---
def add_labels(df):
    future_max = df["close"].shift(-1).iloc[::-1].rolling(LABEL_HORIZON).max().iloc[::-1]
    df["label"] = ((future_max - df["close"]) / df["close"] >= POP_THRESHOLD).astype(int)
    return df

# --- LOAD AND PREP DATA ---
st.info("Fetching and preparing data for ~50 tickers...")
ticker_list = scrape_tickers()
raw_data = [fetch_data(t) for t in ticker_list]
all_data = pd.concat(raw_data).dropna()

if all_data.empty:
    st.error("No data pulled. Try refreshing or changing filters.")
    st.stop()

all_data = all_data.groupby("ticker").apply(compute_features).dropna(subset=["ret_1", "ret_5", "ret_10"]).reset_index(drop=True)
all_data = all_data.groupby("ticker").apply(add_labels).reset_index(drop=True)

# --- TRAIN MODEL ---
st.success("Training model...")
features = ["ret_1", "ret_5", "ret_10", "vol_10", "dev_vwap", "minute_of_day"]
train_df = all_data.dropna(subset=features + ["label"])

X = train_df[features].values
y = train_df["label"].values
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
model = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.07, use_label_encoder=False, eval_metric='logloss')
model.fit(X_scaled, y)

# --- APPLY MODEL TO LATEST ROW OF EACH TICKER ---
st.subheader("Predicted Pop Candidates (Next 30 min)")
latest_rows = all_data.groupby("ticker").tail(1).dropna(subset=features)
X_latest = scaler.transform(latest_rows[features].values)
preds = model.predict_proba(X_latest)[:, 1]
latest_rows["p_pop"] = preds

# --- DISPLAY RESULTS ---
top_hits = latest_rows.sort_values("p_pop", ascending=False).head(20)

for _, row in top_hits.iterrows():
    col1, col2 = st.columns([1, 4])
    with col1:
        st.metric(label=row["ticker"], value=f"{row['p_pop']:.2f}", delta=f"{row['ret_1'] * 100:.2f}% 1m")
    with col2:
        hist = all_data[all_data["ticker"] == row["ticker"]].tail(LOOKBACK_MINUTES)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hist.index, y=hist["close"], mode="lines", line=dict(width=2)))
        fig.update_layout(height=150, margin=dict(l=20, r=20, t=10, b=10), xaxis=dict(showgrid=False), yaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True)

st.caption("This demo trains an XGBoost model on-the-fly using recent price/volume behavior across ~50 tickers.")
