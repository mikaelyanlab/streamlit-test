import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import tempfile, pathlib, json, os

# -------------------------------------------
# Setup
# -------------------------------------------
st.set_page_config(page_title="Clickable Course Network", layout="wide")
st.title("🪲 Insect–Microbe Systems — Clickable Course Network")

CSV_PATH = "/mnt/data/course_cleaned.csv"
CLICK_PATH = pathlib.Path(tempfile.gettempdir()) / "clicked_node.json"

DEFAULT_COLUMNS = [
    "session_id","date","title","instructor","module",
    "activity","keywords","notes","connect_with"
]

# -------------------------------------------
# Helpers
# -------------------------------------------
def _clean_keywords(s):
    if pd.isna(s) or not str(s).strip():
        return []
    return [t.strip().lower() for t in str(s).replace(";",",").split(",") if t.strip()]

def _split_multi(s):
    if pd.isna(s) or not str(s).strip():
        return []
    return [t.strip() for t in str(s).replace(";",",").split(",") if t.strip()]

# -------------------------------------------
# Load CSV
# -------------------------------------------
try:
    df = pd.read_csv(CSV_PATH)
    st.success(f"Loaded {len(df)} sessions from {CSV_PATH}")
except Exception as e:
    st.error(f"Failed to load default CSV: {e}")
    st.stop()

# -------------------------------------------
# Build networkx graph
# -------------------------------------------
G = nx.Graph()
for _, r in df.iterrows():
    sid = str(r["session_id"]).strip()
    if not sid:
        continue
    G.add_node(
        sid,
        title=r["title"],
        module=r["module"],
        date=r["date"],
        activity=r["activity"],
        instructor=r["instructor"],
        keywords=_clean_keywords(r["keywords"]),
        notes=r["notes"],
    )

# Shared keyword edges
for i, a in enumerate(G.nodes()):
    for j, b in enumerate(list(G.nodes())[i+1:]):
        shared = len(set(G.nodes[a]["keywords"]) & set(G.nodes[b]["keywords"]))
        if shared >= 1:
            G.add_edge(a, b)

# Manual connects
for _, r in df.iterrows():
    for m in _split_multi(r.get("connect_with", "")):
        if m in G.nodes and m != r["session_id"]:
            G.add_edge(r["session_id"], m)

# -------------------------------------------
# PyVis rendering
# -------------------------------------------
net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="#111")
net.force_atlas_2based(gravity=-50, central_gravity=0.02, spring_length=120)

palette = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd",
           "#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"]
modules = sorted({G.nodes[n]["module"] for n in G.nodes})
color_map = {m: palette[i % len(palette)] for i, m in enumerate(modules)}

for n in G.nodes():
    d = G.nodes[n]
    net.add_node(
        n,
        label=n,
        color=color_map.get(d["module"], "#777"),
        title=f"{d['title']}<br><b>Module:</b> {d['module']}",
        size=18,
    )
for u, v in G.edges():
    net.add_edge(u, v, width=1)

# Inject JS click listener that writes clicked node to file
html_path = pathlib.Path(tempfile.NamedTemporaryFile(delete=False, suffix=".html").name)
net.write_html(html_path.as_posix(), notebook=False, local=True)
with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

click_js = f"""
<script>
const path = "{CLICK_PATH.as_posix().replace('\\','/')}";
network.on("selectNode", function(params) {{
  if(params.nodes.length > 0){{
    const nodeId = params.nodes[0];
    // Write to file via Streamlit-provided endpoint
    fetch("streamlit-file://" + path + "?data=" + encodeURIComponent(nodeId))
    .catch(err => console.error(err));
  }}
}});
</script>
"""
html = html.replace("</body>", click_js + "</body>")

# -------------------------------------------
# Layout
# -------------------------------------------
left, right = st.columns([3, 2])
with left:
    st.components.v1.html(html, height=760, scrolling=False)

# -------------------------------------------
# Check clicked node (poll the temp file)
# -------------------------------------------
clicked_node = None
if CLICK_PATH.exists():
    try:
        with open(CLICK_PATH) as f:
            node_id = f.read().strip()
            if node_id:
                clicked_node = node_id
    except Exception:
        pass

# -------------------------------------------
# Passport panel
# -------------------------------------------
with right:
    st.markdown("### 📘 Session Passport")
    if clicked_node and clicked_node in df["session_id"].values:
        r = df[df["session_id"] == clicked_node].iloc[0]
        st.markdown(f"""
        <div style='border-left:6px solid #1f77b4;
                    background:#f9f9f9;border-radius:8px;
                    padding:0.8em 1em;'>
        <h3>{r["title"]}</h3>
        <p><b>Date:</b> {r["date"]}<br>
        <b>Module:</b> {r["module"]}<br>
        <b>Activity:</b> {r["activity"]}<br>
        <b>Instructor:</b> {r["instructor"]}</p>
        <p><b>Keywords:</b> {r["keywords"]}</p>
        <p><b>Notes:</b><br>{r["notes"]}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Click a node in the network to view its details.")
