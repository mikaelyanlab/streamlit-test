# app.py — Public-facing Course Explorer
from __future__ import annotations
import io
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st

# ---------------------------------------------------------
# 1. EMBEDDED CSV (FULL CONTENT FROM YOUR UPLOADED FILE)
# ---------------------------------------------------------
CSV_TEXT = """
session_id,date,title,instructor,module,activity,keywords,notes,connect_with
W1-Tu,1/13/2026,Course Introduction & Systems Bootcamp I,You,The Individual as a System: Feedback and Flow,Lecture,"feedback, dissipative structure, cybernetics, stocks flows", "Course overview; systems framing using insect–microbe interactions.",W1-Th
W1-Th,1/15/2026,Systems Bootcamp II - Mapping Feedback Flow,You,The Individual as a System: Feedback and Flow,Workshop,"flow, homeostasis, trophallaxis, colony stability","Explore feedback via visual loops and interactive examples.",W2-Tu
W2-Tu,1/20/2026,Simulation Lab: Termite Gut Flows,You,The Individual as a System: Feedback and Flow,Lab,"simulation, redox, microbial syntrophy, termite","Introduce stocks and flows. Students explore flows in termite gut model.",W2-Th
W2-Th,1/22/2026,From Feedback to Constraint - Defining Boundaries,You,Transition to M2,Discussion,"feedback, constraint, individuality","Constraint closure and autonomy in the holobiont.",W3-Tu
W3-Tu,1/27/2026,Constraint Closure and Autonomy,You,The Emergence of the Holobiont: Constraint and Closure,Lecture,"constraint closure, canalization, autonomy, Kauffman","Model gut retention and resource availability with constraint closure.",W3-Th
W3-Th,1/29/2026,Holobiont Simulation Lab: Constraint Networks,You,The Emergence of the Holobiont: Constraint and Closure,Lab,"autonomy, simulation, boundaries","Students explore constraint dependencies in a gut model.",W4-Tu
W4-Tu,2/4/2026,Ecological Constraint: Nitrogen & Resource Flow,You,Ecological Interactions and Resource Feedback,Lecture,"nitrogen, resource feedback, syntrophy, nutrient flux","Connect gut ecology to colony nutrient budget.",W4-Th
W4-Th,2/6/2026,Damage–Response Framework & Dysbiosis,You,Ecological Interactions and Resource Feedback,Discussion,"dysbiosis, damage response, pathogen probes","Map how dysbiosis emerges in termite and cockroach systems.",W5-Tu
W5-Tu,2/11/2026,Constraint, Robustness & Fragility,You,Constraint, Robustness & Evolutionary Possibility,Lecture,"robustness, fragility, redundancy","Explore robustness–fragility trade-offs via termite and maggot systems.",W5-Th
W5-Th,2/13/2026,Evolvability & Constraint Networks,You,Constraint, Robustness & Evolutionary Possibility,Discussion,"evolvability, constraint network, canalization","Evolutionary pathways in termite digestion and beetle gut morphology.",W6-Tu
W6-Tu,2/18/2026,Simulation Lab: Constraint Rewiring,You,Constraint, Robustness & Evolutionary Possibility,Lab,"simulation, innovation, network rewiring","Students experiment with rewiring constraints in simplified insect systems.",W6-Th
W6-Th,2/20/2026,Midterm Integration Workshop,You,Transition to M4,Workshop,"integration, synthesis","Integrate first-half theories via case comparison.",W7-Tu
W7-Tu,2/25/2026,Niche Construction & Symbiosis as Co-Search,You,Synthesis: Systems Function Across Scales,Lecture,"niche construction, symbiosis, co-search","Explore insect–microbe co-design of constraint networks.",W7-Th
W7-Th,2/27/2026,Gaia & Ecosystem Feedback via Insects,You,Synthesis: Systems Function Across Scales,Discussion,"ecosystem energetics, gaia, multilevel feedback","Role of decomposers in regulating planetary flows.",W8-Tu
W8-Tu,3/4/2026,Hierarchy & Multiscale Constraint Propagation,You,Synthesis: Systems Function Across Scales,Lecture,"hierarchy theory, multiscale, propagation","Students explore cross-scale constraints from gut to ecosystem.",W8-Th
W8-Th,3/6/2026,Studio I: Capstone Mapping Session,You,Capstone,Workshop,"capstone, system mapping","Students build early maps of their chosen system.",W9-Tu
W9-Tu,3/18/2026,Nitrogen Flux Modeling Workshop,You,Modeling Systems Across Scales,Lab,"nitrogen, modeling, consumer-resource","Hands-on nitrogen flux simulation.",W9-Th
W9-Th,3/20/2026,Mutualism Economics in Insect Systems,You,Modeling Systems Across Scales,Lecture,"mutualism, resource exchange, economics","Analyze nutrient economics of obligate symbioses.",W10-Tu
W10-Tu,3/25/2026,Convergence & Adaptive Peaks in Gut Systems,You,Comparative Systems: Convergence vs. Divergence,Lecture,"convergence, adaptive peaks, constraint grammar","Why wood-feeders converge or diverge.",W10-Th
W10-Th,3/27/2026,Comparative Gut Architecture,You,Comparative Systems: Convergence vs. Divergence,Discussion,"comparative guts, termites, passalids","Cross-taxon comparison via constraints.",W11-Tu
W11-Tu,4/1/2026,Historical Contingency & Lineage Constraint,You,Comparative Systems: Convergence vs. Divergence,Discussion,"contingency, lineage specific","Divergence in similar ecological niches.",W11-Th
W11-Th,4/3/2026,Constraint Grammar Workshop,You,Comparative Systems: Convergence vs. Divergence,Workshop,"constraint grammar, modularity","Students map constraint substitution rules.",W12-Tu
W12-Tu,4/8/2026,Ecosystem Feedback & Insect Guilds,You,Insects in Ecosystems,Lecture,"ecosystem feedback, guilds","Connect decomposers to biogeochemical stability.",W12-Th
W12-Th,4/10/2026,Gaia, Closure & Planetary Coherence,You,Insects in Ecosystems,Discussion,"gaia, feedback, closure","Planetary coherence via countless small constraints.",W13-Tu
W13-Tu,4/15/2026,Studio II: Capstone Development,You,Capstone,Workshop,"capstone, design","Develop and critique capstone proposals.",W13-Th
W13-Th,4/17/2026,Workshop: Capstone Peer Review,You,Capstone,Workshop,"peer review, capstone","Students evaluate constraint mapping clarity.",W14-Tu
W14-Tu,4/22/2026,Final Capstone Presentations,You,Capstone,Presentation,"presentation, synthesis","Capstone final session.",W14-Th
W14-Th,4/24/2026,Constraint Grammar of Life (Course Synthesis),You,Course Synthesis,Lecture,"synthesis, grammar of life","Wrap-up synthesis across the theory stack.",""
"""

