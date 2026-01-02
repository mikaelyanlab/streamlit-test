import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
import datetime
import hashlib

# Constants
APP_TITLE = "Symbiotic Systems Lab: Unlocking Levels"
COURSE_NAME = "Symbiotic Stories: Battles, Bonds and Beyond"
INSTRUCTOR = "Dr. Aram Mikaelyan (North Carolina State University)"
THEME = "Symbiosis at the interface of resource utilization + systems theory (feedback, flow, constraints, robustness, rewiring)."
UNLOCK_FILE = "unlock_state.json"
DEFAULT_MAX_LEVEL = 0
LEVELS = {
    0: "Level 0: Systems Grammar Playground",
    1: "Level 1: Termite Gut Flows",
    2: "Level 2: Nitrogen Flux & Bottlenecks",
    3: "Level 3: Pathogen as Probe",
    4: "Level 4: Constraint Rewiring Studio",
    5: "Level 5: Convergence Skins",
    6: "Capstone Builder Mode"
}
PAGES = ["Home", "About / Theory Ladder", "Grading & Rubric", "Instructor Console"] + list(LEVELS.values())
PASSWORD_HASH = hashlib.sha256(b"password123").hexdigest()  # Change this in production

# Load or initialize unlock state
if os.path.exists(UNLOCK_FILE):
    with open(UNLOCK_FILE, 'r') as f:
        unlock_data = json.load(f)
    max_level_unlocked = unlock_data.get('max_level', DEFAULT_MAX_LEVEL)
else:
    max_level_unlocked = DEFAULT_MAX_LEVEL
    with open(UNLOCK_FILE, 'w') as f:
        json.dump({'max_level': max_level_unlocked}, f)

# Helper functions
def save_unlock_state(level):
    with open(UNLOCK_FILE, 'w') as f:
        json.dump({'max_level': level}, f)

def simulate_single_stock(params):
    dt = params['dt']
    total_time = params['total_time']
    steps = int(total_time / dt)
    X = np.zeros(steps)
    X[0] = params['initial_X']
    inflow = params['inflow']
    outflow_base = params['outflow']
    setpoint = params['setpoint']
    gain = params['gain']
    delay = params['delay']
    noise_amp = params['noise_amp']
    
    delayed_errors = [0] * delay
    for t in range(1, steps):
        error = setpoint - X[t-1]
        delayed_errors.append(error)
        delayed_error = delayed_errors.pop(0)
        adjustment = gain * delayed_error
        outflow = max(0, outflow_base - adjustment)  # Adjust outflow
        noise = np.random.normal(0, noise_amp)
        X[t] = max(0, X[t-1] + dt * (inflow - outflow + noise))
    return X

def simulate_gut_flows(params):
    dt = params['dt']
    total_time = params['total_time']
    steps = int(total_time / dt)
    S = np.zeros(steps)
    M = np.zeros(steps)
    P = np.zeros(steps)
    S[0] = params['initial_S']
    M[0] = params['initial_M']
    P[0] = params['initial_P']
    k_dep = params['k_dep']
    k_ferm = params['k_ferm']
    k_abs = params['k_abs']
    k_wash = 1 / params['retention_time']
    inhibition_P = params['inhibition_P']
    noise_amp = params['noise_amp']
    
    for t in range(1, steps):
        dep = k_dep * S[t-1]
        ferm = k_ferm * M[t-1] / (1 + P[t-1] / inhibition_P)
        abs_ = k_abs * P[t-1]
        wash_M = k_wash * M[t-1]
        wash_P = k_wash * P[t-1]
        noise_S = np.random.normal(0, noise_amp)
        noise_M = np.random.normal(0, noise_amp)
        noise_P = np.random.normal(0, noise_amp)
        
        S[t] = max(0, S[t-1] + dt * (-dep + noise_S))
        M[t] = max(0, M[t-1] + dt * (dep - ferm - wash_M + noise_M))
        P[t] = max(0, P[t-1] + dt * (ferm - abs_ - wash_P + noise_P))
    
    yield_ = np.sum(P) * dt
    stability = np.var(P[int(steps*0.8):])
    throughput = np.sum(ferm) * dt
    return S, M, P, {'yield': yield_, 'stability': stability, 'throughput': throughput}

