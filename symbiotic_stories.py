# app.py — FINAL WORKING: Click node → passport (Plotly, no JS, physics-like)
import io
import pandas as pd
import plotly.graph_objs as go
import networkx as nx
import streamlit as st
from typing import List

# Utils
DEFAULT_COLUMNS = ["session_id","date","title","instructor","module","activity","keywords","notes","connect_with"]
SAMPLE_ROWS = [{"session_id":"W1-Tu","date":"2026-01-13","title":"Bootcamp","instructor":"You","module":"Systems","activity":"Lecture","keywords":"systems, loops","notes":"Intro.","connect_with":""}]

def _clean_keywords(s: str) -> List[str]:
    if pd.isna(s) or not s: return []
    return [t.strip().lower() for t in str(s).replace(";", ",").split(",") if t.strip()]

def _split_multi(s: str) -> List[str]:
    if pd.isna(s) or not s: return []
    return [t.strip() for t in str(s).replace(";", ",").split(",") if t.strip()]

# Setup
st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")
if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)
if "selected_node" not in st.session_state:
    st.session_state.selected_node = None

# Sidebar
st.sidebar.title("Course Session Network")
with st.sidebar.expander("Data IO", True):
    buf = io.StringIO(); st.session_state.sessions.to_csv(buf, index=False)
    st.download_button("Download sessions.csv", buf.getvalue(), "sessions.csv")
    up = st.file_uploader("Upload sessions.csv", type="csv")
    if up: st.session_state.sessions = pd.read_csv(up, dtype=str).fillna(""); st.success("Loaded")
    if st.button("Reset to sample"): st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS); st.success("Reset")
with st.sidebar.expander("Network Settings", True):
    min_shared = st.slider("Min shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)

tab_data, tab_graph = st.tabs(["Data / Edit", "Graph Explorer"])

# Data Tab
with tab_data:
    with st.form("add_session"):
        sid = st.text_input("Session ID")
        title = st.text_input("Title")
        if st.form_submit_button("Add") and sid:
            r = {k:"" for k in DEFAULT_COLUMNS}; r["session_id"] = sid; r["title"] = title or "Untitled"
            st.session_state.sessions = pd.concat([st.session_state.sessions, pd.DataFrame([r])], ignore_index=True)
    st.data_editor(st.session_state.sessions[DEFAULT_COLUMNS], hide_index=True, num_rows="dynamic", key="edit")

# Graph Tab
with tab_graph:
    df = st.session_state.sessions.copy()
    G = nx.Graph()
    for _, r in df.iterrows():
        G.add_node(r["session_id"], **r.to_dict())

    nodes = list(G.nodes())
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            a, b = nodes[i], nodes[j]
            if len(set(_clean_keywords(G.nodes[a]["keywords"])) & set(_clean_keywords(G.nodes[b]["keywords"]))) >= min_shared:
                G.add_edge(a, b)
    if include_manual:
        for n in nodes:
            for m in _split_multi(G.nodes[n]["connect_with"]):
                if m in nodes and m != n: G.add_edge(n, m)

    pos = nx.spring_layout(G, k=2, iterations=50)

    # Edges
    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    # Nodes
    node_x, node_y, node_text, node_ids = [], [], [], []
    for n in nodes:
        x, y = pos[n]
        d = G.nodes[n]
        node_x.append(x); node_y.append(y)
        node_text.append(f"<b>{n}</b><br>{d['title']}<br>{d['date']}<br>{d['module']}")
        node_ids.append(n)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(color='#ccc'), hoverinfo='none'))
    fig.add_trace(go.Scatter(x=node_x, y=node_y, mode='markers+text', text=node_ids, textposition="top center",
                             marker=dict(size=40, color='#1f77b4'), hoverinfo='text', hovertext=node_text,
                             customdata=node_ids))
    fig.update_layout(showlegend=False, hovermode='closest', margin=dict(l=0,r=0,t=0,b=0),
                      xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                      yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                      height=700, paper_bgcolor='white', plot_bgcolor='white')

    # Click → rerun
    click = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode=["points"])

    # Get clicked node
    selected = None
    if click and click["selection"]["points"]:
        selected = click["selection"]["points"][0]["customdata"]
        st.session_state.selected_node = selected

    # Show passport
    sel = st.session_state.selected_node
    if sel and sel in df["session_id"].values:
        d = df[df["session_id"] == sel].iloc[0]
        st.markdown("### Session Passport")
        st.markdown(f"#### {d['title']}")
        st.markdown(f"**Date:** {d['date']}\n**Instructor:** {d['instructor']}\n**Module:** {d['module']}\n**Activity:** {d['activity']}\n**Keywords:** {d['keywords']}\n\n**Notes:**\n{d['notes']}")
    else:
        st.markdown("_Click a node to view its Session Passport._")
