# app.py
# Streamlit MVP: trains an intraday "pop" model (>=5% in next 30 min) on recent 1m data
# and replays the last trading day with continuously updating predictions & plotly chart.

import os
import time
from datetime import datetime, timedelta
import pytz
import numpy as np
import pandas as pd
import yfinance as yf
import streamlit as st
from dateutil.tz import gettz

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import precision_recall_fscore_support
from xgboost import XGBClassifier
import plotly.graph_objects as go

# -----------------------
# Streamlit Page Config
# -----------------------
st.set_page_config(page_title="Stock Pop Predictor (Local)", layout="wide")
st.title("📈 Stock Pop Predictor (Local Streamlit MVP)")
st.caption("Flags 5–10% ‘pop’ candidates in the next 30 minutes; trained on recent 1m bars.")

# -----------------------
# Sidebar Controls
# -----------------------
with st.sidebar:
    st.header("Controls")
    ticker = st.text_input("Ticker", value="NVDA")
    lookback_days = st.slider("Lookback (days, 1m bars available ≤7d)", min_value=2, max_value=7, value=5)
    pop_threshold = st.slider("Pop threshold (future max return in 30m)", 0.03, 0.12, 0.05, 0.01)
    prob_threshold = st.slider("Alert if predicted P(pop) ≥", 0.10, 0.90, 0.50, 0.05)
    refresh_ms = st.number_input("Replay refresh (ms)", min_value=250, max_value=5000, value=1000, step=250)
    autoplay = st.toggle("Autoplay last day", value=True)
    st.markdown("---")
    st.caption("Tip: For robust live feeds beyond 7 days, switch later to Polygon/Alpaca APIs.")

# -----------------------
# Helpers
# -----------------------
NY = gettz("America/New_York")

@st.cache_data(ttl=300, show_spinner=False)
def load_yf_1m(ticker: str, days: int) -> pd.DataFrame:
    # Yahoo provides 1m bars only for up to 7 days (incl. today).
    df = yf.download(tickers=ticker, period=f"{days}d", interval="1m", prepost=True, progress=False)
    if df.empty:
        return df
    df = df.tz_convert("America/New_York") if df.index.tz is not None else df.tz_localize("America/New_York")
    df = df.rename(columns=str.lower)
    return df

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Basic returns
    out["ret_1"]  = out["close"].pct_change(1)
    out["ret_3"]  = out["close"].pct_change(3)
    out["ret_5"]  = out["close"].pct_change(5)
    out["ret_10"] = out["close"].pct_change(10)
    out["ret_15"] = out["close"].pct_change(15)

    # Volatility & volume
    out["vol_10"] = out["close"].pct_change().rolling(10).std()
    out["vol_30"] = out["close"].pct_change().rolling(30).std()
    out["rv_10"]  = out["volume"] / (out["volume"].rolling(390).mean())  # relative vol vs. ~1 trading day
    out["volchg_5"] = out["volume"].pct_change(5)

    # VWAP deviation (intraday)
    typical = (out["high"] + out["low"] + out["close"]) / 3.0
    cum_vol = out["volume"].cumsum()
    cum_vp = (typical * out["volume"]).cumsum()
    out["vwap"] = cum_vp / np.where(cum_vol == 0, np.nan, cum_vol)
    out["dev_vwap"] = (out["close"] - out["vwap"]) / out["vwap"]

    # RSI (14) via simple implementation
    delta = out["close"].diff()
    up = np.where(delta > 0, delta, 0.0)
    down = np.where(delta < 0, -delta, 0.0)
    roll_up = pd.Series(up, index=out.index).rolling(14).mean()
    roll_down = pd.Series(down, index=out.index).rolling(14).mean()
    rs = roll_up / (roll_down.replace(0, np.nan))
    out["rsi14"] = 100.0 - (100.0 / (1.0 + rs))

    # Time-of-day features
    local_times = out.index.tz_convert("America/New_York")
    out["minute_of_day"] = local_times.hour * 60 + local_times.minute
    out["minutes_since_open"] = (local_times - local_times.normalize() - timedelta(hours=9, minutes=30)).total_seconds() / 60.0
    out["minutes_to_close"] = (timedelta(hours=16) - (local_times - local_times.normalize())).total_seconds() / 60.0

    return out

def add_forward_pop_label(df: pd.DataFrame, horizon_min: int, threshold: float) -> pd.Series:
    """
    Label = 1 if max(close in next `horizon_min` minutes) / current_close - 1 >= threshold
    Efficient vectorization using reversed rolling max.
    """
    close = df["close"]
    # future rolling max over next H bars (exclude current bar by shifting)
    future_max = close.shift(-1).iloc[::-1].rolling(horizon_min).max().iloc[::-1]
    label = ((future_max - close) / close) >= threshold
    return label.astype(int)

def train_model(train_df: pd.DataFrame, feature_cols: list[str]) -> tuple[XGBClassifier, StandardScaler]:
    X = train_df[feature_cols].values
    y = train_df["label"].values
    # Handle class imbalance via scale_pos_weight
    pos = y.sum()
    neg = len(y) - pos
    spw = (neg / max(pos, 1))

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    # Simple XGB baseline
    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.07,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        random_state=42,
        scale_pos_weight=spw,
        n_jobs=4,
        tree_method="hist"  # fast on CPU
    )
    model.fit(Xs, y)
    return model, scaler