def simulate_nitrogen(params):
    dt = params['dt']
    total_time = params['total_time']
    steps = int(total_time / dt)
    S = np.zeros(steps)
    M = np.zeros(steps)
    P = np.zeros(steps)
    N = np.zeros(steps)
    S[0] = params['initial_S']
    M[0] = params['initial_M']
    P[0] = params['initial_P']
    N[0] = params['initial_N']
    k_dep = params['k_dep']
    k_ferm = params['k_ferm']
    k_abs = params['k_abs']
    k_wash = 1 / params['retention_time']
    inhibition_P = params['inhibition_P']
    noise_amp = params['noise_amp']
    N_threshold = params['N_threshold']
    recycling_frac = params['recycling_frac'] if params['recycling'] else 0
    fixation_rate = params['fixation_rate'] if params['fixation'] else 0
    N_loss = params['N_loss']
    
    for t in range(1, steps):
        dep = k_dep * S[t-1]
        f_N = min(1, N[t-1] / N_threshold)
        ferm = k_ferm * M[t-1] * f_N / (1 + P[t-1] / inhibition_P)
        abs_ = k_abs * P[t-1]
        wash_M = k_wash * M[t-1]
        wash_P = k_wash * P[t-1]
        recycle_N = recycling_frac * (wash_M + wash_P)
        noise_S = np.random.normal(0, noise_amp)
        noise_M = np.random.normal(0, noise_amp)
        noise_P = np.random.normal(0, noise_amp)
        noise_N = np.random.normal(0, noise_amp)
        
        S[t] = max(0, S[t-1] + dt * (-dep + noise_S))
        M[t] = max(0, M[t-1] + dt * (dep - ferm - wash_M + noise_M))
        P[t] = max(0, P[t-1] + dt * (ferm - abs_ - wash_P + noise_P))
        N[t] = max(0, N[t-1] + dt * (fixation_rate + recycle_N - N_loss * N[t-1] + noise_N))
    
    yield_ = np.sum(P) * dt
    stability = np.var(P[int(steps*0.8):])
    throughput = np.sum(ferm) * dt
    limiting = 'N-limited' if np.mean(N[int(steps*0.8):]) < N_threshold else 'C-limited'
    canal_var = []  # For canalization: run multiple with noise
    for _ in range(5):
        params['noise_amp'] = noise_amp * 2  # Temp increase for test
        _, _, _, metrics = simulate_gut_flows(params)  # Reuse base sim for simplicity
        canal_var.append(metrics['yield'])
        params['noise_amp'] = noise_amp
    canalization = np.var(canal_var)
    return S, M, P, N, {'yield': yield_, 'stability': stability, 'throughput': throughput, 'limiting': limiting, 'canalization': canalization}

def simulate_pathogen(params):
    # Extend nitrogen sim with pathogen
    dt = params['dt']
    total_time = params['total_time']
    steps = int(total_time / dt)
    S = np.zeros(steps)
    M = np.zeros(steps)
    P = np.zeros(steps)
    N = np.zeros(steps)
    Path = np.zeros(steps)  # Pathogen load
    S[0] = params['initial_S']
    M[0] = params['initial_M']
    P[0] = params['initial_P']
    N[0] = params['initial_N']
    Path[0] = params['initial_Path']
    k_dep = params['k_dep']
    k_ferm = params['k_ferm']
    k_abs = params['k_abs']
    k_wash = 1 / params['retention_time']
    inhibition_P = params['inhibition_P']
    noise_amp = params['noise_amp']
    N_threshold = params['N_threshold']
    recycling_frac = params['recycling_frac'] if params['recycling'] else 0
    fixation_rate = params['fixation_rate'] if params['fixation'] else 0
    N_loss = params['N_loss']
    path_growth = params['path_growth']
    immune_intensity = params['immune_intensity']
    path_effect = params['path_effect']  # Steal M, reduce ferm
    
    for t in range(1, steps):
        path_load = Path[t-1] * (1 - immune_intensity * 0.5)  # Immune reduces path
        dep = k_dep * S[t-1]
        f_N = min(1, N[t-1] / N_threshold)
        ferm_red = max(0, 1 - path_load * path_effect)
        ferm = k_ferm * M[t-1] * f_N * ferm_red / (1 + P[t-1] / inhibition_P)
        steal_M = path_load * 0.1 * M[t-1]
        abs_ = k_abs * P[t-1]
        wash_M = k_wash * M[t-1]
        wash_P = k_wash * P[t-1]
        recycle_N = recycling_frac * (wash_M + wash_P)
        noise_S = np.random.normal(0, noise_amp)
        noise_M = np.random.normal(0, noise_amp)
        noise_P = np.random.normal(0, noise_amp)
        noise_N = np.random.normal(0, noise_amp)
        noise_Path = np.random.normal(0, noise_amp * 0.5)
        
        S[t] = max(0, S[t-1] + dt * (-dep + noise_S))
        M[t] = max(0, M[t-1] + dt * (dep - ferm - wash_M - steal_M + noise_M))
        P[t] = max(0, P[t-1] + dt * (ferm - abs_ - wash_P + noise_P))
        N[t] = max(0, N[t-1] + dt * (fixation_rate + recycle_N - N_loss * N[t-1] + noise_N))
        Path[t] = max(0, Path[t-1] + dt * (path_growth * Path[t-1] * (1 - immune_intensity)) + noise_Path)
    
    damage = 0.1 * np.mean(Path) + 0.05 * (immune_intensity ** 2) + 0.2 * (1 - np.mean(P)/params['setpoint_P'])
    yield_ = np.sum(P) * dt
    stability = np.var(P[int(steps*0.8):])
    var = np.var(P)
    sign_changes = np.sum(np.diff(np.sign(np.diff(P))) != 0)
    collapse = np.mean(P[int(steps*0.8):]) < 0.1 * params['setpoint_P']
    if collapse:
        failure = 'Collapse'
    elif sign_changes > 10 and var > 0.1:
        failure = 'Oscillatory'
    else:
        failure = 'Stable'
    return S, M, P, N, Path, {'yield': yield_, 'stability': stability, 'damage': damage, 'failure': failure}

