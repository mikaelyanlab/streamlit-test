import time
from datetime import datetime, timedelta
import pytz
import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
from dateutil.tz import gettz
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import precision_recall_fscore_support
from xgboost import XGBClassifier
import plotly.graph_objects as go

# -----------------------
# Page Setup
# -----------------------
st.set_page_config(page_title="📈 Stock Pop Predictor", layout="wide")
st.title("📈 Stock Pop Predictor (Streamlit Cloud)")
st.caption("Flags 5–10% pops in the next 30 minutes using XGBoost, trained on 1-minute Yahoo data.")

NY = gettz("America/New_York")

# -----------------------
# Sidebar Controls
# -----------------------
with st.sidebar:
    st.header("Controls")
    ticker = st.text_input("Ticker", value="NVDA")
    lookback_days = st.slider("Lookback (1-min data limit: 7 days)", 2, 7, 5)
    pop_threshold = st.slider("Label pop as return ≥", 0.03, 0.12, 0.05, step=0.01)
    prob_threshold = st.slider("Alert threshold (predicted pop probability)", 0.10, 0.90, 0.50, step=0.05)
    st.caption("Autoplay disabled for cloud stability — use ⏩ buttons to step through.")

# -----------------------
# Data Functions
# -----------------------
@st.cache_data(ttl=300)
def load_data(ticker, days):
    df = yf.download(ticker, period=f"{days}d", interval="1m", prepost=True, progress=False)
    if df.empty:
        return df
    df = df.rename(columns=str.lower)
    df = df.tz_localize(None).tz_localize("UTC").tz_convert("America/New_York")
    return df

def add_features(df):
    df["ret_1"] = df["close"].pct_change(1)
    df["ret_5"] = df["close"].pct_change(5)
    df["ret_10"] = df["close"].pct_change(10)
    df["vol_10"] = df["close"].pct_change().rolling(10).std()
    df["rv_10"] = df["volume"] / df["volume"].rolling(390).mean()
    vwap = (df["high"] + df["low"] + df["close"]) / 3
    df["vwap"] = vwap
    df["dev_vwap"] = (df["close"] - vwap) / vwap
    df["minute_of_day"] = df.index.hour * 60 + df.index.minute
    return df

def add_pop_label(df, horizon=30, threshold=0.05):
    future_max = df["close"].shift(-1).iloc[::-1].rolling(horizon).max().iloc[::-1]
    return ((future_max - df["close"]) / df["close"] >= threshold).astype(int)

@st.cache_resource
def train_model(train_df, features):
    X = train_df[features].dropna().values
    y = train_df["label"].loc[train_df[features].notna().all(axis=1)].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.07, use_label_encoder=False, eval_metric='logloss')
    model.fit(X_scaled, y)
    return model, scaler

# -----------------------
# Load & Process Data
# -----------------------
with st.status("Loading data..."):
    df = load_data(ticker, lookback_days)
    if df.empty:
        st.error("No data returned. Try another ticker or shorter lookback.")
        st.stop()
    df = add_features(df)
    df["label"] = add_pop_label(df, threshold=pop_threshold)
    df.dropna(inplace=True)

# -----------------------
# Train/Test Split
# -----------------------
dates = sorted(df.index.date)
train_df = df[df.index.date < dates[-1]]
test_df = df[df.index.date == dates[-1]]
features = ["ret_1", "ret_5", "ret_10", "vol_10", "rv_10", "dev_vwap", "minute_of_day"]

if len(train_df) < 100:
    st.warning("Not enough data to train. Try increasing lookback.")
    st.stop()

with st.status("Training model..."):
    model, scaler = train_model(train_df, features)

# -----------------------
# Inference Setup
# -----------------------
test_df = test_df.copy()
test_X = scaler.transform(test_df[features])
test_df["p_pop"] = model.predict_proba(test_X)[:, 1]
alerts = test_df[test_df["p_pop"] >= prob_threshold]

# -----------------------
# Interactive Replay
# -----------------------
st.subheader(f"{ticker} on {dates[-1]}")

if "replay_idx" not in st.session_state:
    st.session_state.replay_idx = 60

cols = st.columns([1,1,1,4])
if cols[0].button("⏮ Reset"):
    st.session_state.replay_idx = 60
if cols[1].button("⏪ -20"):
    st.session_state.replay_idx = max(60, st.session_state.replay_idx - 20)
if cols[2].button("⏩ +20"):
    st.session_state.replay_idx = min(len(test_df) - 1, st.session_state.replay_idx + 20)

idx = st.session_state.replay_idx
live_df = test_df.iloc[:idx + 1]

# -----------------------
# Plotting
# -----------------------
fig = go.Figure()
fig.add_trace(go.Scatter(x=live_df.index, y=live_df["close"], name="Price", mode="lines"))
pop_points = live_df[live_df["p_pop"] >= prob_threshold]
fig.add_trace(go.Scatter(
    x=pop_points.index,
    y=pop_points["close"],
    mode="markers",
    name="Predicted Pop",
    marker=dict(size=9, symbol="triangle-up", color="red")
))
fig.update_layout(height=500, margin=dict(l=20, r=20, t=30, b=40), template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

# -----------------------
# Probability Strip + Alerts
# -----------------------
st.caption("Prediction probability (last 30 minutes)")
st.line_chart(live_df["p_pop"].tail(30))

st.caption("Recent predictions ≥ threshold")
st.dataframe(pop_points[["close", "p_pop"]].tail(10))
