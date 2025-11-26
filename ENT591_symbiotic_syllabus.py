from __future__ import annotations
import io
import json
import pandas as pd
import networkx as nx
from pyvis.network import Network
import streamlit as st

# ---------------------------------------------------------
# 1. DATA – updated with graded flag
# ---------------------------------------------------------
DATA_JSON = r"""
[
  {
    "session_id": "W1-Tu",
    "date": "1/13/2026",
    "title": "Course Introduction & Systems Bootcamp I",
    "instructor": "Mikaelyan",
    "module": "The Individual as a System: Feedback and Flow",
    "activity": "Lecture",
    "keywords": "feedback, dissipative structure, cybernetics, termite gut",
    "notes": "Course overview; systems framing using insect‑microbe examples. Discuss autonomy, feedback, openness. Introduce course expectations. Begin discussion of systems as defined by Prigogine and Wiener.",
    "connect_with": "W1-Th",
    "theory": "We introduce Ashby's cybernetics and Prigogine's dissipative structures to frame an insect as a feedback‑controlled, far‑from‑equilibrium system, using Meadows' stocks and flows to show how physiology is continuous regulation of flux.",
    "graded": false
  },
  {
    "session_id": "W1-Th",
    "date": "1/15/2026",
    "title": "Systems Bootcamp II - Mapping Feedback Flow",
    "instructor": "Mikaelyan",
    "module": "The Individual as a System: Feedback and Flow",
    "activity": "Workshop",
    "keywords": "flow, homeostasis, trophallaxis, colony stability",
    "notes": "Explore feedback via visual loops and interactive tools. Introduce cybernetics and feedback via Wiener; students simulate simple positive/negative loops in Streamlit using digestive and behavioral analogies.",
    "connect_with": "W2-Tu",
    "theory": "We use Schrödinger's neg‑entropy and Ashby's law of requisite variety to show that boundaries (cuticle, tracheae, gut) are constraints that reduce environmental possibilities so control becomes energetically affordable.",
    "graded": false
  },
  {
    "session_id": "W2-Tu",
    "date": "1/20/2026",
    "title": "Simulation Lab: Termite Gut Flows",
    "instructor": "Mikaelyan",
    "module": "The Individual as a System: Feedback and Flow",
    "activity": "Lab",
    "keywords": "simulation, redox, microbial syntrophy, termite",
    "notes": "Introduce stocks and flows. Students explore flow‑through insect gut models using Streamlit sandbox. Framing via metabolic networks and resource bottlenecks.",
    "connect_with": "W2-Th",
    "theory": "Meadows' stock‑flow formalism and Lotka‑Odum energetics are applied to a termite gut model so students can see how feedback and throughput stabilize redox and nutrient gradients in a dissipative structure.",
    "graded": true,
    "assessment_type": "lab"
  },
  {
    "session_id": "W2-Th",
    "date": "1/22/2026",
    "title": "From Feedback to Constraint - Defining Boundaries",
    "instructor": "Mikaelyan",
    "module": "Transition to M2",
    "activity": "Discussion",
    "keywords": "feedback, constraint, individuality",
    "notes": "Constraint closure and autonomy in the holobiont. Streamlit model of host‑microbe bottlenecks. Waddington's landscape introduced for multi‑variable constraint interaction.",
    "connect_with": "W3-Tu",
    "theory": "Wagner's constraint‑closure theory and Kauffman's autocatalytic sets are introduced to formalize how repeated feedback hardens into architecture, with Vermeij's forbidden phenotypes as evidence that past successes canalize future evolutionary options.",
    "graded": false
  },
  {
    "session_id": "W3-Tu",
    "date": "1/27/2026",
    "title": "Constraint Closure and Autonomy",
    "instructor": "Mikaelyan",
    "module": "The Emergence of the Holobiont: Constraint and Integration",
    "activity": "Lecture",
    "keywords": "constraint closure, canalization, autonomy, Kauffman",
    "notes": "Model gut retention and resource availability via diet in cockroaches. Students manipulate inputs like pH, fiber content, retention time. Systems framing: input‑processing‑output chains.",
    "connect_with": "W3-Th",
    "theory": "We develop holobiont autonomy using Moreno‑Mossio style constraint closure and Deacon's idea of coupled constraints, treating the insect‑microbe system as a self‑maintaining organization rather than a host plus add‑ons.",
    "graded": false
  },
  {
    "session_id": "W3-Th",
    "date": "1/29/2026",
    "title": "Case Study: Holobiont as System",
    "instructor": "Mikaelyan",
    "module": "The Emergence of the Holobiont: Constraint and Integration",
    "activity": "Case Discussion",
    "keywords": "robustness, holobiont, nitrogen cycle, symbiosis",
    "notes": "Instructor check‑ins and one‑on‑one explanations. In‑class feedback used for formative grading. Discussion of emergent properties from varying initial constraints.",
    "connect_with": "W4-Tu",
    "theory": "Rosen's metabolism‑repair intuition and Deacon's teleodynamics are used qualitatively to analyze a real holobiont case, highlighting how coupled constraints across host tissues and microbes sustain identity over perturbations.",
    "graded": false
  },
  {
    "session_id": "W4-Tu",
    "date": "2/3/2026",
    "title": "Nitrogen Flux and System Stability",
    "instructor": "Mikaelyan",
    "module": "The Emergence of the Holobiont: Constraint and Integration",
    "activity": "Streamlit Lab",
    "keywords": "nitrogen flux, feedback closure, termite",
    "notes": "Termite social digestion and trophallaxis. Streamlit model demonstrates emergent function through group behavior. Scale transitions from individual to collective.",
    "connect_with": "W4-Th",
    "theory": "Lotka‑Odum ecosystem energetics and Arditi & Ginzburg's consumer‑resource theory frame nitrogen flux as an outer feedback that writes ecological constraint onto termite gut morphology, community composition, and behavior.",
    "graded": true,
    "assessment_type": "lab"
  },
  {
    "session_id": "W4-Th",
    "date": "2/5/2026",
    "title": "Integration vs Vulnerability",
    "instructor": "Mikaelyan",
    "module": "Transition to M3",
    "activity": "Discussion",
    "keywords": "autonomy, fragility, robustness",
    "notes": "Explore effects of group size, redundancy, and task‑sharing. Discuss concepts of distributed control and efficiency plateaus using the trophallaxis simulator.",
    "connect_with": "W5-Tu",
    "theory": "Kitano's robustness‑fragility trade‑off and Holling's resilience concepts help students interpret integration versus vulnerability, showing how redundancy and modularity in insect‑microbe networks buffer shocks but create new failure modes.",
    "graded": false
  },
  {
    "session_id": "W5-Tu",
    "date": "2/10/2026",
    "title": "Host-Damage Response Framework",
    "instructor": "Mikaelyan",
    "module": "Pathogenic Hijack: Robustness and Vulnerability",
    "activity": "Lecture",
    "keywords": "pathogen, robustness, feedback failure, Casadevall",
    "notes": "Introduce host‑pathogen models; immune‑microbe tradeoffs. Damage‑response framework introduced. Class discussion on ecological context of virulence.",
    "connect_with": "W5-Th",
    "theory": "Casadevall and Pirofski's damage‑response framework recasts infection as a systems‑level outcome of host‑microbe feedback, revealing how the same microbe can be commensal or lethal depending on where constraints and setpoints sit.",
    "graded": false
  },
  {
    "session_id": "W5-Th",
    "date": "2/12/2026",
    "title": "Pathogen as Probe of System Structure",
    "instructor": "Mikaelyan",
    "module": "Pathogenic Hijack: Robustness and Vulnerability",
    "activity": "Lab",
    "keywords": "Wolbachia, Massospora, immune feedback",
    "notes": "Students manipulate pathogen dose, microbiome composition, and host condition in a Streamlit model to explore survival vs. damage thresholds.",
    "connect_with": "W6-Tu",
    "theory": "We treat pathogens as experimental probes of system structure, using the damage‑response framework plus basic multilevel selection logic to show how fitness can be misaligned between microbe, individual insect, and colony.",
    "graded": true,
    "assessment_type": "lab"
  },
  {
    "session_id": "W6-Tu",
    "date": "2/17/2026",
    "title": "Wellness Day",
    "instructor": "Mikaelyan",
    "module": "-",
    "activity": "-",
    "keywords": "-",
    "notes": "Mini‑presentations: students present behavior of simulation models with varied inputs. Discussion on parameter sensitivity and model structure.",
    "connect_with": "W6-Th",
    "theory": "Wellness day — no new theoretical content is introduced; students consolidate earlier systems and constraint frameworks.",
    "graded": false
  },
  {
    "session_id": "W6-Th",
    "date": "2/19/2026",
    "title": "Constraint Rewiring and Evolutionary Change",
    "instructor": "Mikaelyan",
    "module": "Evolutionary Transformation: Rewiring Constraint Networks",
    "activity": "Lecture",
    "keywords": "evolution, constraint network, Kemp",
    "notes": "Dashboard activity: compare constraint interaction across different simulation models (e.g. diet, social, pathogen). Emphasize modularity and integration.",
    "connect_with": "W7-Tu",
    "theory": "Wagner's theory of evolvability and Vermeij's evolutionary constraint ideas ground our view of innovation as constraint rewiring, where lineages reorganize developmental and ecological couplings to access previously forbidden phenotypes.",
    "graded": false
  },
  {
    "session_id": "W7-Tu",
    "date": "2/24/2026",
    "title": "Major Transitions and Constraint Substitution",
    "instructor": "Mikaelyan",
    "module": "Evolutionary Transformation: Rewiring Constraint Networks",
    "activity": "Reading Discussion",
    "keywords": "major transitions, substitution, social insect",
    "notes": "Species interactions during carrion decomposition. Blowfly and dermestid scenarios explored in simulated environment. Timing and priority effects.",
    "connect_with": "W7-Th",
    "theory": "Szathmáry & Maynard Smith's major transitions theory and multilevel selection are applied to insect‑microbe systems, showing how social digestion and symbiosis create new levels of individuality and new arenas for selection.",
    "graded": false
  },
  {
    "session_id": "W7-Th",
    "date": "2/26/2026",
    "title": "Constraint Rewiring Simulation Workshop",
    "instructor": "Mikaelyan",
    "module": "Evolutionary Transformation: Rewiring Constraint Networks",
    "activity": "Streamlit Lab",
    "keywords": "simulation, network stability, rewiring",
    "notes": "Functional redundancy and role switching in communities. Use model to simulate control shifts when dominant decomposers are removed.",
    "connect_with": "W8-Tu",
    "theory": "We implement simple agent‑based and differential models so students can see constraint rewiring generate new attractors, making concrete the idea that evolution explores configuration space under structural limits.",
    "graded": true,
    "assessment_type": "lab"
  },
  {
    "session_id": "W8-Tu",
    "date": "3/3/2026",
    "title": "Midterm Synthesis and Bridge to Ecology",
    "instructor": "Mikaelyan",
    "module": "Transition to M5",
    "activity": "Discussion",
    "keywords": "constraint, ecology, resource pressure",
    "notes": "Add perturbations (e.g. pathogens, abiotic shifts) to previously stable models. Introduce resilience, stability landscapes, and attractor dynamics.",
    "connect_with": "W8-Th",
    "theory": "This synthesis session explicitly connects all prior theories — cybernetics, constraint closure, robustness, damage‑response, evolvability, and major transitions — into one narrative of how insect‑microbe systems learn and persist.",
    "graded": true,
    "assessment_type": "synthesis"
  },
  {
    "session_id": "W8-Th",
    "date": "3/5/2026",
    "title": "Resource Scarcity and Symbiosis",
    "instructor": "Mikaelyan",
    "module": "Resource Drives and Ecological Constraint",
    "activity": "Lecture",
    "keywords": "autocatalytic set, niche construction, resource constraint",
    "notes": "Student‑led model edits. Each group proposes new configuration, justifies it, and tests the emergent outcomes in the Streamlit framework.",
    "connect_with": "W9-Tu",
    "theory": "Niche construction theory and Kauffman's autocatalytic sets frame resource scarcity and symbiosis as a coupled search: insects and microbes co-create constraint networks that stabilize metabolism under limiting nutrients.",
    "graded": false
  },
  {
    "session_id": "W9-Tu",
    "date": "3/10/2026",
    "title": "Spring Break",
    "instructor": "Mikaelyan",
    "module": "-",
    "activity": "-",
    "keywords": "-",
    "notes": "No class.",
    "connect_with": "-",
    "theory": "Spring Break — no class meeting and no new theory.",
    "graded": false
  },
  {
    "session_id": "W9-Th",
    "date": "3/12/2026",
    "title": "Spring Break",
    "instructor": "Mikaelyan",
    "module": "-",
    "activity": "-",
    "keywords": "-",
    "notes": "No class.",
    "connect_with": "W10-Tu",
    "theory": "Spring Break — no class meeting and no new theory.",
    "graded": false
  },
  {
    "session_id": "W10-Tu",
    "date": "3/17/2026",
    "title": "Nitrogen Flux Model Workshop",
    "instructor": "Mikaelyan",
    "module": "Resource Drives and Ecological Constraint",
    "activity": "Streamlit Lab",
    "keywords": "nitrogen limitation, fermentation, termite, cockroach",
    "notes": "Gas flux dashboard: students examine cross‑system outputs (NH3, CH4, CO2). Compare diet, group size, species. Emergence across nested systems.",
    "connect_with": "W10-Th",
    "theory": "We extend Lotka‑Odum energetics and consumer‑resource theory into a hands‑on nitrogen flux model, helping students see how constraint at the resource level channels coexistence, competition, and potential convergence.",
    "graded": true,
    "assessment_type": "lab"
  },
  {
    "session_id": "W10-Th",
    "date": "3/19/2026",
    "title": "Phloem and Sugar Symbioses",
    "instructor": "Mikaelyan",
    "module": "Resource Drives and Ecological Constraint",
    "activity": "Mini Lab",
    "keywords": "aphid, ant, sugar metabolism, amino acid",
    "notes": "Interpret patterns. Discussion on flow‑through systems as energy/material processors. Students reflect on limits of inference across systems.",
    "connect_with": "W11-Tu",
    "theory": "Mutualism economics à la Douglas and simple consumer‑resource models are used to analyse phloem and sugar symbioses, highlighting how trading partners share and shift constraints on carbon and nitrogen processing.",
    "graded": false
  },
  {
    "session_id": "W11-Tu",
    "date": "3/24/2026",
    "title": "From Resource Constraint to Convergence",
    "instructor": "Mikaelyan",
    "module": "Transition to M6",
    "activity": "Seminar",
    "keywords": "constraint grammar, convergence",
    "notes": "Construct feedback networks linking multiple biological scales. Systems bootstrapping. Simulation of feedback across levels using custom diagrams.",
    "connect_with": "W11-Th",
    "theory": "We introduce convergence as evidence of underlying constraint grammar, using Simpson's adaptive peaks and Wagner's constraint networks to argue that similar pressures plus similar constraints yield similar insect‑microbe designs.",
    "graded": false
  },
  {
    "session_id": "W11-Th",
    "date": "3/26/2026",
    "title": "Functional Convergence in Gut Designs",
    "instructor": "Mikaelyan",
    "module": "Convergence and Divergence",
    "activity": "Lecture",
    "keywords": "convergence, attractor, evolvability",
    "notes": "Constraint rewiring: loss or change of control mechanisms in systems. Explore repair vs. rewiring in models of microbial succession or pathogenesis.",
    "connect_with": "W12-Tu",
    "theory": "Comparative gut designs in termites, passalids, and other wood‑feeders are read through convergence theory and correlated progression (Kemp), emphasising how repeated modules, not identical genes, explain functional similarity.",
    "graded": false
  },
  {
    "session_id": "W12-Tu",
    "date": "3/31/2026",
    "title": "Divergence and Alternative Stable States",
    "instructor": "Mikaelyan",
    "module": "Convergence and Divergence",
    "activity": "Discussion",
    "keywords": "divergence, stable state, innovation",
    "notes": "Final project sprint I. Students select a system level and design a new simulation‑based inquiry. Justify variables, feedbacks, and expected flows.",
    "connect_with": "W12-Th",
    "theory": "Gould's historical contingency and Wagner's lineage‑specific constraints explain why similar ecological problems can produce divergent holobiont architectures and alternative stable states in gut communities.",
    "graded": false
  },
  {
    "session_id": "W12-Th",
    "date": "4/2/2026",
    "title": "Cross‑Lineage Constraint Grammar Workshop",
    "instructor": "Mikaelyan",
    "module": "Convergence and Divergence",
    "activity": "Workshop",
    "keywords": "constraint grammar, comparative evolution",
    "notes": "Final project sprint II. Instructor and peer feedback. Prepare short walkthrough + explanation of logic and simulated outcomes.",
    "connect_with": "W13-Tu",
    "theory": "We treat 'constraint grammar' explicitly, asking students to map which developmental, ecological, and symbiotic constraints can be substituted, combined, or held fixed to generate the observed space of insect‑microbe solutions.",
    "graded": false
  },
  {
    "session_id": "W13-Tu",
    "date": "4/7/2026",
    "title": "From Convergence to Planetary Feedbacks",
    "instructor": "Mikaelyan",
    "module": "Transition to M7",
    "activity": "Lecture",
    "keywords": "scaling, feedback, constraint coupling",
    "notes": "Student presentations (Group A). Focus on systems representation, theory integration, and clarity of simulated design.",
    "connect_with": "W13-Th",
    "theory": "Odum's ecosystem energetics and Lovelock's Gaia hypothesis are reframed through insects, casting decomposer guilds and their microbes as distributed constraint networks that help stabilise planetary carbon and nutrient fluxes.",
    "graded": false
  },
  {
    "session_id": "W13-Th",
    "date": "4/9/2026",
    "title": "Gaia Theory and Planetary Coherence",
    "instructor": "Mikaelyan",
    "module": "Nested Systems and Planetary Coherence",
    "activity": "Lecture + Streamlit Model",
    "keywords": "Gaia, teleodynamics, planetary homeostasis",
    "notes": "Student presentations (Group B). As above. Peer and instructor scoring.",
    "connect_with": "W14-Tu",
    "theory": "We make Gaia concrete by connecting constraint closure and multilevel feedback to real insect‑driven biogeochemical cycles, arguing that biospheric coherence emerges from countless local insect‑microbe control systems.",
    "graded": false
  },
  {
    "session_id": "W14-Tu",
    "date": "4/14/2026",
    "title": "Integrating Gut to Globe Feedbacks",
    "instructor": "Mikaelyan",
    "module": "Nested Systems and Planetary Coherence",
    "activity": "Workshop",
    "keywords": "integration, scaling, resilience",
    "notes": "Synthesis discussion: What defines a system? How do microbial partners shape boundaries, constraints, and outcomes?",
    "connect_with": "W14-Th",
    "theory": "Students integrate gut‑scale, colony‑scale, and ecosystem‑scale models to see how constraints propagate across levels, making Levin's hierarchy theory tangible in insect‑microbe and decomposer‑guild examples.",
    "graded": false
  },
  {
    "session_id": "W14-Th",
    "date": "4/16/2026",
    "title": "Capstone Studio I - Model Rewiring",
    "instructor": "Mikaelyan",
    "module": "Capstone Studio",
    "activity": "In‑Class Project",
    "keywords": "rewiring, stability, innovation",
    "notes": "Guest lecture (tentative): microbial symbiosis in biotech. Open reflection on usefulness and limits of systems thinking.",
    "connect_with": "W15-Tu",
    "theory": "Capstone Studio I uses all prior theories — constraint closure, robustness, niche construction, convergence/divergence, and evolutionary learning — as a design language for proposing and critiquing model rewiring.",
    "graded": false
  },
  {
    "session_id": "W15-Tu",
    "date": "4/21/2026",
    "title": "Capstone Studio II - Peer Review",
    "instructor": "Mikaelyan",
    "module": "Capstone Studio",
    "activity": "Poster Session",
    "keywords": "evaluation, synthesis, feedback design",
    "notes": "Conceptual quiz: draw or describe system structure and behavior. In‑class one‑on‑one explanations. Simulation logic check.",
    "connect_with": "W15-Th",
    "theory": "During peer review, students evaluate each other's capstones explicitly on how well they operationalise the course's systems theories and make constraint structures, feedbacks, and evolutionary possibilities legible.",
    "graded": true,
    "assessment_type": "peer_review"
  },
  {
    "session_id": "W15-Th",
    "date": "4/23/2026",
    "title": "Final Capstone Presentations",
    "instructor": "Mikaelyan",
    "module": "Capstone Studio",
    "activity": "Presentation",
    "keywords": "integration, synthesis, systems grammar",
    "notes": "Final wrap‑up. Students write course feedback. Recap on autonomy, feedback, constraint, emergence across all levels.",
    "connect_with": "W16-Tu",
    "theory": "Final capstone presentations require students to narrate their focal system using the full theoretical stack from the course, effectively demonstrating fluency in constraint‑centred systems thinking for insect‑microbe interactions.",
    "graded": true,
    "assessment_type": "final_presentation"
  },
  {
    "session_id": "W16-Tu",
    "date": "4/28/2026",
    "title": "Reflection Colloquium - From Gut to Gaia",
    "instructor": "Mikaelyan",
    "module": "Course Wrap-Up",
    "activity": "Discussion",
    "keywords": "reflection, coherence, feedback grammar",
    "notes": "Integrate concepts from individual to planetary scale; discuss future directions.",
    "connect_with": "-",
    "theory": "We close by making explicit how thermodynamic, informational, developmental, ecological, and evolutionary constraints form a coherent grammar of life, and ask students to reflect on how insect‑microbe systems instantiate that grammar.",
    "graded": false
  }
]
"""

