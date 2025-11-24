from __future__ import annotations

import io
from typing import List

import networkx as nx
import pandas as pd
import streamlit as st
from pyvis.network import Network

# ---------------------------------------------------------
# 1. EMBEDDED COURSE DATA (JSON, NOT CSV)
# ---------------------------------------------------------
# Replace the [...] below with the full contents of
# course_full_streamlit_theory.json that you downloaded from:
#   sandbox:/mnt/data/course_full_streamlit_theory.json
#
# After you paste it once in GitHub, the app is 100% self-contained.
DATA_JSON = r"""
[
  {
    "session_id":"W1-Tu",
    "date":"1/13/2026",
    "title":"Course Introduction & Systems Bootcamp I",
    "instructor":"You",
    "module":"The Individual as a System: Feedback and Flow",
    "activity":"Lecture",
    "keywords":"feedback, dissipative structure, cybernetics, stocks flows",
    "notes":"Course overview; systems framing using insect–microbe interactions.",
    "connect_with":"W1-Th"
  },
  {
    "session_id":"W1-Th",
    "date":"1/15/2026",
    "title":"Systems Bootcamp II - Mapping Feedback Flow",
    "instructor":"You",
    "module":"The Individual as a System: Feedback and Flow",
    "activity":"Workshop",
    "keywords":"flow, homeostasis, trophallaxis, colony stability",
    "notes":"Explore feedback via visual loops and interactive examples.",
    "connect_with":"W2-Tu"
  },
  {
    "session_id":"W2-Tu",
    "date":"1/20/2026",
    "title":"Simulation Lab: Termite Gut Flows",
    "instructor":"You",
    "module":"The Individual as a System: Feedback and Flow",
    "activity":"Lab",
    "keywords":"simulation, redox, microbial syntrophy, termite",
    "notes":"Introduce stocks and flows. Students explore flows in termite gut model.",
    "connect_with":"W2-Th"
  },
  {
    "session_id":"W2-Th",
    "date":"1/22/2026",
    "title":"From Feedback to Constraint - Defining Boundaries",
    "instructor":"You",
    "module":"Transition to M2",
    "activity":"Discussion",
    "keywords":"feedback, constraint, individuality",
    "notes":"Constraint closure and autonomy in the holobiont.",
    "connect_with":"W3-Tu"
  },
  {
    "session_id":"W3-Tu",
    "date":"1/27/2026",
    "title":"Constraint Closure and Autonomy",
    "instructor":"You",
    "module":"The Emergence of the Holobiont: Constraint and Closure",
    "activity":"Lecture",
    "keywords":"constraint closure, canalization, autonomy, Kauffman",
    "notes":"Model gut retention and resource availability with constraint closure.",
    "connect_with":"W3-Th"
  },
  {
    "session_id":"W3-Th",
    "date":"1/29/2026",
    "title":"Holobiont Simulation Lab: Constraint Networks",
    "instructor":"You",
    "module":"The Emergence of the Holobiont: Constraint and Closure",
    "activity":"Lab",
    "keywords":"autonomy, simulation, boundaries",
    "notes":"Students explore constraint dependencies in a gut model.",
    "connect_with":"W4-Tu"
  },
  {
    "session_id":"W4-Tu",
    "date":"2/4/2026",
    "title":"Ecological Constraint: Nitrogen & Resource Flow",
    "instructor":"You",
    "module":"Ecological Interactions and Resource Feedback",
    "activity":"Lecture",
    "keywords":"nitrogen, resource feedback, syntrophy, nutrient flux",
    "notes":"Connect gut ecology to colony nutrient budget.",
    "connect_with":"W4-Th"
  },
  {
    "session_id":"W4-Th",
    "date":"2/6/2026",
    "title":"Damage–Response Framework & Dysbiosis",
    "instructor":"You",
    "module":"Ecological Interactions and Resource Feedback",
    "activity":"Discussion",
    "keywords":"dysbiosis, damage response, pathogen probes",
    "notes":"Map how dysbiosis emerges in termite and cockroach systems.",
    "connect_with":"W5-Tu"
  },
  {
    "session_id":"W5-Tu",
    "date":"2/11/2026",
    "title":"Constraint, Robustness & Fragility",
    "instructor":"You",
    "module":"Constraint, Robustness & Evolutionary Possibility",
    "activity":"Lecture",
    "keywords":"robustness, fragility, redundancy",
    "notes":"Explore robustness–fragility trade-offs via termite and maggot systems.",
    "connect_with":"W5-Th"
  },
  {
    "session_id":"W5-Th",
    "date":"2/13/2026",
    "title":"Evolvability & Constraint Networks",
    "instructor":"You",
    "module":"Constraint, Robustness & Evolutionary Possibility",
    "activity":"Discussion",
    "keywords":"evolvability, constraint network, canalization",
    "notes":"Evolutionary pathways in termite digestion and beetle gut morphology.",
    "connect_with":"W6-Tu"
  },
  {
    "session_id":"W6-Tu",
    "date":"2/18/2026",
    "title":"Simulation Lab: Constraint Rewiring",
    "instructor":"You",
    "module":"Constraint, Robustness & Evolutionary Possibility",
    "activity":"Lab",
    "keywords":"simulation, innovation, network rewiring",
    "notes":"Students experiment with rewiring constraints in simplified insect systems.",
    "connect_with":"W6-Th"
  },
  {
    "session_id":"W6-Th",
    "date":"2/20/2026",
    "title":"Midterm Integration Workshop",
    "instructor":"You",
    "module":"Transition to M4",
    "activity":"Workshop",
    "keywords":"integration, synthesis",
    "notes":"Integrate first-half theories via case comparison.",
    "connect_with":"W7-Tu"
  },
  {
    "session_id":"W7-Tu",
    "date":"2/25/2026",
    "title":"Niche Construction & Symbiosis as Co-Search",
    "instructor":"You",
    "module":"Synthesis: Systems Function Across Scales",
    "activity":"Lecture",
    "keywords":"niche construction, symbiosis, co-search",
    "notes":"Explore insect–microbe co-design of constraint networks.",
    "connect_with":"W7-Th"
  },
  {
    "session_id":"W7-Th",
    "date":"2/27/2026",
    "title":"Gaia & Ecosystem Feedback via Insects",
    "instructor":"You",
    "module":"Synthesis: Systems Function Across Scales",
    "activity":"Discussion",
    "keywords":"ecosystem energetics, gaia, multilevel feedback",
    "notes":"Role of decomposers in regulating planetary flows.",
    "connect_with":"W8-Tu"
  },
  {
    "session_id":"W8-Tu",
    "date":"3/4/2026",
    "title":"Hierarchy & Multiscale Constraint Propagation",
    "instructor":"You",
    "module":"Synthesis: Systems Function Across Scales",
    "activity":"Lecture",
    "keywords":"hierarchy theory, multiscale, propagation",
    "notes":"Students explore cross-scale constraints from gut to ecosystem.",
    "connect_with":"W8-Th"
  },
  {
    "session_id":"W8-Th",
    "date":"3/6/2026",
    "title":"Studio I: Capstone Mapping Session",
    "instructor":"You",
    "module":"Capstone",
    "activity":"Workshop",
    "keywords":"capstone, system mapping",
    "notes":"Students build early maps of their chosen system.",
    "connect_with":"W9-Tu"
  },
  {
    "session_id":"W9-Tu",
    "date":"3/18/2026",
    "title":"Nitrogen Flux Modeling Workshop",
    "instructor":"You",
    "module":"Modeling Systems Across Scales",
    "activity":"Lab",
    "keywords":"nitrogen, modeling, consumer-resource",
    "notes":"Hands-on nitrogen flux simulation.",
    "connect_with":"W9-Th"
  },
  {
    "session_id":"W9-Th",
    "date":"3/20/2026",
    "title":"Mutualism Economics in Insect Systems",
    "instructor":"You",
    "module":"Modeling Systems Across Scales",
    "activity":"Lecture",
    "keywords":"mutualism, resource exchange, economics",
    "notes":"Analyze nutrient economics of obligate symbioses.",
    "connect_with":"W10-Tu"
  },
  {
    "session_id":"W10-Tu",
    "date":"3/25/2026",
    "title":"Convergence & Adaptive Peaks in Gut Systems",
    "instructor":"You",
    "module":"Comparative Systems: Convergence vs. Divergence",
    "activity":"Lecture",
    "keywords":"convergence, adaptive peaks, constraint grammar",
    "notes":"Why wood-feeders converge or diverge.",
    "connect_with":"W10-Th"
  },
  {
    "session_id":"W10-Th",
    "date":"3/27/2026",
    "title":"Comparative Gut Architecture",
    "instructor":"You",
    "module":"Comparative Systems: Convergence vs. Divergence",
    "activity":"Discussion",
    "keywords":"comparative guts, termites, passalids",
    "notes":"Cross-taxon comparison via constraints.",
    "connect_with":"W11-Tu"
  },
  {
    "session_id":"W11-Tu",
    "date":"4/1/2026",
    "title":"Historical Contingency & Lineage Constraint",
    "instructor":"You",
    "module":"Comparative Systems: Convergence vs. Divergence",
    "activity":"Discussion",
    "keywords":"contingency, lineage specific",
    "notes":"Divergence in similar ecological niches.",
    "connect_with":"W11-Th"
  },
  {
    "session_id":"W11-Th",
    "date":"4/3/2026",
    "title":"Constraint Grammar Workshop",
    "instructor":"You",
    "module":"Comparative Systems: Convergence vs. Divergence",
    "activity":"Workshop",
    "keywords":"constraint grammar, modularity",
    "notes":"Students map constraint substitution rules.",
    "connect_with":"W12-Tu"
  },
  {
    "session_id":"W12-Tu",
    "date":"4/8/2026",
    "title":"Ecosystem Feedback & Insect Guilds",
    "instructor":"You",
    "module":"Insects in Ecosystems",
    "activity":"Lecture",
    "keywords":"ecosystem feedback, guilds",
    "notes":"Connect decomposers to biogeochemical stability.",
    "connect_with":"W12-Th"
  },
  {
    "session_id":"W12-Th",
    "date":"4/10/2026",
    "title":"Gaia, Closure & Planetary Coherence",
    "instructor":"You",
    "module":"Insects in Ecosystems",
    "activity":"Discussion",
    "keywords":"gaia, feedback, closure",
    "notes":"Planetary coherence via countless small constraints.",
    "connect_with":"W13-Tu"
  },
  {
    "session_id":"W13-Tu",
    "date":"4/15/2026",
    "title":"Studio II: Capstone Development",
    "instructor":"You",
    "module":"Capstone",
    "activity":"Workshop",
    "keywords":"capstone, design",
    "notes":"Develop and critique capstone proposals.",
    "connect_with":"W13-Th"
  },
  {
    "session_id":"W13-Th",
    "date":"4/17/2026",
    "title":"Workshop: Capstone Peer Review",
    "instructor":"You",
    "module":"Capstone",
    "activity":"Workshop",
    "keywords":"peer review, capstone",
    "notes":"Students evaluate constraint mapping clarity.",
    "connect_with":"W14-Tu"
  },
  {
    "session_id":"W14-Tu",
    "date":"4/22/2026",
    "title":"Final Capstone Presentations",
    "instructor":"You",
    "module":"Capstone",
    "activity":"Presentation",
    "keywords":"presentation, synthesis",
    "notes":"Capstone final session.",
    "connect_with":"W14-Th"
  },
  {
    "session_id":"W14-Th",
    "date":"4/24/2026",
    "title":"Constraint Grammar of Life (Course Synthesis)",
    "instructor":"You",
    "module":"Course Synthesis",
    "activity":"Lecture",
    "keywords":"synthesis, grammar of life",
    "notes":"Full synthesis; discuss future directions.",
    "connect_with":"-"
  }
]
"""

