from __future__ import annotations
import io
import json
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st

# ---------------------------------------------------------
# 1. FULL EMBEDDED DATA (converted from your CSV)
# ---------------------------------------------------------
DATA_JSON = r"""
[
  {
    "session_id": "W1-Tu",
    "date": "1/13/2026",
    "title": "Course Introduction & Systems Bootcamp I",
    "instructor": "You",
    "module": "Systems Bootcamp",
    "activity": "Interactive lecture",
    "keywords": "systems thinking, feedback loops",
    "notes": "Define balancing and reinforcing loops.",
    "connect_with": ""
  },
  {
    "session_id": "W1-Th",
    "date": "1/15/2026",
    "title": "Systems Bootcamp II - Mapping Feedback Flow",
    "instructor": "You",
    "module": "Systems Bootcamp",
    "activity": "Mapping exercise",
    "keywords": "feedback, flows, regulation",
    "notes": "Physiology as dynamic control system. Loop drawing.",
    "connect_with": ""
  },
  {
    "session_id": "W2-Tu",
    "date": "1/20/2026",
    "title": "Boundaries and Constraint",
    "instructor": "You",
    "module": "Constraint",
    "activity": "Interactive lecture",
    "keywords": "constraint, boundaries, requisite variety",
    "notes": "Cuticle, gut, tracheae as constraint architectures.",
    "connect_with": ""
  },
  {
    "session_id": "W2-Th",
    "date": "1/22/2026",
    "title": "Constraint Closure Simulation Lab",
    "instructor": "You",
    "module": "Constraint",
    "activity": "Simulation",
    "keywords": "constraint closure, autonomy",
    "notes": "Explore closure with termite gut models.",
    "connect_with": ""
  },
  {
    "session_id": "W3-Tu",
    "date": "1/27/2026",
    "title": "Holobiont Autonomy",
    "instructor": "You",
    "module": "Holobiont",
    "activity": "Lecture",
    "keywords": "autonomy, constraint networks",
    "notes": "Syntrophic feedback as organizing principle.",
    "connect_with": ""
  },
  {
    "session_id": "W3-Th",
    "date": "1/29/2026",
    "title": "Holobiont Constraint Lab",
    "instructor": "You",
    "module": "Holobiont",
    "activity": "Lab",
    "keywords": "autonomy, simulation",
    "notes": "Modeling cross-taxa gut closure.",
    "connect_with": ""
  },
  {
    "session_id": "W4-Tu",
    "date": "2/4/2026",
    "title": "Ecological Constraint: Resource Limitation",
    "instructor": "You",
    "module": "Ecology",
    "activity": "Lecture",
    "keywords": "nitrogen, resource limitation",
    "notes": "Resource-driven feedback in gut ecology.",
    "connect_with": ""
  },
  {
    "session_id": "W4-Th",
    "date": "2/6/2026",
    "title": "Damage–Response and Dysbiosis",
    "instructor": "You",
    "module": "Ecology",
    "activity": "Discussion",
    "keywords": "dysbiosis, damage response",
    "notes": "Host–microbe stability landscapes.",
    "connect_with": ""
  },
  {
    "session_id": "W5-Tu",
    "date": "2/11/2026",
    "title": "Robustness–Fragility Trade-offs",
    "instructor": "You",
    "module": "Robustness",
    "activity": "Lecture",
    "keywords": "robustness, fragility",
    "notes": "Constraint networks and resilience.",
    "connect_with": ""
  },
  {
    "session_id": "W5-Th",
    "date": "2/13/2026",
    "title": "Evolvability & Constraint Networks",
    "instructor": "You",
    "module": "Evolution",
    "activity": "Discussion",
    "keywords": "evolvability, constraint network",
    "notes": "How constraints scaffold novelty.",
    "connect_with": ""
  },
  {
    "session_id": "W6-Tu",
    "date": "2/18/2026",
    "title": "Constraint Rewiring Simulation",
    "instructor": "You",
    "module": "Evolution",
    "activity": "Lab",
    "keywords": "rewiring, innovation",
    "notes": "Simulating innovation via rewiring.",
    "connect_with": ""
  },
  {
    "session_id": "W6-Th",
    "date": "2/20/2026",
    "title": "Integration Workshop",
    "instructor": "You",
    "module": "Integration",
    "activity": "Workshop",
    "keywords": "integration, synthesis",
    "notes": "Cross-theory comparison.",
    "connect_with": ""
  },
  {
    "session_id": "W7-Tu",
    "date": "2/25/2026",
    "title": "Niche Construction & Symbiosis",
    "instructor": "You",
    "module": "Synthesis",
    "activity": "Lecture",
    "keywords": "niche construction, symbiosis",
    "notes": "Constraint co-design.",
    "connect_with": ""
  },
  {
    "session_id": "W7-Th",
    "date": "2/27/2026",
    "title": "Ecosystem Feedback & Gaia",
    "instructor": "You",
    "module": "Synthesis",
    "activity": "Discussion",
    "keywords": "ecosystem energetics, gaia",
    "notes": "System-wide coherence.",
    "connect_with": ""
  },
  {
    "session_id": "W8-Tu",
    "date": "3/4/2026",
    "title": "Hierarchy & Multiscale Constraint",
    "instructor": "You",
    "module": "Synthesis",
    "activity": "Lecture",
    "keywords": "hierarchy theory",
    "notes": "Cross-scale constraint propagation.",
    "connect_with": ""
  },
  {
    "session_id": "W8-Th",
    "date": "3/6/2026",
    "title": "Capstone Studio I",
    "instructor": "You",
    "module": "Capstone",
    "activity": "Workshop",
    "keywords": "capstone, mapping",
    "notes": "Project scoping.",
    "connect_with": ""
  },
  {
    "session_id": "W9-Tu",
    "date": "3/18/2026",
    "title": "Nitrogen Flux Modeling",
    "instructor": "You",
    "module": "Modeling",
    "activity": "Lab",
    "keywords": "nitrogen, modeling",
    "notes": "Hands-on flux simulation.",
    "connect_with": ""
  },
  {
    "session_id": "W9-Th",
    "date": "3/20/2026",
    "title": "Mutualism Economics",
    "instructor": "You",
    "module": "Modeling",
    "activity": "Lecture",
    "keywords": "mutualism, economics",
    "notes": "Resource exchange in symbioses.",
    "connect_with": ""
  },
  {
    "session_id": "W10-Tu",
    "date": "3/25/2026",
    "title": "Convergence & Adaptive Peaks",
    "instructor": "You",
    "module": "Comparative",
    "activity": "Lecture",
    "keywords": "convergence, adaptive peaks",
    "notes": "Constraint grammar of convergence.",
    "connect_with": ""
  },
  {
    "session_id": "W10-Th",
    "date": "3/27/2026",
    "title": "Comparative Gut Architecture",
    "instructor": "You",
    "module": "Comparative",
    "activity": "Discussion",
    "keywords": "guts, termites, passalids",
    "notes": "Cross-taxon comparison.",
    "connect_with": ""
  },
  {
    "session_id": "W11-Tu",
    "date": "4/1/2026",
    "title": "Historical Contingency",
    "instructor": "You",
    "module": "Comparative",
    "activity": "Discussion",
    "keywords": "contingency",
    "notes": "Lineage-specific constraints.",
    "connect_with": ""
  },
  {
    "session_id": "W11-Th",
    "date": "4/3/2026",
    "title": "Constraint Grammar Workshop",
    "instructor": "You",
    "module": "Comparative",
    "activity": "Workshop",
    "keywords": "constraint grammar",
    "notes": "Modularity & substitution.",
    "connect_with": ""
  },
  {
    "session_id": "W12-Tu",
    "date": "4/8/2026",
    "title": "Ecosystem Feedback & Guilds",
    "instructor": "You",
    "module": "Ecosystem",
    "activity": "Lecture",
    "keywords": "ecosystem, guilds",
    "notes": "Decomposer-driven stability.",
    "connect_with": ""
  },
  {
    "session_id": "W12-Th",
    "date": "4/10/2026",
    "title": "Planetary Coherence & Gaia",
    "instructor": "You",
    "module": "Ecosystem",
    "activity": "Discussion",
    "keywords": "gaia, closure",
    "notes": "Planetary-scale coherence.",
    "connect_with": ""
  },
  {
    "session_id": "W13-Tu",
    "date": "4/15/2026",
    "title": "Capstone Studio II",
    "instructor": "You",
    "module": "Capstone",
    "activity": "Workshop",
    "keywords": "capstone, design",
    "notes": "Proposal development.",
    "connect_with": ""
  },
  {
    "session_id": "W13-Th",
    "date": "4/17/2026",
    "title": "Capstone Peer Review",
    "instructor": "You",
    "module": "Capstone",
    "activity": "Workshop",
    "keywords": "peer review",
    "notes": "Constraint mapping critique.",
    "connect_with": ""
  },
  {
    "session_id": "W14-Tu",
    "date": "4/22/2026",
    "title": "Capstone Presentations",
    "instructor": "You",
    "module": "Capstone",
    "activity": "Presentation",
    "keywords": "presentation, synthesis",
    "notes": "Final presentations.",
    "connect_with": ""
  },
  {
    "session_id": "W14-Th",
    "date": "4/24/2026",
    "title": "Course Synthesis: Constraint Grammar of Life",
    "instructor": "You",
    "module": "Synthesis",
    "activity": "Lecture",
    "keywords": "synthesis, constraint grammar",
    "notes": "Grand synthesis.",
    "connect_with": ""
  }
]
"""

# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------
df = pd.read_json(io.StringIO(DATA_JSON), dtype=str).fillna("")

def clean_kw(s):
    return [k.strip().lower() for k in s.replace(";",",").split(",") if k.strip()]

def split_ids(s):
    return [x.strip() for x in s.split(",") if x.strip()]

# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Insect–Microbe Systems Explorer")
st.title("Insect–Microbe Systems — Course Explorer")

with st.sidebar:
    st.header("Network Settings")
    min_shared = st.slider("Min shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)

tab_data, tab_graph = st.tabs(["Session Table", "Graph Explorer"])

with tab_data:
    st.dataframe(df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# Graph
# ---------------------------------------------------------
with tab_graph:
    G = nx.Graph()

    for _, row in df.iterrows():
        kws = clean_kw(row["keywords"])
        d = row.to_dict()
        d["keywords"] = kws
        G.add_node(row["session_id"], **d)

    nodes = list(G.nodes())

    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            a, b = nodes[i], nodes[j]
            shared = len(set(G.nodes[a]["keywords"]) & set(G.nodes[b]["keywords"]))
            if shared >= min_shared:
                G.add_edge(a,b)

    if include_manual:
        for n in nodes:
            for m in split_ids(G.nodes[n]["connect_with"]):
                if m in nodes and m != n:
                    G.add_edge(n,m)

    modules = sorted(df["module"].unique())
    palette = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b",
               "#e377c2","#7f7f7f","#bcbd22","#17becf"]
    cmap = {m: palette[i % len(palette)] for i,m in enumerate(modules)}

    net = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#222")
    net.barnes_hut()

    for node in G.nodes():
        d = G.nodes[node]
        html_tip = f"""
        <div style='font-family:sans-serif; font-size:14px; line-height:1.25;'>
          <b>{d['title']}</b><br>
          {d['date']} | {d['module']}<br>
          {d['activity']}<br>
          <i>{', '.join(d['keywords'])}</i>
          <hr style='margin:6px 0;'>
          {d['notes']}
        </div>
        """

        net.add_node(
            node,
            label=node,
            title="",        # disable default tooltip
            shape="dot",
            size=25,
            color=cmap.get(d["module"], "#999"),
            custom_html=html_tip
        )

    for u,v in G.edges():
        net.add_edge(u,v,color="#ccc")

    net.set_options("""
    { "interaction": { "hover": true, "navigationButtons": true },
      "physics": { "enabled": true,
                   "stabilization": {"enabled": true, "iterations": 500},
                   "barnesHut": {"springLength": 150} } }
    """)

    net.save_graph("graph.html")
    html = open("graph.html","r",encoding="utf8").read()

    js = """
    const tip = document.createElement('div');
    tip.style.position = 'fixed';
    tip.style.background = '#ffffe6';
    tip.style.border = '1px solid #aaa';
    tip.style.padding = '8px 12px';
    tip.style.borderRadius = '4px';
    tip.style.boxShadow = '2px 2px 4px rgba(0,0,0,0.2)';
    tip.style.display = 'none';
    tip.style.pointerEvents = 'none';
    tip.style.maxWidth = '420px';
    tip.style.zIndex = 9999;
    document.body.appendChild(tip);

    network.on("hoverNode", (params)=> {
      const node = network.body.data.nodes.get(params.node);
      if(node && node.custom_html){
        tip.innerHTML = node.custom_html;
        tip.style.display = "block";
      }
    });

    network.on("blurNode", ()=> tip.style.display = "none");
    document.addEventListener("mousemove", (e)=>{
      tip.style.left = (e.clientX + 12) + "px";
      tip.style.top = (e.clientY + 12) + "px";
    });
    """

    html = html.replace("</script>", js + "</script>")
    st.components.v1.html(html, height=750)

    st.markdown("### Session Passport")
    sel = st.selectbox(
        "Choose session:",
        df["session_id"],
        format_func=lambda x: f"{x} — {df[df['session_id']==x]['title'].values[0]}"
    )

    d = df[df["session_id"]==sel].iloc[0]
    st.subheader(d["title"])
    st.write(f"**Date:** {d['date']}")
    st.write(f"**Instructor:** {d['instructor']}")
    st.write(f"**Module:** {d['module']}")
    st.write(f"**Activity:** {d['activity']}")
    st.write(f"**Keywords:** {d['keywords']}")
    st.write(f"**Notes:** {d['notes']}")