def evaluate(model, scaler, df, feature_cols):
    X = scaler.transform(df[feature_cols].values)
    y_true = df["label"].values
    y_prob = model.predict_proba(X)[:, 1]
    pred = (y_prob >= 0.5).astype(int)
    p, r, f1, _ = precision_recall_fscore_support(y_true, pred, average="binary", zero_division=0)
    return dict(precision=p, recall=r, f1=f1, support=int(y_true.sum()), prob=y_prob)

def make_plot(df_live: pd.DataFrame, yprob: pd.Series | None, prob_threshold: float):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_live.index, y=df_live["close"],
        mode="lines", name="Price"
    ))

    if yprob is not None:
        alerts = (yprob >= prob_threshold)
        if alerts.any():
            fig.add_trace(go.Scatter(
                x=df_live.index[alerts],
                y=df_live.loc[alerts, "close"],
                mode="markers",
                marker=dict(size=9, symbol="triangle-up"),
                name=f"Predicted pop ≥ {prob_threshold:.2f}"
            ))

    fig.update_layout(
        height=540,
        margin=dict(l=40, r=30, t=30, b=40),
        xaxis_title="Time (ET)",
        yaxis_title="Price",
        template="plotly_white"
    )
    return fig

# -----------------------
# Data Load & Prep
# -----------------------
with st.status("Loading 1-minute data from Yahoo Finance…", expanded=False) as s:
    df_raw = load_yf_1m(ticker, lookback_days)
    if df_raw.empty:
        s.update(label="No data returned. Try another ticker or reduce lookback.", state="error")
        st.stop()
    s.update(label="Data loaded.", state="complete")

df = add_features(df_raw)

# Label: 30-minute forward max ≥ threshold
H = 30
df["label"] = add_forward_pop_label(df, horizon_min=H, threshold=pop_threshold)

# Drop early NaNs from features
feature_cols = [
    "ret_1","ret_3","ret_5","ret_10","ret_15",
    "vol_10","vol_30","rv_10","volchg_5",
    "dev_vwap","rsi14","minute_of_day","minutes_since_open","minutes_to_close"
]
df = df.dropna(subset=feature_cols + ["label"]).copy()

# Split into train (all but last date) and test (last date)
all_dates = np.array(sorted({d.date() for d in df.index}))
if len(all_dates) < 2:
    st.error("Need at least 2 trading days in lookback to train & test. Increase lookback or wait for more data.")
    st.stop()

train_dates = all_dates[:-1]
test_date = all_dates[-1]
train_df = df.loc[df.index.date.astype("O").isin(train_dates)].copy()
test_df  = df.loc[df.index.date == test_date].copy()

st.subheader("Data Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Training days", f"{len(train_dates)}")
c2.metric("Test day", str(test_date))
c3.metric("Train samples", f"{len(train_df):,}")
c4.metric("Test samples", f"{len(test_df):,}")

# Train model
with st.status("Training baseline XGBoost…", expanded=False) as s:
    model, scaler = train_model(train_df, feature_cols)
    s.update(label="Model trained.", state="complete")

# Evaluate on held-out last day
metrics = evaluate(model, scaler, test_df, feature_cols)
st.write(
    f"**Held-out last day ({test_date})** — "
    f"Precision: {metrics['precision']:.3f} · Recall: {metrics['recall']:.3f} · F1: {metrics['f1']:.3f} · Positives: {metrics['support']}"
)

# -----------------------
# Replay of LAST DAY
# -----------------------
st.subheader(f"Intraday Replay — {ticker} on {test_date} (ET)")

# Session state for replay index
if "replay_i" not in st.session_state:
    st.session_state.replay_i = 60  # start after first hour to have features stabilized

# Buttons
colA, colB, colC, colD = st.columns([1,1,1,2])
if colA.button("⏮ Reset"):
    st.session_state.replay_i = 60
if colB.button("⏪ -20"):
    st.session_state.replay_i = max(60, st.session_state.replay_i - 20)
if colC.button("⏩ +20"):
    st.session_state.replay_i = min(len(test_df)-1, st.session_state.replay_i + 20)

# Autoplay via autorefresh
if autoplay:
    st.experimental_rerun  # (keep linter quiet)
    st_autorefresh = st.experimental_memo  # dummy reference
    st.experimental_set_query_params()     # noop
    st.experimental_rerun                  # docs hint
    # Use built-in autorefresh widget
    _ = st.autorefresh(interval=refresh_ms, limit=1, key=f"tick_{time.time_ns()}")

# Build slice up to current index
i = st.session_state.replay_i = min(st.session_state.replay_i + (1 if autoplay else 0), len(test_df)-1)
live_df = test_df.iloc[: i+1].copy()

# Predict probabilities up to i
Xp = scaler.transform(live_df[feature_cols].values)
yprob_live = pd.Series(model.predict_proba(Xp)[:, 1], index=live_df.index, name="p_pop")

# Plot
fig = make_plot(live_df, yprob_live, prob_threshold)
st.plotly_chart(fig, use_container_width=True)

# Probability strip
st.caption("Prediction probability over time (current replay window)")
st.line_chart(yprob_live, height=160)

# Alerts table (last ~10)
alerts = live_df.loc[yprob_live >= prob_threshold, ["close"]].assign(p_pop=yprob_live[yprob_live >= prob_threshold])
st.write("Recent alerts (threshold hit):")
st.dataframe(alerts.tail(10))

st.info(
    "This MVP uses Yahoo 1m data (≤7 days history). For robust live trading, "
    "swap in a proper real-time feed (Polygon/Alpaca), and route orders to a paper account."
)
