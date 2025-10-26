# app_basic.py — Stable PyVis build (tooltip = passport)
# ---------------------------------------------------------------
# Guaranteed to display your network from course_cleaned.csv
# ---------------------------------------------------------------

import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st
import tempfile, pathlib, io, csv

st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")
st.title("🪲 Insect–Microbe Systems Course Network")

# --------------------------------------------------------------------
# Utilities
# --------------------------------------------------------------------
DEFAULT_COLUMNS = [
    "session_id","date","title","instructor","module",
    "activity","keywords","notes","connect_with"
]

def _clean_keywords(s):
    if pd.isna(s) or not str(s).strip(): return []
    toks=[t.strip().lower() for t in str(s).replace(";",",").split(",")]
    return sorted({t for t in toks if t})

def _split_multi(s):
    if pd.isna(s) or not str(s).strip(): return []
    return [t.strip() for t in str(s).replace(";",",").split(",") if t.strip()]

def _load_csv_uploaded(file_obj):
    raw=file_obj.read().decode("utf-8",errors="replace")
    raw=(raw.replace("\r\n","\n").replace("\r","\n")
            .replace("“",'"').replace("”",'"')
            .replace("‘","'").replace("’","'")
            .replace("\u00A0"," "))
    reader=csv.reader(io.StringIO(raw))
    rows=[r for r in reader if any(r)]
    clean=[]
    for r in rows:
        if len(r)<9: r+=['']*(9-len(r))
        elif len(r)>9: r=r[:9]
        clean.append(r)
    header = clean[0] if set(clean[0]) & set(DEFAULT_COLUMNS) else DEFAULT_COLUMNS
    data = clean[1:] if header==clean[0] else clean
    df = pd.DataFrame(data, columns=header).fillna("")
    for c in DEFAULT_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[DEFAULT_COLUMNS]

# --------------------------------------------------------------------
# Load data
# --------------------------------------------------------------------
path = "/mnt/data/course_cleaned.csv"
try:
    df = pd.read_csv(path)
    st.success(f"Loaded {len(df)} sessions from default file.")
except Exception as e:
    st.warning(f"Could not load default CSV ({e}). Upload manually below.")
    df = pd.DataFrame(columns=DEFAULT_COLUMNS)

up = st.file_uploader("Upload sessions.csv (optional)", type=["csv"])
if up is not None:
    df = _load_csv_uploaded(up)
    st.success(f"Loaded {len(df)} rows from uploaded file.")

if df.empty:
    st.stop()

# --------------------------------------------------------------------
# Network controls
# --------------------------------------------------------------------
min_shared = st.sidebar.slider("Min shared keywords", 1, 5, 1)
include_manual = st.sidebar.checkbox("Include manual connects", True)

# --------------------------------------------------------------------
# Build graph
# --------------------------------------------------------------------
G = nx.Graph()
for _,r in df.iterrows():
    sid = r["session_id"]
    if not sid: 
        continue
    kws = _clean_keywords(r["keywords"])
    title_html = (
        f"<b>{r['title']}</b><br>"
        f"<b>Date:</b> {r['date']} | <b>Module:</b> {r['module']}<br>"
        f"<b>Activity:</b> {r['activity']}<br>"
        f"<b>Instructor:</b> {r['instructor']}<br>"
        f"<b>Keywords:</b> {r['keywords']}<br>"
        f"<b>Notes:</b> {r['notes']}"
    )
    G.add_node(sid, module=r["module"], title=title_html, keywords=kws)

nodes=list(G.nodes())
for i in range(len(nodes)):
    for j in range(i+1,len(nodes)):
        a,b=nodes[i],nodes[j]
        shared=len(set(G.nodes[a]["keywords"]) & set(G.nodes[b]["keywords"]))
        if shared>=min_shared:
            G.add_edge(a,b)

if include_manual:
    for _,r in df.iterrows():
        a=r["session_id"]
        for b in _split_multi(r["connect_with"]):
            if b in G.nodes and b!=a:
                G.add_edge(a,b)

# --------------------------------------------------------------------
# PyVis network
# --------------------------------------------------------------------
net = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#111")
net.force_atlas_2based(gravity=-50, central_gravity=0.02, spring_length=120)

modules = sorted({G.nodes[n]["module"] for n in G.nodes})
palette = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd",
            "#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"]
color_map = {m:palette[i%len(palette)] for i,m in enumerate(modules)}

for n in G.nodes:
    d=G.nodes[n]
    net.add_node(
        n,
        label=n,
        title=d["title"],
        color=color_map.get(d["module"], "#777"),
        shape="dot",
        size=18
    )
for u,v in G.edges():
    net.add_edge(u,v,width=1)

# Render to HTML temp file
html_path = pathlib.Path(tempfile.NamedTemporaryFile(delete=False, suffix=".html").name)
net.write_html(html_path.as_posix(), notebook=False, local=True)
with open(html_path, "r", encoding="utf-8") as f:
    html=f.read()

st.components.v1.html(html, height=750, scrolling=False)
