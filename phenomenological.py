# Aram Mikaelyan, Assistant Professor, Department of Entomology and Plant Pathology, NCSU
# Contact: amikael@ncsu.edu | Methane Oxidation Model (Streamlit App)

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import math
import plotly.graph_objects as go

# --- Constants ---
E_a = 50e3  # Activation energy (J/mol)
R = 8.314   # Universal gas constant (J/mol/K)
T_ref = 298.15  # Reference temperature (K)

# --- ODE System ---
def methane_oxidation(C, t, C_atm, g_s, Vmax_ref, Km_ref, Pi, O2_init, T, k_L, V_cell, scaling_factor):
    C_cyt, CH3OH, O2_cyt = C

    T_K = T + 273.15
    Km_T = Km_ref * (1 + 0.02 * (T - 25))
    Vmax_temp = Vmax_ref * scaling_factor * np.exp(E_a / R * (1/T_ref - 1/T_K))
    Vmax = Vmax_temp * np.exp(-0.02 * Pi / 100)

    H_0 = 1.4  # Henry’s Law constant
    alpha = 0.02
    beta = 0.01
    H_CH4 = H_0 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)

    C_atm_mmolL = C_atm * 0.0409  # ppm to mmol/L
    P_CH4 = g_s * C_atm  # pseudo-partial pressure
    C_cyt_eq = H_CH4 * P_CH4
    J_CH4 = k_L * (C_cyt_eq - C_cyt)

    V_MMO = Vmax * (C_cyt / (Km_T + C_cyt)) if C_cyt > 0 else 0

    # O2 influx and consumption
    O2_env = 210  # mmol/m3 ≈ 0.21 atm
    J_O2 = g_s * O2_env / 1000  # mmol/L/s
    dO2_dt = J_O2 - V_MMO

    k_MeOH = 0.000011
    dC_cyt_dt = J_CH4 - V_MMO
    dCH3OH_dt = V_MMO - k_MeOH * CH3OH

    # Clamp O2 to non-negative
    return [dC_cyt_dt, dCH3OH_dt, max(dO2_dt, -O2_cyt)]

# --- Streamlit UI ---
st.title("Methane Oxidation Model (Temperature + Osmolarity + O₂ Influx)")

C_atm = st.sidebar.slider("Atmospheric CH₄ (ppm)", 0.1, 10.0, 1.8)
g_s = st.sidebar.slider("Stomatal Conductance (mol/m²/s)", 0.01, 0.2, 0.05)
log_vmax = st.sidebar.slider("log₁₀(Vmax_ref, mmol/L/s)", -3.0, math.log10(2.0), -1.5)
Vmax_ref = 10 ** log_vmax
Km_ref = st.sidebar.slider("Methane Affinity (Km, mmol/L)", 0.1, 2.0, 0.5)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 50)
O2_init = st.sidebar.slider("Initial O₂ (mmol/L)", 0.01, 2.0, 0.5)
T = st.sidebar.slider("Temperature (°C)", 5, 45, 25)
k_L = st.sidebar.slider("k_L (Mass Transfer, m/s)", 0.001, 0.1, 0.01)
cellular_material = st.sidebar.slider("Cellular Material (g/L)", 0.1, 200.0, 1.0)

baseline_cell_density = 0.7
scaling_factor = cellular_material / baseline_cell_density
V_cell = 1e-15

# --- Solve ODEs ---
time = np.linspace(0, 100, 500)
C0 = [0.2, 0.1, O2_init]
sol = odeint(methane_oxidation, C0, time, args=(C_atm, g_s, Vmax_ref, Km_ref, Pi, O2_init, T, k_L, V_cell, scaling_factor))

# --- Plot ---
fig, ax = plt.subplots()
ax.plot(time, sol[:, 0], label="Cytosolic CH₄")
ax.plot(time, sol[:, 1], label="Methanol (CH₃OH)")
ax.plot(time, sol[:, 2], label="Cytosolic O₂")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Concentration (mmol/L)")
ax.legend()
st.pyplot(fig)

# --- V_MMO Final ---
T_K = T + 273.15
Km_T = Km_ref * (1 + 0.02 * (T - 25))
Vmax_temp = Vmax_ref * scaling_factor * np.exp(E_a / R * (1/T_ref - 1/T_K))
Vmax_osm = Vmax_temp * np.exp(-0.02 * Pi / 100)
C_cyt_final = sol[-1, 0]
V_MMO_final = Vmax_osm * (C_cyt_final / (Km_T + C_cyt_final)) if C_cyt_final > 0 else 0

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=V_MMO_final,
    number={'suffix': " mmol/L/s"},
    title={'text': "Final CH₄ Oxidation Rate"},
    gauge={
        'axis': {'range': [0, 0.3]},
        'bar': {'color': "#ffcc00"},
        'steps': [{'range': [0.03 * i, 0.03 * (i + 1)], 'color': f"rgba(255,0,0,{0.1 + i*0.09})"} for i in range(10)],
        'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': V_MMO_final}
    }
))

col1, col2 = st.columns([2, 1])
with col1:
    st.pyplot(fig)
with col2:
    st.plotly_chart(fig_gauge, use_container_width=True)

st.markdown("***Hornstein E. and Mikaelyan A., in prep.***")
