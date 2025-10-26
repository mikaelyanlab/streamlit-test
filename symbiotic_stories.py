# app.py — Working: Click node → passport below (physics on, instant)
from __future__ import annotations
import io
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st

DEFAULT_COLUMNS = ["session_id","date","title","instructor","module","activity","keywords","notes","connect_with"]
SAMPLE_ROWS = [{"session_id":"W1-Tu","date":"2026-01-13","title":"Systems Bootcamp","instructor":"You","module":"Bootcamp","activity":"Lecture","keywords":"systems, loops","notes":"Intro.","connect_with":""}]

def _clean_keywords(s:str):
    if pd.isna(s) or not s: return []
    return sorted({t.strip().lower() for t in str(s).replace(";",",").split(",") if t.strip()})

def _split_multi(s:str):
    if pd.isna(s) or not s: return []
    return [t.strip() for t in str(s).replace(";",",").split(",") if t.strip()]

st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")
if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)
if "selected_node" not in st.session_state:
    st.session_state.selected_node = None

st.sidebar.title("Network")
with st.sidebar.expander("IO", True):
    buf = io.StringIO(); st.session_state.sessions.to_csv(buf, index=False)
    st.download_button("Download", buf.getvalue(), "sessions.csv")
    up = st.file_uploader("Upload", type=["csv"])
    if up: st.session_state.sessions = pd.read_csv(up, dtype=str).fillna(""); st.success("Loaded")
    if st.button("Reset"): st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS); st.success("Reset")
with st.sidebar.expander("Settings", True):
    min_shared = st.slider("Min keywords",1,5,1)
    include_manual = st.checkbox("Manual",True)

tab_data, tab_graph = st.tabs(["Data","Graph"])

with tab_data:
    with st.form("add"):
        c1,c2 = st.columns(2)
        sid = c1.text_input("ID")
        title = c2.text_input("Title")
        if st.form_submit_button("Add") and sid:
            r = {"session_id":sid,"title":title or "Untitled","date":"","instructor":"","module":"","activity":"","keywords":"","notes":"","connect_with":""}
            st.session_state.sessions = pd.concat([st.session_state.sessions, pd.DataFrame([r])], ignore_index=True)
    st.data_editor(st.session_state.sessions[DEFAULT_COLUMNS], hide_index=True, num_rows="dynamic", key="edit")

with tab_graph:
    df = st.session_state.sessions.copy()
    G = nx.Graph()
    for _,r in df.iterrows():
        G.add_node(r["session_id"], **{**r.to_dict(), "keywords":_clean_keywords(r["keywords"])})

    nodes = list(G.nodes)
    for i in range(len(nodes)):
        for j in range(i+1,len(nodes)):
            a,b = nodes[i],nodes[j]
            if len(set(G.nodes[a]["keywords"]) & set(G.nodes[b]["keywords"])) >= min_shared:
                G.add_edge(a,b)
    if include_manual:
        for n in nodes:
            for m in _split_multi(G.nodes[n]["connect_with"]):
                if m in nodes and m!=n: G.add_edge(n,m)

    net = Network("700px","100%",directed=False,bgcolor="#ffffff")
    net.barnes_hut()
    for n in nodes:
        d = G.nodes[n]
        net.add_node(n,label=n,color="#1f77b4",size=25)
    for u,v in G.edges: net.add_edge(u,v,color="#cccccc")

    net.set_options('{"physics":{"barnesHut":{"springLength":150}},"interaction":{"selectConnectedEdges":false}}')

    # Click handler
    js = """
    <script>
    window.network.on("click", function(p) {
      if (p.nodes.length) {
        const node = p.nodes[0];
        const url = new URL(location.href);
        url.searchParams.set("node", node);
        history.replaceState(null, "", url);
        window.dispatchEvent(new HashChangeEvent("hashchange"));
      }
    });
    </script>
    """
    html = net.generate_html()
    html = html.replace("</body>", js + "</body>")

    # Use iframe with hash change to trigger rerun
    iframe_id = "net_iframe"
    st.components.v1.html(f'<iframe id="{iframe_id}" srcdoc={repr(html)} style="width:100%;height:700px;border:none;"></iframe>', height=750)

    # Trigger rerun on hash change
    st.write("""
    <script>
    window.addEventListener('hashchange', () => parent.location.reload());
    </script>
    """, unsafe_allow_html=True)

    # Read selection
    qp = st.experimental_get_query_params()
    if "node" in qp:
        node = qp["node"][0]
        if node in df["session_id"].values:
            st.session_state.selected_node = node
        st.experimental_set_query_params()

    sel = st.session_state.selected_node
    if sel and sel in df["session_id"].values:
        d = df[df["session_id"]==sel].iloc[0]
        st.markdown("### Passport")
        st.markdown(f"**{d['title']}**")
        st.write(d.to_dict())
    else:
        st.markdown("_Click node to view passport._")
