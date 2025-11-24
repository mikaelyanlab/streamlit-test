# symbiotic_stories.py — FINAL, CLICK-TO-PASSPORT VERSION
from __future__ import annotations

import io
from typing import List

import networkx as nx
import pandas as pd
import streamlit as st
from pyvis.network import Network
from streamlit_js_eval import streamlit_js_eval

# ------------------------------------------------------
# COLUMN MODEL — including theory
# ------------------------------------------------------
DEFAULT_COLUMNS = [
    "session_id", "date", "title", "instructor", "module",
    "activity", "keywords", "notes", "connect_with", "theory"
]

SAMPLE_ROWS = [{
    "session_id": "W1-Tu",
    "date": "2026-01-13",
    "title": "Systems Bootcamp – Insects as Systems within Systems",
    "instructor": "You",
    "module": "Systems Bootcamp",
    "activity": "Interactive lecture",
    "keywords": "systems thinking, feedback loops",
    "notes": "Define balancing and reinforcing loops.",
    "connect_with": "",
    "theory": "Ashby cybernetics; Meadows feedback"
}]

# ------------------------------------------------------
# MOJIBAKE CLEANUP
# ------------------------------------------------------
def clean_mojibake(s: str) -> str:
    if not isinstance(s, str):
        return s
    rep = {
        "â€™": "’", "â€˜": "‘", "â€œ": "“", "â€": "”",
        "â€“": "–", "â€”": "—",
        "Ã©": "é", "Ã¨": "è", "Ã ": "à", "Ã¡": "á", "Ã³": "ó",
        "â€¦": "…",
    }
    for k, v in rep.items():
        s = s.replace(k, v)
    return s


def fix_df_unicode(df: pd.DataFrame) -> pd.DataFrame:
    return df.applymap(clean_mojibake)


# ------------------------------------------------------
# KEYWORD HELPERS
# ------------------------------------------------------
def _clean_keywords(s: str) -> List[str]:
    if pd.isna(s) or not str(s).strip():
        return []
    toks = [t.strip().lower() for t in str(s).replace(";", ",").split(",")]
    return sorted({t for t in toks if t})


def _split_multi(s: str) -> List[str]:
    if pd.isna(s) or not str(s).strip():
        return []
    return [t.strip() for t in str(s).replace(";", ",").split(",") if t.strip()]


# ------------------------------------------------------
# STREAMLIT SETUP
# ------------------------------------------------------
st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")

if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)

if "clicked_node" not in st.session_state:
    st.session_state.clicked_node = None

# ------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------
st.sidebar.title("Course Session Network")

with st.sidebar.expander("Data IO", expanded=True):

    # Download current CSV
    buf = io.StringIO()
    st.session_state.sessions.to_csv(buf, index=False)
    st.download_button("Download sessions.csv", buf.getvalue(), "sessions.csv", "text/csv")

    # Upload sessions.csv with robust encoding
    up = st.file_uploader("Upload sessions.csv", type=["csv"])
    if up:
        raw = up.read()  # IMPORTANT: read once

        # Try UTF-8 then Latin-1
        try:
            df = pd.read_csv(io.BytesIO(raw), dtype=str, encoding="utf-8")
        except Exception:
            try:
                df = pd.read_csv(io.BytesIO(raw), dtype=str, encoding="latin1")
            except Exception:
                st.error("Unable to read CSV. Check encoding/format.")
                st.stop()

        df = df.fillna("")
        df = fix_df_unicode(df)

        # Ensure required columns exist
        for col in DEFAULT_COLUMNS:
            if col not in df.columns:
                df[col] = ""

        df = df[DEFAULT_COLUMNS]
        st.session_state.sessions = df
        st.success("CSV loaded successfully.")

    if st.button("Reset sample"):
        st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)

