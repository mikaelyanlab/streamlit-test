import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import json
import os
import datetime
import hashlib
import io

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
RUBRIC = [
    "Model execution & correctness (0–5)",
    "Systems reasoning (feedback/flow/constraint logic) (0–5)",
    "Theory integration (use the named theories appropriately) (0–5)",
    "Clarity & evidence (plots/tables + interpretation) (0–5)"
]

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
    ferm_ts = np.zeros(steps)  # To track cumulative
    abs_ts = np.zeros(steps)
    S[0] = params['initial_S']
    M[0] = params['initial_M']
    P[0] = params['initial_P']
    inflow_S = params['inflow_S']
    k_dep = params['k_dep']
    k_ferm = params['k_ferm']
    k_abs = params.get('k_abs', 0.15)
    k_wash = params.get('k_wash', 1 / params.get('retention_time', 10.0))
    inhibition_P = params['inhibition_P']
    noise_amp = params['noise_amp']
    cross_feed = params.get('cross_feed', 0)
    K_cf = 1.0
    
    for t in range(1, steps):
        dep_bonus = cross_feed * P[t-1] / (P[t-1] + K_cf) if cross_feed > 0 else 0
        dep = k_dep * S[t-1] * (1 + dep_bonus)
        ferm = k_ferm * M[t-1] / (1 + P[t-1] / inhibition_P)
        abs_ = k_abs * P[t-1]
        wash_M = k_wash * M[t-1]
        wash_P = k_wash * P[t-1]
        noise_S = np.random.normal(0, noise_amp)
        noise_M = np.random.normal(0, noise_amp)
        noise_P = np.random.normal(0, noise_amp)
        
        S[t] = max(0, S[t-1] + dt * (inflow_S - dep + noise_S))
        M[t] = max(0, M[t-1] + dt * (dep - ferm - wash_M + noise_M))
        P[t] = max(0, P[t-1] + dt * (ferm - abs_ - wash_P + noise_P))
        ferm_ts[t] = ferm
        abs_ts[t] = abs_
    
    P_final = P[-1]
    cum_ferm = np.sum(ferm_ts) * dt
    cum_abs = np.sum(abs_ts) * dt
    stability = np.var(P[int(steps*0.8):])
    return S, M, P, {'P_final': P_final, 'cum_ferm': cum_ferm, 'cum_abs': cum_abs, 'stability': stability}

def simulate_nitrogen_core(params):
    dt = params['dt']
    total_time = params['total_time']
    steps = int(total_time / dt)
    S = np.zeros(steps)
    M = np.zeros(steps)
    P = np.zeros(steps)
    N = np.zeros(steps)
    ferm_ts = np.zeros(steps)
    abs_ts = np.zeros(steps)
    S[0] = params['initial_S']
    M[0] = params['initial_M']
    P[0] = params['initial_P']
    N[0] = params['initial_N']
    inflow_S = params['inflow_S']
    k_dep = params['k_dep']
    k_ferm = params['k_ferm']
    k_abs = params.get('k_abs', 0.15)
    k_wash = params.get('k_wash', 1 / params.get('retention_time', 10.0))
    inhibition_P = params['inhibition_P']
    noise_amp = params['noise_amp']
    N_threshold = params['N_threshold']
    recycling_frac = params['recycling_frac'] if params['recycling'] else 0
    fixation_rate = params['fixation_rate'] if params['fixation'] else 0
    N_loss = params['N_loss']
    cross_feed = params.get('cross_feed', 0)
    K_cf = 1.0
    
    for t in range(1, steps):
        dep_bonus = cross_feed * P[t-1] / (P[t-1] + K_cf) if cross_feed > 0 else 0
        dep = k_dep * S[t-1] * (1 + dep_bonus)
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
        
        S[t] = max(0, S[t-1] + dt * (inflow_S - dep + noise_S))
        M[t] = max(0, M[t-1] + dt * (dep - ferm - wash_M + noise_M))
        P[t] = max(0, P[t-1] + dt * (ferm - abs_ - wash_P + noise_P))
        N[t] = max(0, N[t-1] + dt * (fixation_rate + recycle_N - N_loss * N[t-1] + noise_N))
        ferm_ts[t] = ferm
        abs_ts[t] = abs_
    
    P_final = P[-1]
    cum_ferm = np.sum(ferm_ts) * dt
    cum_abs = np.sum(abs_ts) * dt
    stability = np.var(P[int(steps*0.8):])
    limiting = 'N-limited' if np.mean(N[int(steps*0.8):]) < N_threshold else 'C-limited'
    return S, M, P, N, {'P_final': P_final, 'cum_ferm': cum_ferm, 'cum_abs': cum_abs, 'stability': stability, 'limiting': limiting}