def simulate_rewiring(params):
    # Extend pathogen sim with rewiring options
    cross_feed = params['cross_feed'] if params['cross_feed_on'] else 0
    redundancy = 2 if params['redundancy'] else 1
    guild_type = params['guild_type']  # 'high_fragile' or 'low_robust'
    host_control_str = params['host_control_str']
    cost = host_control_str * 0.1 + (1 if params['redundancy'] else 0) * 0.05
    if guild_type == 'high_fragile':
        params['k_ferm'] *= 1.2
        params['noise_amp'] *= 1.5
        params['inhibition_P'] /= 1.5
    else:
        params['k_ferm'] *= 0.8
        params['noise_amp'] /= 1.5
        params['inhibition_P'] *= 1.5
    
    params['k_abs'] *= (1 + host_control_str * 0.5)
    params['k_wash'] /= (1 + host_control_str * 0.5)
    
    S, M, P, N, Path, metrics = simulate_pathogen(params)
    # Add cross-feed: P feeds back to dep
    for t in range(1, len(S)):
        dep_bonus = cross_feed * P[t-1] * 0.01
        params['k_dep'] += dep_bonus  # Temp, but simulate fully would need re-sim
    
    # Re-sim with adjustments
    S, M, P, N, Path, metrics = simulate_pathogen(params)  # Approximate
    
    closure_score = sum([params['cross_feed_on'], params['recycling'], params['redundancy'], host_control_str > 0.5])
    metrics['cost'] = cost
    metrics['closure'] = closure_score
    return S, M, P, N, Path, metrics

def simulate_convergence(params, skin):
    if skin == 'phloem':
        params['initial_N'] /= 2  # N-poor
        params['k_ferm'] *= 0.8
    elif skin == 'carcass':
        params['initial_S'] *= 2  # Pulse
        params['inflow_S'] = 0  # No steady input
    # Multi-start
    yields = []
    for _ in range(10):
        params['initial_S'] += np.random.uniform(-0.5, 0.5) * params['initial_S']
        params['initial_M'] += np.random.uniform(-0.5, 0.5) * params['initial_M']
        S, M, P, N, Path, metrics = simulate_rewiring(params)  # Use full model
        yields.append(metrics['yield'])
    attractors = len(set([round(y, 1) for y in yields]))  # Cluster proxy
    return yields, {'attractors': attractors}

def midterm_gate_sim(params, perturbation):
    if perturbation == 'scarcity':
        params['inflow_S'] /= 2
    elif perturbation == 'toxin':
        params['k_ferm'] /= 2
    elif perturbation == 'oxygen':
        params['k_abs'] /= 1.5
    # Hysteresis: sweep up and down
    sweeps = []
    for val in np.linspace(0, 1, 10):
        params['pert_val'] = val
        _, _, P, _, _, metrics = simulate_pathogen(params)
        sweeps.append(metrics['yield'])
    for val in np.linspace(1, 0, 10):
        params['pert_val'] = val
        _, _, P, _, _, metrics = simulate_pathogen(params)
        sweeps.append(metrics['yield'])
    return sweeps

def export_run_package(level_id, level_name, params, metrics, interpretation, time_series=None):
    data = {
        'level_id': level_id,
        'level_name': level_name,
        'timestamp': datetime.datetime.now().isoformat(),
        'parameters': params,
        'model_outputs': metrics,
        'interpretation': interpretation
    }
    if time_series:
        data['time_series'] = {k: v.tolist() for k, v in time_series.items()}
    return json.dumps(data, indent=4)

def load_run_package(uploaded_file):
    if uploaded_file:
        return json.load(uploaded_file)
    return None

# Streamlit app
st.title(APP_TITLE)
st.markdown(f"**Course:** {COURSE_NAME}  \n**Theme:** {THEME}  \n**Instructor:** {INSTRUCTOR}")