with st.sidebar.expander("Network Settings", expanded=True):
    min_shared = st.slider("Min shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)

# ------------------------------------------------------
# MAIN UI — Tabs
# ------------------------------------------------------
tab_data, tab_graph = st.tabs(["Data / Edit", "Graph Explorer"])

# ------------------------------------------------------
# DATA TAB
# ------------------------------------------------------
with tab_data:
    st.markdown("## Add / Edit Session")

    with st.form("add_session"):
        c1, c2, c3, c4 = st.columns(4)
        sid = c1.text_input("Session ID", placeholder="W2-Tu")
        date = c2.text_input("Date (YYYY-MM-DD)")
        title = c3.text_input("Title")
        instr = c4.text_input("Instructor", "You")

        c5, c6, c7 = st.columns(3)
        module = c5.text_input("Module")
        activity = c6.text_input("Activity")
        kws = c7.text_input("Keywords (comma-separated)")

        notes = st.text_area("Notes")
        theory = st.text_area("Theory (full sentences)")
        connect = st.text_input("Connect with (IDs comma-separated)")

        if st.form_submit_button("Add / Update") and sid.strip():
            r = {
                "session_id": sid.strip(),
                "date": date.strip(),
                "title": title.strip(),
                "instructor": instr.strip(),
                "module": module.strip() or "Unassigned",
                "activity": activity.strip(),
                "keywords": kws.strip(),
                "notes": notes.strip(),
                "connect_with": connect.strip(),
                "theory": theory.strip(),
            }

            df = st.session_state.sessions
            if sid in df["session_id"].values:
                df.loc[df["session_id"] == sid, list(r.keys())] = pd.Series(r)
            else:
                st.session_state.sessions = pd.concat(
                    [df, pd.DataFrame([r])],
                    ignore_index=True,
                )
            st.success(f"Saved {sid}")

    st.markdown("### Inline Edit")
    edited = st.data_editor(
        st.session_state.sessions[DEFAULT_COLUMNS],
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
    )

    if not edited.equals(st.session_state.sessions[DEFAULT_COLUMNS]):
        st.session_state.sessions = edited.copy()

# ------------------------------------------------------
# GRAPH TAB
# ------------------------------------------------------
with tab_graph:
    df = st.session_state.sessions.copy()

    G = nx.Graph()

    # Nodes
    for _, row in df.iterrows():
        kws = _clean_keywords(row["keywords"])
        node_data = row.to_dict()
        node_data["keywords"] = kws
        G.add_node(row["session_id"], **node_data)

    nodes = list(G.nodes())

    # Keyword edges
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

    # PyVis network
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

    # Add nodes with custom HTML tooltip (includes theory)
    for n in G.nodes():
        d = G.nodes[n]
        html_tip = (
            f"<b>{d['title']}</b><br>"
            f"{d['date']} | {d['module']}<br>"
            f"{d['activity']}<br>"
            f"<i>{', '.join(d['keywords'])}</i><br><hr>"
            f"<small>{d['theory']}</small>"
        )

        net.add_node(
            n,
            label=n,
            title="",  # disable default tooltip
            color=color_map.get(d["module"], "#999999"),
            size=25,
            shape="dot",
            custom_html=html_tip,
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

    # Save graph and inject JS for tooltip + click→localStorage
    net.save_graph("graph.html")
    html = open("graph.html", "r", encoding="utf-8").read()

    html = html.replace("</script>", """
    const tip = document.createElement('div');
    tip.style.position='fixed';
    tip.style.background='#ffffe6';
    tip.style.border='1px solid #aaa';
    tip.style.padding='6px 8px';
    tip.style.borderRadius='4px';
    tip.style.boxShadow='2px 2px 4px rgba(0,0,0,0.2)';
    tip.style.display='none';
    tip.style.pointerEvents='none';
    tip.style.maxWidth='400px';
    tip.style.lineHeight='1.25';
    document.body.appendChild(tip);

    network.on("hoverNode",(params)=>{
      const node=network.body.data.nodes.get(params.node);
      if(node && node.custom_html){
        tip.innerHTML=node.custom_html;
        tip.style.display='block';
      }
    });

    network.on("blurNode",()=>tip.style.display='none');

    document.addEventListener('mousemove',(e)=>{
      tip.style.left=(e.clientX+12)+'px';
      tip.style.top=(e.clientY+12)+'px';
    });

    // CLICK: store clicked node ID in localStorage
    network.on("selectNode",(p)=>{
      const id = p.nodes[0];
      if(id){
        window.localStorage.setItem('clicked_node', id);
      }
    });
    </script>""")

    st.components.v1.html(html, height=750)

    # ----------------
    # Session Passport
    # ----------------
    st.markdown("---")
    st.markdown("### Session Passport")

    # Ask browser for last clicked node (from localStorage)
    clicked_from_js = streamlit_js_eval(
        js_expressions="localStorage.getItem('clicked_node')",
        key="get_clicked_node"
    )

    if clicked_from_js:
        st.session_state.clicked_node = clicked_from_js

    # Fallback to selectbox if nothing clicked yet
    selected = st.session_state.clicked_node or st.selectbox(
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
            f"**Notes:**  \n{d['notes']}  \n\n"
            f"**Theory:**  \n{d['theory']}"
        )
