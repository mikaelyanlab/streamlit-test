# app.py — WORKING: Click node → passport (PyVis + Streamlit.msg bridge)
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
with st.sidebar.expander("Data"):
    buf = io.StringIO(); st.session_state.sessions.to_csv(buf, index=False)
    st.download_button("Download", buf.getvalue(), "sessions.csv")
    up = st.file_uploader("Upload", type="csv")
    if up: st.session_state.sessions = pd.read_csv(up, dtype=str).fillna(""); st.success("Loaded")
    if st.button("Reset"): st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)
with st.sidebar.expander("Settings"):
    min_shared = st.slider("Min keywords",1,5,1)
    include_manual = st.checkbox("Manual",True)

tab_data, tab_graph = st.tabs(["Data","Graph"])

with tab_data:
    with st.form("add"):
        sid = st.text_input("ID")
        title = st.text_input("Title")
        if st.form_submit_button("Add") and sid:
            r = {k:"" for k in DEFAULT_COLUMNS}; r["session_id"]=sid; r["title"]=title
            st.session_state.sessions = pd.concat([st.session_state.sessions, pd.DataFrame([r])], ignore_index=True)
    st.data_editor(st.session_state.sessions[DEFAULT_COLUMNS], hide_index=True, num_rows="dynamic")

with tab_graph:
    df = st.session_state.sessions.copy()
    G = nx.Graph()
    for _, r in df.iterrows():
        G.add_node(r["session_id"], **r.to_dict())

    nodes = list(G.nodes())
    for i in range(len(nodes)):
        for j in range(i+1,len(nodes)):
            a,b = nodes[i],nodes[j]
            if len(set(_clean_keywords(G.nodes[a]["keywords"])) & set(_clean_keywords(G.nodes[b]["keywords"]))) >= min_shared:
                G.add_edge(a,b)
    if include_manual:
        for n in nodes:
            for m in _split_multi(G.nodes[n]["connect_with"]):
                if m in nodes and m != n: G.add_edge(n,m)

    net = Network("700px","100%",directed=False)
    net.barnes_hut()
    for n in nodes:
        net.add_node(n, label=n, color="#1f77b4", size=30)
    for u,v in G.edges: net.add_edge(u,v,color="#ccc")

    net.set_options('{"physics":{"barnesHut":{"springLength":150}}}')

    # Inject bridge
    js = """
    <script>
    const net = window.network;
    net.on("click", (p) => {
      if (p.nodes.length) {
        Streamlit.setComponentValue(p.nodes[0]);
      }
    });
    </script>
    """
    html = net.generate_html()
    html = html.replace("</body>", js + "</body>")

    # Custom component
    component = st.components.v1.html(html, height=700, key="pyvis")
    selected = component  # Direct from JS

    if selected and selected in df["session_id"].values:
        d = df[df["session_id"] == selected].iloc[0]
        st.markdown("### Session Passport")
        st.markdown(f"#### {d['title']}")
        st.markdown(f"**Date:** {d['date']}\n**Instructor:** {d['instructor']}\n**Module:** {d['module']}\n**Keywords:** {d['keywords']}\n**Notes:** {d['notes']}")
    else:
        st.markdown("_Click a node to view its Session Passport._")