# Sidebar navigation
unlocked_pages = ["Home", "About / Theory Ladder", "Grading & Rubric"] + [LEVELS[i] for i in range(max_level_unlocked + 1)] + ["Instructor Console"]
locked_pages = [LEVELS[i] for i in range(max_level_unlocked + 1, len(LEVELS))]
page = st.sidebar.radio("Navigation", unlocked_pages + locked_pages, disabled=lambda p: p in locked_pages)

st.sidebar.markdown(f"**Unlocked through Level {max_level_unlocked}/{len(LEVELS)-1}**")

# Schedule anchors
st.sidebar.markdown("**Milestones**")
milestones = [
    "2026-01-15: Systems Bootcamp II – Mapping Feedback Flow",
    "2026-01-20: Simulation Lab – Termite Gut Flows (Level 1)",
    "2026-02-03: Nitrogen Flux & System Stability (Level 2)",
    "2026-02-12: Pathogen as Probe of System Structure (Level 3)",
    "2026-02-26: Constraint Rewiring Workshop (Level 4)",
    "2026-03-03: Midterm synthesis gate: Bridge to Ecology + prediction-before-test",
    "2026-03-17/2026-03-19: Resource scarcity & convergence skins (Level 5)",
    "Late semester: Capstone Builder Mode"
]
for m in milestones:
    st.sidebar.markdown(f"- {m}")

if page in locked_pages:
    st.markdown(f"### {page} is Locked")
    st.markdown("This level will unlock theories like [next theory preview]. Contact instructor for unlock.")
elif page == "Home":
    st.markdown("Welcome to the Symbiotic Systems Lab app. Use the sidebar to navigate levels as they unlock.")
    st.markdown("**Goal:** Unlock levels across the semester, each building interactive modeling tools for systems theory in symbioses.")
elif page == "About / Theory Ladder":
    st.markdown("### Theory Ladder")
    theories = {
        "FOUNDATIONS": [
            ("Cybernetics & feedback loops (Norbert Wiener)", "Negative vs positive feedback; gain; delay; stability/oscillation/runaway. (Levels 0,1,2,3,4,5)"),
            ("Stocks & flows", "Reservoirs + fluxes as the language of dynamics. (All levels)"),
            ("Dissipative structures (Prigogine)", "Stable organization in far-from-equilibrium systems sustained by throughput. (Levels 1,2)"),
        ],
        "CONSTRAINTS / AUTONOMY": [
            ("Constraint-based thinking", "Constraints define the space of possible behaviors; bottlenecks determine outcomes. (Levels 2,3,4,5)"),
            ("Constraint closure / autonomy", "Mutually sustaining constraints (host + symbionts) create a higher-order “unit.” (Levels 4,5)"),
            ("Canalization (Waddington)", "Robustness of trajectories/phenotypes despite perturbation. (Levels 2,3)"),
        ],
        "ROBUSTNESS / DISEASE AS PROBE": [
            ("Host–Damage Response (HDR)", "Disease outcome depends on host response + microbe factors; damage landscape. (Level 3)"),
            ("Robustness vs fragility", "Integration improves function but can create single points of failure; failure modes reveal wiring. (Levels 3,4)"),
        ],
        "EVOLUTIONARY ARCHITECTURE": [
            ("Constraint rewiring", "Evolution/design as reconfiguration of constraints and dependencies. (Level 4)"),
            ("Major transitions", "When selection shifts from parts toward higher-level integrated units. (Levels 4,5)"),
        ],
        "CONVERGENCE / ECOLOGY / SCALE": [
            ("Niche construction", "Organisms (and symbioses) modify environments, generating feedback on selection and resource regimes. (Level 5)"),
            ("Autocatalytic sets (Kauffman)", "Self-sustaining reaction networks as a motif of collective metabolism. (Level 5)"),
            ("Alternative stable states & hysteresis", "Tipping points and non-reversibility. (Midterm, Level 5)"),
            ("Scale thinking", "Gut → colony → ecosystem; optional Gaia-style regulation. (Midterm, Capstone)"),
        ]
    }
    for section, items in theories.items():
        st.markdown(f"#### {section}")
        for name, desc in items:
            st.markdown(f"- **{name}**: {desc}")
elif page == "Grading & Rubric":
    st.markdown("### Course Scoring")
    st.markdown("Final Grade (%) = 0.40(Labs & Simulations) + 0.40(Capstone Project) + 0.20(Participation & Reflection)")
    st.markdown("### Labs & Simulations Rubric (20 points each)")
    rubric = [
        "Model execution & correctness (0–5)",
        "Systems reasoning (feedback/flow/constraint logic) (0–5)",
        "Theory integration (use the named theories appropriately) (0–5)",
        "Clarity & evidence (plots/tables + interpretation) (0–5)"
    ]
    for item in rubric:
        st.markdown(f"- {item}")
