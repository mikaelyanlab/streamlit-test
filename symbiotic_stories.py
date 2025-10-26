# app.py — WORKING: Click node in Plotly graph → passport below (force layout, instant)
from __future__ import annotations
import io
import pandas as pd
import plotty.graph_objs as go
import networkx as nx
import streamlit as st
from typing import List

# ------------------ Utils ------------------
DEFAULT_COLUMNS = ["session_id","date","title","instructor","module","activity","keywords","notes","connect_with"]
SAMPLE_ROWS = [{"session_id":"W1-Tu","date":"2026-01-13","title":"Bootcamp","instructor":"You","module":"Systems","activity":"Lecture","keywords":"systems, loops","notes":"Intro.","connect_with":""}]

def _clean_keywords(s:str) -> List[str]:
    if pd.isna(s) or not s: return []
    return [t.strip().lower() for t in str(s).replace(";",",").split(",") if t]

def _split_multi(s:str) -> List[str]:
    if pd.isna(s) or not s: return []
    return [t.strip() for t in str(s).replace(";",",").split(",") if t]

# ------------------ Setup ------------------
st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")
if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)
if "selected_node" not in st.session_state:
    st.session_state.selected_node = None

# ------------------ Sidebar ------------------
st.sidebar.title("Network")
with st.sidebar.expander("IO"):
    buf = io.StringIO(); st.session_state.sessions.to_csv(buf, index=False)
    st.download_button("Download", buf.getvalue(), "sessions.csv")
    up = st.file_uploader("Upload", type="csv")
    if up: st.session_state.sessions = pd.read_csv(up, dtype=str).fillna(""); st.success("Loaded")
    if st.button("Reset"): st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS); st.success("Reset")
with st.sidebar.expander("Settings"):
    min_shared = st.slider("Min keywords",1,5,1)
    include_manual = st.checkbox("Manual",True)

tab_data, tab_graph = st.tabs(["Data","Graph"])

# ------------------ Data Tab ------------------
with tab_data:
    with st.form("add"):
        sid = st.text_input("ID")
        title = st.text_input("Title")
        if st.form_submit_button("Add") and sid:
            r = {k:"" for k in DEFAULT_COLUMNS}; r["session_id"]=sid; r["title"]=title or "Untitled"
            st.session_state.sessions = pd.concat([st.session_state.sessions, pd.DataFrame([r])], ignore_index=True)
    st.data_editor(st.session_state.sessions[DEFAULT_COLUMNS], hide_index=True, num_rows="dynamic", key="edit")

# ------------------ Graph Tab ------------------
with tab_graph:
    df = st.session_state.sessions.copy()
    G = nx.Graph()
    for _, r in df.iterrows():
        G.add_node(r["session_id"], **r.to_dict())

    nodes = list(G.nodes)
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            a, b = nodes[i], nodes[j]
            shared = len(set(_clean_keywords(G.nodes[a]["keywords"])) & set(_clean_keywords(G.nodes[b]["keywords"])))
            if shared >= min_shared:
                G.add_edge(a, b)
    if include_manual:
        for n in nodes:
            for m in _split_multi(G.nodes[n]["connect_with"]):
                if m in nodes and m != n: G.add_edge(n, m)

    # Force layout
    pos = nx.spring_layout(G, k=1, iterations=50)

    # Edges
    edge_x, edge_y = [], []
    for u, v in G.edges:
        x0, y0 = pos[u][0], pos[u][1]
        x1, y1 = pos[v][0], pos[v][1]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    # Nodes
    node_x, node_y, node_text, node_color = [], [], [], []
    palette = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd"]
    mods = sorted({G.nodes[n]["module"] for n in nodes})
    color_map = {m: palette[i%len(palette)] for i,m in enumerate(mods)}
    for n in nodes:
        x, y = pos[n]
        d = G.nodes[n]
        node_x.append(x); node_y.append(y)
        node_text.append(f"{n}<br>{d['title']}<br>{d['date']}<br>{d['module']}")
        node_color.append(color_map.get(d["module"], "#999"))

    # Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(color='#ccc', width=1), hoverinfo='none'))
    fig.add_trace(go.Scatter(x=node_x, y=node_y, mode='markers+text', text=[n for n in nodes], textposition="top center",
                             marker=dict(size=30, color=node_color, line=dict(width=2)),
                             hoverinfo='text', hovertext=node_text, customdata=nodes))
    fig.update_layout(showlegend=False, hovermode='closest', margin=dict(b=20,l=5,r=5,t=20),
                      xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                      yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                      height=700, paper_bgcolor='white', plot_bgcolor='white')

    # Click handler
    click = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="point")

    # Get selected
    if click and click["selection"]["points"]:
        sel_id = click["selection"]["points"][0]["customdata"]
        st.session_state.selected_node = sel_id

    sel = st.session_state.selected_node
    if sel and sel in df["session_id"].values:
        d = df[df["session_id"] == sel].iloc[0]
        st.markdown("### Session Passport")
        st.markdown(f"#### {d['title']}")
        st.markdown(f"**Date:** {d['date']}  \n**Instructor:** {d['instructor']}  \n**Module:** {d['module']}  \n**Activity:** {d['activity']}  \n**Keywords:** {d['keywords']}  \n\n**Notes:**  \n{d['notes']}")
    else:
        st.markdown("_Click a node to view its Session Passport._")
