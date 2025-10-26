# app.py — Insect–Microbe Systems Course Network (Cytoscape click-to-details)
# ---------------------------------------------------------------------------
from __future__ import annotations
import io, csv
from typing import List, Dict, Any

import pandas as pd
import networkx as nx
import streamlit as st
from streamlit_cytoscapejs import cytoscape

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
st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")

if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)

if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

# ============================ Sidebar ==============================
st.sidebar.title("Course Session Network")

with st.sidebar.expander("Data IO", expanded=True):
    buf = io.StringIO(); st.session_state.sessions.to_csv(buf, index=False)
    st.download_button("Download sessions.csv", buf.getvalue(), "sessions.csv", "text/csv")

    up = st.file_uploader("Upload sessions.csv", type=["csv"])
    if up is not None:
        try:
            raw = up.read().decode("utf-8", errors="replace")
            raw = (raw.replace("\r\n","\n").replace("\r","\n")
                   .replace("“",'"').replace("”",'"')
                   .replace("‘","'").replace("’","'")
                   .replace("\u00A0"," "))
            df = pd.read_csv(io.StringIO(raw), dtype=str, quoting=csv.QUOTE_ALL)
            missing = set(DEFAULT_COLUMNS) - set(df.columns)
            if missing:
                raise ValueError(f"Missing columns: {missing}")
            st.session_state.sessions = df[DEFAULT_COLUMNS].fillna("")
            st.success("CSV loaded.")
        except Exception as e:
            st.error(f"Upload failed: {e}")

    if st.button("Reset to sample"):
        st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)
        st.success("Reset.")

with st.sidebar.expander("Network Settings", expanded=True):
    min_shared = st.slider("Min shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)
    layout_name = st.selectbox("Layout", ["cose", "cose-bilkent", "cola", "breadthfirst", "concentric", "grid", "circle"], index=0)

# ============================ Tabs ================================
tab_data, tab_graph = st.tabs(["Data / Edit","Graph Explorer"])

# ============================ Data Tab ============================
with tab_data:
    st.markdown("## Add / Edit Session")
    with st.form("add_session"):
        c1,c2,c3,c4=st.columns(4)
        sid=c1.text_input("Session ID", placeholder="W2-Tu")
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
               "instructor":instr.strip(),"module":(module.strip() or "Unassigned"),
               "activity":activity.strip(),"keywords":kws.strip(),
               "notes":notes.strip(),"connect_with":connect.strip()}
            df=st.session_state.sessions
            if sid in df["session_id"].values:
                idx=df.index[df["session_id"]==sid][0]
                for k,v in r.items(): df.at[idx,k]=v
            else:
                st.session_state.sessions = pd.concat([df, pd.DataFrame([r])], ignore_index=True)
            st.success(f"Saved {sid}")

    st.markdown("### Inline Table Edit")
    edited = st.data_editor(
        st.session_state.sessions[DEFAULT_COLUMNS],
        hide_index=True, use_container_width=True, num_rows="dynamic",
        key="table_edit"
    )
    if not edited.equals(st.session_state.sessions[DEFAULT_COLUMNS]):
        st.session_state.sessions = edited.copy()