elif page == "Instructor Console":
    st.markdown("### Instructor Console")
    password = st.text_input("Enter password", type="password")
    if hashlib.sha256(password.encode()).hexdigest() == PASSWORD_HASH:
        new_level = st.slider("Set max unlocked level", 0, len(LEVELS)-1, max_level_unlocked)
        if st.button("Update Unlock"):
            max_level_unlocked = new_level
            save_unlock_state(new_level)
            st.success("Updated!")
        st.markdown(f"Current: Level {max_level_unlocked}")
    else:
        st.error("Incorrect password")
elif page == LEVELS[0]:
    st.markdown("### Level 0: Systems Grammar Playground (Ungraded Bootcamp)")
    st.markdown("#### Learning Objectives")
    st.markdown("- Understand basic feedback loops.\n- Explore stocks and flows.\n- Observe stable, oscillatory, runaway regimes.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- Cybernetics & feedback loops.\n- Stocks & flows.")
    st.markdown("#### What to Submit")
    st.markdown("- Optional: Download run package.")
    st.markdown("#### Rubric")
    st.markdown("Not graded.")

    col1, col2 = st.columns(2)
    with col1:
        dt = st.number_input("dt", 0.01, 1.0, 0.1)
        total_time = st.number_input("Total time", 10, 500, 100)
        initial_X = st.number_input("Initial X", 0.0, 100.0, 10.0)
        inflow = st.number_input("Inflow", 0.0, 10.0, 1.0)
        outflow = st.number_input("Outflow base", 0.0, 10.0, 1.0)
        setpoint = st.number_input("Setpoint", 0.0, 100.0, 20.0)
        gain = st.number_input("Gain", -10.0, 10.0, -1.0)
        delay = st.number_input("Delay (steps)", 0, 50, 5)
        noise_amp = st.number_input("Noise amplitude", 0.0, 1.0, 0.1)
        if st.button("Show example settings"):
            gain = -2.0
            delay = 10
            noise_amp = 0.2
            st.experimental_rerun()
        if st.button("Reset to defaults"):
            pass  # Streamlit rerun resets

    params = {
        'dt': dt, 'total_time': total_time, 'initial_X': initial_X, 'inflow': inflow,
        'outflow': outflow, 'setpoint': setpoint, 'gain': gain, 'delay': delay, 'noise_amp': noise_amp
    }

    X = simulate_single_stock(params)
    metrics = {'final_X': X[-1], 'variance': np.var(X[int(len(X)*0.8):])}

    with col2:
        fig, ax = plt.subplots()
        ax.plot(X)
        ax.set_title("Stock X over time")
        st.pyplot(fig)

        st.markdown(f"Metrics: {metrics}")

    interpretation = st.text_area("Interpretation")
    if st.button("Download run package"):
        json_str = export_run_package(0, LEVELS[0], params, metrics, interpretation, {'X': X})
        st.download_button("Download JSON", json_str, file_name=f"level0_{datetime.datetime.now().isoformat()}.json")
elif page == LEVELS[1]:
    st.markdown("### Level 1: Termite Gut Flows (Graded Lab)")
    st.markdown("#### Learning Objectives")
    st.markdown("- Model gut fermentation as stocks/flows.\n- Explore dissipative structures in symbiosis.\n- Adjust host controls for yield/stability.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- Stocks & flows.\n- Dissipative structures.\n- Distributed homeostasis.")
    st.markdown("#### What to Submit")
    st.markdown("- Download run package with interpretation.")
    st.markdown("#### Rubric")
    rubric_text = "\n".join(["- " + r for r in rubric])
    st.markdown(rubric_text)

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload previous run package (optional)")
        prev_params = load_run_package(uploaded) or {}
        dt = st.number_input("dt", 0.01, 1.0, prev_params.get('dt', 0.1))
        total_time = st.number_input("Total time", 10, 500, prev_params.get('total_time', 100))
        initial_S = st.number_input("Initial S", 0.0, 100.0, prev_params.get('initial_S', 50.0))
        initial_M = st.number_input("Initial M", 0.0, 100.0, prev_params.get('initial_M', 10.0))
        initial_P = st.number_input("Initial P", 0.0, 100.0, prev_params.get('initial_P', 0.0))
        k_dep = st.number_input("k_dep", 0.0, 1.0, prev_params.get('k_dep', 0.1))
        k_ferm = st.number_input("k_ferm", 0.0, 1.0, prev_params.get('k_ferm', 0.2))
        k_abs = st.number_input("k_abs", 0.0, 1.0, prev_params.get('k_abs', 0.15))
        retention_time = st.number_input("Retention time", 1.0, 100.0, prev_params.get('retention_time', 10.0))
        inhibition_P = st.number_input("Inhibition P", 1.0, 100.0, prev_params.get('inhibition_P', 20.0))
        noise_amp = st.number_input("Noise amplitude", 0.0, 1.0, prev_params.get('noise_amp', 0.05))
        if st.button("Reset to defaults"):
            pass

    params = {
        'dt': dt, 'total_time': total_time, 'initial_S': initial_S, 'initial_M': initial_M, 'initial_P': initial_P,
        'k_dep': k_dep, 'k_ferm': k_ferm, 'k_abs': k_abs, 'retention_time': retention_time,
        'inhibition_P': inhibition_P, 'noise_amp': noise_amp
    }

    S, M, P, metrics = simulate_gut_flows(params)

    with col2:
        fig, ax = plt.subplots()
        ax.plot(S, label='S')
        ax.plot(M, label='M')
        ax.plot(P, label='P')
        ax.legend()
        ax.set_title("Time series")
        st.pyplot(fig)

        st.markdown(f"Metrics: {metrics}")

    interpretation = st.text_area("Interpretation (required for submission)")
    if st.button("Download run package"):
        json_str = export_run_package(1, LEVELS[1], params, metrics, interpretation, {'S': S, 'M': M, 'P': P})
        st.download_button("Download JSON", json_str, file_name=f"level1_{datetime.datetime.now().isoformat()}.json")
