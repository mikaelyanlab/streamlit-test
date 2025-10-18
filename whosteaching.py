# app.py
# EPP Course Network — Streamlit app
# -------------------------------------------------------------
# Features
# - Manually add/edit courses (no live scraping)
# - Course attributes: id, title, number, prefix, level, instructors, term, modality,
#   crosslisting, enrollment, keywords
# - Dynamic network:
#     * edges by shared keywords (threshold slider) or by Jaccard similarity
#     * optional cross-list edges
#     * node size = enrollment (scalable)
#     * node color = instructor (active coloring)
#     * community detection ("islands") via greedy modularity
# - Import/export CSV; reset dataset
# - PyVis interactive network rendered in-app (safe for Streamlit Cloud)
#
# Requirements (requirements.txt):
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

# Prefer PyVis; fall back to Plotly if unavailable
try:
    from pyvis.network import Network  # type: ignore
    from streamlit.components.v1 import html
    HAS_PYVIS = True
except Exception:
    HAS_PYVIS = False
    import plotly.graph_objects as go  # type: ignore

# --------------------------- Utility ---------------------------

DEFAULT_COLUMNS = [
    "course_id", "title", "number", "prefix", "level",
    "instructors", "typical_term", "modality",
    "is_crosslisted", "crosslist_with",
    "enrollment", "keywords"
]

SAMPLE_ROWS = [
    {
        "course_id": "ENT425", "title": "General Entomology", "number": 425, "prefix": "ENT",
        "level": "UG", "instructors": "Mikaelyan", "typical_term": "Fall", "modality": "In-person",
        "is_crosslisted": False, "crosslist_with": "",
        "enrollment": 120, "keywords": "morphology, physiology, ecology, behavior, systematics"
    },
    {
        "course_id": "ENT305", "title": "Introduction to Forensic Entomology", "number": 305, "prefix": "ENT",
        "level": "UG", "instructors": "Mikaelyan", "typical_term": "Fall", "modality": "In-person",
        "is_crosslisted": False, "crosslist_with": "",
        "enrollment": 60, "keywords": "forensics, decomposition, succession, evidence"
    },
    {
        "course_id": "ENT582", "title": "Medical and Veterinary Entomology", "number": 582, "prefix": "ENT",
        "level": "GR", "instructors": "Hayes", "typical_term": "Spring", "modality": "In-person",
        "is_crosslisted": False, "crosslist_with": "",
        "enrollment": 25, "keywords": "vectors, disease, parasites, epidemiology"
    },
    {
        "course_id": "ENT550", "title": "Fundamentals of Arthropod Management", "number": 550, "prefix": "ENT",
        "level": "GR", "instructors": "Jones", "typical_term": "Fall", "modality": "In-person/Hybrid",
        "is_crosslisted": False, "crosslist_with": "",
        "enrollment": 35, "keywords": "IPM, management, sampling, thresholds"
    },
    {
        "course_id": "PP501", "title": "Biology of Plant Pathogens", "number": 501, "prefix": "PP",
        "level": "GR", "instructors": "Villani", "typical_term": "Fall", "modality": "In-person",
        "is_crosslisted": True, "crosslist_with": "PB501, MB501",
        "enrollment": 45, "keywords": "bacteria, fungi, viruses, oomycetes, nematodes"
    },
    {
        "course_id": "PP506", "title": "Epidemiology & Plant Disease Control", "number": 506, "prefix": "PP",
        "level": "GR", "instructors": "Villani", "typical_term": "Spring", "modality": "In-person",
        "is_crosslisted": False, "crosslist_with": "",
        "enrollment": 30, "keywords": "epidemiology, control, surveillance"
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


# --------------------------- App State ---------------------------

st.set_page_config(page_title="EPP Course Network", layout="wide")

if "courses" not in st.session_state:
    st.session_state.courses = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)

# --------------------------- Sidebar ---------------------------

st.sidebar.title("EPP Course Network")

with st.sidebar.expander("Data IO", expanded=True):
    # Download current dataset
    csv_buf = io.StringIO()
    st.session_state.courses.to_csv(csv_buf, index=False)
    st.download_button(
        label="Download courses.csv",
        data=csv_buf.getvalue(),
        file_name="courses.csv",
        mime="text/csv",
    )

    up = st.file_uploader("Upload courses.csv", type=["csv"], help="Must include the columns defined in the template.")
    if up is not None:
        try:
            df_up = pd.read_csv(up)
            missing = [c for c in DEFAULT_COLUMNS if c not in df_up.columns]
            if missing:
                st.error(f"Missing columns: {missing}")
            else:
                st.session_state.courses = df_up[DEFAULT_COLUMNS].copy()
                st.success("Dataset loaded.")
        except Exception as e:
            st.error(f"Upload failed: {e}")

    if st.button("Reset to sample dataset"):
        st.session_state.courses = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)
        st.success("Reset complete.")

