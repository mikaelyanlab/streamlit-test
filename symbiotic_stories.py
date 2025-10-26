# app.py — FIXED: Colors by module, query_params, passport on click
import io
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st

DEFAULT_COLUMNS = ["session_id","date","title","instructor","module","activity","keywords","notes","connect_with"]
SAMPLE_ROWS = [{"session_id":"W1-Tu","date":"2026-01-13","title":"Bootcamp","instructor":"You","module":"Systems","activity":"Lecture","keywords":"systems","notes":"Intro.","connect_with":""}]

def _clean_keywords(s): return [t.strip().lower() for t in str(s).replace(";",",").split(",") if t.strip()] if s else []
def _split_multi(s): return [t.strip() for t in str(s).replace(";",",").split(",") if t.strip()] if s else []

st.set_page_config(page_title="Network", layout="wide")
if "sessions" not in st.session_state: st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)

# Sidebar
st.sidebar.title("Course Session Network")
with st.sidebar.expander("Data IO"):
    buf = io.StringIO(); st.session_state.sessions.to_csv(buf, index=False)
    st.download_button("Download sessions.csv", buf.getvalue(), "sessions.csv")
    up = st.file_uploader("Upload sessions.csv", type="csv")
    if up: st.session_state.sessions = pd.read_csv(up, dtype=str).fillna(""); st.success("Loaded")
    if st.button("Reset to sample"): st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS); st.success("Reset")
with st.sidebar.expander("Network Settings"):
    min_shared = st.slider("Min shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)
    color_by = st.selectbox("Color nodes by", ["module", "instructor", "activity"])

tab_data, tab_graph = st.tabs(["Data / Edit", "Graph Explorer"])

with tab_data:
    with st.form("add_session"):
        c1, c2 = st.columns(2)
        sid = c1.text_input("Session ID")
        title = c2.text_input("Title")
        if st.form_submit_button("Add / Update") and sid:
            r = {k: "" for k in DEFAULT_COLUMNS}
            r["session_id"] = sid; r["title"] = title or "Untitled"
            df = st.session_state.sessions
            if sid in df["session_id"].values:
                idx = df[df["session_id"] == sid].index[0]
                for k in r: df.at[idx, k] = r[k]
            else:
                st.session_state.sessions = pd.concat([df, pd.DataFrame([r])], ignore_index=True)
            st.success(f"Saved {sid}")
    st.data_editor(st.session_state.sessions[DEFAULT_COLUMNS], hide_index=True, num_rows="dynamic", key="edit")

with tab_graph:
    df = st.session_state.sessions.copy()
    G = nx.Graph()
    for _, r in df.iterrows():
        G.add_node(r["session_id"], **r.to_dict())

    nodes = list(G.nodes())
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            a, b = nodes[i], nodes[j]
            if len(set(_clean_keywords(G.nodes[a]["keywords"])) & set(_clean_keywords(G.nodes[b]["keywords"]))) >= min_shared:
                G.add_edge(a, b)
    if include_manual:
        for n in nodes:
            for m in _split_multi(G.nodes[n]["connect_with"]):
                if m in nodes and m != n: G.add_edge(n, m)

    net = Network(height="700px", width="100%", directed=False, bgcolor="#ffffff", font_color="#000000")
    net.barnes_hut()

    # Color map
    palette = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"]
    values = sorted({G.nodes[n][color_by] for n in nodes})
    color_map = {v: palette[i % len(palette)] for i, v in enumerate(values)}

    for n in nodes:
        d = G.nodes[n]
        color = color_map.get(d[color_by], "#999999")
        net.add_node(n, label=n, color=color, size=30)
    for u, v in G.edges:
        net.add_edge(u, v, color="#cccccc")

    net.set_options('{"physics":{"barnesHut":{"springLength":150}},"interaction":{"navigationButtons":true}}')

    # JS click → update URL
    js = """
    <script>
    window.network.on("click", function(params) {
      if (params.nodes.length > 0) {
        const node = params.nodes[0];
        const url = new URL(window.parent.location);
        url.searchParams.set("node", node);
        window.parent.location = url;
      }
    });
    </script>
    """
    html = net.generate_html()
    html = html.replace("</body>", js + "</body>")

    st.components.v1.html(html, height=750)

    # Use st.query_params (fixes warning)
    qp = st.query_params
    selected = qp.get("node", [None])[0]
    if selected and selected in df["session_id"].values:
        d = df[df["session_id"] == selected].iloc[0]
        st.markdown("### Session Passport")
        st.markdown(f"#### {d['title']}")
        st.markdown(f"**Date:** {d['date']}\n**Instructor:** {d['instructor']}\n**Module:** {d['module']}\n**Activity:** {d['activity']}\n**Keywords:** {d['keywords']}\n\n**Notes:**\n{d['notes']}")
        if st.button("Clear selection"):
            st.query_params.clear()
    else:
        st.markdown("_Click a node to view its Session Passport._")