elif page == LEVELS[2]:
    st.markdown("### Level 2: Nitrogen Flux & Bottlenecks (Graded Lab)")
    st.markdown("#### Learning Objectives")
    st.markdown("- Add nitrogen constraint to gut model.\n- Identify bottlenecks.\n- Test canalization with perturbations.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- Constraint-based thinking.\n- Canalization.\n- Safe operating space.")
    st.markdown("#### What to Submit")
    st.markdown("- Download run package with interpretation.")
    st.markdown("#### Rubric")
    st.markdown(rubric_text)

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload previous run package (optional)")
        prev_params = load_run_package(uploaded) or {}
        params = prev_params.copy()  # Inherit from Level 1
        initial_N = st.number_input("Initial N", 0.0, 100.0, prev_params.get('initial_N', 20.0))
        N_threshold = st.number_input("N threshold", 1.0, 50.0, prev_params.get('N_threshold', 10.0))
        recycling = st.checkbox("Recycling loop", prev_params.get('recycling', False))
        recycling_frac = st.number_input("Recycling frac", 0.0, 1.0, prev_params.get('recycling_frac', 0.2)) if recycling else 0
        fixation = st.checkbox("Fixation loop", prev_params.get('fixation', False))
        fixation_rate = st.number_input("Fixation rate", 0.0, 1.0, prev_params.get('fixation_rate', 0.05)) if fixation else 0
        N_loss = st.number_input("N loss rate", 0.0, 0.5, prev_params.get('N_loss', 0.01))
        params.update({'initial_N': initial_N, 'N_threshold': N_threshold, 'recycling': recycling, 'recycling_frac': recycling_frac,
                       'fixation': fixation, 'fixation_rate': fixation_rate, 'N_loss': N_loss})

    S, M, P, N, metrics = simulate_nitrogen(params)

    with col2:
        fig, ax = plt.subplots()
        ax.plot(S, label='S')
        ax.plot(M, label='M')
        ax.plot(P, label='P')
        ax.plot(N, label='N')
        ax.legend()
        st.pyplot(fig)

        st.markdown(f"Metrics: {metrics}")

    interpretation = st.text_area("Interpretation")
    if st.button("Download run package"):
        json_str = export_run_package(2, LEVELS[2], params, metrics, interpretation, {'S': S, 'M': M, 'P': P, 'N': N})
        st.download_button("Download JSON", json_str, file_name=f"level2_{datetime.datetime.now().isoformat()}.json")
