# app.py
# Symbiosis Course Session Network — Streamlit app
# -------------------------------------------------------------
# Features
# - Add/Edit class sessions (lecture, discussion, break, project‑week)
# - Session attributes: id, date, title, instructor, module, activity, keywords, notes, connect_with
# - Dynamic network:
#     * edges by shared keywords (threshold slider) or by manual connects ("connect_with")
#     * node size fixed (or configurable)
#     * node color = module (active coloring)
#     * community detection by module or keyword overlap
# - Import/export CSV; reset dataset
# - PyVis interactive network rendered in‑app
#
# Requirements:
# streamlit>=1.36
# pandas>=2.0
# networkx>=3.2
# pyvis==0.3.2
# jinja2>=3.0
#
# Run:  streamlit run app.py
# -------------------------------------------------------------

from __future__ import annotations
import io
import pathlib
import tempfile
from typing import List, Dict

import pandas as pd
import streamlit as st
import networkx as nx

# Prefer PyVis; fallback to Plotly
try:
    from pyvis.network import Network  # type: ignore
    from streamlit.components.v1 import html
    HAS_PYVIS = True
except Exception:
    HAS_PYVIS = False
    import plotly.graph_objects as go  # type: ignore

# --------------------------- Utility ---------------------------

DEFAULT_COLUMNS = [
    "session_id", "date", "title", "instructor", "module",
    "activity", "keywords", "notes", "connect_with"
]

# Sample initial rows (you will replace with your 17‑week schedule)
SAMPLE_ROWS = [
    {
        "session_id": "W1-Tu", "date": "2025‑01‑14", "title": "Ch 1 – What is Symbiosis?",
        "instructor": "You", "module": "Foundations",
        "activity": "Intro discussion", "keywords": "symbiosis, mutualism, parasitism",
        "notes": "Define terms; systems diagram", "connect_with": ""
    },
    {
        "session_id": "W1-Th", "date": "2025‑01‑16", "title": "Symbiosis — scope & examples",
        "instructor": "You", "module": "Foundations",
        "activity": "Mini case‑studies", "keywords": "commensalism, amensalism, insect symbiosis",
        "notes": "", "connect_with": "W1‑Tu"
    },
    # … add more initial rows for each session/week
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

# --------------------------- App State ---------------------------

st.set_page_config(page_title="Symbiosis Course Session Network", layout="wide")

if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)

# --------------------------- Sidebar ---------------------------

st.sidebar.title("Course Session Network")

with st.sidebar.expander("Data IO", expanded=True):
    csv_buf = io.StringIO()
    st.session_state.sessions.to_csv(csv_buf, index=False)
    st.download_button(
        label="Download sessions.csv",
        data=csv_buf.getvalue(),
        file_name="sessions.csv",
        mime="text/csv",
    )

    up = st.file_uploader("Upload sessions.csv", type=["csv"], help="Must include the columns defined in the template.")
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

with st.sidebar.expander("Network Settings", expanded=True):
    min_shared = st.slider("Min shared keywords for an edge", 1, 5, 1, help="Higher values yield sparser graphs.")
    include_manual = st.checkbox("Include manual connect_with edges", value=True)
    use_jaccard = st.checkbox(
        "Use Jaccard similarity instead of raw count",
        value=False,
        help="If on, edge forms when Jaccard ≥ threshold (slider below).",
    )
    jaccard_thr = st.slider("Jaccard threshold", 0.0, 1.0, 0.2, 0.05)
    size_min, size_max = st.slider("Node size range (px)", 5, 60, (12, 38))

with st.sidebar.expander("Filters", expanded=False):
    all_instr = sorted({i for row in st.session_state.sessions["instructor"].fillna("") for i in _split_multi(row)})
    pick_instr = st.multiselect("Instructor(s)", options=all_instr, default=[])
    pick_module = st.multiselect("Module(s)", options=sorted({m for m in st.session_state.sessions["module"].fillna("")}), default=[])

# --------------------------- Main: Data Entry ---------------------------

st.markdown("## Add / Edit Session")

with st.form("add_session"):
    col1, col2, col3, col4 = st.columns([1,1,1,1])
    session_id = col1.text_input("Session ID", placeholder="W3-Tu")
    date = col2.date_input("Date")
    title = col3.text_input("Title", placeholder="Ch 3 – Nutritional Symbioses")
    instructor = col4.text_input("Instructor(s)", placeholder="You")
    col5, col6, col7 = st.columns([1,1,1])
    module = col5.text_input("Module", placeholder="Nutritional Symbiosis")
    activity = col6.text_input("Activity", placeholder="Case discussion / Lab")
    keywords = col7.text_area("Keywords (comma-separated)", placeholder="aphid, buchnera, nitrogen")
    notes = st.text_area("Notes", placeholder="Reading: Chapter 3, bring laptop for modeling")
    connect_with = st.text_input("Connect with (optional comma-separated session IDs)", placeholder="W2‑Th, W3‑Tu")
    submitted = st.form_submit_button("Add / Update")
    if submitted:
        if not session_id:
            st.warning("Session ID is required.")
        else:
            row = {
                "session_id": session_id.strip(),
                "date": date.strftime("%Y‑%m‑%d"),
                "title": title.strip(),
                "instructor": instructor.strip(),
                "module": module.strip() if module.strip() else "Unassigned",
                "activity": activity.strip(),
                "keywords": keywords.strip(),
                "notes": notes.strip(),
                "connect_with": connect_with.strip()
            }
            df = st.session_state.sessions
            if session_id in df["session_id"].values:
                st.session_state.sessions.loc[df["session_id"] == session_id, :] = row
                st.success(f"Updated {session_id}.")
            else:
                st.session_state.sessions = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                st.success(f"Added {session_id}.")
    if st.form_submit_button("Clear fields"):
        st.rerun()