# Load data
df = pd.read_json(io.StringIO(DATA_JSON))
df = df.fillna("")

def clean_kw(s): 
    return [k.strip().lower() for k in str(s).replace(";", ",").split(",") if k.strip()]
def split_ids(s): 
    return [x.strip() for x in str(s).split(",") if x.strip()]

# ---------------------------------------------------------
# Themes
# ---------------------------------------------------------
THEME_KEYWORDS = {
    "Feedback": {"feedback","cybernetics","flow","homeostasis","neg-entropy","regulation","stability","trophallaxis"},
    "Constraint": {"constraint","constraint closure","canalization","boundary","autonomy","architecture","individuality"},
    "Evolution": {"evolution","rewiring","innovation","divergence","convergence","major transitions","multilevel"},
    "Symbiosis": {"symbiosis","holobiont","mutualism","pathogen","microbe","microbiome","syntrophy","commensal"},
    "Robustness": {"robustness","fragility","resilience","vulnerability","failure","redundancy","buffering"},
    "Resource Flux": {"nitrogen","carbon","resource","amino acid","fermentation","redox","gas flux"}
}
def assign_themes(keywords):
    ks = set(keywords)
    return sorted({theme for theme, kws in THEME_KEYWORDS.items() if ks & kws})

# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="ENT-591/791-006 | Insect–Microbe Systems Explorer")
st.markdown("<h2 style='margin-bottom: 0.5em;'>Symbiotic Stories: Battles, Bonds, and Beyond</h2>", unsafe_allow_html=True)
st.caption("Spring 2026 • Dr. Aram Mikaelyan (Entomology and Plant Pathology, NCSU) • Gardner Hall, 1406")
st.caption("[Check out the Mikaelyan Lab](https://www.mikaelyanlab.com)")