elif page == LEVELS[3]:
    st.markdown("### Level 3: Pathogen as Probe (Graded Lab)")
    st.markdown("#### Learning Objectives")
    st.markdown("- Perturb model with pathogen.\n- Compute damage via HDR.\n- Classify failure modes.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- Host–Damage Response (HDR).\n- Robustness vs fragility.\n- Perturbation reveals structure.")
    st.markdown("#### What to Submit")
    st.markdown("- Download run package with interpretation.")
    st.markdown("#### Rubric")
    st.markdown(rubric_text)

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload previous run package (optional)")
        prev_params = load_run_package(uploaded) or {}
        params = prev_params.copy()  # Inherit
        initial_Path = st.number_input("Initial Pathogen", 0.0, 10.0, prev_params.get('initial_Path', 1.0))
        path_growth = st.number_input("Pathogen growth", 0.0, 1.0, prev_params.get('path_growth', 0.1))
        path_effect = st.number_input("Pathogen effect", 0.0, 1.0, prev_params.get('path_effect', 0.2))
        immune_intensity = st.number_input("Immune intensity", 0.0, 1.0, prev_params.get('immune_intensity', 0.5))
        setpoint_P = st.number_input("Setpoint P", 1.0, 100.0, prev_params.get('setpoint_P', 10.0))
        params.update({'initial_Path': initial_Path, 'path_growth': path_growth, 'path_effect': path_effect,
                       'immune_intensity': immune_intensity, 'setpoint_P': setpoint_P})

    S, M, P, N, Path, metrics = simulate_pathogen(params)

    with col2:
        fig, ax = plt.subplots()
        ax.plot(S, label='S')
        ax.plot(M, label='M')
        ax.plot(P, label='P')
        ax.plot(N, label='N')
        ax.plot(Path, label='Path')
        ax.legend()
        st.pyplot(fig)

        st.markdown(f"Metrics: {metrics}")

    interpretation = st.text_area("Interpretation")
    if st.button("Download run package"):
        json_str = export_run_package(3, LEVELS[3], params, metrics, interpretation, {'S': S, 'M': M, 'P': P, 'N': N, 'Path': Path})
        st.download_button("Download JSON", json_str, file_name=f"level3_{datetime.datetime.now().isoformat()}.json")
elif page == LEVELS[4]:
    st.markdown("### Level 4: Constraint Rewiring Studio (Graded Lab)")
    st.markdown("#### Learning Objectives")
    st.markdown("- Rewire model constraints.\n- Measure closure and tradeoffs.\n- Defend rewiring choices.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- Constraint rewiring.\n- Robustness–evolvability.\n- Major transitions.\n- Constraint closure.")
    st.markdown("#### What to Submit")
    st.markdown("- Download run package with defense text.")
    st.markdown("#### Rubric")
    st.markdown(rubric_text)

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload previous run package (optional)")
        prev_params = load_run_package(uploaded) or {}
        params = prev_params.copy()
        cross_feed_on = st.checkbox("Add cross-feeding", prev_params.get('cross_feed_on', False))
        cross_feed = st.number_input("Cross-feed frac", 0.0, 1.0, prev_params.get('cross_feed', 0.1)) if cross_feed_on else 0
        redundancy = st.checkbox("Add redundancy", prev_params.get('redundancy', False))
        guild_type = st.selectbox("Guild type", ['high_fragile', 'low_robust'], index=0 if prev_params.get('guild_type', 'high_fragile') == 'high_fragile' else 1)
        host_control_str = st.number_input("Host control strength", 0.0, 1.0, prev_params.get('host_control_str', 0.5))
        params.update({'cross_feed_on': cross_feed_on, 'cross_feed': cross_feed, 'redundancy': redundancy,
                       'guild_type': guild_type, 'host_control_str': host_control_str})

    S, M, P, N, Path, metrics = simulate_rewiring(params)

    with col2:
        fig, ax = plt.subplots()
        ax.plot(P, label='P (yield proxy)')
        ax.plot([metrics['stability']] * len(P), label='Stability')
        ax.plot([metrics['cost']] * len(P), label='Cost')
        ax.plot([metrics['closure']] * len(P), label='Closure')
        ax.legend()
        st.pyplot(fig)

        st.markdown(f"Metrics: {metrics}")

    interpretation = st.text_area("Defense text (required)")
    if st.button("Download run package"):
        json_str = export_run_package(4, LEVELS[4], params, metrics, interpretation, {'S': S, 'M': M, 'P': P, 'N': N, 'Path': Path})
        st.download_button("Download JSON", json_str, file_name=f"level4_{datetime.datetime.now().isoformat()}.json")
elif page == LEVELS[5]:
    st.markdown("### Level 5: Convergence Skins (Completion-based)")
    st.markdown("#### Learning Objectives")
    st.markdown("- Apply skins to model different symbioses.\n- Observe convergence to attractors.\n- Explore niche construction.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- Niche construction.\n- Autocatalytic sets.\n- Convergence as attractors.")
    st.markdown("#### What to Submit")
    st.markdown("- Download run package.")
    st.markdown("#### Rubric")
    st.markdown("Completion-based.")

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload previous run package (optional)")
        prev_params = load_run_package(uploaded) or {}
        params = prev_params.copy()
        skin = st.selectbox("Skin", ['termite', 'phloem', 'carcass'])

    yields, metrics = simulate_convergence(params, skin)

    with col2:
        fig, ax = plt.subplots()
        ax.hist(yields)
        ax.set_title("Convergence attractors")
        st.pyplot(fig)

        st.markdown(f"Metrics: {metrics}")

    interpretation = st.text_area("Interpretation")
    if st.button("Download run package"):
        json_str = export_run_package(5, LEVELS[5], params, metrics, interpretation, {'yields': np.array(yields)})
        st.download_button("Download JSON", json_str, file_name=f"level5_{datetime.datetime.now().isoformat()}.json")