def simulate_nitrogen(params):
    S, M, P, N, metrics = simulate_nitrogen_core(params)
    canal_var = []
    for _ in range(5):
        temp_params = params.copy()
        temp_params['noise_amp'] = params['noise_amp'] * 2
        _, _, _, _, temp_metrics = simulate_nitrogen_core(temp_params)
        canal_var.append(temp_metrics['cum_abs'])
    metrics['canalization'] = np.var(canal_var)
    return S, M, P, N, metrics

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
    ferm_ts = np.zeros(steps)
    abs_ts = np.zeros(steps)
    S[0] = params['initial_S']
    M[0] = params['initial_M']
    P[0] = params['initial_P']
    N[0] = params['initial_N']
    Path[0] = params['initial_Path']
    inflow_S = params['inflow_S']
    k_dep = params['k_dep']
    k_ferm = params['k_ferm']
    k_abs = params.get('k_abs', 0.15)
    k_wash = params.get('k_wash', 1 / params.get('retention_time', 10.0))
    inhibition_P = params['inhibition_P']
    noise_amp = params['noise_amp']
    N_threshold = params['N_threshold']
    recycling_frac = params['recycling_frac'] if params['recycling'] else 0
    fixation_rate = params['fixation_rate'] if params['fixation'] else 0
    N_loss = params['N_loss']
    path_growth = params['path_growth']
    immune_intensity = params['immune_intensity']
    path_effect = params['path_effect']  # Steal M, reduce ferm
    cross_feed = params.get('cross_feed', 0)
    K_cf = 1.0
    if 'pert_val' in params:
        if params['perturbation'] == 'oxygen':
            k_ferm *= (1 - params['pert_val'])
        elif params['perturbation'] == 'toxin':
            k_ferm *= (1 - params['pert_val'])
        elif params['perturbation'] == 'scarcity':
            inflow_S *= (1 - params['pert_val'])
    
    for t in range(1, steps):
        path_load = Path[t-1] * (1 - immune_intensity * 0.5)  # Immune reduces path
        dep_bonus = cross_feed * P[t-1] / (P[t-1] + K_cf) if cross_feed > 0 else 0
        dep = k_dep * S[t-1] * (1 + dep_bonus)
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
        
        S[t] = max(0, S[t-1] + dt * (inflow_S - dep + noise_S))
        M[t] = max(0, M[t-1] + dt * (dep - ferm - wash_M - steal_M + noise_M))
        P[t] = max(0, P[t-1] + dt * (ferm - abs_ - wash_P + noise_P))
        N[t] = max(0, N[t-1] + dt * (fixation_rate + recycle_N - N_loss * N[t-1] + noise_N))
        Path[t] = max(0, Path[t-1] + dt * (path_growth * Path[t-1] * (1 - immune_intensity)) + noise_Path)
        ferm_ts[t] = ferm
        abs_ts[t] = abs_
    
    damage = 0.1 * np.mean(Path) + 0.05 * (immune_intensity ** 2) + 0.2 * (1 - np.mean(P)/params['setpoint_P'])
    P_final = P[-1]
    cum_ferm = np.sum(ferm_ts) * dt
    cum_abs = np.sum(abs_ts) * dt
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
    return S, M, P, N, Path, {'P_final': P_final, 'cum_ferm': cum_ferm, 'cum_abs': cum_abs, 'stability': stability, 'damage': damage, 'failure': failure}

def simulate_rewiring(params):
    p = params.copy()  # Avoid in-place mutation
    cross_feed_on = p['cross_feed_on']
    p['cross_feed'] = p['cross_feed'] if cross_feed_on else 0
    redundancy = 2 if p['redundancy'] else 1
    guild_type = p['guild_type']  # 'high_fragile' or 'low_robust'
    host_control_str = p['host_control_str']
    cost = host_control_str * 0.1 + (redundancy - 1) * 0.05
    p['k_dep'] *= redundancy
    if guild_type == 'high_fragile':
        p['k_ferm'] *= 1.2
        p['noise_amp'] *= 1.5
        p['inhibition_P'] /= 1.5
    else:
        p['k_ferm'] *= 0.8
        p['noise_amp'] /= 1.5
        p['inhibition_P'] *= 1.5
    
    p['k_abs'] = p.get('k_abs', 0.15)
    p['k_abs'] *= (1 + host_control_str * 0.5)
    p['k_wash'] = p.get('k_wash', 1 / p.get('retention_time', 10.0))
    p['k_wash'] /= (1 + host_control_str * 0.5)
    
    S, M, P, N, Path, metrics = simulate_pathogen(p)
    closure_score = sum([cross_feed_on, p['recycling'], p['redundancy'], host_control_str > 0.5])
    metrics['cost'] = cost
    metrics['closure'] = closure_score
    return S, M, P, N, Path, metrics

