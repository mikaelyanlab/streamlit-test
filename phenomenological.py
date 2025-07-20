# Aram Mikaelyan, Assistant Professor, Department of Entomology and Plant Pathology, NCSU
# Contact: amikael@ncsu.edu | Methane Oxidation Model (Streamlit App)

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import math
import plotly.graph_objects as go

# Arrhenius parameters
E_a = 50e3       # J/mol
R   = 8.314      # J/(mol·K)
T_ref = 298.15   # K (25 °C)

def methane_oxidation(C, t, C_atm, g_s, Vmax_ref, Km_ref, Pi, O2_ext, T, k_L, V_cell, scaling):
    C_cyt, CH3OH, O2_cyt = C
    # Convert to Kelvin
    T_K = T + 273.15

    # Corrected Arrhenius for Vmax
    Vmax_T = Vmax_ref * scaling * np.exp(E_a/R * (1/T_ref - 1/T_K))
    # Km temperature adjustment
    Km_T = Km_ref * (1 + 0.02*(T - 25))
    # Osmotic inhibition
    Vmax = Vmax_T * np.exp(-0.02*(Pi/100))

    # Methane uptake
    H_CH4 = 1.4
    P_CH4 = g_s * C_atm
    C_eq  = H_CH4 * P_CH4
    J_CH4 = k_L * (C_eq - C_cyt)

    # Oxidation by MMO
    V_MMO = Vmax * (C_cyt / (Km_T + C_cyt))

    # O2 influx clamp
    J_O2 = g_s * (O2_ext - O2_cyt)
    J_O2 = max(J_O2, 0)

    # Rates of change
    dC_cyt_dt  = J_CH4 - V_MMO
    dCH3OH_dt  = V_MMO - 0.000011 * CH3OH
    dO2_dt     = J_O2  - V_MMO

    return [dC_cyt_dt, dCH3OH_dt, dO2_dt]

# ---- Streamlit UI ----
st.title("Methane Oxidation Model with Enzyme Sensitivity")
st.sidebar.header("Adjust Model Parameters")

C_atm     = st.sidebar.slider("Atmospheric CH₄ (ppm)",                0.1, 10.0, 1.9)
g_s       = st.sidebar.slider("Stomatal Conductance (gₛ, mol/m²/s)", 0.01, 0.2, 0.10)
log_vmax  = st.sidebar.slider("log₁₀(Max sMMO Activity, mmol/L/s)", -3.0, math.log10(2.0), -1.3, step=0.1)
Vmax_ref  = 10**log_vmax
st.sidebar.text(f"Vmax_ref = {Vmax_ref:.5f} mmol/L/s")
Km_ref    = st.sidebar.slider("Methane Affinity (Km_ref, mmol/L)",    0.1, 2.0, 0.5)
Pi        = st.sidebar.slider("Cytosolic Osmolarity (%)",           0,   100, 30)
O2_cyt    = st.sidebar.slider("Cytosolic O₂ (mmol/L)",             0.01, 2.0, 0.20)
O2_ext    = st.sidebar.slider("External O₂ (mmol/L)",              0.01, 2.0, 0.20)
T         = st.sidebar.slider("Temperature (°C)",                   5,    45,   25)
k_L       = st.sidebar.slider("Mass Transfer Coefficient (k_L, m/s)",1e-6, 1e-3, 5e-5)
cell_mass = st.sidebar.slider("Cellular Material (g/L)",           0.1,  200.0,100.0)

# Derived parameters
scaling = cell_mass / 0.7
V_cell  = 1e-15  # L

# Solve ODE
time = np.linspace(0, 100, 500)
C0   = [0.2, 0.1, O2_cyt]  # initial [CH4_cyt, CH3OH, O2_cyt]
sol  = odeint(
    methane_oxidation, C0, time,
    args=(C_atm, g_s, Vmax_ref, Km_ref, Pi, O2_ext, T, k_L, V_cell, scaling)
)

# Plot concentrations
fig, ax = plt.subplots()
ax.plot(time, sol[:,0], label="C_cyt (CH₄)")
ax.plot(time, sol[:,1], label="CH₃OH")
ax.plot(time, sol[:,2], label="O₂")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Concentration (mmol/L)")
ax.legend()

# Compute V_MMO time series
T_K   = T + 273.15
Vmax_T   = Vmax_ref * scaling * np.exp(E_a/R * (1/T_ref - 1/T_K))
Vmax_osm = Vmax_T * np.exp(-0.02*(Pi/100))
Km_T     = Km_ref * (1 + 0.02*(T - 25))
V_MMO_ts = Vmax_osm * (sol[:,0] / (Km_T + sol[:,0]))

# Use the peak MMO rate (before CH₄ depletion)
V_MMO_peak = V_MMO_ts.max()

# Plotly gauge for peak oxidation rate
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=V_MMO_peak,
    number={'suffix': " mmol/L/s"},
    title={'text': "Peak CH₄ Oxidation Rate"},
    gauge={'axis': {'range': [0, max(Vmax_ref, V_MMO_peak)*1.2]}}
))

# Display side by side
col1, col2 = st.columns([2, 1])
with col1:
    st.pyplot(fig)
with col2:
    st.plotly_chart(fig_gauge, use_container_width=True)

st.markdown("***Hornstein E. and Mikaelyan A., in prep.***")
