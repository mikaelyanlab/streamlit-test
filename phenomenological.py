# Aram Mikaelyan, Assistant Professor, Department of Entomology and Plant Pathology, NCSU  
# Contact: amikael@ncsu.edu | Methane Oxidation Model (Streamlit App)

import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import math
import plotly.graph_objects as go

# Arrhenius equation parameters
E_a = 50e3  # J/mol
R = 8.314  # J/(mol*K)
T_ref = 298.15  # 25°C in Kelvin

# Define the model
def methane_oxidation(C, t, C_atm, g_s, Vmax_ref, Km_ref, Pi, O2_ext, T, k_L, V_cell, scaling_factor):
    C_cyt, CH3OH, O2_cyt = C
    T_K = T + 273.15
    # Arrhenius for Vmax
    Vmax_T = Vmax_ref * scaling_factor * np.exp(E_a / R * (1/T_ref - 1/T_K))
    Km_T = Km_ref * (1 + 0.02 * (T - 25))
    Vmax = Vmax_T * np.exp(-0.02 * (Pi / 100))
    # Methane uptake
    H_CH4 = 1.4
    P_CH4 = g_s * C_atm
    C_cyt_eq = H_CH4 * P_CH4
    J_CH4 = k_L * (C_cyt_eq - C_cyt)
    # Oxidation
    V_MMO = Vmax * (C_cyt / (Km_T + C_cyt))
    # Oxygen influx clamp
    J_O2 = g_s * (O2_ext - O2_cyt)
    J_O2 = max(J_O2, 0)
    # Dynamics
    dC_cyt_dt = J_CH4 - V_MMO
    dCH3OH_dt = V_MMO - 0.000011 * CH3OH
    dO2_dt = J_O2 - V_MMO
    return [dC_cyt_dt, dCH3OH_dt, dO2_dt]

# Streamlit UI
st.title("Methane Oxidation Model with Enzyme Sensitivity")
st.sidebar.header("Adjust Model Parameters")
# Sliders
C_atm = st.sidebar.slider("Atmospheric CH₄ (ppm)", 0.1, 10.0, 1.8)
g_s = st.sidebar.slider("Stomatal Conductance (gₛ, mol/m²/s)", 0.01, 0.2, 0.05)
log_vmax = st.sidebar.slider("log₁₀(Max sMMO Activity, mmol/L/s)", -3.0, math.log10(2.0), -1.3, step=0.1)
Vmax_ref = 10 ** log_vmax
st.sidebar.text(f"Vmax_ref = {Vmax_ref:.6f} mmol/L/s")
Km_ref = st.sidebar.slider("Methane Affinity (Km_ref, mmol/L)", 0.1, 2.0, 0.5)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 30)
O2_cyt = st.sidebar.slider("Cytosolic O₂ (mmol/L)", 0.01, 2.0, 0.2)
O2_ext = st.sidebar.slider("External O₂ (mmol/L)", 0.01, 2.0, 0.2)
T = st.sidebar.slider("Temperature (°C)", 5, 45, 25)
k_L = st.sidebar.slider("Mass Transfer Coefficient (k_L, m/s)", 1e-6, 1e-3, 5e-5)
cellular_material = st.sidebar.slider("Cellular Material (g/L)", 0.1, 200.0, 100.0)

# Scaling Vmax
baseline_cell_density = 0.7
scaling_factor = cellular_material / baseline_cell_density
V_cell = 1e-15  # L

# Initial conditions and solve ODEs
time = np.linspace(0, 100, 500)
C0 = [0.2, 0.1, O2_cyt]
sol = odeint(
    methane_oxidation, C0, time,
    args=(C_atm, g_s, Vmax_ref, Km_ref, Pi, O2_ext, T, k_L, V_cell, scaling_factor)
)

# Plot results
fig, ax = plt.subplots()
ax.plot(time, sol[:, 0], label="C_cyt (CH₄)")
ax.plot(time, sol[:, 1], label="CH₃OH")
ax.plot(time, sol[:, 2], label="O₂")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Concentration (mmol/L)")
ax.legend()

# Display side-by-side with gauge
# Compute final V_MMO
def compute_V_MMO_final():
    Km_T = Km_ref * (1 + 0.02 * (T - 25))
    Vmax_T = Vmax_ref * scaling_factor * np.exp(E_a / R * (1/T_ref - 1/(T + 273.15)))
    Vmax_osm = Vmax_T * np.exp(-0.02 * (Pi / 100))
    C_final = sol[-1, 0]
    return Vmax_osm * (C_final / (Km_T + C_final))

V_MMO_final = compute_V_MMO_final()
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=V_MMO_final,
    number={'suffix': " mmol/L/s"},
    title={'text': "Final CH₄ Oxidation Rate"},
    gauge={'axis': {'range': [0, max(Vmax_ref, V_MMO_final)*1.2]}}
))
col1, col2 = st.columns([2, 1])
with col1:
    st.pyplot(fig)
with col2:
    st.plotly_chart(fig_gauge, use_container_width=True)

# Footer
st.markdown("***Hornstein E. and Mikaelyan A., in prep.***)"}]}
