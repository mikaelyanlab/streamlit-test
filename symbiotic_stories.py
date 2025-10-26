# app.py — Insect–Microbe Systems Course Network
# Formatted HTML tooltips + working node-click → passport
from __future__ import annotations
import io
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st
from typing import List

DEFAULT_COLUMNS = [
    "session_id","date","title","instructor","module",
    "activity","keywords","notes","connect_with"
]
SAMPLE_ROWS=[{
    "session_id":"W1-Tu","date":"2026-01-13",
    "title":"Systems Bootcamp – Insects as Systems within Systems",
    "instructor":"You","module":"Systems Bootcamp",
    "activity":"Interactive lecture",
    "keywords":"systems thinking, feedback loops",
    "notes":"Define balancing and reinforcing loops.",
    "connect_with":""
}]

def _clean_keywords(s:str)->List[str]:
    if pd.isna(s) or not str(s).strip(): return []
    toks=[t.strip().lower() for t in str(s).replace(";",",").split(",")]
    return sorted({t for t in toks if t})

def _split_multi(s:str)->List[str]:
    if pd.isna(s) or not str(s).strip(): return []
    return [t.strip() for t in str(s).replace(";",",").split(",") if t.strip()]

# -----------------------------------------------------------------
st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")

if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)

# ---------------- Sidebar ----------------
st.sidebar.title("Course Session Network")
with st.sidebar.expander("Data IO", expanded=True):
    buf = io.StringIO(); st.session_state.sessions.to_csv(buf, index=False)
    st.download_button("Download sessions.csv", buf.getvalue(), "sessions.csv","text/csv")

    up = st.file_uploader("Upload sessions.csv", type=["csv"])
    if up:
        df = pd.read_csv(up, dtype=str).fillna("")
        st.session_state.sessions = df
        st.success("CSV loaded.")
    if st.button("Reset sample"):
        st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)