# ---------------------------------------------------------
# 2. Load data from embedded JSON
# ---------------------------------------------------------
def load_sessions_from_json() -> pd.DataFrame:
    if DATA_JSON.strip().startswith("[") is False:
        raise ValueError(
            "DATA_JSON is not filled yet. Paste the JSON array from "
            "course_full_streamlit_theory.json into the DATA_JSON string."
        )
    df = pd.read_json(io.StringIO(DATA_JSON), dtype=str)
    df = df.fillna("")
    # Ensure column order if needed
    expected = [
        "session_id", "date", "title", "instructor", "module",
        "activity", "keywords", "notes", "connect_with"
    ]
    for col in expected:
        if col not in df.columns:
            df[col] = ""
    return df[expected]


def _clean_keywords(s: str) -> List[str]:
    if pd.isna(s) or not str(s).strip():
        return []
    toks = [t.strip().lower() for t in str(s).replace(";", ",").split(",")]
    return sorted({t for t in toks if t})


def _split_multi(s: str) -> List[str]:
    if pd.isna(s) or not str(s).strip():
        return []
    return [t.strip() for t in str(s).replace(";", ",").split(",") if t.strip()]


# ---------------------------------------------------------
# 3. Streamlit layout
# ---------------------------------------------------------
st.set_page_config(page_title="Insect–Microbe Systems Explorer", layout="wide")
st.title("Insect–Microbe Systems — Course Explorer")

