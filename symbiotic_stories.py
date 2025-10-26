# app.py — Insect–Microbe Systems Course Network
# -------------------------------------------------------------------
from __future__ import annotations
import io, csv, pathlib, tempfile
import pandas as pd
import networkx as nx
import streamlit as st
import streamlit.components.v1 as components
from typing import List
from pyvis.network import Network

# ============================ Utilities ============================
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

# ============================ App setup ============================
st.set_page_config(page_title="Insect–Microbe Systems",layout="wide")
if "sessions" not in st.session_state:
    st.session_state.sessions=pd.DataFrame(SAMPLE_ROWS,columns=DEFAULT_COLUMNS)
if "selected_node" not in st.session_state:
    st.session_state.selected_node = ""

# ============================ Sidebar ==============================
st.sidebar.title("Course Session Network")
with st.sidebar.expander("Data IO",expanded=True):
    buf=io.StringIO(); st.session_state.sessions.to_csv(buf,index=False)
    st.download_button("Download sessions.csv",buf.getvalue(),"sessions.csv","text/csv")
    up=st.file_uploader("Upload sessions.csv",type=["csv"])
    if up is not None:
        try:
            raw=up.read().decode("utf-8",errors="replace")
            raw=(raw.replace("\r\n","\n").replace("\r","\n")
                 .replace("“",'"').replace("”",'"')
                 .replace("‘","'").replace("’","'")
                 .replace("\u00A0"," "))
            df=pd.read_csv(io.StringIO(raw), dtype=str)
            missing = set(DEFAULT_COLUMNS) - set(df.columns)
            if missing: raise ValueError(f"Missing columns: {missing}")
            st.session_state.sessions=df[DEFAULT_COLUMNS].fillna("")
            st.success("CSV loaded.")
        except Exception as e:
            st.error(f"Upload failed: {e}")
    if st.button("Reset to sample"):
        st.session_state.sessions=pd.DataFrame(SAMPLE_ROWS,columns=DEFAULT_COLUMNS)
        st.success("Reset.")
with st.sidebar.expander("Network Settings",expanded=True):
    min_shared=st.slider("Min shared keywords",1,5,1)
    include_manual=st.checkbox("Include manual connects",True)
    size_min,size_max=st.slider("Node size range",5,60,(14,38))

# ============================ Tabs ================================
tab_data,tab_graph=st.tabs(["Data / Edit","Graph Explorer"])

# ============================ Data Tab ============================
with tab_data:
    st.markdown("## Add / Edit Session")
    with st.form("add_session"):
        c1,c2,c3,c4=st.columns(4)
        sid=c1.text_input("Session ID",placeholder="W2-Tu")
        date=c2.text_input("Date (YYYY-MM-DD)")
        title=c3.text_input("Title")
        instr=c4.text_input("Instructor","You")
        c5,c6,c7=st.columns(3)
        module=c5.text_input("Module")
        activity=c6.text_input("Activity")
        kws=c7.text_input("Keywords (comma-separated)")
        notes=st.text_area("Notes")
        connect=st.text_input("Connect with (IDs comma-separated)")
        if st.form_submit_button("Add / Update") and sid.strip():
            r={"session_id":sid.strip(),"date":date.strip(),"title":title.strip(),
               "instructor":instr.strip(),"module":module.strip() or "Unassigned",
               "activity":activity.strip(),"keywords":kws.strip(),
               "notes":notes.strip(),"connect_with":connect.strip()}
            df=st.session_state.sessions
            if sid in df["session_id"].values:
                idx=df[df["session_id"]==sid].index[0]
                for k,v in r.items(): df.at[idx,k]=v
            else:
                st.session_state.sessions=pd.concat([df,pd.DataFrame([r])],ignore_index=True)
            st.success(f"Saved {sid}")
    st.markdown("### Inline Table Edit")
    edited=st.data_editor(st.session_state.sessions,hide_index=True,use_container_width=True,num_rows="dynamic",key="table_edit")
    if not edited.equals(st.session_state.sessions):
        st.session_state.sessions=edited.copy()

# ============================ Graph Tab ===========================
with tab_graph:
    st.markdown("## Interactive Course Graph")
    df=st.session_state.sessions.copy()
    G=nx.Graph()
    for _,row in df.iterrows():
        kws=_clean_keywords(row["keywords"])
        node_data = row.to_dict()
        node_data["keywords"] = kws
        G.add_node(row["session_id"], **node_data)
    nodes=list(G.nodes())
    for i in range(len(nodes)):
        for j in range(i+1,len(nodes)):
            a,b=nodes[i],nodes[j]
            shared=len(set(G.nodes[a]["keywords"])&set(G.nodes[b]["keywords"]))
            if shared>=min_shared:
                G.add_edge(a,b)
    if include_manual:
        for n in nodes:
            for m in _split_multi(G.nodes[n]["connect_with"]):
                if m in nodes and m!=n:
                    G.add_edge(n,m)
    mods=sorted({G.nodes[n]["module"] for n in nodes})
    PALETTE=["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"]
    color_map={m:PALETTE[i%len(PALETTE)] for i,m in enumerate(mods)}
    net=Network(height="700px",width="100%",bgcolor="#fff",font_color="#111")
    net.force_atlas_2based(gravity=-50,central_gravity=0.02,spring_length=120)
    for n in nodes:
        d=G.nodes[n]
        net.add_node(n,label=n,color=color_map.get(d["module"],"#777"),
                     size=(size_min+size_max)/2, title=d["title"])
    for u,v in G.edges():
        net.add_edge(u,v,width=1)
    # ----------- click→Streamlit bridge -----------
    html_file = tempfile.NamedTemporaryFile(delete=False,suffix=".html",mode="w+",encoding="utf-8")
    net.write_html(html_file.name)
    html_file.seek(0)
    html = html_file.read()
    html_file.close()
    html = html.replace(
        "</body>",
        """
        <script>
        network.on("selectNode", function(params) {
            if (params.nodes.length > 0) {
                const nodeId = params.nodes[0];
                window.parent.postMessage({clickedNode: nodeId}, "*");
            }
        });
        </script>
        </body>
        """
    )
    components.html(html, height=750, scrolling=False)
    st.markdown("""
    <script>
    window.addEventListener("message", function(e) {
        if (e.data.clickedNode) {
            const input = document.querySelector('input[data-testid="stTextInput"]');
            if (input) {
                input.value = e.data.clickedNode;
                input.dispatchEvent(new Event("input", {bubbles: true}));
            }
        }
    });
    </script>
    """, unsafe_allow_html=True)
    clicked = st.text_input("", key="clicked_node", label_visibility="collapsed")
    if clicked:
        st.session_state.selected_node = clicked
        st.rerun()
    st.markdown("---")
    node = st.session_state.selected_node
    if node and node in df["session_id"].values:
        r = df[df["session_id"] == node].iloc[0]
        color = color_map.get(r["module"], "#999")
        st.markdown(f"""
        <div style='border-left:6px solid {color};background:#f9f9f9;border-radius:8px;padding:1em;'>
        <h3>🪲 {r['title']}</h3>
        <p><strong>Date:</strong> {r['date']} | <strong>Module:</strong> {r['module']} | <strong>Activity:</strong> {r['activity']}</p>
        <p><strong>Instructor:</strong> {r['instructor']}</p>
        <p><strong>Keywords:</strong> {r['keywords']}</p>
        <p><strong>Notes:</strong><br>{r['notes'].replace('\n', '<br>')}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Click a node to view its Session Passport.")
