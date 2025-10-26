import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import tempfile, os, pathlib

st.set_page_config(page_title="Insect–Microbe Systems — Clickable Network", layout="wide")
st.title("🪲 Insect–Microbe Systems — Clickable Course Network")

# ---------------------------------------------------------------------
# Load CSV
# ---------------------------------------------------------------------
CSV_FILE = "course_cleaned.csv"
DEFAULT_COLUMNS = [
    "session_id","date","title","instructor","module",
    "activity","keywords","notes","connect_with"
]

def _clean_keywords(s):
    if pd.isna(s) or not str(s).strip():
        return []
    return [t.strip().lower() for t in str(s).replace(";",",").split(",") if t.strip()]

def _split_multi(s):
    if pd.isna(s) or not str(s).strip():
        return []
    return [t.strip() for t in str(s).replace(";",",").split(",") if t.strip()]

# ---- Step 1: Check if file exists ----
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    st.success(f"✅ Loaded {len(df)} sessions from '{CSV_FILE}'.")
else:
    st.warning("No local 'course_cleaned.csv' found. Please upload your dataset below:")
    uploaded = st.file_uploader("Upload your course CSV", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
        st.success(f"✅ Uploaded {len(df)} sessions.")
    else:
        st.stop()

# ---------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------
G = nx.Graph()
for _, r in df.iterrows():
    sid = str(r["session_id"]).strip()
    if not sid:
        continue
    G.add_node(
        si
