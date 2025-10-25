# app.py
# ------------------------------------------------------------------
# Symbiosis Course Session Network — Editable Version
# ------------------------------------------------------------------
# Enhancements:
# - Inline table editing with st.data_editor
# - Quick-edit sidebar tool
# - Manual connection creator
# - Autosave + Undo
# - Tabbed interface (Data / Graph / Legend)
# ------------------------------------------------------------------

from __future__ import annotations
import io
import pathlib
import tempfile
from typing import List, Dict
import pandas as pd
import streamlit as st
import networkx as nx

try:
    from pyvis.network import Network  # type: ignore
    from streamlit.components.v1 import html
    HAS_PYVIS = True
except Exception:
    HAS_PYVIS = False
    import plotly.graph_objects as go  # type: ignore

# --------------------- Utility ---------------------
DEFAULT_COLUMNS = [
    "session_id", "date", "title", "instructor", "module",
    "activity", "keywords", "notes", "connect_with"
]

SAMPLE_ROWS = [
    {
        "session_id": "W1-Tu", "date": "2025-01-14", "title": "Ch 1 – What is Symbiosis?",
        "instructor": "You", "module": "Foundations",
        "activity": "Intro discussion", "keywords": "symbiosis, mutualism, parasitism",
        "notes": "Define terms; systems diagram", "connect_with": ""
    },
    {
        "session_id": "W1-Th", "date": "2025-01-16", "title": "Symbiosis — scope & examples",
        "instructor": "You", "module": "Foundations",
        "activity": "Mini case-studies", "keywords": "commensalism, amensalism, insect symbiosis",
        "notes": "", "connect_with": "W1-Tu"
    },
]

def _clean_keywords(s: str) -> List[str]:
    if pd.isna(s) or not str(s).strip():
        return []
    toks = [t.strip().lower() for t in str(s).replace(";", ",").split(",")]
    return sorted(list({t for t in toks if t}))

def _split_multi(s: str) -> List[str]:
    if pd.isna(s) or not str(s).strip():
        return []
    return [t.strip() for t in str(s).replace(";", ",").split(",") if t.strip()]

# --------------------- State ---------------------
st.set_page_config(page_title="Symbiosis Course Session Network", layout="wide")

if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)

# --------------------- Sidebar ---------------------
st.sidebar.title("Course Session Network")

# --- Data IO ---
with st.sidebar.expander("Data IO", expanded=True):
    csv_buf = io.StringIO()
    st.session_state.sessions.to_csv(csv_buf, index=False)
    st.download_button(
        label="Download sessions.csv",
        data=csv_buf.getvalue(),
        file_name="sessions.csv",
        mime="text/csv",
    )

    up = st.file_uploader("Upload sessions.csv", type=["csv"])
    if up is not None:
        try:
            df_up = pd.read_csv(up)
            missing = [c for c in DEFAULT_COLUMNS if c not in df_up.columns]
            if missing:
                st.error(f"Missing columns: {missing}")
            else:
                st.session_state.sessions = df_up[DEFAULT_COLUMNS].copy()
                st.success("Dataset loaded.")
        except Exception as e:
            st.error(f"Upload failed: {e}")

    if st.button("Reset to sample dataset"):
        st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)
        st.success("Reset complete.")

    # Autosave + Undo
    if st.checkbox("Autosave edits", value=False):
        st.session_state.sessions.to_csv("sessions_autosave.csv", index=False)
        st.sidebar.info("Autosaved to sessions_autosave.csv")
    if st.button("Undo last change"):
        try:
            st.session_state.sessions = pd.read_csv("sessions_autosave.csv")
            st.success("Reverted to last autosave.")
        except FileNotFoundError:
            st.warning("No autosave file found.")

# --- Network Settings ---
with st.sidebar.expander("Network Settings", expanded=True):
    min_shared = st.slider("Min shared keywords for an edge", 1, 5, 1)
    include_manual = st.checkbox("Include manual connect_with edges", value=True)
    use_jaccard = st.checkbox("Use Jaccard similarity", value=False)
    jaccard_thr = st.slider("Jaccard threshold", 0.0, 1.0, 0.2, 0.05)
    size_min, size_max = st.slider("Node size range (px)", 5, 60, (12, 38))

