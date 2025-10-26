# app.py — Insect–Microbe Systems Course Network
# -------------------------------------------------------------------
from __future__ import annotations
import io, csv
import pandas as pd
import networkx as nx
import streamlit as st
import plotly.graph_objects as go
from typing import List

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
    st.session_state.selected_node = None

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
            df=pd.read_csv(io.StringIO(raw), dtype=str, quoting=csv.QUOTE_ALL)
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

# ============================ Tabs ================================
tab_data,tab_graph=st.tabs(["Data / Edit","Graph Explorer"])

# ============================ Data Tab ============================
with tab_data:
    st.markdown("## Add / Edit Session")
    with st.form("add_session"):
        c1,c2,c3,c4=st.columns(4)
        sid=c1.text_input("Session ID",placeholder="W2-Tu")
        date=c2.text_input("Date (YYYY-MM-DD)")
        title=c3.text_input("Title")
        instr=c4.text_input("Instructor","You")
        c5,c6,c7=st.columns(3)
        module=c5.text_input("Module")
        activity=c6.text_input("Activity")
        kws=c7.text_input("Keywords (comma-separated)")
        notes=st.text_area("Notes")
        connect=st.text_input("Connect with (IDs comma-separated)")
        if st.form_submit_button("Add / Update") and sid.strip():
            r={"session_id":sid.strip(),"date":date.strip(),"title":title.strip(),
               "instructor":instr.strip(),"module":module.strip() or "Unassigned",
               "activity":activity.strip(),"keywords":kws.strip(),
               "notes":notes.strip(),"connect_with":connect.strip()}
            df=st.session_state.sessions
            if sid in df["session_id"].values:
                idx=df[df["session_id"]==sid].index[0]
                for k,v in r.items(): df.at[idx,k]=v
            else:
                st.session_state.sessions=pd.concat([df,pd.DataFrame([r])],ignore_index=True)
            st.success(f"Saved {sid}")
    st.markdown("### Inline Table Edit")
    edited=st.data_editor(
        st.session_state.sessions[DEFAULT_COLUMNS],
        hide_index=True, use_container_width=True, num_rows="dynamic",
        key="table_edit"
    )
    if not edited.equals(st.session_state.sessions[DEFAULT_COLUMNS]):
        st.session_state.sessions=edited.copy()

# ============================ Graph Tab ===========================
with tab_graph:
    st.markdown("## Interactive Course Graph")
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
                G.add_edge(a, b)
    if include_manual:
        for n in nodes:
            for m in _split_multi(G.nodes[n]["connect_with"]):
                if m in nodes and m != n:
                    G.add_edge(n, m)
    mods = sorted({G.nodes[n]["module"] for n in nodes})
    PALETTE = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"]
    color_map = {m: PALETTE[i%len(PALETTE)] for i, m in enumerate(mods)}
    pos = nx.spring_layout(G, k=3, iterations=50, seed=42)

    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]; x1, y1 = pos[v]
        edge_x += [x0, x1, None]; edge_y += [y0, y1, None]
    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1, color="#888"), hoverinfo="none")

    node_x, node_y, node_text, node_color, node_size, node_ids = [], [], [], [], [], []
    for n in nodes:
        x, y = pos[n]
        d = G.nodes[n]
        node_x.append(x); node_y.append(y)
        node_text.append(f"<b>{n}</b><br>{d['title']}<br>{d['module']}<br>{d['date']}")
        node_color.append(color_map.get(d["module"], "#777"))
        node_size.append(30)
        node_ids.append(n)

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text", text=[n for n in nodes],
        textposition="top center", marker=dict(size=node_size, color=node_color),
        hovertext=node_text, hovertemplate="%{hovertext}<extra></extra>",
        customdata=[ [nid] for nid in node_ids ]
    )

    fig = go.Figure(data=[edge_trace, node_trace], layout=go.Layout(
        showlegend=False, hovermode="closest",
        margin=dict(b=20, l=5, r=5, t=40),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=700, paper_bgcolor="white", plot_bgcolor="white"
    ))

    col1, col2 = st.columns([3, 2])
    with col1:
        event = st.plotly_chart(fig, use_container_width=True, key="graph_click", on_select="rerun")
    with col2:
        st.markdown("### Session Passport")
        if event and event.get("selection") and event["selection"].get("points"):
            point = event["selection"]["points"][0]
            node_id = point["customdata"][0]
            st.session_state.selected_node = node_id
        if st.session_state.selected_node:
            r = df[df["session_id"] == st.session_state.selected_node].iloc[0]
            st.markdown(f"#### 🪲 **{r['title']}**")
            st.markdown(f"**Date:** {r['date']} | **Module:** {r['module']} | **Activity:** {r['activity']}")
            st.markdown(f"**Instructor:** {r['instructor']}")
            st.markdown(f"**Keywords:** `{r['keywords']}`")
            st.markdown("**Notes:**"); st.markdown(r['notes'])
            if r['connect_with']: st.markdown(f"**Connect with:** {r['connect_with']}")
        else:
            st.info("Click a node to view details.")
