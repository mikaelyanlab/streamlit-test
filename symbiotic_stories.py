import io, csv
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
import streamlit as st

# ---------- data ----------
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

def _clean_keywords(s):
    if not str(s).strip(): return []
    return [t.strip().lower() for t in str(s).replace(";",",").split(",") if t.strip()]

# ---------- setup ----------
st.set_page_config(page_title="Insect–Microbe Systems", layout="wide")

if "sessions" not in st.session_state:
    st.session_state.sessions = pd.DataFrame(SAMPLE_ROWS, columns=DEFAULT_COLUMNS)
if "selected" not in st.session_state:
    st.session_state.selected = None

# ---------- sidebar ----------
st.sidebar.title("Course Session Network")
buf = io.StringIO()
st.session_state.sessions.to_csv(buf, index=False)
st.sidebar.download_button("Download CSV", buf.getvalue(), "sessions.csv")
min_shared = st.sidebar.slider("Min shared keywords", 1, 5, 1)

# ---------- network ----------
df = st.session_state.sessions.copy()
G = nx.Graph()
for _, r in df.iterrows():
    kws = _clean_keywords(r["keywords"])
    d = r.to_dict(); d["keywords"]=kws
    G.add_node(r["session_id"], **d)

nodes=list(G.nodes())
for i,a in enumerate(nodes):
    for j,b in enumerate(nodes):
        if j<=i: continue
        shared=len(set(G.nodes[a]["keywords"]) & set(G.nodes[b]["keywords"]))
        if shared>=min_shared: G.add_edge(a,b)

pos = nx.spring_layout(G, seed=42, k=2)
palette=["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd"]
mods=sorted({G.nodes[n]["module"] for n in nodes})
color_map={m:palette[i%len(palette)] for i,m in enumerate(mods)}

edge_x,edge_y=[],[]
for u,v in G.edges():
    x0,y0=pos[u]; x1,y1=pos[v]
    edge_x+=[x0,x1,None]; edge_y+=[y0,y1,None]
edge_trace=go.Scatter(x=edge_x,y=edge_y,mode="lines",
                      line=dict(width=1,color="#ccc"),hoverinfo="none")

node_x,node_y,colors,text=[],[],[],[]
for n in nodes:
    x,y=pos[n]; node_x.append(x); node_y.append(y)
    colors.append(color_map.get(G.nodes[n]["module"],"#777"))
    text.append(n)

node_trace=go.Scatter(
    x=node_x,y=node_y,mode="markers+text",
    text=text,textposition="top center",
    marker=dict(size=28,color=colors,line=dict(width=1,color="#000")),
    hovertemplate="%{text}<extra></extra>"
)

fig=go.Figure(data=[edge_trace,node_trace])
fig.update_layout(
    showlegend=False,hovermode=False,
    margin=dict(l=10,r=10,b=10,t=30),
    xaxis=dict(showgrid=False,zeroline=False,visible=False),
    yaxis=dict(showgrid=False,zeroline=False,visible=False),
    height=700
)

st.subheader("Click any node to see its Session Passport")

# ---------- click handler ----------
def show_details(event):
    if not event or "points" not in event: return
    label = event["points"][0]["text"]
    d = G.nodes[label]
    st.session_state.selected = label
    with details_container:
        st.markdown(f"### {d['title']}")
        st.markdown(
            f"**Session ID:** {label}  \n"
            f"**Date:** {d['date']}  \n"
            f"**Instructor:** {d['instructor']}  \n"
            f"**Module:** {d['module']}  \n"
            f"**Activity:** {d['activity']}  \n"
            f"**Keywords:** {', '.join(d['keywords']) if d['keywords'] else ''}  \n\n"
            f"**Notes:**  \n{d['notes']}"
        )

details_container = st.container()
st.plotly_chart(fig, use_container_width=True, on_click=show_details)

# ---------- persist selection ----------
if st.session_state.selected and st.session_state.selected in G.nodes:
    d = G.nodes[st.session_state.selected]
    with details_container:
        st.markdown(f"### {d['title']}")
        st.markdown(
            f"**Session ID:** {st.session_state.selected}  \n"
            f"**Date:** {d['date']}  \n"
            f"**Instructor:** {d['instructor']}  \n"
            f"**Module:** {d['module']}  \n"
            f"**Activity:** {d['activity']}  \n"
            f"**Keywords:** {', '.join(d['keywords']) if d['keywords'] else ''}  \n\n"
            f"**Notes:**  \n{d['notes']}"
        )