# ============================ Graph Tab ===========================
with tab_graph:
    st.markdown("## Interactive Course Graph")

    # ---- Build graph ----
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

    # ---- Cytoscape elements ----
    # Color by module (stable palette)
    PALETTE = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd",
               "#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"]
    modules = sorted({G.nodes[n].get("module","Unassigned") for n in nodes})
    color_map = {m: PALETTE[i % len(PALETTE)] for i,m in enumerate(modules)}

    elements: List[Dict[str, Any]] = []
    for n in nodes:
        d = G.nodes[n]
        # Build a rich, HTML-safe tooltip
        tooltip = (
            f"<b>{d['title']}</b><br>"
            f"<b>ID:</b> {n}<br>"
            f"<b>Date:</b> {d['date']}<br>"
            f"<b>Module:</b> {d['module']}<br>"
            f"<b>Instructor:</b> {d['instructor']}<br>"
            f"<b>Activity:</b> {d['activity']}<br>"
            f"<b>Keywords:</b> {', '.join(d['keywords']) if d['keywords'] else ''}<br>"
            f"<b>Notes:</b> {d['notes'][:400]}{'…' if len(d['notes'])>400 else ''}"
        )
        elements.append({
            "data": {
                "id": n,
                "label": n,
                "title": tooltip,
                # Keep full record so we don't have to look back
                "full": {
                    "session_id": n,
                    "date": d["date"],
                    "title": d["title"],
                    "instructor": d["instructor"],
                    "module": d["module"],
                    "activity": d["activity"],
                    "keywords": d["keywords"],
                    "notes": d["notes"],
                    "connect_with": d["connect_with"],
                }
            },
            "classes": d["module"] if d["module"] else "Unassigned"
        })
    for u, v in G.edges():
        elements.append({"data": {"source": u, "target": v}})

    # ---- Stylesheet (module color, nice nodes) ----
    stylesheet = [
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "width": 45, "height": 45,
                "font-size": 10,
                "font-weight": "600",
                "text-valign": "bottom",
                "text-halign": "center",
                "text-margin-y": -6,
                "color": "#111",
                "background-color": "#777",
                "border-width": 1,
                "border-color": "#000"
            }
        },
        {
            "selector": "edge",
            "style": {"line-color": "#bbb", "width": 1}
        },
        {
            "selector": "node:selected",
            "style": {"border-width": 3, "border-color": "#222", "background-color": "#ffd166"}
        },
        # One class per module for color
    ]
    for mod, col in color_map.items():
        stylesheet.append({
            "selector": f'node[class = "{mod}"]',
            "style": {"background-color": col}
        })

    # ---- Layout ----
    layout = {"name": layout_name}

    # ---- Render and capture selection ----
    selected = cytoscape(
        elements=elements,
        layout=layout,
        stylesheet=stylesheet,
        height="700px",
        width="100%",
        user_zooming_enabled=True,
        user_panning_enabled=True,
        selection_type="single",  # single-node selection
            # Enable tooltips via HTML title on hover (Cytoscape shows them natively)
        # NOTE: streamlit-cytoscapejs exposes 'title' when hovering, selection returned to Python
        key="cy"
    )

    # `selected` is commonly a dict like {"selected": ["node_id"]} or a list of ids
    sel_id = None
    if selected:
        if isinstance(selected, dict) and "selected" in selected and selected["selected"]:
            sel_id = selected["selected"][0]
        elif isinstance(selected, list) and len(selected) > 0:
            sel_id = selected[0]
        elif isinstance(selected, str):
            sel_id = selected

    if sel_id and sel_id in G.nodes:
        d = G.nodes[sel_id]
        st.session_state.selected_id = sel_id
        st.markdown(f"### {d['title']}")
        st.markdown(
            f"**Session ID:** {sel_id}  \n"
            f"**Date:** {d['date']}  \n"
            f"**Instructor:** {d['instructor']}  \n"
            f"**Module:** {d['module']}  \n"
            f"**Activity:** {d['activity']}  \n"
            f"**Keywords:** {', '.join(d['keywords']) if d['keywords'] else ''}  \n\n"
            f"**Notes:**  \n{d['notes']}"
        )
    elif st.session_state.selected_id and st.session_state.selected_id in G.nodes:
        # Preserve last selection across reruns (e.g., editing data on the left)
        d = G.nodes[st.session_state.selected_id]
        st.markdown(f"### {d['title']}")
        st.markdown(
            f"**Session ID:** {st.session_state.selected_id}  \n"
            f"**Date:** {d['date']}  \n"
            f"**Instructor:** {d['instructor']}  \n"
            f"**Module:** {d['module']}  \n"
            f"**Activity:** {d['activity']}  \n"
            f"**Keywords:** {', '.join(d['keywords']) if d['keywords'] else ''}  \n\n"
            f"**Notes:**  \n{d['notes']}"
        )
    else:
        st.caption("Click a node to view full, selectable session details below.")