with st.sidebar.expander("Network Settings", expanded=True):
    min_shared = st.slider("Min shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)

tab_data, tab_graph = st.tabs(["Data / Edit", "Graph Explorer"])

# ---------------- Data Tab ----------------
with tab_data:
    st.markdown("## Add / Edit Session")
    with st.form("add_session"):
        c1,c2,c3,c4 = st.columns(4)
        sid = c1.text_input("Session ID", placeholder="W2-Tu")
        date = c2.text_input("Date (YYYY-MM-DD)")
        title = c3.text_input("Title")
        instr = c4.text_input("Instructor","You")
        c5,c6,c7 = st.columns(3)
        module = c5.text_input("Module")
        activity = c6.text_input("Activity")
        kws = c7.text_input("Keywords (comma-separated)")
        notes = st.text_area("Notes")
        connect = st.text_input("Connect with (IDs comma-separated)")
        if st.form_submit_button("Add / Update") and sid.strip():
            r = {"session_id":sid.strip(),"date":date.strip(),"title":title.strip(),
                 "instructor":instr.strip(),"module":module.strip() or "Unassigned",
                 "activity":activity.strip(),"keywords":kws.strip(),
                 "notes":notes.strip(),"connect_with":connect.strip()}
            df = st.session_state.sessions
            if sid in df["session_id"].values:
                df.loc[df["session_id"]==sid, list(r.keys())] = pd.Series(r)
            else:
                st.session_state.sessions = pd.concat([df,pd.DataFrame([r])],ignore_index=True)
            st.success(f"Saved {sid}")

    st.markdown("### Inline Edit")
    edited = st.data_editor(st.session_state.sessions[DEFAULT_COLUMNS],
                            hide_index=True,use_container_width=True,num_rows="dynamic")
    if not edited.equals(st.session_state.sessions[DEFAULT_COLUMNS]):
        st.session_state.sessions = edited.copy()

# ---------------- Graph Tab ----------------
with tab_graph:
    df = st.session_state.sessions.copy()
    G = nx.Graph()
    for _,row in df.iterrows():
        kws=_clean_keywords(row["keywords"])
        node_data=row.to_dict(); node_data["keywords"]=kws
        G.add_node(row["session_id"],**node_data)
    nodes=list(G.nodes())
    for i in range(len(nodes)):
        for j in range(i+1,len(nodes)):
            a,b=nodes[i],nodes[j]
            shared=len(set(G.nodes[a]["keywords"])&set(G.nodes[b]["keywords"]))
            if shared>=min_shared: G.add_edge(a,b)
    if include_manual:
        for n in nodes:
            for m in _split_multi(G.nodes[n]["connect_with"]):
                if m in nodes and m!=n: G.add_edge(n,m)

    net=Network(height="700px",width="100%",directed=False,bgcolor="#fff",font_color="#222")
    net.barnes_hut()

    palette=["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b",
             "#e377c2","#7f7f7f","#bcbd22","#17becf"]
    mods=sorted({G.nodes[n]["module"] for n in nodes})
    color_map={m:palette[i%len(palette)] for i,m in enumerate(mods)}

    for n in G.nodes():
        d=G.nodes[n]
        hover=(f"<div style='font-family:sans-serif;font-size:13px;'>"
               f"<b>{d['title']}</b><br>"
               f"{d['date']} | {d['module']}<br>"
               f"{d['activity']}<br>"
               f"<i>{', '.join(d['keywords'])}</i></div>")
        net.add_node(
            n,label=n,title=hover,
            color=color_map.get(d["module"],"#999"),size=25,shape="dot"
        )
    for u,v in G.edges(): net.add_edge(u,v,color="#ccc")

    net.set_options("""
    {
      "interaction": {"hover": true, "navigationButtons": true},
      "physics": {
        "enabled": true,
        "stabilization": {"enabled": true, "iterations": 500},
        "barnesHut": {"springLength": 150}
      }
    }
    """)

    # ---- Custom JS: our own tooltip + working click → passport ----
    js = """
    const tooltip = document.createElement('div');
    tooltip.style.position = 'fixed';
    tooltip.style.background = '#ffffe6';
    tooltip.style.border = '1px solid #aaa';
    tooltip.style.padding = '6px 8px';
    tooltip.style.borderRadius = '4px';
    tooltip.style.boxShadow = '2px 2px 4px rgba(0,0,0,0.2)';
    tooltip.style.display = 'none';
    tooltip.style.pointerEvents = 'none';
    document.body.appendChild(tooltip);

    network.once("stabilizationIterationsDone", function () {
        network.setOptions({ physics: false });
    });

    network.on("hoverNode", function(params) {
        const nodeId = params.node;
        const node = network.body.data.nodes.get(nodeId);
        if (node && node.title) {
            tooltip.innerHTML = node.title;
            tooltip.style.display = 'block';
        }
    });
    network.on("blurNode", function() {
        tooltip.style.display = 'none';
    });
    network.on("dragging", function(){ tooltip.style.display = 'none'; });
    network.on("hoverEdge", function(){ tooltip.style.display = 'none'; });

    document.addEventListener('mousemove', function(e){
        tooltip.style.left = (e.clientX + 12) + 'px';
        tooltip.style.top = (e.clientY + 12) + 'px';
    });

    network.on("selectNode", function(p) {
        const id = p.nodes[0];
        if (id) {
            localStorage.setItem('clicked', id);
            window.parent.postMessage({ type: 'nodeClick', id: id }, "*");
        }
    });
    """
    net.save_graph("graph.html")
    html=open("graph.html","r",encoding="utf-8").read().replace("</script>",js+"</script>")
    st.components.v1.html(html,height=750)

    # --- handle clicks from iframe ---
    clicked_id = None
    try:
        clicked_id = st.session_state.get("clicked")
    except: pass

    st.markdown("---")
    st.markdown("### Session Passport")

    st.markdown("""
        <script>
        window.addEventListener("message", (e)=>{
            if(e.data && e.data.type==="nodeClick"){
                const id=e.data.id;
                window.localStorage.setItem('clicked', id);
                window.location.reload();
            }
        });
        </script>
    """, unsafe_allow_html=True)

    # Get node id stored by JS
    query = st.query_params
    clicked_id = query.get("clicked") or None
    if clicked_id:
        clicked_id = clicked_id[0] if isinstance(clicked_id, list) else clicked_id

    selected = clicked_id or st.selectbox(
        "Select a session:",
        sorted(df["session_id"]),
        format_func=lambda x: f"{x} — {df.loc[df['session_id']==x,'title'].values[0]}"
    )

    if selected in df["session_id"].values:
        d = df.loc[df["session_id"]==selected].iloc[0]
        st.markdown(f"#### {d['title']}")
        st.markdown(
            f"**Date:** {d['date']}  \n"
            f"**Instructor:** {d['instructor']}  \n"
            f"**Module:** {d['module']}  \n"
            f"**Activity:** {d['activity']}  \n"
            f"**Keywords:** {d['keywords']}  \n\n"
            f"**Notes:**  \n{d['notes']}"
        )
