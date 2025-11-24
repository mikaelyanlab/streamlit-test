# symbiotic_stories.py — FINAL FULLY PATCHED VERSION

from __future__ import annotations
import io
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st
from typing import List

# ------------------------------------------------------
# FIX 1: DEFAULT_COLUMNS updated to include "theory"
# ------------------------------------------------------
DEFAULT_COLUMNS = [
    "session_id","date","title","instructor","module",
    "activity","keywords","notes","connect_with","theory"
]

SAMPLE_ROWS=[{
    "session_id":"W1-Tu","date":"2026-01-13",
    "title":"Systems Bootcamp – Insects as Systems within Systems",
    "instructor":"You","module":"Systems Bootcamp",
    "activity":"Interactive lecture",
    "keywords":"systems thinking, feedback loops",
    "notes":"Define balancing and reinforcing loops.",
    "connect_with":"",
    "theory":"Ashby cybernetics; Meadows feedback"
}]

# ------------------------------------------------------
# FIX 2: Mojibake cleanup table
# ------------------------------------------------------
def clean_mojibake(s: str) -> str:
    if not isinstance(s, str): 
        return s
    rep = {
        "â€™":"’","â€˜":"‘","â€œ":"“","â€":"”",
        "â€“":"–","â€”":"—",
        "Ã©":"é","Ã¨":"è","Ã ":"à","Ã¡":"á","Ã³":"ó",
        "â€¦":"…"
    }
    for k,v in rep.items():
        s = s.replace(k,v)
    return s

def fix_df_unicode(df: pd.DataFrame) -> pd.DataFrame:
    return df.applymap(clean_mojibake)

# ------------------------------------------------------
# Helpers
# ------------------------------------------------------
def _clean_keywords(s:str)->List[str]:
    if pd.isna(s) or not str(s).strip(): return []
    toks=[t.strip().lower() for t in str(s).replace(";",",").split(",")]
    return sorted({t for t in toks if t})

def _split_multi(s:str)->List[str]:
    if pd.isna(s) or not str(s).strip(): return []
    return [t.strip() for t in str(s).replace(";",",").split(",") if t.strip()]

# ------------------------------------------------------
# Streamlit Setup
# ------------------------------------------------------
st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")

if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)

# ------------------------------------------------------
# Sidebar
# ------------------------------------------------------
st.sidebar.title("Course Session Network")

with st.sidebar.expander("Data IO", expanded=True):

    # Download current CSV
    buf = io.StringIO()
    st.session_state.sessions.to_csv(buf, index=False)
    st.download_button("Download sessions.csv", buf.getvalue(), "sessions.csv","text/csv")

    # Upload new csv with robust encoding fallback
    up = st.file_uploader("Upload sessions.csv", type=["csv"])
    if up:
        try:
            df = pd.read_csv(up, dtype=str, encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(up, dtype=str, encoding="latin1")

        df = df.fillna("")
        df = fix_df_unicode(df)

        # Ensure all expected columns exist
        for col in DEFAULT_COLUMNS:
            if col not in df.columns:
                df[col] = ""

        # Keep only expected columns (extra cols ignored)
        df = df[DEFAULT_COLUMNS]

        st.session_state.sessions = df
        st.success("CSV loaded cleanly.")

    # Reset button
    if st.button("Reset sample"):
        st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)