with st.sidebar.expander("Network Settings", expanded=True):
    min_shared = st.slider("Min shared keywords for an edge", 1, 5, 1, help="Higher values yield sparser graphs.")
    include_cross = st.checkbox("Include cross-list edges", value=True)
    use_jaccard = st.checkbox(
        "Use Jaccard similarity instead of raw count",
        value=False,
        help="If on, edge forms when Jaccard ≥ threshold (slider below).",
    )
    jaccard_thr = st.slider("Jaccard threshold", 0.0, 1.0, 0.2, 0.05)
    size_min, size_max = st.slider("Node size range (px)", 5, 60, (12, 38))

with st.sidebar.expander("Filters", expanded=False):
    all_instr = sorted({i for row in st.session_state.courses["instructors"].fillna("") for i in _split_multi(row)})
    pick_instr = st.multiselect("Instructor(s)", options=all_instr, default=[])
    pick_level = st.multiselect("Level(s)", options=["UG", "GR"], default=[])

# --------------------------- Main: Data Entry ---------------------------

st.markdown("## Add / Edit Courses")

with st.form("add_course"):
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    course_id = col1.text_input("Course ID", placeholder="ENT425")
    title = col2.text_input("Title", placeholder="General Entomology")
    prefix = col3.text_input("Prefix", value="ENT")
    number = col4.number_input("Number", min_value=0, max_value=999, value=425)

    col5, col6, col7 = st.columns([1, 1, 1])
    level = col5.selectbox("Level", ["UG", "GR"], index=0)
    instructors = col6.text_input("Instructor(s)", placeholder="LastName or Last1, Last2")
    enrollment = col7.number_input("Enrollment", min_value=0, max_value=10000, value=50)

    col8, col9, col10 = st.columns([1, 1, 1])
    typical_term = col8.text_input("Typical term", placeholder="Fall")
    modality = col9.text_input("Modality", placeholder="In-person/Hybrid/Online")
    is_crosslisted = col10.checkbox("Cross-listed?", value=False)

    crosslist_with = st.text_input("Crosslist with (optional comma-separated IDs)", placeholder="PB501, MB501")
    keywords = st.text_area("Keywords (comma-separated)", placeholder="morphology, physiology, ecology")

    submit_col, clear_col = st.columns([0.2, 0.2])
    submitted = submit_col.form_submit_button("Add / Update")
    cleared = clear_col.form_submit_button("Clear fields")

    if submitted:
        if not course_id:
            st.warning("Course ID is required.")
        else:
            row = {
                "course_id": course_id.strip(),
                "title": title.strip(),
                "number": int(number),
                "prefix": prefix.strip(),
                "level": level,
                "instructors": instructors.strip(),
                "typical_term": typical_term.strip(),
                "modality": modality.strip(),
                "is_crosslisted": bool(is_crosslisted),
                "crosslist_with": crosslist_with.strip(),
                "enrollment": int(enrollment),
                "keywords": keywords.strip(),
            }
            df = st.session_state.courses
            if course_id in df["course_id"].values:
                st.session_state.courses.loc[df["course_id"] == course_id, :] = row
                st.success(f"Updated {course_id}.")
            else:
                st.session_state.courses = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                st.success(f"Added {course_id}.")
    if cleared:
        st.rerun()

st.markdown("---")

# --------------------------- Table & Row Ops ---------------------------

st.markdown("### Current Courses")

df_show = st.session_state.courses.copy()

