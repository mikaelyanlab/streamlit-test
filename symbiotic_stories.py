# app.py — Insect–Microbe Systems Course Network (PyVis click-to-details)
# -----------------------------------------------------------------------
from __future__ import annotations
import io
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st
from typing import List

# ------------------ Utility functions ------------------
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

# ------------------ App setup ------------------
st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")
if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)
if "selected_node" not in st.session_state:
    st.session_state.selected_node = None

# ------------------ Sidebar ------------------
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
    if st.button("Reset to sample"):
        st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)
        st.success("Reset.")
with st.sidebar.expander("Network Settings", expanded=True):
    min_shared = st.slider("Min shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)

# ------------------ Tabs ------------------
tab_data, tab_graph = st.tabs(["Data / Edit", "Graph Explorer"])

# ------------------ Data Tab ------------------
with tab_data:
    st.markdown("## Add / Edit Session")
    with st.form("add_session"):
        c1,c2,c3,c4 = st.columns(4)
        sid = c1.text_input("Session ID", placeholder="W2-Tu")
        date = c2.text_input("Date (YYYY-MM-DD)")
        title = c3.text_input("Title")
        instr = c4.text_input("Instructor","You")
        c5,c6,c7 = st.columns(3)
        module = c5.text_input("Module")
        activity = c6.text_input("Activity")
        kws = c7.text_input("Keywords (comma-separated)")
        notes = st.text_area("Notes")
        connect = st.text_input("Connect with (IDs comma-separated)")
        if st.form_submit_button("Add / Update") and sid.strip():
            r = {k: v.strip() if isinstance(v,str) else v for k,v in {
                "session_id": sid, "date": date, "title": title, "instructor": instr,
                "module": module or "Unassigned", "activity": activity,
                "keywords": kws, "notes": notes, "connect_with": connect
            }.items()}
            df = st.session_state.sessions
            if sid in df["session_id"].values:
                idx = df.index[df["session_id"]==sid][0]
                for k,v in r.items(): df.at[idx,k]=v
            else:
                st.session_state.sessions = pd.concat([df,pd.DataFrame([r])],ignore_index=True)
            st.success(f"Saved {sid}")
    st.markdown("### Inline Table Edit")
    edited = st.data_editor(
        st.session_state.sessions[DEFAULT_COLUMNS],
        hide_index=True, use_container_width=True, num_rows="dynamic",
        key="table_edit"
    )
    if not edited.equals(st.session_state.sessions[DEFAULT_COLUMNS]):
        st.session_state.sessions = edited.copy()

# ------------------ Graph Tab ------------------
with tab_graph:
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

    net = Network(height="700px", width="100%", directed=False, bgcolor="#ffffff", font_color="#222222")
    net.barnes_hut()
    palette = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"]
    mods = sorted({G.nodes[n]["module"] for n in nodes})
    color_map = {m: palette[i%len(palette)] for i, m in enumerate(mods)}

    for n in G.nodes():
        d = G.nodes[n]
        net.add_node(n, label=n, title="", color=color_map.get(d["module"], "#999"), size=25)
    for u, v in G.edges():
        net.add_edge(u, v, color="#cccccc")

    net.set_options("""
    var options = {
      "nodes": {"borderWidth":1,"shadow":false},
      "edges": {"color":{"inherit":true},"smooth":false},
      "physics": {"barnesHut": {"springLength":150},"minVelocity":0.75},
      "interaction": {"navigationButtons": true}
    }
    """)

    net.save_graph("network.html")
    html = open("network.html", "r", encoding="utf-8").read()

    js_click = """
    <script>
    const network = window.network;
    network.on("click", function(params) {
        if (params.nodes.length > 0) {
            const nodeId = params.nodes[0];
            const url = new URL(window.parent.location);
            url.searchParams.set("node", nodeId);
            window.parent.location = url;
        }
    });
    </script>
    """
    html = html.replace("</body>", js_click + "</body>")
    with open("network.html", "w", encoding="utf-8") as f:
        f.write(html)

    st.components.v1.html(html, height=750)

    # Handle selection
    query_params = st.experimental_get_query_params()
    if "node" in query_params:
        node = query_params["node"][0]
        if node in df["session_id"].values:
            st.session_state.selected_node = node
        st.experimental_set_query_params()  # Clear

    selected = st.session_state.selected_node
    if selected and selected in df["session_id"].values:
        d = df.loc[df["session_id"] == selected].iloc[0]
        st.markdown("### Session Passport")
        st.markdown(f"#### {d['title']}")
        st.markdown(
            f"**Date:** {d['date']}  \n"
            f"**Instructor:** {d['instructor']}  \n"
            f"**Module:** {d['module']}  \n"
            f"**Activity:** {d['activity']}  \n"
            f"**Keywords:** {d['keywords']}  \n\n"
            f"**Notes:**  \n{d['notes']}"
        )
    else:
        st.markdown("_Click a node to view its Session Passport._")
