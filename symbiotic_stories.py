import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import tempfile, os, pathlib

st.set_page_config(page_title="Insect–Microbe Systems — Clickable Network", layout="wide")
st.title("🪲 Insect–Microbe Systems — Clickable Course Network")

# ---------------------------------------------------------------------
# Load CSV
# ---------------------------------------------------------------------
CSV_FILE = "course_cleaned.csv"
DEFAULT_COLUMNS = [
    "session_id","date","title","instructor","module",
    "activity","keywords","notes","connect_with"
]

def _clean_keywords(s):
    if pd.isna(s) or not str(s).strip():
        return []
    return [t.strip().lower() for t in str(s).replace(";",",").split(",") if t.strip()]

def _split_multi(s):
    if pd.isna(s) or not str(s).strip():
        return []
    return [t.strip() for t in str(s).replace(";",",").split(",") if t.strip()]

# ---- Step 1: Check if file exists ----
if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    st.success(f"✅ Loaded {len(df)} sessions from '{CSV_FILE}'.")
else:
    st.warning("No local 'course_cleaned.csv' found. Please upload your dataset below:")
    uploaded = st.file_uploader("Upload your course CSV", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
        st.success(f"✅ Uploaded {len(df)} sessions.")
    else:
        st.stop()

# ---------------------------------------------------------------------
# Build graph
# ---------------------------------------------------------------------
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

# ---------------------------------------------------------------------
# PyVis rendering
# ---------------------------------------------------------------------
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

# Write PyVis HTML
tmp_html = pathlib.Path(tempfile.NamedTemporaryFile(delete=False, suffix=".html").name)
net.write_html(tmp_html.as_posix(), notebook=False, local=True)
with open(tmp_html, "r", encoding="utf-8") as f:
    html = f.read()

# Add JS bridge (this works locally)
bridge = """
<script>
function reportNode(id){
  const url = new URL(window.location);
  url.searchParams.set("node", id);
  window.location.href = url.toString();
}
network.on("selectNode", function(params){
  if(params.nodes.length > 0){
    reportNode(params.nodes[0]);
  }
});
</script>
"""
html = html.replace("</body>", bridge + "</body>")

# ---------------------------------------------------------------------
# Layout: Left (graph) | Right (passport)
# ---------------------------------------------------------------------
left, right = st.columns([3,2])
with left:
    st.components.v1.html(html, height=760, scrolling=False)

# Determine selected node
node = st.query_params.get("node", [None])[0] if hasattr(st, "query_params") else None
if not node:
    query = st.experimental_get_query_params()
    node = query.get("node", [None])[0]

with right:
    st.markdown("### 📘 Session Passport")
    if node and node in df["session_id"].values:
        r = df[df["session_id"] == node].iloc[0]
        st.markdown(f"""
        <div style='border-left:6px solid #1f77b4;background:#f9f9f9;
                    border-radius:8px;padding:0.8em 1em;'>
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