df = load_sessions_from_json()

with st.sidebar:
    st.header("Network Settings")
    min_shared = st.slider("Minimum shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)

tab_data, tab_graph = st.tabs(["Session Table", "Graph Explorer"])

# ---------------------------------------------------------
# 4. Session Table
# ---------------------------------------------------------
with tab_data:
    st.markdown("### Full Course Outline")
    st.dataframe(df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# 5. Graph Explorer
# ---------------------------------------------------------
with tab_graph:
    G = nx.Graph()

    # Nodes
    for _, row in df.iterrows():
        kws = _clean_keywords(row["keywords"])
        data = row.to_dict()
        data["keywords"] = kws
        G.add_node(row["session_id"], **data)

    nodes = list(G.nodes())

    # Keyword-based edges
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            shared = len(set(G.nodes[a]["keywords"]) & set(G.nodes[b]["keywords"]))
            if shared >= min_shared:
                G.add_edge(a, b)

    # Manual connects
    if include_manual:
        for n in nodes:
            for m in _split_multi(G.nodes[n]["connect_with"]):
                if m in nodes and m != n:
                    G.add_edge(n, m)

    net = Network(
        height="700px",
        width="100%",
        bgcolor="#ffffff",
        font_color="#222222",
        directed=False,
    )
    net.barnes_hut()

    # Color by module
    palette = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]
    modules = sorted(df["module"].unique())
    colors = {m: palette[i % len(palette)] for i, m in enumerate(modules)}

    for node in G.nodes():
        d = G.nodes[node]
        tip = (
            f"<b>{d['title']}</b><br>"
            f"{d['date']} | {d['module']}<br>"
            f"{d['activity']}<br>"
            f"<i>{', '.join(d['keywords'])}</i>"
        )
        net.add_node(
            node,
            label=node,
            title=tip,
            color=colors.get(d["module"], "#999999"),
            size=25,
            shape="dot",
        )

    for u, v in G.edges():
        net.add_edge(u, v, color="#cccccc")

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

    net.save_graph("graph.html")
    with open("graph.html", "r", encoding="utf-8") as f:
        html = f.read()
    st.components.v1.html(html, height=750)

    # Session Passport
    st.markdown("### Session Passport")
    selected = st.selectbox(
        "Choose a session:",
        df["session_id"].tolist(),
        format_func=lambda x: f"{x} — {df.loc[df['session_id'] == x, 'title'].values[0]}",
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