with st.sidebar.expander("Network Settings", expanded=True):
    min_shared = st.slider("Min shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)

# ------------------------------------------------------
# Tabs
# ------------------------------------------------------
tab_data, tab_graph = st.tabs(["Data / Edit", "Graph Explorer"])

# ------------------------------------------------------
# DATA TAB
# ------------------------------------------------------
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
        theory = st.text_area("Theory (full sentences)")

        connect = st.text_input("Connect with (IDs comma-separated)")

        if st.form_submit_button("Add / Update") and sid.strip():
            r = {
                "session_id":sid.strip(),
                "date":date.strip(),
                "title":title.strip(),
                "instructor":instr.strip(),
                "module":module.strip() or "Unassigned",
                "activity":activity.strip(),
                "keywords":kws.strip(),
                "notes":notes.strip(),
                "connect_with":connect.strip(),
                "theory":theory.strip()
            }

            df = st.session_state.sessions
            if sid in df["session_id"].values:
                df.loc[df["session_id"]==sid, list(r.keys())] = pd.Series(r)
            else:
                st.session_state.sessions = pd.concat([df,pd.DataFrame([r])],ignore_index=True)

            st.success(f"Saved {sid}")

    st.markdown("### Inline Edit")
    edited = st.data_editor(
        st.session_state.sessions[DEFAULT_COLUMNS],
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic"
    )

    if not edited.equals(st.session_state.sessions[DEFAULT_COLUMNS]):
        st.session_state.sessions = edited.copy()

# ------------------------------------------------------
# GRAPH TAB
# ------------------------------------------------------
with tab_graph:
    df = st.session_state.sessions.copy()

    # Build graph
    G = nx.Graph()
    for _,row in df.iterrows():
        kws=_clean_keywords(row["keywords"])
        node_data=row.to_dict()
        node_data["keywords"]=kws
        G.add_node(row["session_id"],**node_data)

    nodes=list(G.nodes())

    # Keyword-based edges
    for i in range(len(nodes)):
        for j in range(i+1,len(nodes)):
            a,b=nodes[i],nodes[j]
            shared=len(set(G.nodes[a]["keywords"])&set(G.nodes[b]["keywords"]))
            if shared>=min_shared:
                G.add_edge(a,b)

    # Manual connections
    if include_manual:
        for n in nodes:
            for m in _split_multi(G.nodes[n]["connect_with"]):
                if m in nodes and m!=n:
                    G.add_edge(n,m)

    # PyVis network
    net=Network(height="700px",width="100%",directed=False,bgcolor="#fff",font_color="#222")
    net.barnes_hut()

    palette=["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b",
             "#e377c2","#7f7f7f","#bcbd22","#17becf"]
    mods=sorted({G.nodes[n]["module"] for n in nodes})
    color_map={m:palette[i%len(palette)] for i,m in enumerate(mods)}

    for n in G.nodes():
        d=G.nodes[n]
        html_tip = (
            f"<b>{d['title']}</b><br>"
            f"{d['date']} | {d['module']}<br>"
            f"{d['activity']}<br>"
            f"<i>{', '.join(d['keywords'])}</i><br><hr>"
            f"<small>{d['theory']}</small>"
        )

        net.add_node(
            n,label=n,title="",  
            color=color_map.get(d["module"],"#999"),size=25,shape="dot",
            custom_html=html_tip
        )

    for u,v in G.edges(): 
        net.add_edge(u,v,color="#ccc")

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

    # Inject custom tooltip JS
    net.save_graph("graph.html")
    html=open("graph.html","r",encoding="utf-8").read()
    html = html.replace("</script>", """
    const tip = document.createElement('div');
    tip.style.position='fixed';
    tip.style.background='#ffffe6';
    tip.style.border='1px solid #aaa';
    tip.style.padding='6px 8px';
    tip.style.borderRadius='4px';
    tip.style.boxShadow='2px 2px 4px rgba(0,0,0,0.2)';
    tip.style.display='none';
    tip.style.pointerEvents='none';
    tip.style.maxWidth='400px';
    tip.style.lineHeight='1.25';
    document.body.appendChild(tip);

    network.on("hoverNode",(params)=>{
      const node=network.body.data.nodes.get(params.node);
      if(node && node.custom_html){
        tip.innerHTML=node.custom_html;
        tip.style.display='block';
      }
    });
    network.on("blurNode",()=>tip.style.display='none');
    document.addEventListener('mousemove',(e)=>{
      tip.style.left=(e.clientX+12)+'px';
      tip.style.top=(e.clientY+12)+'px';
    });

    network.on("selectNode",(p)=>{
      const id=p.nodes[0];
      if(id){
        localStorage.setItem('clicked', id);
        window.parent.postMessage({type:'nodeClick', id:id}, '*');
      }
    });
    </script>""")

    st.components.v1.html(html,height=750)

    # Passport
    st.markdown("---")
    st.markdown("### Session Passport")

    st.markdown("""
    <script>
    window.addEventListener("message",(e)=>{
      if(e.data && e.data.type==="nodeClick"){
         const id=e.data.id;
         window.localStorage.setItem('clicked', id);
         window.location.reload();
      }
    });
    </script>
    """, unsafe_allow_html=True)

    clicked_id = st.query_params.get("clicked")
    if clicked_id:
        clicked_id = clicked_id[0] if isinstance(clicked_id, list) else clicked_id
    else:
        clicked_id = None

    selected = clicked_id or st.selectbox(
        "Select a session:",
        sorted(df["session_id"]),
        format_func=lambda x: f"{x} — {df.loc[df["session_id"]==x,'title'].values[0]}"
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
            f"**Notes:**  \n{d['notes']}  \n\n"
            f"**Theory:**  \n{d['theory']}"
        )
