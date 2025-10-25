# app.py — Insect–Microbe Systems Course Network (Final Build)
# ----------------------------------------------------------------------
# Features:
# ✅ Robust CSV import with validation (handles smart quotes & commas)
# ✅ Add / edit / delete sessions
# ✅ Inline data_editor
# ✅ PyVis network with clickable nodes (no hover clutter)
# ✅ “Session Passport” panel showing full details on click
# ----------------------------------------------------------------------

from __future__ import annotations
import io
import csv
import pathlib
import tempfile
import pandas as pd
import streamlit as st
import networkx as nx
import streamlit.components.v1 as components
from typing import List, Dict

from pyvis.network import Network

# ----------------------------------------------------------------------
# Utility functions
# ----------------------------------------------------------------------

DEFAULT_COLUMNS = [
    "session_id", "date", "title", "instructor", "module",
    "activity", "keywords", "notes", "connect_with"
]

SAMPLE_ROWS = [
    {
        "session_id": "W1-Tu", "date": "2026-01-13",
        "title": "Systems Bootcamp – Insects as Systems within Systems",
        "instructor": "You", "module": "Systems Bootcamp",
        "activity": "Interactive lecture",
        "keywords": "systems thinking, feedback loops",
        "notes": "Define balancing and reinforcing loops.",
        "connect_with": ""
    }
]

REQUIRED_COLS = DEFAULT_COLUMNS


def _clean_keywords(s: str) -> List[str]:
    if pd.isna(s) or not str(s).strip():
        return []
    toks = [t.strip().lower() for t in str(s).replace(";", ",").split(",")]
    return sorted(list({t for t in toks if t}))


def _split_multi(s: str) -> List[str]:
    if pd.isna(s) or not str(s).strip():
        return []
    return [t.strip() for t in str(s).replace(";", ",").split(",") if t.strip()]


# ----------------------------------------------------------------------
# Streamlit page config
# ----------------------------------------------------------------------
st.set_page_config(page_title="Insect–Microbe Systems Network", layout="wide")

if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)

# ----------------------------------------------------------------------
# Sidebar — Data management and settings
# ----------------------------------------------------------------------

st.sidebar.title("Course Session Network")

with st.sidebar.expander("📂 Data IO", expanded=True):
    # Download
    csv_buf = io.StringIO()
    st.session_state.sessions.to_csv(csv_buf, index=False)
    st.download_button("⬇️ Download sessions.csv", csv_buf.getvalue(),
                       "sessions.csv", "text/csv")

    # Upload
    up = st.file_uploader("Upload sessions.csv", type=["csv"])
    if up is not None:
        try:
            raw_bytes = up.read()
            text = raw_bytes.decode("utf-8", errors="replace")
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = (text.replace("“", '"').replace("”", '"')
                        .replace("’", "'").replace("‘", "'")
                        .replace("\u00A0", " "))
            text = text.strip()

            # Validator
            rdr = csv.reader(io.StringIO(text))
            rows = list(rdr)
            if not rows:
                raise ValueError("Empty file.")
            header = rows[0]
            expected_n = len(REQUIRED_COLS)
            if header != REQUIRED_COLS:
                st.warning(f"Header mismatch.\nExpected: {REQUIRED_COLS}\nFound: {header}")

            problems = []
            for idx, r in enumerate(rows[1:], start=2):
                if len(r) != expected_n:
                    problems.append((idx, len(r), r[:3]))
            if problems:
                st.error(f"{len(problems)} malformed row(s) found. Expected {expected_n} columns.")
                for ln, ncols, preview in problems[:5]:
                    st.write(f"Line {ln}: {ncols} cols → {preview}")

            # Parse robustly
            try:
                df_up = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
            except Exception:
                df_up = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False,
                                    engine="python", sep=",", quotechar='"', escapechar="\\")

            missing = [c for c in REQUIRED_COLS if c not in df_up.columns]
            if missing:
                st.error(f"Missing columns: {missing}")
            else:
                df_up = df_up[REQUIRED_COLS].fillna("")
                st.session_state.sessions = df_up.copy()
                st.success("✅ Dataset loaded successfully.")
        except Exception as e:
            st.error(f"Upload failed. Please re-download the template and paste your data.\n\nDetails: {e}")

    if st.button("Reset to sample dataset"):
        st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=REQUIRED_COLS)
        st.success("Reset complete.")

with st.sidebar.expander("⚙️ Network Settings", expanded=True):
    min_shared = st.slider("Min shared keywords for edge", 1, 5, 1)
    include_manual = st.checkbox("Include manual connect_with edges", value=True)
    use_jaccard = st.checkbox("Use Jaccard similarity", value=False)
    jaccard_thr = st.slider("Jaccard threshold", 0.0, 1.0, 0.2, 0.05)
    size_min, size_max = st.slider("Node size range", 5, 60, (14, 38))

# ----------------------------------------------------------------------
# Main tabs
# ----------------------------------------------------------------------

tab_data, tab_graph = st.tabs(["📋 Data / Edit", "🕸️ Graph Explorer"])

# ----------------------------------------------------------------------
# Data / Edit tab
# ----------------------------------------------------------------------