# Apply filters
if pick_instr:
    df_show = df_show[df_show["instructors"].apply(lambda s: any(x in _split_multi(s) for x in pick_instr))]
if pick_level:
    df_show = df_show[df_show["level"].isin(pick_level)]

st.dataframe(df_show, use_container_width=True, hide_index=True)

colA, colB, _ = st.columns([0.3, 0.3, 0.4])
with colA:
    to_del = st.text_input("Delete course by ID")
    if st.button("Delete"):
        if to_del and to_del in st.session_state.courses["course_id"].values:
            st.session_state.courses = st.session_state.courses[st.session_state.courses["course_id"] != to_del]
            st.success(f"Deleted {to_del}.")
        else:
            st.warning("Unknown course ID.")
with colB:
    to_load = st.text_input("Load course into form (ID)")
    if st.button("Load to form"):
        df = st.session_state.courses
        if to_load in df["course_id"].values:
            r = df.loc[df["course_id"] == to_load].iloc[0].to_dict()
            st.info("Scroll up and paste values into the form.")
            st.json(r)
        else:
            st.warning("Unknown course ID.")

# --------------------------- Build Graph ---------------------------

st.markdown("---")
st.markdown("## Network View")

G = nx.Graph()

# Add nodes
for _, row in df_show.iterrows():
    kws = _clean_keywords(row["keywords"])  # list
    instr_list = _split_multi(row["instructors"]) or ["(Unassigned)"]
    G.add_node(
        row["course_id"],
        title=row["title"],
        number=int(row["number"]) if not pd.isna(row["number"]) else None,
        prefix=row["prefix"],
        level=row["level"],
        instructors=instr_list,
        typical_term=row["typical_term"],
        modality=row["modality"],
        is_crosslisted=bool(row["is_crosslisted"]),
        crosslist_with=_split_multi(row["crosslist_with"]),
        enrollment=int(row["enrollment"]) if not pd.isna(row["enrollment"]) else 0,
        keywords=kws,
    )

# Keyword-overlap edges
nodes = list(G.nodes())
for i in range(len(nodes)):
    for j in range(i + 1, len(nodes)):
        a, b = nodes[i], nodes[j]
        ak = set(G.nodes[a]["keywords"]) if G.nodes[a]["keywords"] else set()
        bk = set(G.nodes[b]["keywords"]) if G.nodes[b]["keywords"] else set()
        if not ak or not bk:
            continue
        inter = ak & bk
        if use_jaccard:
            union = ak | bk
            jac = len(inter) / len(union) if union else 0.0
            if jac >= jaccard_thr and len(inter) > 0:
                G.add_edge(a, b, edge_type="topical_overlap", weight=jac, note=f"Jaccard {jac:.2f}")
        else:
            if len(inter) >= min_shared:
                G.add_edge(
                    a, b,
                    edge_type="topical_overlap",
                    weight=len(inter),
                    note=f"Shared: {', '.join(sorted(inter))}"
                )

# Cross-list edges
if include_cross:
    id_set = set(G.nodes())
    for n in nodes:
        xlist = G.nodes[n]["crosslist_with"]
        for x in xlist:
            if x in id_set and n != x:
                G.add_edge(n, x, edge_type="crosslist", weight=1, note="cross-listed")

# Communities (islands)
if G.number_of_edges() > 0 and G.number_of_nodes() > 2:
    communities = list(nx.algorithms.community.greedy_modularity_communities(G))
    comm_map: Dict[str, int] = {}
    for i, comm in enumerate(communities):
        for n in comm:
            comm_map[n] = i
else:
    comm_map = {n: 0 for n in G.nodes()}
nx.set_node_attributes(G, comm_map, name="island")

# Instructor-based color mapping
all_instructors = sorted({instr for n in G.nodes() for instr in G.nodes[n]["instructors"]})
PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    "#393b79", "#637939", "#8c6d31", "#843c39", "#7b4173"
]
color_map = {name: PALETTE[i % len(PALETTE)] for i, name in enumerate(all_instructors)}

