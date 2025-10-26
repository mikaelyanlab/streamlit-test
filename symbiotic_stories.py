# app.py — Insect–Microbe Systems Course Network (click-to-display fixed)
# -------------------------------------------------------------------
from __future__ import annotations
import io, csv
from typing import List
import pandas as pd
import networkx as nx
import streamlit as st
from streamlit_plotly_events import plotly_events
import plotly.graph_objects as go

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

# ============================ Setup ============================
st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")

if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)

# ============================ Sidebar ============================
st.sidebar.title("Course Session Network")

with st.sidebar.expander("Data IO", expanded=True):
    buf = io.StringIO()
    st.session_state.sessions.to_csv(buf, index=False)
    st.download_button("Download sessions.csv", buf.getvalue(), "sessions.csv", "text/csv")

    up = st.file_uploader("Upload sessions.csv", type=["csv"])
    if up:
        df = pd.read_csv(up, dtype=str).fillna("")
        st.session_state.sessions = df
        st.success("CSV loaded.")

with st.sidebar.expander("Network Settings", expanded=True):
    min_shared = st.slider("Min shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)

# ============================ Build Graph ============================
df = st.session_state.sessions.copy()
G = nx.Graph()
for _, row in df.iterrows():
    kws = _clean_keywords(row["keywords"])
    node_data = row.to_dict()
    node_data["keywords"] = kws
    G.add_node(row["session_id"], **node_data)

nodes = list(G.nodes())
for i in range(len(nodes)):
    for j in range(i+1, len(nodes)):
        a, b = nodes[i], nodes[j]
        shared = len(set(G.nodes[a]["keywords"]) & set(G.nodes[b]["keywords"]))
        if shared >= min_shared:
            G.add_edge(a,b)
if include_manual:
    for n in nodes:
        for m in _split_multi(G.nodes[n]["connect_with"]):
            if m in nodes and m != n:
                G.add_edge(n,m)

mods = sorted({G.nodes[n]["module"] for n in nodes})
PALETTE = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd",
           "#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"]
color_map = {m:PALETTE[i%len(PALETTE)] for i,m in enumerate(mods)}
pos = nx.spring_layout(G, k=2.5, iterations=50, seed=42)

# edges
edge_x, edge_y = [], []
for u,v in G.edges():
    x0,y0=pos[u]; x1,y1=pos[v]
    edge_x+=[x0,x1,None]; edge_y+=[y0,y1,None]
edge_trace = go.Scatter(
    x=edge_x, y=edge_y, mode="lines",
    line=dict(width=1,color="#aaa"), hoverinfo="none"
)

# nodes
node_x,node_y,node_color,text=[],[],[],[]
for n in nodes:
    x,y = pos[n]
    d = G.nodes[n]
    node_x.append(x); node_y.append(y)
    node_color.append(color_map.get(d["module"],"#777"))
    text.append(n)

node_trace = go.Scatter(
    x=node_x, y=node_y, mode="markers+text",
    text=text, textposition="top center",
    marker=dict(size=28, color=node_color, line=dict(width=1,color="black")),
    hoverinfo="skip"
)

fig = go.Figure(data=[edge_trace,node_trace],
    layout=go.Layout(
        hovermode=False, showlegend=False,
        margin=dict(b=20,l=20,r=20,t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=700, paper_bgcolor="white", plot_bgcolor="white"
    )
)

st.subheader("Interactive Course Graph (Click a node)")
click = plotly_events(fig, click_event=True, hover_event=False, select_event=False, override_height=700, key="evt")

if click:
    node_label = click[0].get("text")
    if node_label in G.nodes:
        d = G.nodes[node_label]
        st.markdown(f"### {d['title']}")
        st.markdown(
            f"**Session ID:** {node_label}  \n"
            f"**Date:** {d['date']}  \n"
            f"**Instructor:** {d['instructor']}  \n"
            f"**Module:** {d['module']}  \n"
            f"**Activity:** {d['activity']}  \n"
            f"**Keywords:** {', '.join(d['keywords']) if d['keywords'] else ''}  \n\n"
            f"**Notes:**  \n{d['notes']}"
        )
else:
    st.info("Click a node to view its Session Passport.")