# --- Quick Edit Tool ---
with st.sidebar.expander("Quick Edit Session", expanded=False):
    df = st.session_state.sessions
    if not df.empty:
        sel_id = st.selectbox("Select session", df["session_id"])
        if st.button("Load for Edit"):
            sel = df.query("session_id == @sel_id").iloc[0]
            st.session_state["form_prefill"] = sel.to_dict()
            st.experimental_rerun()

# --------------------- Main Tabs ---------------------
tab_data, tab_graph, tab_legend = st.tabs(["📋 Data / Edit", "🕸️ Graph", "🎨 Legend"])

with tab_data:
    st.markdown("## Add / Edit Session")

    prefill = st.session_state.get("form_prefill", {})

    with st.form("add_session"):
        col1, col2, col3, col4 = st.columns([1,1,1,1])
        session_id = col1.text_input("Session ID", value=prefill.get("session_id", ""), placeholder="W3-Tu")
        date = col2.text_input("Date (YYYY-MM-DD)", value=prefill.get("date", ""))
        title = col3.text_input("Title", value=prefill.get("title", ""))
        instructor = col4.text_input("Instructor(s)", value=prefill.get("instructor", ""))
        col5, col6, col7 = st.columns([1,1,1])
        module = col5.text_input("Module", value=prefill.get("module", ""))
        activity = col6.text_input("Activity", value=prefill.get("activity", ""))
        keywords = col7.text_area("Keywords (comma-separated)", value=prefill.get("keywords", ""))
        notes = st.text_area("Notes", value=prefill.get("notes", ""))
        connect_with = st.text_input("Connect with", value=prefill.get("connect_with", ""))
        submitted = st.form_submit_button("Add / Update")
        if submitted:
            if not session_id:
                st.warning("Session ID is required.")
            else:
                row = {
                    "session_id": session_id.strip(),
                    "date": date.strip(),
                    "title": title.strip(),
                    "instructor": instructor.strip(),
                    "module": module.strip() if module.strip() else "Unassigned",
                    "activity": activity.strip(),
                    "keywords": keywords.strip(),
                    "notes": notes.strip(),
                    "connect_with": connect_with.strip(),
                }
                df = st.session_state.sessions
                if session_id in df["session_id"].values:
                    st.session_state.sessions.loc[df["session_id"] == session_id, :] = row
                    st.success(f"Updated {session_id}.")
                else:
                    st.session_state.sessions = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                    st.success(f"Added {session_id}.")
        if st.form_submit_button("Clear fields"):
            st.session_state["form_prefill"] = {}
            st.experimental_rerun()

    st.markdown("---")

    st.markdown("### Inline Table Edit")
    edited_df = st.data_editor(
        st.session_state.sessions,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="editable_table",
    )
    if not edited_df.equals(st.session_state.sessions):
        st.session_state.sessions = edited_df.copy()
        st.success("Table updated in memory.")

    # Delete session
    colA, colB = st.columns([0.4, 0.4])
    with colA:
        to_del = st.text_input("Delete session by ID")
        if st.button("Delete"):
            if to_del and to_del in st.session_state.sessions["session_id"].values:
                st.session_state.sessions = st.session_state.sessions[st.session_state.sessions["session_id"] != to_del]
                st.success(f"Deleted {to_del}.")
            else:
                st.warning("Unknown session ID.")