st.markdown("---")

# --------------------------- Table & Row Operations ---------------------------

st.markdown("### Current Sessions")

df_show = st.session_state.sessions.copy()

if pick_instr:
    df_show = df_show[df_show["instructor"].apply(lambda s: any(x in _split_multi(s) for x in pick_instr))]
if pick_module:
    df_show = df_show[df_show["module"].isin(pick_module)]

st.dataframe(df_show, use_container_width=True, hide_index=True)

colA, colB, _ = st.columns([0.3, 0.3, 0.4])
with colA:
    to_del = st.text_input("Delete session by ID")
    if st.button("Delete"):
        if to_del and to_del in st.session_state.sessions["session_id"].values:
            st.session_state.sessions = st.session_state.sessions[st.session_state.sessions["session_id"] != to_del]
            st.success(f"Deleted {to_del}.")
        else:
            st.warning("Unknown session ID.")
with colB:
    to_load = st.text_input("Load session into form (ID)")
    if st.button("Load to form"):
        df = st.session_state.sessions
        if to_load in df["session_id"].values:
            r = df.loc[df["session_id"] == to_load].iloc[0].to_dict()
            st.info("Scroll up and paste values into the form.")
            st.json(r)
        else:
            st.warning("Unknown session ID.")

# --------------------------- Build Graph ---------------------------

st.markdown("---")
st.markdown("## Session Network View")

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
        connect_with=_split_multi(row["connect_with"])
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
                    G.add_edge(a, b, edge_type="keyword_overlap", weight=jac,
                               note=f"Jaccard {jac:.2f}")
            else:
                shared = len(ak & bk)
                if shared >= min_shared:
                    G.add_edge(a, b, edge_type="keyword_overlap", weight=shared,
                               note=f"Shared: {', '.join(sorted(ak & bk))}")

if include_manual:
    for n in nodes:
        connects = G.nodes[n].get("connect_with", [])
        for m in connects:
            if m in nodes and m != n:
                G.add_edge(n, m, edge_type="manual_connect", weight=1, note="manual connect")

# Community mapping by module
modules = sorted({G.nodes[n]["module"] for n in G.nodes()})
mod_index = {mod: idx for idx, mod in enumerate(modules)}
comm_map: Dict[str, int] = {n: mod_index.get(G.nodes[n]["module"], 0) for n in G.nodes()}
nx.set_node_attributes(G, comm_map, name="community")

# Module‑based color mapping
PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
color_map = {mod: PALETTE[i % len(PALETTE)] for i, mod in enumerate(modules)}

def scale_size(x: float) -> float:
    return (size_min + size_max) / 2

# --------------------------- Render Graph ---------------------------

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
        width = max(1, 2 if ed.get("weight",1) >= 2 else 1)
        title_e = f"{et} — {ed.get('note','')}"
        net.add_edge(u, v, title=title_e, width=width, physics=True, smooth=True, dashes=dashes)
    tmp_path = pathlib.Path(tempfile.NamedTemporaryFile(delete=False, suffix=".html").name)
    net.write_html(tmp_path.as_posix(), notebook=False, local=True)
    with open(tmp_path, "r", encoding="utf-8") as f:
        html_code = f.read()
    html(html_code, height=820, scrolling=True)
else:
    st.warning("PyVis not found. Using Plotly fallback.")
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
        node_x.append(x)
        node_y.append(y)
        text.append(f"{n}: {data.get('title','')}")
        sizes.append(scale_size(1))
        colors.append(color_map.get(data.get('module',''), '#777777'))
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers', text=text, hoverinfo='text',
        marker=dict(size=sizes, color=colors, line=dict(width=0.5))
    )
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(template=None, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

# --------------------------- Legend & Summary ---------------------------

st.markdown("### Legend: Module Color Mapping")
for mod, c in color_map.items():
    st.markdown(f"<div style='display:flex;align-items:center;gap:8px;'>"
                f"<div style='width:14px;height:14px;background:{c};border‑radius:50%;'></div>"
                f"<span>{mod}</span></div>", unsafe_allow_html=True)

st.caption(
    "Edges: solid = keyword overlap; dashed = manual connect. "
    "Node color = module. Hover over a node for session details."
)