elif page == "Midterm Gate":  # Note: Not in levels, but assume unlocked after 4
    if max_level_unlocked < 4:
        st.error("Locked until after Level 4")
    else:
        st.markdown("### Midterm Gate: Bridge to Ecology")
        st.markdown("#### Learning Objectives")
        st.markdown("- Predict before test.\n- Explore hysteresis and stable states.\n- Scale thinking.")
        st.markdown("#### Theories Calcified Here")
        st.markdown("- Alternative stable states & hysteresis.\n- Scale thinking.")
        st.markdown("#### What to Submit")
        st.markdown("- Download run package with prediction.")

        col1, col2 = st.columns(2)
        with col1:
            uploaded = st.file_uploader("Upload previous run package (optional)")
            prev_params = load_run_package(uploaded) or {}
            params = prev_params.copy()
            perturbation = st.selectbox("Perturbation", ['scarcity', 'toxin', 'oxygen'])
            prediction = st.text_area("Prediction (required)")

        if st.button("Run simulation"):
            sweeps = midterm_gate_sim(params, perturbation)
            with col2:
                fig, ax = plt.subplots()
                ax.plot(sweeps)
                ax.set_title("Hysteresis sweep")
                st.pyplot(fig)

        if st.button("Download run package"):
            metrics = {'sweeps': sweeps}
            json_str = export_run_package('midterm', "Midterm Gate", params, metrics, prediction, {'sweeps': np.array(sweeps)})
            st.download_button("Download JSON", json_str, file_name=f"midterm_{datetime.datetime.now().isoformat()}.json")
elif page == LEVELS[6]:
    st.markdown("### Capstone Builder Mode")
    st.markdown("#### Learning Objectives")
    st.markdown("- Build custom system model.\n- Define boundaries, resources, constraints.\n- Compute scoring metrics.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- All prior + scale thinking, major transitions.")
    st.markdown("#### What to Submit")
    st.markdown("- Download System Model Card JSON.")

    col1, col2 = st.columns(2)
    with col1:
        boundary_stocks = st.multiselect("Boundary stocks", ['S', 'M', 'P', 'N', 'Path'])
        resource_regime = st.selectbox("Resource regime", ['steady', 'pulsed'])
        cn_ratio = st.number_input("C:N ratio", 1.0, 100.0, 10.0)
        recycling = st.checkbox("Recycling")
        fixation = st.checkbox("Fixation")
        redundancy = st.checkbox("Redundancy")
        cross_feed = st.checkbox("Cross-feeding")
        metrics_to_score = st.multiselect("Scoring metrics", ['yield', 'stability', 'resilience', 'closure', 'cost'])

    params = {  # Build params from inputs
        'boundary_stocks': boundary_stocks,
        'resource_regime': resource_regime,
        'cn_ratio': cn_ratio,
        'recycling': recycling,
        'fixation': fixation,
        'redundancy': redundancy,
        'cross_feed': cross_feed,
        # Add defaults for simulation
        'dt': 0.1, 'total_time': 100, 'initial_S': 50, 'initial_M': 10, 'initial_P': 0, 'initial_N': 20 / cn_ratio, 'initial_Path': 0,
        'k_dep': 0.1, 'k_ferm': 0.2, 'k_abs': 0.15, 'retention_time': 10, 'inhibition_P': 20, 'noise_amp': 0.05,
        'N_threshold': 10, 'recycling_frac': 0.2 if recycling else 0, 'fixation_rate': 0.05 if fixation else 0, 'N_loss': 0.01,
        'path_growth': 0, 'path_effect': 0, 'immune_intensity': 0, 'setpoint_P': 10,
        'cross_feed_on': cross_feed, 'cross_feed': 0.1 if cross_feed else 0, 'guild_type': 'low_robust', 'host_control_str': 0.5
    }

    S, M, P, N, Path, sim_metrics = simulate_rewiring(params)
    scored = {m: sim_metrics.get(m, 0) for m in metrics_to_score}

    with col2:
        st.markdown(f"Scored Metrics: {scored}")

    interpretation = st.text_area("Capstone notes")
    if st.button("Download System Model Card"):
        json_str = export_run_package(6, LEVELS[6], params, scored, interpretation)
        st.download_button("Download JSON", json_str, file_name=f"capstone_{datetime.datetime.now().isoformat()}.json")