def simulate_convergence(params, skin):
    p = params.copy()
    if skin == 'phloem':
        p['initial_N'] /= 2  # N-poor
        p['k_ferm'] *= 0.8
    elif skin == 'carcass':
        p['initial_S'] *= 2  # Pulse
        p['inflow_S'] = 0  # No steady input
    # Multi-start
    yields = []
    for _ in range(10):
        temp_params = p.copy()
        temp_params['initial_S'] += np.random.uniform(-0.5, 0.5) * p['initial_S']
        temp_params['initial_M'] += np.random.uniform(-0.5, 0.5) * p['initial_M']
        _, _, _, _, _, metrics = simulate_rewiring(temp_params)  # Use full model
        yields.append(metrics['cum_abs'])
    attractors = len(set([round(y, 1) for y in yields]))  # Cluster proxy
    return yields, {'attractors': attractors}

def midterm_gate_sim(params, perturbation):
    sweeps = []
    for val in np.linspace(0, 1, 10):
        temp_params = params.copy()
        temp_params['pert_val'] = val
        temp_params['perturbation'] = perturbation
        _, _, P, _, _, metrics = simulate_pathogen(temp_params)
        sweeps.append(metrics['cum_abs'])
    for val in np.linspace(1, 0, 10):
        temp_params = params.copy()
        temp_params['pert_val'] = val
        temp_params['perturbation'] = perturbation
        _, _, P, _, _, metrics = simulate_pathogen(temp_params)
        sweeps.append(metrics['cum_abs'])
    return sweeps

def load_settings_csv(uploaded_file):
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        prev_params = {}
        for _, row in df.iterrows():
            val = row['Value']
            if isinstance(val, str):
                low = val.lower()
                if low == 'true':
                    val = True
                elif low == 'false':
                    val = False
                else:
                    try:
                        val = int(val)
                    except ValueError:
                        try:
                            val = float(val)
                        except ValueError:
                            pass
            prev_params[row['Parameter']] = val
        return prev_params
    return None

# Streamlit app
st.title(APP_TITLE)
st.markdown(f"**Course:** {COURSE_NAME}  \n**Theme:** {THEME}  \n**Instructor:** {INSTRUCTOR}")

# Sidebar navigation
unlocked_pages = ["Home", "About / Theory Ladder", "Grading & Rubric"] + [LEVELS[i] for i in range(max_level_unlocked + 1)]
if max_level_unlocked >= 4:
    unlocked_pages.append("Midterm Gate")
unlocked_pages.append("Instructor Console")

locked_pages = [LEVELS[i] for i in range(max_level_unlocked + 1, len(LEVELS))]
if max_level_unlocked < 4:
    locked_pages.append("Midterm Gate")

page = st.sidebar.radio("Navigation", unlocked_pages)

for p in locked_pages:
    st.sidebar.markdown(f"- {p} (Locked)")

st.sidebar.markdown(f"**Unlocked through Level {max_level_unlocked}/{len(LEVELS)-1}**")

# Schedule anchors
st.sidebar.markdown("**Milestones**")
milestones = [
    "2026-01-15: Systems Bootcamp II – Mapping Feedback Flow",
    "2026-01-20: Simulation Lab – Termite Gut Flows (Level 1)",
    "2026-02-03: Nitrogen Flux & System Stability (Level 2)",
    "2026-02-12: Pathogen as Probe of System Structure (Level 3)",
    "2026-02-26: Constraint Rewiring Workshop (Level 4)",
    "2026-03-03: Midterm synthesis gate: Bridge to Ecology",
    "2026-03-17/2026-03-19: Resource scarcity & convergence skins (Level 5)",
    "Late semester: Capstone Builder Mode"
]
for m in milestones:
    st.sidebar.markdown(f"- {m}")