# Node size scaling by enrollment
enrollments = [G.nodes[n].get("enrollment", 0) for n in G.nodes()]
if enrollments:
    e_min, e_max = min(enrollments), max(enrollments)

    def scale_size(x: int | float) -> float:
        if e_max == e_min:
            return (size_min + size_max) / 2
        return size_min + (size_max - size_min) * ((x - e_min) / (e_max - e_min))
else:
    def scale_size(x: int | float) -> float:
        return (size_min + size_max) / 2

# --------------------------- Render Graph ---------------------------

if HAS_PYVIS:
    net = Network(height="800px", width="100%", bgcolor="#ffffff", font_color="#222")
    net.force_atlas_2based(gravity=-50, central_gravity=0.02, spring_length=120, spring_strength=0.05,
                           damping=0.4, overlap=1.5)

    # Add nodes
    for n in G.nodes():
        data = G.nodes[n]
        instrs = data["instructors"]
        color = color_map[instrs[0]] if instrs else "#777777"
        size = scale_size(data.get("enrollment", 0))
        title_html = f"""
            <b>{n}: {data.get('title','')}</b><br>
            Level: {data.get('level','')} | Prefix: {data.get('prefix','')} | Number: {data.get('number','')}<br>
            Instructors: {', '.join(instrs)}<br>
            Term: {data.get('typical_term','')} | Modality: {data.get('modality','')}<br>
            Enrollment: {data.get('enrollment',0)}<br>
            Keywords: {', '.join(data.get('keywords', []))}<br>
            Cross-listed: {data.get('is_crosslisted', False)} ({', '.join(data.get('crosslist_with', []))})<br>
            Island: {data.get('island', 0)}
        """
        net.add_node(n, label=n, title=title_html, color=color, size=size, shape="dot")

    # Add edges
    for u, v, ed in G.edges(data=True):
        et = ed.get("edge_type", "overlap")
        dashes = (et == "crosslist")
        width = 1 if et == "crosslist" else max(1, 2 if ed.get("weight", 1) >= 2 else 1)
        title_e = f"{et} — {ed.get('note','')}"
        net.add_edge(u, v, title=title_e, width=width, physics=True, smooth=True, dashes=dashes)

    # IMPORTANT: do not call net.show(); write HTML and embed it
    tmp_path = pathlib.Path(tempfile.NamedTemporaryFile(delete=False, suffix=".html").name)
    net.write_html(tmp_path.as_posix(), notebook=False, local=True)
    with open(tmp_path, "r", encoding="utf-8") as f:
        html_code = f.read()
    html(html_code, height=820, scrolling=True)

else:
    # Plotly fallback (less interactive)
    st.warning(
        "PyVis not found. Using a Plotly fallback (add 'pyvis==0.3.2' to requirements.txt for richer interactivity)."
    )
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
        sizes.append(scale_size(data.get('enrollment', 0)))
        instrs = data.get('instructors', ['(Unassigned)'])
        colors.append(color_map.get(instrs[0], '#777777'))
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode='markers', text=text, hoverinfo='text',
        marker=dict(size=sizes, color=colors, line=dict(width=0.5))
    )
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(template=None, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

# --------------------------- Legends & Summaries ---------------------------

st.markdown("### Legends")

# Instructor legend
if all_instructors:
    leg_cols = st.columns(min(4, len(all_instructors)))
    for idx, name in enumerate(all_instructors):
        with leg_cols[idx % len(leg_cols)]:
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:8px;'>"
                f"<div style='width:14px;height:14px;background:{color_map[name]};border-radius:50%;'></div>"
                f"<span>{name}</span></div>",
                unsafe_allow_html=True,
            )

# Island summary
if G.number_of_nodes() > 0:
    df_islands = pd.DataFrame({
        "course_id": list(G.nodes()),
        "island": [G.nodes[n]["island"] for n in G.nodes()],
        "instructors": [", ".join(G.nodes[n]["instructors"]) for n in G.nodes()],
        "enrollment": [G.nodes[n]["enrollment"] for n in G.nodes()],
    }).sort_values(["island", "course_id"])
    with st.expander("Island composition (communities)", expanded=False):
        st.dataframe(df_islands, use_container_width=True, hide_index=True)

st.caption(
    "Edges: solid = topical overlap; dashed = cross-listed. "
    "Node color = instructor (first listed). Node size = enrollment."
)