with tab_data:
    st.markdown("## Add / Edit Session")

    with st.form("add_session"):
        c1, c2, c3, c4 = st.columns(4)
        session_id = c1.text_input("Session ID", placeholder="W2-Tu")
        date = c2.text_input("Date (YYYY-MM-DD)")
        title = c3.text_input("Title")
        instructor = c4.text_input("Instructor(s)", value="You")

        c5, c6, c7 = st.columns(3)
        module = c5.text_input("Module")
        activity = c6.text_input("Activity")
        keywords = c7.text_input("Keywords (comma-separated)")

        notes = st.text_area("Notes")
        connect_with = st.text_input("Connect with (IDs comma-separated)")

        submitted = st.form_submit_button("Add / Update")
        if submitted:
            if not session_id.strip():
                st.warning("Session ID required.")
            else:
                row = {
                    "session_id": session_id.strip(),
                    "date": date.strip(),
                    "title": title.strip(),
                    "instructor": instructor.strip(),
                    "module": module.strip() or "Unassigned",
                    "activity": activity.strip(),
                    "keywords": keywords.strip(),
                    "notes": notes.strip(),
                    "connect_with": connect_with.strip()
                }
                df = st.session_state.sessions
                if session_id in df["session_id"].values:
                    st.session_state.sessions.loc[df["session_id"] == session_id, :] = row
                    st.success(f"Updated {session_id}")
                else:
                    st.session_state.sessions = pd.concat(
                        [df, pd.DataFrame([row])], ignore_index=True)
                    st.success(f"Added {session_id}")

    st.markdown("### Inline Table Edit")
    edited = st.data_editor(
        st.session_state.sessions,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        key="table_edit"
    )
    if not edited.equals(st.session_state.sessions):
        st.session_state.sessions = edited.copy()
        st.info("Table updated in memory.")

# ----------------------------------------------------------------------
# Graph tab
# ----------------------------------------------------------------------

with tab_graph:
    st.markdown("## Interactive Course Graph")

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
            connect_with=_split_multi(row["connect_with"])
        )

    # Edge logic
    nodes = list(G.nodes())
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            ak, bk = set(G.nodes[a]["keywords"]), set(G.nodes[b]["keywords"])
            if ak and bk:
                if use_jaccard:
                    union = ak | bk
                    jac = len(ak & bk) / len(union) if union else 0
                    if jac >= jaccard_thr:
                        G.add_edge(a, b, edge_type="keyword", weight=jac)
                else:
                    shared = len(ak & bk)
                    if shared >= min_shared:
                        G.add_edge(a, b, edge_type="keyword", weight=shared)
    if include_manual:
        for n in nodes:
            for m in G.nodes[n]["connect_with"]:
                if m in nodes and m != n:
                    G.add_edge(n, m, edge_type="manual", weight=1)

    modules = sorted({G.nodes[n]["module"] for n in G.nodes()})
    PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
               "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    color_map = {mod: PALETTE[i % len(PALETTE)] for i, mod in enumerate(modules)}
    def scale_size(x): return (size_min + size_max) / 2

    # Build PyVis network
    net = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#111111")
    net.force_atlas_2based(gravity=-50, central_gravity=0.02, spring_length=120,
                           spring_strength=0.05, damping=0.4, overlap=1.5)
    for n in G.nodes():
        data = G.nodes[n]
        color = color_map.get(data["module"], "#777777")
        net.add_node(n, label=n, color=color, size=scale_size(1), title=data["title"])
    for u, v, ed in G.edges(data=True):
        dashes = (ed.get("edge_type") == "manual")
        width = max(1, 2 if ed.get("weight", 1) >= 2 else 1)
        net.add_edge(u, v, width=width, physics=True, smooth=True, dashes=dashes)

    # JS click capture
    click_js = """
    <script type="text/javascript">
        var inputEl = window.parent.document.getElementById("clickedNode");
        if (!inputEl) {
            inputEl = window.parent.document.createElement("input");
            inputEl.type = "hidden";
            inputEl.id = "clickedNode";
            window.parent.document.body.appendChild(inputEl);
        }
        network.on("click", function(params) {
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                inputEl.value = nodeId;
                var ev = new Event("input", { bubbles: true });
                inputEl.dispatchEvent(ev);
            }
        });
    </script>
    """

    tmp_path = pathlib.Path(tempfile.NamedTemporaryFile(delete=False, suffix=".html").name)
    net.write_html(tmp_path.as_posix(), notebook=False, local=True)
    html_code = tmp_path.read_text(encoding="utf-8").replace("</body>", click_js + "</body>")
    components.html(html_code, height=750, scrolling=False)

    clicked_node = st.text_input("clicked", key="clickedNode", label_visibility="collapsed")

    st.markdown("---")

    # Session Passport
    if clicked_node:
        if clicked_node in df_show["session_id"].values:
            row = df_show[df_show["session_id"] == clicked_node].iloc[0]
            color = color_map.get(row["module"], "#888888")
            st.markdown(f"""
            <div style='border-left:6px solid {color};
                        background:#f9f9f9;
                        border-radius:8px;
                        padding:0.8em 1em;'>
            <h3 style='margin-top:0'>🪲 {row["title"]}</h3>
            <p><strong>Date:</strong> {row["date"]} &nbsp;|&nbsp;
               <strong>Module:</strong> {row["module"]} &nbsp;|&nbsp;
               <strong>Activity:</strong> {row["activity"]}</p>
            <p><strong>Instructor:</strong> {row["instructor"]}</p>
            <p><strong>Keywords:</strong> {row["keywords"]}</p>
            <p><strong>Notes:</strong><br>{row["notes"]}</p>
            """, unsafe_allow_html=True)
            links = [x.strip() for x in str(row["connect_with"]).split(",") if x.strip()]
            if links:
                st.markdown("<p><strong>Connected Sessions:</strong> " +
                            ", ".join(links) + "</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning("Node not found in dataset.")
    else:
        st.info("Click a node to view its Session Passport.")