if page == "Home":
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
    for item in RUBRIC:
        st.markdown(f"- {item}")
elif page == "Instructor Console":
    st.markdown("### Instructor Console")
    password = st.text_input("Enter password", type="password")
    if password and hashlib.sha256(password.encode()).hexdigest() != PASSWORD_HASH:
        st.error("Incorrect password")
    if hashlib.sha256(password.encode()).hexdigest() == PASSWORD_HASH:
        new_level = st.slider("Set max unlocked level", 0, len(LEVELS)-1, max_level_unlocked)
        if st.button("Update Unlock"):
            max_level_unlocked = new_level
            save_unlock_state(new_level)
            st.success("Updated!")
        st.markdown(f"Current: Level {max_level_unlocked}")
elif page == LEVELS[0]:
    st.markdown("### Level 0: Systems Grammar Playground (Ungraded Bootcamp)")
    st.markdown("#### Learning Objectives")
    st.markdown("- Understand basic feedback loops.\n- Explore stocks and flows.\n- Observe stable, oscillatory, runaway regimes.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- Cybernetics & feedback loops.\n- Stocks & flows.")
    st.markdown("#### Rubric")
    st.markdown("Not graded.")

    col1, col2 = st.columns(2)
    with col1:
        dt = st.number_input("dt", 0.01, 1.0, 0.1, key='L0_dt')
        total_time = st.number_input("Total time", 10, 500, 100, key='L0_total_time')
        initial_X = st.number_input("Initial X", 0.0, 100.0, 10.0, key='L0_initial_X')
        inflow = st.number_input("Inflow", 0.0, 10.0, 1.0, key='L0_inflow')
        outflow = st.number_input("Outflow base", 0.0, 10.0, 1.0, key='L0_outflow')
        setpoint = st.number_input("Setpoint", 0.0, 100.0, 20.0, key='L0_setpoint')
        gain = st.number_input("Gain", -10.0, 10.0, -1.0, key='L0_gain')
        delay = st.number_input("Delay (steps)", 0, 50, 5, key='L0_delay')
        noise_amp = st.number_input("Noise amplitude", 0.0, 1.0, 0.1, key='L0_noise_amp')
        if st.button("Show example settings"):
            st.session_state['L0_gain'] = -2.0
            st.session_state['L0_delay'] = 10
            st.session_state['L0_noise_amp'] = 0.2
            st.rerun()
        if st.button("Reset to defaults"):
            for key in list(st.session_state.keys()):
                if key.startswith('L0_'):
                    del st.session_state[key]
            st.rerun()

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

    params_df = pd.DataFrame(list(params.items()), columns=['Parameter', 'Value'])
    csv = params_df.to_csv(index=False)
    st.download_button("Export Settings CSV", csv, "settings.csv", "text/csv")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    st.download_button("Download Figure", buf, "figure.png", "image/png")