with tab_graph:
    st.markdown("## Session Network View")

    df_show = st.session_state.sessions.copy()
    G = nx.Graph()

    for _, row in df_show.iterrows():
        kws = _clean_keywords(row["keywords"])
        instr_list = _split_multi(row["instructor"]) or ["(Unassigned)"]
        module_value = row["module"].strip() if pd.notna(row["module"]) else "Unassigned"
        G.add_node(
            row["session_id"],
            title=row["title"],
            date=row["date"],
            instructor=instr_list,
            module=module_value,
            activity=row["activity"],
            keywords=kws,
            notes=row["notes"],
            connect_with=_split_multi(row["connect_with"]),
        )

    # Edge creation
    nodes = list(G.nodes())
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            a, b = nodes[i], nodes[j]
            ak = set(G.nodes[a]["keywords"])
            bk = set(G.nodes[b]["keywords"])
            if ak and bk:
                if use_jaccard:
                    union = ak | bk
                    jac = len(ak & bk) / len(union) if union else 0.0
                    if jac >= jaccard_thr:
                        G.add_edge(a, b, edge_type="keyword_overlap", weight=jac, note=f"Jaccard {jac:.2f}")
                else:
                    shared = len(ak & bk)
                    if shared >= min_shared:
                        G.add_edge(a, b, edge_type="keyword_overlap", weight=shared, note=f"Shared: {', '.join(sorted(ak & bk))}")
    if include_manual:
        for n in nodes:
            connects = G.nodes[n].get("connect_with", [])
            for m in connects:
                if m in nodes and m != n:
                    G.add_edge(n, m, edge_type="manual_connect", weight=1, note="manual connect")

    # Module colors
    modules = sorted({G.nodes[n]["module"] for n in G.nodes()})
    PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
               "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    color_map = {mod: PALETTE[i % len(PALETTE)] for i, mod in enumerate(modules)}
    def scale_size(x: float) -> float: return (size_min + size_max) / 2

    # Render graph
    if HAS_PYVIS:
        net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="#222")
        net.force_atlas_2based(gravity=-50, central_gravity=0.02, spring_length=120, spring_strength=0.05, damping=0.4, overlap=1.5)
        for n in G.nodes():
            data = G.nodes[n]
            color = color_map.get(data["module"], "#777777")
            size = scale_size(1)
            title_html = f"""
                <b>{n}: {data.get('title','')}</b><br>
                Date: {data.get('date','')}<br>
                Module: {data.get('module','')}<br>
                Instructor(s): {', '.join(data.get('instructor', []))}<br>
                Activity: {data.get('activity','')}<br>
                Keywords: {', '.join(data.get('keywords', []))}<br>
                Notes: {data.get('notes','')}<br>
            """
            net.add_node(n, label=n, title=title_html, color=color, size=size, shape="dot")
        for u, v, ed in G.edges(data=True):
            et = ed.get("edge_type", "keyword_overlap")
            dashes = (et == "manual_connect")
            width = max(1, 2 if ed.get("weight", 1) >= 2 else 1)
            title_e = f"{et} — {ed.get('note','')}"
            net.add_edge(u, v, title=title_e, width=width, physics=True, smooth=True, dashes=dashes)
        tmp_path = pathlib.Path(tempfile.NamedTemporaryFile(delete=False, suffix=".html").name)
        net.write_html(tmp_path.as_posix(), notebook=False, local=True)
        html_code = tmp_path.read_text(encoding="utf-8")
        html(html_code, height=820, scrolling=True)
        st.download_button("Download Graph (.html)", html_code, "network.html")
    else:
        st.warning("PyVis not found, using Plotly fallback.")
        pos = nx.spring_layout(G, seed=42, k=0.6)
        edge_x, edge_y = [], []
        for u, v in G.edges():
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x += [x0, x1, None]
            edge_y += [y0, y1, None]
        edge_trace = go.Scatter(x=edge_x, y=edge_y, mode='lines', hoverinfo='none', line=dict(width=1))
        node_x, node_y, text, sizes, colors = [], [], [], [], []
        for n, data in G.nodes(data=True):
            x, y = pos[n]
            node_x.append(x); node_y.append(y)
            text.append(f"{n}: {data.get('title','')}")
            sizes.append(scale_size(1))
            colors.append(color_map.get(data.get('module',''), '#777777'))
        node_trace = go.Scatter(
            x=node_x, y=node_y, mode='markers', text=text, hoverinfo='text',
            marker=dict(size=sizes, color=colors, line=dict(width=0.5))
        )
        fig = go.Figure(data=[edge_trace, node_trace])
        fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    # Manual connection creator
    with st.expander("Add Manual Connection"):
        n1 = st.selectbox("From session", G.nodes(), key="conn1")
        n2 = st.selectbox("To session", G.nodes(), key="conn2")
        if st.button("Add connection"):
            if n1 != n2:
                df = st.session_state.sessions
                row_idx = df.index[df["session_id"] == n1]
                if not row_idx.empty:
                    current = df.loc[row_idx, "connect_with"].iloc[0]
                    new_val = f"{current},{n2}" if current else n2
                    st.session_state.sessions.loc[row_idx, "connect_with"] = new_val
                    st.success(f"Connected {n1} → {n2}")
                    st.experimental_rerun()

with tab_legend:
    st.markdown("### Legend: Module Color Mapping")
    for mod, c in color_map.items():
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;'>"
            f"<div style='width:14px;height:14px;background:{c};border-radius:50%;'></div>"
            f"<span>{mod}</span></div>",
            unsafe_allow_html=True,
        )

    st.caption(
        "Edges: solid = keyword overlap; dashed = manual connect. "
        "Node color = module. Hover over a node for session details."
    )
