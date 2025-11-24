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
    "module": "The Individual as a System: Feedback and Flow",
    "activity": "Lecture",
    "keywords": "feedback, dissipative structure, cybernetics, termite gut",
    "notes": "Course overview; systems framing using insect–microbe examples. Discuss autonomy, feedback, openness. Introduce course expectations. Begin discussion of systems as defined by Prigogine and Wiener.",
    "connect_with": "W1-Th"
  },
  {
    "session_id": "W1-Th",
    "date": "1/15/2026",
    "title": "Systems Bootcamp II - Mapping Feedback Flow",
    "instructor": "You",
    "module": "The Individual as a System: Feedback and Flow",
    "activity": "Workshop",
    "keywords": "flow, homeostasis, trophallaxis, colony stability",
    "notes": "Explore feedback via visual loops and interactive tools. Introduce cybernetics and feedback via Wiener; students simulate simple positive/negative loops in Streamlit using digestive and behavioral analogies.",
    "connect_with": "W2-Tu"
  },
  {
    "session_id": "W2-Tu",
    "date": "1/20/2026",
    "title": "Simulation Lab: Termite Gut Flows",
    "instructor": "You",
    "module": "The Individual as a System: Feedback and Flow",
    "activity": "Lab",
    "keywords": "simulation, redox, microbial syntrophy, termite",
    "notes": "Introduce stocks and flows. Students explore flow-through insect gut models using Streamlit sandbox. Framing via metabolic networks and resource bottlenecks.",
    "connect_with": "W2-Th"
  },
  {
    "session_id": "W2-Th",
    "date": "1/22/2026",
    "title": "From Feedback to Constraint - Defining Boundaries",
    "instructor": "You",
    "module": "Transition to M2",
    "activity": "Discussion",
    "keywords": "feedback, constraint, individuality",
    "notes": "Constraint closure and autonomy in the holobiont. Streamlit model of host-microbe bottlenecks. Waddington’s landscape introduced for multi-variable constraint interaction.",
    "connect_with": "W3-Tu"
  },
  {
    "session_id": "W3-Tu",
    "date": "1/27/2026",
    "title": "Constraint Closure and Autonomy",
    "instructor": "You",
    "module": "The Emergence of the Holobiont: Constraint and Integration",
    "activity": "Lecture",
    "keywords": "constraint closure, canalization, autonomy, Kauffman",
    "notes": "Model gut retention and resource availability via diet in cockroaches. Students manipulate inputs like pH, fiber content, retention time. Systems framing: input–processing–output chains.",
    "connect_with": "W3-Th"
  },
  {
    "session_id": "W3-Th",
    "date": "1/29/2026",
    "title": "Case Study: Holobiont as System",
    "instructor": "You",
    "module": "The Emergence of the Holobiont: Constraint and Integration",
    "activity": "Case Discussion",
    "keywords": "robustness, holobiont, nitrogen cycle, symbiosis",
    "notes": "Instructor check-ins and one-on-one explanations. In-class feedback used for formative grading. Discussion of emergent properties from varying initial constraints.",
    "connect_with": "W4-Tu"
  },
  {
    "session_id": "W4-Tu",
    "date": "2/3/2026",
    "title": "Nitrogen Flux and System Stability",
    "instructor": "You",
    "module": "The Emergence of the Holobiont: Constraint and Integration",
    "activity": "Streamlit Lab",
    "keywords": "nitrogen flux, feedback closure, termite",
    "notes": "Termite social digestion and trophallaxis. Streamlit model demonstrates emergent function through group behavior. Scale transitions from individual to collective.",
    "connect_with": "W4-Th"
  },
  {
    "session_id": "W4-Th",
    "date": "2/5/2026",
    "title": "Integration vs Vulnerability",
    "instructor": "You",
    "module": "Transition to M3",
    "activity": "Discussion",
    "keywords": "autonomy, fragility, robustness",
    "notes": "Explore effects of group size, redundancy, and task-sharing. Discuss concepts of distributed control and efficiency plateaus using the trophallaxis simulator.",
    "connect_with": "W5-Tu"
  },
  {
    "session_id": "W5-Tu",
    "date": "2/10/2026",
    "title": "Host-Damage Response Framework",
    "instructor": "You",
    "module": "Pathogenic Hijack: Robustness and Vulnerability",
    "activity": "Lecture",
    "keywords": "pathogen, robustness, feedback failure, Casadevall",
    "notes": "Introduce host-pathogen models; immune–microbe tradeoffs. Damage-response framework introduced. Class discussion on ecological context of virulence.",
    "connect_with": "W5-Th"
  },
  {
    "session_id": "W5-Th",
    "date": "2/12/2026",
    "title": "Pathogen as Probe of System Structure",
    "instructor": "You",
    "module": "Pathogenic Hijack: Robustness and Vulnerability",
    "activity": "Lab",
    "keywords": "Wolbachia, Massospora, immune feedback",
    "notes": "Students manipulate pathogen dose, microbiome composition, and host condition in a Streamlit model to explore survival vs. damage thresholds.",
    "connect_with": "W6-Tu"
  },
  {
    "session_id": "W6-Tu",
    "date": "2/17/2026",
    "title": "Wellness Day",
    "instructor": "You",
    "module": "-",
    "activity": "-",
    "keywords": "-",
    "notes": "Mini-presentations: students present behavior of simulation models with varied inputs. Discussion on parameter sensitivity and model structure.",
    "connect_with": "W6-Th"
  },
  {
    "session_id": "W6-Th",
    "date": "2/19/2026",
    "title": "Constraint Rewiring and Evolutionary Change",
    "instructor": "You",
    "module": "Evolutionary Transformation: Rewiring Constraint Networks",
    "activity": "Lecture",
    "keywords": "evolution, constraint network, Kemp",
    "notes": "Dashboard activity: compare constraint interaction across different simulation models (e.g., diet, social, pathogen). Emphasize modularity and integration.",
    "connect_with": "W7-Tu"
  },
  {
    "session_id": "W7-Tu",
    "date": "2/24/2026",
    "title": "Major Transitions and Constraint Substitution",
    "instructor": "You",
    "module": "Evolutionary Transformation: Rewiring Constraint Networks",
    "activity": "Reading Discussion",
    "keywords": "major transitions, substitution, social insect",
    "notes": "Species interactions during carrion decomposition. Blowfly and dermestid scenarios explored in simulated environment. Timing and priority effects.",
    "connect_with": "W7-Th"
  },
  {
    "session_id": "W7-Th",
    "date": "2/26/2026",
    "title": "Constraint Rewiring Simulation Workshop",
    "instructor": "You",
    "module": "Evolutionary Transformation: Rewiring Constraint Networks",
    "activity": "Streamlit Lab",
    "keywords": "simulation, network stability, rewiring",
    "notes": "Functional redundancy and role switching in communities. Use model to simulate control shifts when dominant decomposers are removed.",
    "connect_with": "W8-Tu"
  },
  {
    "session_id": "W8-Tu",
    "date": "3/3/2026",
    "title": "Midterm Synthesis and Bridge to Ecology",
    "instructor": "You",
    "module": "Transition to M5",
    "activity": "Discussion",
    "keywords": "constraint, ecology, resource pressure",
    "notes": "Add perturbations (e.g., pathogens, abiotic shifts) to previously stable models. Introduce resilience, stability landscapes, and attractor dynamics.",
    "connect_with": "W8-Th"
  },
  {
    "session_id": "W8-Th",
    "date": "3/5/2026",
    "title": "Resource Scarcity and Symbiosis",
    "instructor": "You",
    "module": "Resource Drives and Ecological Constraint",
    "activity": "Lecture",
    "keywords": "autocatalytic set, niche construction, resource constraint",
    "notes": "Student-led model edits. Each group proposes new configuration, justifies it, and tests the emergent outcomes in the Streamlit framework.",
    "connect_with": "W10-Tu"
  },
  {
    "session_id": "W9",
    "date": "3/10/2026",
    "title": "Spring Break",
    "instructor": "You",
    "module": "-",
    "activity": "-",
    "keywords": "-",
    "notes": "No class.",
    "connect_with": "-"
  },
  {
    "session_id": "W10-Tu",
    "date": "3/17/2026",
    "title": "Nitrogen Flux Model Workshop",
    "instructor": "You",
    "module": "Resource Drives and Ecological Constraint",
    "activity": "Streamlit Lab",
    "keywords": "nitrogen limitation, fermentation, termite, cockroach",
    "notes": "Gas flux dashboard: students examine cross-system outputs (NH3, CH4, CO2). Compare diet, group size, species. Emergence across nested systems.",
    "connect_with": "W10-Th"
  },
  {
    "session_id": "W10-Th",
    "date": "3/19/2026",
    "title": "Phloem and Sugar Symbioses",
    "instructor": "You",
    "module": "Resource Drives and Ecological Constraint",
    "activity": "Mini Lab",
    "keywords": "aphid, ant, sugar metabolism, amino acid",
    "notes": "Interpret patterns. Discussion on flow-through systems as energy/material processors. Students reflect on limits of inference across systems.",
    "connect_with": "W11-Tu"
  },
  {
    "session_id": "W11-Tu",
    "date": "3/24/2026",
    "title": "From Resource Constraint to Convergence",
    "instructor": "You",
    "module": "Transition to M6",
    "activity": "Seminar",
    "keywords": "constraint grammar, convergence",
    "notes": "Construct feedback networks linking multiple biological scales. Systems bootstrapping. Simulation of feedback across levels using custom diagrams.",
    "connect_with": "W11-Th"
  },
  {
    "session_id": "W11-Th",
    "date": "3/26/2026",
    "title": "Functional Convergence in Gut Designs",
    "instructor": "You",
    "module": "Convergence and Divergence",
    "activity": "Lecture",
    "keywords": "convergence, attractor, evolvability",
    "notes": "Constraint rewiring: loss or change of control mechanisms in systems. Explore repair vs. rewiring in models of microbial succession or pathogenesis.",
    "connect_with": "W12-Tu"
  },
  {
    "session_id": "W12-Tu",
    "date": "3/31/2026",
    "title": "Divergence and Alternative Stable States",
    "instructor": "You",
    "module": "Convergence and Divergence",
    "activity": "Discussion",
    "keywords": "divergence, stable state, innovation",
    "notes": "Final project sprint I. Students select a system level and design a new simulation-based inquiry. Justify variables, feedbacks, and expected flows.",
    "connect_with": "W12-Th"
  },
  {
    "session_id": "W12-Th",
    "date": "4/2/2026",
    "title": "Cross-Lineage Constraint Grammar Workshop",
    "instructor": "You",
    "module": "Convergence and Divergence",
    "activity": "Workshop",
    "keywords": "constraint grammar, comparative evolution",
    "notes": "Final project sprint II. Instructor and peer feedback. Prepare short walkthrough + explanation of logic and simulated outcomes.",
    "connect_with": "W13-Tu"
  },
  {
    "session_id": "W13-Tu",
    "date": "4/7/2026",
    "title": "From Convergence to Planetary Feedbacks",
    "instructor": "You",
    "module": "Transition to M7",
    "activity": "Lecture",
    "keywords": "scaling, feedback, constraint coupling",
    "notes": "Student presentations (Group A). Focus on systems representation, theory integration, and clarity of simulated design.",
    "connect_with": "W13-Th"
  },
  {
    "session_id": "W13-Th",
    "date": "4/9/2026",
    "title": "Gaia Theory and Planetary Coherence",
    "instructor": "You",
    "module": "Nested Systems and Planetary Coherence",
    "activity": "Lecture + Streamlit Model",
    "keywords": "Gaia, teleodynamics, planetary homeostasis",
    "notes": "Student presentations (Group B). As above. Peer and instructor scoring.",
    "connect_with": "W14-Tu"
  },
  {
    "session_id": "W14-Tu",
    "date": "4/14/2026",
    "title": "Integrating Gut to Globe Feedbacks",
    "instructor": "You",
    "module": "Nested Systems and Planetary Coherence",
    "activity": "Workshop",
    "keywords": "integration, scaling, resilience",
    "notes": "Synthesis discussion: What defines a system? How do microbial partners shape boundaries, constraints, and outcomes?",
    "connect_with": "W14-Th"
  },
  {
    "session_id": "W14-Th",
    "date": "4/16/2026",
    "title": "Capstone Studio I - Model Rewiring",
    "instructor": "You",
    "module": "Capstone Studio",
    "activity": "In-Class Project",
    "keywords": "rewiring, stability, innovation",
    "notes": "Guest lecture (tentative): microbial symbiosis in biotech. Open reflection on usefulness and limits of systems thinking.",
    "connect_with": "W15-Tu"
  },
  {
    "session_id": "W15-Tu",
    "date": "4/21/2026",
    "title": "Capstone Studio II - Peer Review",
    "instructor": "You",
    "module": "Capstone Studio",
    "activity": "Poster Session",
    "keywords": "evaluation, synthesis, feedback design",
    "notes": "Conceptual quiz: draw or describe system structure and behavior. In-class one-on-one explanations. Simulation logic check.",
    "connect_with": "W15-Th"
  },
  {
    "session_id": "W15-Th",
    "date": "4/23/2026",
    "title": "Final Capstone Presentations",
    "instructor": "You",
    "module": "Capstone Studio",
    "activity": "Presentation",
    "keywords": "integration, synthesis, systems grammar",
    "notes": "Final wrap-up. Students write course feedback. Recap on autonomy, feedback, constraint, emergence across all levels.",
    "connect_with": "W16-Tu"
  },
  {
    "session_id": "W16-Tu",
    "date": "4/28/2026",
    "title": "Reflection Colloquium - From Gut to Gaia",
    "instructor": "You",
    "module": "Course Wrap-Up",
    "activity": "Discussion",
    "keywords": "reflection, coherence, feedback grammar",
    "notes": "Integrate concepts from individual to planetary scale; discuss future directions.",
    "connect_with": "-"
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
st.set_page_config(layout="wide", page_title="ENT-591/791-006 | Insect–Microbe Systems Explorer")
st.title("Insect–Microbe Systems — Course Explorer")
st.caption("ENT-591/791-006 • Spring 2026 • Tuesdays & Thursdays • 1:30 to 2:45 • 01406  Gardner Hall (Main Campus)")
st.caption("Dr. Aram Mikaelyan • Entomology and Plant Pathology (NCSU)")
st.caption("This course examines insects and their microbes as integrated biological systems, moving from individual feedback and flow to holobiont organization, pathogenic disruption, and evolutionary transformation of constraint networks. Students analyze how resource regimes, ecological pressures, and long-term system dynamics shape convergence and divergence across insect–microbe lineages. The capstone synthesizes these ideas into a consistent systems framework that links physiology, evolution, and planetary-scale ecological coherence.")

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