elif page == LEVELS[1]:
    st.markdown("### Level 1: Termite Gut Flows (Graded Lab)")
    st.markdown("#### Learning Objectives")
    st.markdown("- Model gut fermentation as stocks/flows.\n- Explore dissipative structures in symbiosis.\n- Adjust host controls for yield/stability.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- Stocks & flows.\n- Dissipative structures.\n- Distributed homeostasis.")
    st.markdown("#### Rubric")
    for item in RUBRIC:
        st.markdown(f"- {item}")

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload settings CSV (optional)")
        prev_params = load_settings_csv(uploaded) or {}
        dt = st.number_input("dt", 0.01, 1.0, prev_params.get('dt', 0.1), key='L1_dt')
        total_time = st.number_input("Total time", 10, 500, prev_params.get('total_time', 100), key='L1_total_time')
        initial_S = st.number_input("Initial S", 0.0, 100.0, prev_params.get('initial_S', 50.0), key='L1_initial_S')
        initial_M = st.number_input("Initial M", 0.0, 100.0, prev_params.get('initial_M', 10.0), key='L1_initial_M')
        initial_P = st.number_input("Initial P", 0.0, 100.0, prev_params.get('initial_P', 0.0), key='L1_initial_P')
        inflow_S = st.number_input("Inflow S", 0.0, 10.0, prev_params.get('inflow_S', 1.0), key='L1_inflow_S')
        k_dep = st.number_input("k_dep", 0.0, 1.0, prev_params.get('k_dep', 0.1), key='L1_k_dep')
        k_ferm = st.number_input("k_ferm", 0.0, 1.0, prev_params.get('k_ferm', 0.2), key='L1_k_ferm')
        k_abs = st.number_input("k_abs", 0.0, 1.0, prev_params.get('k_abs', 0.15), key='L1_k_abs')
        retention_time = st.number_input("Retention time", 1.0, 100.0, prev_params.get('retention_time', 10.0), key='L1_retention_time')
        inhibition_P = st.number_input("Inhibition P", 1.0, 100.0, prev_params.get('inhibition_P', 20.0), key='L1_inhibition_P')
        noise_amp = st.number_input("Noise amplitude", 0.0, 1.0, prev_params.get('noise_amp', 0.05), key='L1_noise_amp')
        if st.button("Reset to defaults"):
            for key in list(st.session_state.keys()):
                if key.startswith('L1_'):
                    del st.session_state[key]
            st.rerun()

    params = {
        'dt': dt, 'total_time': total_time, 'initial_S': initial_S, 'initial_M': initial_M, 'initial_P': initial_P,
        'inflow_S': inflow_S, 'k_dep': k_dep, 'k_ferm': k_ferm, 'k_abs': k_abs, 'retention_time': retention_time,
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

    params_df = pd.DataFrame(list(params.items()), columns=['Parameter', 'Value'])
    csv = params_df.to_csv(index=False)
    st.download_button("Export Settings CSV", csv, "settings.csv", "text/csv")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    st.download_button("Download Figure", buf, "figure.png", "image/png")
elif page == LEVELS[2]:
    st.markdown("### Level 2: Nitrogen Flux & Bottlenecks (Graded Lab)")
    st.markdown("#### Learning Objectives")
    st.markdown("- Add nitrogen constraint to gut model.\n- Identify bottlenecks.\n- Test canalization with perturbations.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- Constraint-based thinking.\n- Canalization.\n- Safe operating space.")
    st.markdown("#### Rubric")
    for item in RUBRIC:
        st.markdown(f"- {item}")

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload settings CSV (optional)")
        prev_params = load_settings_csv(uploaded) or {}
        params = prev_params.copy()
        # Set defaults if not present
        params.setdefault('dt', 0.1)
        params.setdefault('total_time', 100)
        params.setdefault('initial_S', 50.0)
        params.setdefault('initial_M', 10.0)
        params.setdefault('initial_P', 0.0)
        params.setdefault('inflow_S', 1.0)
        params.setdefault('k_dep', 0.1)
        params.setdefault('k_ferm', 0.2)
        params.setdefault('k_abs', 0.15)
        params.setdefault('retention_time', 10.0)
        params.setdefault('inhibition_P', 20.0)
        params.setdefault('noise_amp', 0.05)
        initial_N = st.number_input("Initial N", 0.0, 100.0, params.get('initial_N', 20.0), key='L2_initial_N')
        N_threshold = st.number_input("N threshold", 1.0, 50.0, params.get('N_threshold', 10.0), key='L2_N_threshold')
        recycling = st.checkbox("Recycling loop", params.get('recycling', False), key='L2_recycling')
        recycling_frac = st.number_input("Recycling frac", 0.0, 1.0, params.get('recycling_frac', 0.2), key='L2_recycling_frac') if recycling else 0
        fixation = st.checkbox("Fixation loop", params.get('fixation', False), key='L2_fixation')
        fixation_rate = st.number_input("Fixation rate", 0.0, 1.0, params.get('fixation_rate', 0.05), key='L2_fixation_rate') if fixation else 0
        N_loss = st.number_input("N loss rate", 0.0, 0.5, params.get('N_loss', 0.01), key='L2_N_loss')
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

    params_df = pd.DataFrame(list(params.items()), columns=['Parameter', 'Value'])
    csv = params_df.to_csv(index=False)
    st.download_button("Export Settings CSV", csv, "settings.csv", "text/csv")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    st.download_button("Download Figure", buf, "figure.png", "image/png")
elif page == LEVELS[3]:
    st.markdown("### Level 3: Pathogen as Probe (Graded Lab)")
    st.markdown("#### Learning Objectives")
    st.markdown("- Perturb model with pathogen.\n- Compute damage via HDR.\n- Classify failure modes.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- Host–Damage Response (HDR).\n- Robustness vs fragility.\n- Perturbation reveals structure.")
    st.markdown("#### Rubric")
    for item in RUBRIC:
        st.markdown(f"- {item}")

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload settings CSV (optional)")
        prev_params = load_settings_csv(uploaded) or {}
        params = prev_params.copy()
        # Set defaults if not present
        params.setdefault('dt', 0.1)
        params.setdefault('total_time', 100)
        params.setdefault('initial_S', 50.0)
        params.setdefault('initial_M', 10.0)
        params.setdefault('initial_P', 0.0)
        params.setdefault('inflow_S', 1.0)
        params.setdefault('k_dep', 0.1)
        params.setdefault('k_ferm', 0.2)
        params.setdefault('k_abs', 0.15)
        params.setdefault('retention_time', 10.0)
        params.setdefault('inhibition_P', 20.0)
        params.setdefault('noise_amp', 0.05)
        params.setdefault('initial_N', 20.0)
        params.setdefault('N_threshold', 10.0)
        params.setdefault('recycling', False)
        params.setdefault('recycling_frac', 0.2)
        params.setdefault('fixation', False)
        params.setdefault('fixation_rate', 0.05)
        params.setdefault('N_loss', 0.01)
        initial_Path = st.number_input("Initial Pathogen", 0.0, 10.0, params.get('initial_Path', 1.0), key='L3_initial_Path')
        path_growth = st.number_input("Pathogen growth", 0.0, 1.0, params.get('path_growth', 0.1), key='L3_path_growth')
        path_effect = st.number_input("Pathogen effect", 0.0, 1.0, params.get('path_effect', 0.2), key='L3_path_effect')
        immune_intensity = st.number_input("Immune intensity", 0.0, 1.0, params.get('immune_intensity', 0.5), key='L3_immune_intensity')
        setpoint_P = st.number_input("Setpoint P", 1.0, 100.0, params.get('setpoint_P', 10.0), key='L3_setpoint_P')
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

    params_df = pd.DataFrame(list(params.items()), columns=['Parameter', 'Value'])
    csv = params_df.to_csv(index=False)
    st.download_button("Export Settings CSV", csv, "settings.csv", "text/csv")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    st.download_button("Download Figure", buf, "figure.png", "image/png")
elif page == LEVELS[4]:
    st.markdown("### Level 4: Constraint Rewiring Studio (Graded Lab)")
    st.markdown("#### Learning Objectives")
    st.markdown("- Rewire model constraints.\n- Measure closure and tradeoffs.\n- Defend rewiring choices.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- Constraint rewiring.\n- Robustness–evolvability.\n- Major transitions.\n- Constraint closure.")
    st.markdown("#### Rubric")
    for item in RUBRIC:
        st.markdown(f"- {item}")

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload settings CSV (optional)")
        prev_params = load_settings_csv(uploaded) or {}
        params = prev_params.copy()
        # Set defaults if not present
        params.setdefault('dt', 0.1)
        params.setdefault('total_time', 100)
        params.setdefault('initial_S', 50.0)
        params.setdefault('initial_M', 10.0)
        params.setdefault('initial_P', 0.0)
        params.setdefault('inflow_S', 1.0)
        params.setdefault('k_dep', 0.1)
        params.setdefault('k_ferm', 0.2)
        params.setdefault('k_abs', 0.15)
        params.setdefault('retention_time', 10.0)
        params.setdefault('inhibition_P', 20.0)
        params.setdefault('noise_amp', 0.05)
        params.setdefault('initial_N', 20.0)
        params.setdefault('N_threshold', 10.0)
        params.setdefault('recycling', False)
        params.setdefault('recycling_frac', 0.2)
        params.setdefault('fixation', False)
        params.setdefault('fixation_rate', 0.05)
        params.setdefault('N_loss', 0.01)
        params.setdefault('initial_Path', 1.0)
        params.setdefault('path_growth', 0.1)
        params.setdefault('path_effect', 0.2)
        params.setdefault('immune_intensity', 0.5)
        params.setdefault('setpoint_P', 10.0)
        cross_feed_on = st.checkbox("Add cross-feeding", params.get('cross_feed_on', False), key='L4_cross_feed_on')
        cross_feed = st.number_input("Cross-feed frac", 0.0, 1.0, params.get('cross_feed', 0.1), key='L4_cross_feed') if cross_feed_on else 0
        redundancy = st.checkbox("Add redundancy", params.get('redundancy', False), key='L4_redundancy')
        guild_type = st.selectbox("Guild type", ['high_fragile', 'low_robust'], index=0 if params.get('guild_type', 'high_fragile') == 'high_fragile' else 1, key='L4_guild_type')
        host_control_str = st.number_input("Host control strength", 0.0, 1.0, params.get('host_control_str', 0.5), key='L4_host_control_str')
        params.update({'cross_feed_on': cross_feed_on, 'cross_feed': cross_feed, 'redundancy': redundancy,
                       'guild_type': guild_type, 'host_control_str': host_control_str})

    S, M, P, N, Path, metrics = simulate_rewiring(params)

    with col2:
        fig, ax = plt.subplots()
        ax.plot(P, label='P (yield proxy)')
        ax.legend()
        st.pyplot(fig)

        st.markdown("**Scalar Metrics:**")
        st.write({'stability': metrics['stability'], 'cost': metrics['cost'], 'closure': metrics['closure']})

    params_df = pd.DataFrame(list(params.items()), columns=['Parameter', 'Value'])
    csv = params_df.to_csv(index=False)
    st.download_button("Export Settings CSV", csv, "settings.csv", "text/csv")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    st.download_button("Download Figure", buf, "figure.png", "image/png")
elif page == LEVELS[5]:
    st.markdown("### Level 5: Convergence Skins (Completion-based)")
    st.markdown("#### Learning Objectives")
    st.markdown("- Apply skins to model different symbioses.\n- Observe convergence to attractors.\n- Explore niche construction.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- Niche construction.\n- Autocatalytic sets.\n- Convergence as attractors.")
    st.markdown("#### Rubric")
    st.markdown("Completion-based.")

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload settings CSV (optional)")
        prev_params = load_settings_csv(uploaded) or {}
        params = prev_params.copy()
        # Set defaults if not present
        params.setdefault('dt', 0.1)
        params.setdefault('total_time', 100)
        params.setdefault('initial_S', 50.0)
        params.setdefault('initial_M', 10.0)
        params.setdefault('initial_P', 0.0)
        params.setdefault('inflow_S', 1.0)
        params.setdefault('k_dep', 0.1)
        params.setdefault('k_ferm', 0.2)
        params.setdefault('k_abs', 0.15)
        params.setdefault('retention_time', 10.0)
        params.setdefault('inhibition_P', 20.0)
        params.setdefault('noise_amp', 0.05)
        params.setdefault('initial_N', 20.0)
        params.setdefault('N_threshold', 10.0)
        params.setdefault('recycling', False)
        params.setdefault('recycling_frac', 0.2)
        params.setdefault('fixation', False)
        params.setdefault('fixation_rate', 0.05)
        params.setdefault('N_loss', 0.01)
        params.setdefault('initial_Path', 1.0)
        params.setdefault('path_growth', 0.1)
        params.setdefault('path_effect', 0.2)
        params.setdefault('immune_intensity', 0.5)
        params.setdefault('setpoint_P', 10.0)
        params.setdefault('cross_feed_on', False)
        params.setdefault('cross_feed', 0.1)
        params.setdefault('redundancy', False)
        params.setdefault('guild_type', 'high_fragile')
        params.setdefault('host_control_str', 0.5)
        skin = st.selectbox("Skin", ['termite', 'phloem', 'carcass'], key='L5_skin')

    yields, metrics = simulate_convergence(params, skin)

    with col2:
        fig, ax = plt.subplots()
        ax.hist(yields)
        ax.set_title("Convergence attractors")
        st.pyplot(fig)

        st.markdown(f"Metrics: {metrics}")

    params_df = pd.DataFrame(list(params.items()), columns=['Parameter', 'Value'])
    csv = params_df.to_csv(index=False)
    st.download_button("Export Settings CSV", csv, "settings.csv", "text/csv")

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    st.download_button("Download Figure", buf, "figure.png", "image/png")
elif page == "Midterm Gate":
    st.markdown("### Midterm Gate: Bridge to Ecology")
    st.markdown("#### Learning Objectives")
    st.markdown("- Explore hysteresis and stable states.\n- Scale thinking.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- Alternative stable states & hysteresis.\n- Scale thinking.")

    col1, col2 = st.columns(2)
    with col1:
        uploaded = st.file_uploader("Upload settings CSV (optional)")
        prev_params = load_settings_csv(uploaded) or {}
        params = prev_params.copy()
        # Set defaults if not present
        params.setdefault('dt', 0.1)
        params.setdefault('total_time', 100)
        params.setdefault('initial_S', 50.0)
        params.setdefault('initial_M', 10.0)
        params.setdefault('initial_P', 0.0)
        params.setdefault('inflow_S', 1.0)
        params.setdefault('k_dep', 0.1)
        params.setdefault('k_ferm', 0.2)
        params.setdefault('k_abs', 0.15)
        params.setdefault('retention_time', 10.0)
        params.setdefault('inhibition_P', 20.0)
        params.setdefault('noise_amp', 0.05)
        params.setdefault('initial_N', 20.0)
        params.setdefault('N_threshold', 10.0)
        params.setdefault('recycling', False)
        params.setdefault('recycling_frac', 0.2)
        params.setdefault('fixation', False)
        params.setdefault('fixation_rate', 0.05)
        params.setdefault('N_loss', 0.01)
        params.setdefault('initial_Path', 1.0)
        params.setdefault('path_growth', 0.1)
        params.setdefault('path_effect', 0.2)
        params.setdefault('immune_intensity', 0.5)
        params.setdefault('setpoint_P', 10.0)
        perturbation = st.selectbox("Perturbation", ['scarcity', 'toxin', 'oxygen'])

    if st.button("Run simulation"):
        sweeps = midterm_gate_sim(params, perturbation)
        with col2:
            fig, ax = plt.subplots()
            ax.plot(sweeps)
            ax.set_title("Sensitivity Sweep (Forward/Backward)")
            st.pyplot(fig)

        params_df = pd.DataFrame(list(params.items()), columns=['Parameter', 'Value'])
        csv = params_df.to_csv(index=False)
        st.download_button("Export Settings CSV", csv, "settings.csv", "text/csv")

        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        st.download_button("Download Figure", buf, "figure.png", "image/png")
elif page == LEVELS[6]:
    st.markdown("### Capstone Builder Mode")
    st.markdown("#### Learning Objectives")
    st.markdown("- Build custom system model.\n- Define boundaries, resources, constraints.\n- Compute scoring metrics.")
    st.markdown("#### Theories Calcified Here")
    st.markdown("- All prior + scale thinking, major transitions.")

    col1, col2 = st.columns(2)
    with col1:
        boundary_stocks = st.multiselect("Boundary stocks", ['S', 'M', 'P', 'N', 'Path'])
        resource_regime = st.selectbox("Resource regime", ['steady', 'pulsed'])
        cn_ratio = st.number_input("C:N ratio", 1.0, 100.0, 10.0)
        recycling = st.checkbox("Recycling")
        fixation = st.checkbox("Fixation")
        redundancy = st.checkbox("Redundancy")
        cross_feed_on = st.checkbox("Cross-feeding")
        metrics_to_score = st.multiselect("Scoring metrics", ['yield', 'stability', 'resilience', 'closure', 'cost'])

    params = {  # Build params from inputs
        'boundary_stocks': boundary_stocks,
        'resource_regime': resource_regime,
        'cn_ratio': cn_ratio,
        'recycling': recycling,
        'fixation': fixation,
        'redundancy': redundancy,
        'cross_feed_on': cross_feed_on,
        # Add defaults for simulation
        'dt': 0.1, 'total_time': 100, 'initial_S': 50, 'initial_M': 10, 'initial_P': 0, 'initial_N': 20 / cn_ratio, 'initial_Path': 0,
        'inflow_S': 1.0 if resource_regime == 'steady' else 0.0,
        'k_dep': 0.1, 'k_ferm': 0.2, 'k_abs': 0.15, 'retention_time': 10, 'inhibition_P': 20, 'noise_amp': 0.05,
        'N_threshold': 10, 'recycling_frac': 0.2 if recycling else 0, 'fixation_rate': 0.05 if fixation else 0, 'N_loss': 0.01,
        'path_growth': 0, 'path_effect': 0, 'immune_intensity': 0, 'setpoint_P': 10,
        'cross_feed': 0.1 if cross_feed_on else 0, 'guild_type': 'low_robust', 'host_control_str': 0.5
    }

    S, M, P, N, Path, sim_metrics = simulate_rewiring(params)
    scored = {m: sim_metrics.get(m, 0) for m in metrics_to_score if m != 'yield'}
    if 'yield' in metrics_to_score:
        scored['yield'] = sim_metrics['cum_abs']

    with col2:
        st.markdown(f"Scored Metrics: {scored}")

    params_df = pd.DataFrame(list(params.items()), columns=['Parameter', 'Value'])
    csv = params_df.to_csv(index=False)
    st.download_button("Export Settings CSV", csv, "settings.csv", "text/csv")
