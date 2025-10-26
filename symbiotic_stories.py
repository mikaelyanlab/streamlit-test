# app.py — Insect–Microbe Systems Course Network
# -------------------------------------------------------------------
from __future__ import annotations
import io, csv, pathlib, tempfile
import pandas as pd
import networkx as nx
import streamlit as st
import streamlit.components.v1 as components
from typing import List
from pyvis.network import Network

# ============================ Utilities ============================
DEFAULT_COLUMNS = [
    "session_id","date","title","instructor","module",
    "activity","keywords","notes","connect_with"
]
SAMPLE_ROWS=[{
    "session_id":"W1-Tu","date":"2026-01-13",
    "title":"Systems Bootcamp – Insects as Systems within Systems",
    "instructor":"You","module":"Systems Bootcamp",
    "activity":"Interactive lecture",
    "keywords":"systems thinking, feedback loops",
    "notes":"Define balancing and reinforcing loops.",
    "connect_with":""
}]

def _clean_keywords(s:str)->List[str]:
    if pd.isna(s) or not str(s).strip(): return []
    toks=[t.strip().lower() for t in str(s).replace(";",",").split(",")]
    return sorted({t for t in toks if t})

def _split_multi(s:str)->List[str]:
    if pd.isna(s) or not str(s).strip(): return []
    return [t.strip() for t in str(s).replace(";",",").split(",") if t.strip()]

# ============================ App setup ============================
st.set_page_config(page_title="Insect–Microbe Systems",layout="wide")
if "sessions" not in st.session_state:
    st.session_state.sessions=pd.DataFrame(SAMPLE_ROWS,columns=DEFAULT_COLUMNS)
if "selected_node" not in st.session_state:
    st.session_state.selected_node = ""

# ============================ Sidebar ==============================
st.sidebar.title("Course Session Network")
with st.sidebar.expander("Data IO",expanded=True):
    buf=io.StringIO(); st.session_state.sessions.to_csv(buf,index=False)
    st.download_button("Download sessions.csv",buf.getvalue(),"sessions.csv","text/csv")
    up=st.file_uploader("Upload sessions.csv",type=["csv"])
    if up is not None:
        try:
            raw=up.read().decode("utf-8",errors="replace")
            raw=(raw.replace("\r\n","\n").replace("\r","\n")
                 .replace("“",'"').replace("”",'"')
                 .replace("‘","'").replace("’","'")
                 .replace("\u00A0"," "))
            df=pd.read_csv(io.StringIO(raw), dtype=str)
            missing = set(DEFAULT_COLUMNS) - set(df.columns)
            if missing: raise ValueError(f"Missing columns: {missing}")
            st.session_state.sessions=df[DEFAULT_COLUMNS].fillna("")
            st.success("CSV loaded.")
        except Exception as e:
            st.error(f"Upload failed: {e}")
    if st.button("Reset to sample"):
        st.session_state.sessions=pd.DataFrame(SAMPLE_ROWS,columns=DEFAULT_COLUMNS)
        st.success("Reset.")
with st.sidebar.expander("Network Settings",expanded=True):
    min_shared=st.slider("Min shared keywords",1,5,1)
    include_manual=st.checkbox("Include manual connects",True)
    size_min,size_max=st.slider("Node size range",5,60,(14,38))

# ============================ Tabs ================================
tab_data,tab_graph=st.tabs(["Data / Edit","Graph Explorer"])

# ============================ Data Tab ============================
with tab_data:
    st.markdown("## Add / Edit Session")
    with st.form("add_session"):
        c1,c2,c3,c4=st.columns(4)
        sid=c1.text_input("Session ID",placeholder="W2-Tu")
        date=c2.text_input"Date (YYYY-MM-DD)")
        title=c3.text_input("Title")
        instr=c4.text_input("Instructor","You")
        c5,c6,c7=st.columns(3)
        module=c5.text_input("Module")
        activity=c6.text_input("Activity")
        kws=c7.text_input("Keywords (comma-separated)")
        notes=st.text_area("Notes")
        connect=st.text_input("