# ---------------------------------------------------------
# Load embedded CSV
# ---------------------------------------------------------
df = pd.read_csv(io.StringIO(CSV_TEXT), dtype=str).fillna("")

# Build keyword lists
def _clean_keywords(s: str):
    if not s: return []
    toks = [t.strip().lower() for t in s.replace(";", ",").split(",")]
    return sorted({t for t in toks if t})

def _split_multi(s: str):
    if not s: return []
    return [t.strip() for t in s.replace(";", ",").split(",") if t.strip()]

# ---------------------------------------------------------
# Streamlit Layout
# ---------------------------------------------------------
st.set_page_config(page_title="Insect–Microbe Systems Explorer", layout="wide")
st.title("Insect–Microbe Systems — Course Explorer")

with st.sidebar:
    st.header("Network Settings")
    min_shared = st.slider("Minimum shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)

tab_data, tab_graph = st.tabs(["Session Table", "Graph Explorer"])

# ---------------------------------------------------------
# TABLE TAB
# ---------------------------------------------------------
with tab_data:
    st.markdown("### Full Course Outline")
    st.dataframe(df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# GRAPH TAB
# ---------------------------------------------------------
with tab_graph:
    G = nx.Graph()

    # Add nodes
    for _, row in df.iterrows():
        kws = _clean_keywords(row["keywords"])
        data = row.to_dict()
        data["keywords"] = kws
        G.add_node(row["session_id"], **data)

    # Keyword-based edges
    nodes = list(G.nodes())
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            a, b = nodes[i], nodes[j]
            shared = len(set(G.nodes[a]["keywords"]) & set(G.nodes[b]["keywords"]))
            if shared >= min_shared:
                G.add_edge(a, b)

    # Manual connections
    if include_manual:
        for n in nodes:
            for m in _split_multi(G.nodes[n]["connect_with"]):
                if m in nodes and m != n:
                    G.add_edge(n, m)

    # PyVis network build
    net = Network(height="700px", width="100%", bgcolor="#ffffff", font_color="#222")
    net.barnes_hut()

    # Color by module
    palette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
               "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]
    modules = sorted(df["module"].unique())
    colors = {m: palette[i % len(palette)] for i, m in enumerate(modules)}

    for n in G.nodes():
        d = G.nodes[n]
        tip = (
            f"<b>{d['title']}</b><br>"
            f"{d['date']} ({d['module']})<br>"
            f"{d['activity']}<br>"
            f"<i>{', '.join(d['keywords'])}</i>"
        )
        net.add_node(n, label=n, title=tip, color=colors.get(d['module'], "#999"))

    for u, v in G.edges():
        net.add_edge(u, v, color="#cccccc")

    net.save_graph("graph.html")
    with open("graph.html", "r", encoding="utf-8") as f:
        html = f.read()

    st.components.v1.html(html, height=750)

    # Passport
    st.markdown("### Session Passport")
    selected = st.selectbox(
        "Choose a session:",
        df["session_id"].tolist(),
        format_func=lambda x: f"{x} — {df.loc[df['session_id']==x, 'title'].values[0]}"
    )

    d = df[df["session_id"] == selected].iloc[0]
    st.markdown(f"#### {d['title']}")
    st.write(f"**Date:** {d['date']}")
    st.write(f"**Instructor:** {d['instructor']}")
    st.write(f"**Module:** {d['module']}")
    st.write(f"**Activity:** {d['activity']}")
    st.write(f"**Keywords:** {d['keywords']}")
    st.write("**Notes:**")
    st.markdown(d["notes"])
