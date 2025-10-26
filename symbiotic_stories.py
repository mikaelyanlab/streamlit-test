# app.py — Fixed: Instant passport on click (no physics conflict, no iframe issues)
from __future__ import annotations
import io
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st

# ------------------ Utils ------------------
DEFAULT_COLUMNS = ["session_id","date","title","instructor","module","activity","keywords","notes","connect_with"]
SAMPLE_ROWS = [{"session_id":"W1-Tu","date":"2026-01-13","title":"Systems Bootcamp – Insects as Systems within Systems",
                "instructor":"You","module":"Systems Bootcamp","activity":"Interactive lecture",
                "keywords":"systems thinking, feedback loops","notes":"Define balancing and reinforcing loops.","connect_with":""}]

def _clean_keywords(s:str):
    if pd.isna(s) or not s: return []
    return sorted({t.strip().lower() for t in str(s).replace(";",",").split(",") if t.strip()})

def _split_multi(s:str):
    if pd.isna(s) or not s: return []
    return [t.strip() for t in str(s).replace(";",",").split(",") if t.strip()]

# ------------------ Setup ------------------
st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")
if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)
if "selected_node" not in st.session_state:
    st.session_state.selected_node = None

# ------------------ Sidebar ------------------
st.sidebar.title("Course Session Network")
with st.sidebar.expander("Data IO", True):
    buf = io.StringIO(); st.session_state.sessions.to_csv(buf, index=False)
    st.download_button("Download sessions.csv", buf.getvalue(), "sessions.csv")
    up = st.file_uploader("Upload sessions.csv", type=["csv"])
    if up: st.session_state.sessions = pd.read_csv(up, dtype=str).fillna(""); st.success("Loaded")
    if st.button("Reset sample"): st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS); st.success("Reset")
with st.sidebar.expander("Network Settings", True):
    min_shared = st.slider("Min shared keywords",1,5,1)
    include_manual = st.checkbox("Manual connects",True)

# ------------------ Tabs ------------------
tab_data, tab_graph = st.tabs(["Data / Edit","Graph Explorer"])

# ------------------ Data Tab ------------------
with tab_data:
    with st.form("add_session"):
        c1,c2,c3,c4 = st.columns(4)
        sid = c1.text_input("ID",placeholder="W2-Tu")
        date = c2.text_input("Date")
        title = c3.text_input("Title")
        instr = c4.text_input("Instructor","You")
        c5,c6,c7 = st.columns(3)
        module = c5.text_input("Module")
        activity = c6.text_input("Activity")
        kws = c7.text_input("Keywords")
        notes = st.text_area("Notes")
        connect = st.text_input("Connect with")
        if st.form_submit_button("Add / Update") and sid:
            r = {k:v.strip() if isinstance(v,str) else v for k,v in {
                "session_id":sid,"date":date,"title":title,"instructor":instr,
                "module":module or "Unassigned","activity":activity,
                "keywords":kws,"notes":notes,"connect_with":connect}.items()}
            df = st.session_state.sessions
            if sid in df["session_id"].values:
                idx = df[df["session_id"]==sid].index[0]
                for k,v in r.items(): df.at[idx,k]=v
            else:
                st.session_state.sessions = pd.concat([df,pd.DataFrame([r])],ignore_index=True)
            st.success(f"Saved {sid}")
    edited = st.data_editor(st.session_state.sessions[DEFAULT_COLUMNS],hide_index=True,use_container_width=True,num_rows="dynamic",key="edit")
    if not edited.equals(st.session_state.sessions[DEFAULT_COLUMNS]):
        st.session_state.sessions = edited.copy()

# ------------------ Graph Tab ------------------
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

    net = Network(height="700px",width="100%",directed=False,bgcolor="#ffffff",font_color="#222222")
    net.barnes_hut()
    palette = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"]
    mods = sorted({G.nodes[n]["module"] for n in nodes})
    color_map = {m:palette[i%len(palette)] for i,m in enumerate(mods)}

    for n in nodes:
        d = G.nodes[n]
        net.add_node(n,label=n,title="",color=color_map.get(d["module"],"#999"),size=25)
    for u,v in G.edges: net.add_edge(u,v,color="#cccccc")

    net.set_options("""{
      "physics":{"barnesHut":{"springLength":150}},"interaction":{"navigationButtons":true}
    }""")

    # Inject click → update Streamlit state via URL
    net_html = net.generate_html()
    js = """
    <script>
    document.addEventListener("DOMContentLoaded", () => {
      const network = window.network;
      network.on("click", (p) => {
        if (p.nodes.length) {
          const node = p.nodes[0];
          const url = new URL(location.href);
          url.searchParams.set("node", node);
          history.replaceState(null, "", url);
          location.reload();
        }
      });
    });
    </script>
    """
    net_html = net_html.replace("</body>", js + "</body>")

    st.components.v1.html(net_html, height=750)

    # Detect selection
    qp = st.experimental_get_query_params()
    if "node" in qp:
        node = qp["node"][0]
        if node in df["session_id"].values:
            st.session_state.selected_node = node
        st.experimental_set_query_params()  # clear

    sel = st.session_state.selected_node
    if sel and sel in df["session_id"].values:
        d = df[df["session_id"]==sel].iloc[0]
        st.markdown("### Session Passport")
        st.markdown(f"#### {d['title']}")
        st.markdown(f"**Date:** {d['date']}\n**Instructor:** {d['instructor']}\n**Module:** {d['module']}\n**Activity:** {d['activity']}\n**Keywords:** {d['keywords']}\n\n**Notes:**\n{d['notes']}")
    else:
        st.markdown("_Click a node to view its Session Passport._")