with st.sidebar:
    st.header("Network Settings")
    min_shared = st.slider("Min shared keywords", 1, 5, 1)
    include_manual = st.checkbox("Include manual connects", True)
    color_mode = st.selectbox("Color nodes by:", ["Module", "Theme", "Graded"])
    selected_theme = st.multiselect("Filter by conceptual theme(s):", list(THEME_KEYWORDS.keys()))

tab_data, tab_graph, tab_syllabus = st.tabs(["Session Table", "Graph Explorer", "Syllabus & Grading"])

with tab_syllabus:
    st.markdown("""
    ## ENT-591/791-006: Insect–Microbe Systems  
    **Spring 2026 • Dr. Aram Mikaelyan**  
    Tuesdays & Thursdays • 1:30–2:45 PM • 01406 Gardner Hall  

    ### Course Description
    This course explores insects and their microbial partners as integrated, multi-level systems — from individual physiology to planetary biogeochemistry — using a **constraint-centered systems framework**. We move from feedback and flow within individuals, through holobiont emergence and pathogenic disruption, to evolutionary rewiring of constraint networks and convergence/divergence across lineages.

    ### Learning Objectives
    By the end of the course, students will be able to:
    - Model insect–microbe interactions using stocks, flows, feedback loops, and constraint closure
    - Interpret symbiosis, pathogenesis, and social digestion as outcomes of system-level dynamics
    - Explain robustness/fragility trade-offs and evolutionary innovation via constraint rewiring
    - Connect gut-to-Gaia processes through nested feedback and constraint propagation

    ### Graded Components
    | Component                     | Weight | Description |
    |-------------------------------|--------|-----------|
    | **Lab Reports & Simulations** | 40%    | 6 graded Streamlit labs (W2-Tu, W4-Tu, W5-Th, W7-Th, W10-Tu) + midterm synthesis (W8-Tu) |
    | **Capstone Project**          | 40%    | Multi-week simulation-based inquiry: design, peer review (W15-Tu), final presentation (W15-Th) |
    | **Participation & Reflection**| 20%    | In-class contributions, discussions, mini-presentations, final colloquium |

    **Graded sessions are highlighted in red** in the Graph Explorer when "Color nodes by: Graded" is selected.

    ### Policies
    - **Academic Integrity:** Students are expected to engage honestly and thoughtfully in all in-class activities, discussions, and simulation exercises. Representing others' ideas or results as your own during model walkthroughs or group discussions is a violation of course expectations. Collaboration is encouraged where appropriate, but each student must be able to explain and defend the design and logic of any models or feedback systems they present.
    - **Attendance & Participation:** Consistent, active participation is required. Because assessments are embedded in class sessions, absences may directly impact your grade. If you must miss class for a documented reason, contact the instructor as early as possible to arrange a plan.
    - **Use of AI Tools:** Generative AI tools (e.g., ChatGPT, NotebookLM) may be used for brainstorming or model design outside class if they help clarify systems thinking. However, students are expected to demonstrate personal understanding of all concepts presented in class. Overreliance on AI output without comprehension may be treated as academic dishonesty.
    - **Accommodations:** Contact instructor and ODA early
    - **Professional Conduct:** This course thrives on mutual respect and curiosity. Disruptive or dismissive behavior, especially during peer walkthroughs or group critique, undermines the collaborative learning environment and may impact your participation grade.

    ### Required Tools
    - **Laptop** (required for all class sessions)
    - **Web browser** with JavaScript enabled (Chrome or Firefox recommended)
    - **Google Chat** for group communication with the instructor and class
    - No programming or software installation is required. All simulation work will take place via in-class Streamlit applications provided by the instructor.

    ### Course Materials
    - **Moodle** will be used to organize and distribute readings, session notes, and supplemental materials.
    - **Communication:** Google Chat will be used for real-time updates, announcements, and informal Q&A. Students are encouraged to use it to share class-relevant insights, follow-up questions, and general logistical concerns.
        **Please use Moodle messaging or email for private or grade-related issues.**
    """, unsafe_allow_html=True)

    

