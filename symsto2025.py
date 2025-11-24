# symbiotic_stories_public.py
from __future__ import annotations

import io
from typing import List

import networkx as nx
import pandas as pd
import streamlit as st
from pyvis.network import Network

# -------------------------------------------------------------------
# 1. EMBEDDED CSV
# -------------------------------------------------------------------
# Replace the line <<< PASTE YOUR CSV HERE >>> with the full contents
# of course_full_streamlit_theory.csv, including the header row.
# You can just open the CSV in a text editor and paste it in.
CSV_TEXT = """session_id,date,title,instructor,module,activity,keywords,notes,connect_with
<<< PASTE YOUR CSV HERE >>>
"""

DEFAULT_COLUMNS = [
    "session_id", "date", "title", "instructor", "module",
    "activity", "keywords", "notes", "connect_with"
]

# -------------------------------------------------------------------
# 2. Helpers
# -------------------------------------------------------------------
def _clean_keywords(s: str) -> List[str]:
    if pd.isna(s) or not str(s).strip():
        return []
    toks = [t.strip().lower() for t in str(s).replace(";", ",").split(",")]
    return sorted({t for t in toks if t})


def _split_multi(s: str) -> List[str]:
    if pd.isna(s) or not str(s).strip():
        return []
    return [t.strip() for t in str(s).replace(";", ",").split(",") if t.strip()]


def load_sessions_from_embedded_csv() -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(CSV_TEXT), dtype=str).fillna("")
    # Ensure expected columns exist in the right order
    for col in DEFAULT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[DEFAULT_COLUMNS]


# -------------------------------------------------------------------
# 3. Streamlit setup
# -------------------------------------------------------------------
st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")

if "sessions" not in st.session_state:
    st.session_state.sessions = load_sessions_from_embedded_csv()

st.sidebar.title("Course Session Network")

with st.sidebar.expander("Data", expanded=True):
    # Download current sessions as CSV (for your own reference)
    buf = io.StringIO()
    st.session_state.sessions.to_csv(buf, index=False)
    st.download_button(
        "Download sessions.csv",
        buf.getvalue(),
        "sessions.csv",
        "text/csv"
    )

with st.sidebar.expander("Network Settings", expanded=True):
    min_shared = st.slider("Min shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)

tab_data, tab_graph = st.tabs(["Data / View", "Graph Explorer"])

# -------------------------------------------------------------------
# 4. Data tab
# -------------------------------------------------------------------
with tab_data:
    st.markdown("## Session Table (read-only for public viewers)")
    st.dataframe(
        st.session_state.sessions[DEFAULT_COLUMNS],
        hide_index=True,
        use_container_width=True,
    )

# -------------------------------------------------------------------
# 5. Graph tab
# -------------------------------------------------------------------
with tab_graph:
    df = st.session_state.sessions.copy()

    G = nx.Graph()

    # Add nodes
    for _, row in df.iterrows():
        kws = _clean_keywords(row["keywords"])
        node_data = row.to_dict()
        node_data["keywords"] = kws
        G.add_node(row["session_id"], **node_data)

    nodes = list(G.nodes())

    # Keyword-based edges
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            shared = len(set(G.nodes[a]["keywords"]) & set(G.nodes[b]["keywords"]))
            if shared >= min_shared:
                G.add_edge(a, b)

    # Manual connects
    if include_manual:
        for n in nodes:
            for m in _split_multi(G.nodes[n]["connect_with"]):
                if m in nodes and m != n:
                    G.add_edge(n, m)

    # Build PyVis graph
    net = Network(
        height="700px",
        width="100%",
        directed=False,
        bgcolor="#ffffff",
        font_color="#222222",
    )
    net.barnes_hut()

    palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    ]
    mods = sorted({G.nodes[n]["module"] for n in nodes})
    color_map = {m: palette[i % len(palette)] for i, m in enumerate(mods)}

    # Use PyVis's built-in HTML tooltip via the 'title' field
    for n in G.nodes():
        d = G.nodes[n]
        tip = (
            f"<b>{d['title']}</b><br>"
            f"{d['date']} | {d['module']}<br>"
            f"{d['activity']}<br>"
            f"<i>{', '.join(d['keywords'])}</i>"
        )
        net.add_node(
            n,
            label=n,
            title=tip,
            color=color_map.get(d["module"], "#999999"),
            size=25,
            shape="dot",
        )

    for u, v in G.edges():
        net.add_edge(u, v, color="#cccccc")

    net.set_options("""
    {
      "interaction": {"hover": true, "navigationButtons": true},
      "physics": {
        "enabled": true,
        "stabilization": {"enabled": true, "iterations": 500},
        "barnesHut": {"springLength": 150}
      }
    }
    """)

    net.save_graph("graph.html")
    html = open("graph.html", "r", encoding="utf-8").read()
    st.components.v1.html(html, height=750)

    # ----------------
    # Session Passport
    # ----------------
    st.markdown("---")
    st.markdown("### Session Passport")

    selected = st.selectbox(
        "Select a session:",
        sorted(df["session_id"]),
        format_func=lambda x: f"{x} — {df.loc[df['session_id'] == x, 'title'].values[0]}",
    )

    if selected in df["session_id"].values:
        d = df.loc[df["session_id"] == selected].iloc[0]
        st.markdown(f"#### {d['title']}")
        st.markdown(
            f"**Date:** {d['date']}  \n"
            f"**Instructor:** {d['instructor']}  \n"
            f"**Module:** {d['module']}  \n"
            f"**Activity:** {d['activity']}  \n"
            f"**Keywords:** {d['keywords']}  \n\n"
            f"**Notes:**  \n{d['notes']}"
        )