with tab_data:
    st.dataframe(df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------
# Graph Construction
# ---------------------------------------------------------
with tab_graph:
    G = nx.Graph()
    for _, row in df.iterrows():
        kws = clean_kw(row["keywords"])
        d = row.to_dict()
        d["keywords"] = kws
        d["themes"] = assign_themes(kws)
        G.add_node(row["session_id"], **d)

    # Theme filter
    if selected_theme:
        nodes = [n for n in G.nodes() if set(G.nodes[n]["themes"]) & set(selected_theme)]
        G = G.subgraph(nodes).copy()
    else:
        nodes = list(G.nodes())

    # Edges from shared keywords
    for i in range(len(nodes)):
        for j in range(i+1, len(nodes)):
            a, b = nodes[i], nodes[j]
            shared = len(set(G.nodes[a]["keywords"]) & set(G.nodes[b]["keywords"]))
            if shared >= min_shared:
                G.add_edge(a, b)

    # Manual connects
    if include_manual:
        for n in nodes:
            for m in split_ids(G.nodes[n]["connect_with"]):
                if m in nodes and m != n:
                    G.add_edge(n, m)

    # ---------------------------------------------------------
    # Coloring
    # ---------------------------------------------------------
    modules = sorted(df["module"].unique())
    palette = ["#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd","#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf"]
    mod_cmap = {m: palette[i % len(palette)] for i, m in enumerate(modules)}

    theme_palette = {
        "Feedback": "#1f77b4","Constraint": "#ff7f0e","Evolution": "#2ca02c",
        "Symbiosis": "#d62728","Robustness": "#9467bd","Resource Flux": "#8c564b"
    }

    def node_color(d):
        if color_mode == "Module":
            return mod_cmap.get(d["module"], "#999")
        elif color_mode == "Theme":
            return theme_palette.get(d["themes"][0] if d["themes"] else None, "#999")
        else:  # Graded
            if d.get("module") == "-" or "break" in d["title"].lower():
                return "#a3c9f7"      # light blue – no class
            return "#e74c3c" if d.get("graded") else "#95a5a6"   # red / gray

    # ---------------------------------------------------------
    # PyVis Network
    # ---------------------------------------------------------
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
          {"<br><b>Graded: Yes (" + (d.get('assessment_type') or '') + ")</b>" if d.get('graded') else ""}
          <hr style='margin:6px 0;'>
          {d['notes']}
        </div>
        """
        net.add_node(
            node, label=node, title="", shape="dot", size=25,
            color=node_color(d), custom_html=html_tip
        )

    for u, v in G.edges():
        net.add_edge(u, v, color="#ccc")

    net.set_options("""
    {
      "interaction": { "hover": true, "navigationButtons": true },
      "physics": {
        "enabled": true,
        "stabilization": {"enabled": true, "iterations": 500},
        "barnesHut": {"springLength": 150}
      }
    }
    """)

    net.save_graph("graph.html")
    html = open("graph.html", "r", encoding="utf8").read()

    # Custom tooltip JS
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

    # ---------------------------------------------------------
    # Session Passport
    # ---------------------------------------------------------
    st.markdown("### Session Passport")
    sel = st.selectbox(
        "Choose session:",
        df["session_id"],
        format_func=lambda x: f"{x} — {df[df['session_id']==x]['title'].values[0]}"
    )
    d = df[df["session_id"] == sel].iloc[0]
    st.subheader(d["title"])
    st.write(f"**Date:** {d['date']}")
    st.write(f"**Module:** {d['module']}")
    st.write(f"**Activity:** {d['activity']}")
    if d.get("graded"):
        st.write(f"**Assessment:** {d.get('assessment_type','')}")
    st.write(f"**Keywords:** {d['keywords']}")
    st.write(f"**Notes:** {d['notes']}")
