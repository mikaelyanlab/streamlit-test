# Aram Mikaelyan, NCSU | Streamlit App: Methane Oxidation Model with Photosynthesis
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import math
import plotly.graph_objects as go

# --- Constants ---
E_a = 50e3         # J/mol for MMO
E_a_MeOH = 45e3    # J/mol for methanol oxidation
R = 8.314
T_ref = 298.15     # K
k_MeOH_ref = 0.00011  # 1/s at 25°C

# --- ODE System ---
def methane_oxidation(C, t, C_atm, O2_atm, g_s, Vmax_ref, Km_ref, Pi, T,
                      k_L_CH4, k_L_O2, V_cell, scaling_factor, photosynthesis_on):
    C_cyt, CH3OH, O2_cyt = C
    T_K = T + 273.15

    # Vmax and Km adjustments
    Vmax_T = Vmax_ref * scaling_factor * np.exp(-E_a / R * (1/T_K - 1/T_ref))
    Km_T = Km_ref * (1 + 0.02 * (T - 25))
    Vmax = Vmax_T * np.exp(-0.02 * (Pi / 100))
    k_MeOH = k_MeOH_ref * np.exp(-E_a_MeOH / R * (1/T_K - 1/T_ref))

    # Henry’s constants
    H_0_CH4, H_0_O2 = 1.4, 1.3
    alpha, beta = 0.02, 0.01
    H_CH4 = H_0_CH4 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)
    H_O2 = H_0_O2 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)

    # Partial pressures
    P_CH4 = g_s * (C_atm / 1.0)
    P_O2 = g_s * (O2_atm / 100.0)

    # Equilibrium concentrations
    C_cyt_eq = H_CH4 * P_CH4
    O2_eq = H_O2 * P_O2

    # Fluxes
    J_CH4 = k_L_CH4 * (C_cyt_eq - C_cyt)
    J_O2 = k_L_O2 * (O2_eq - O2_cyt)

    # MMO activity
    V_MMO = Vmax * (C_cyt / (Km_T + C_cyt))

    # Optional photosynthetic O₂ production
    O2_prod = 0.015 if photosynthesis_on else 0  # mmol/L/s

    # ODEs
    dC_cyt_dt = J_CH4 - V_MMO
    dCH3OH_dt = V_MMO - k_MeOH * CH3OH
    dO2_dt = J_O2 - V_MMO + O2_prod

    return [dC_cyt_dt, dCH3OH_dt, dO2_dt]

# --- UI ---
st.title("Methane Oxidation Model (with Optional Photosynthetic O₂)")

# Sidebar inputs
st.sidebar.header("Atmosphere & Gas Transfer")
C_atm = st.sidebar.slider("Atmospheric CH₄ (ppm)", 0.1, 10.0, 1.8)
O2_atm = st.sidebar.slider("Atmospheric O₂ (%)", 1.0, 25.0, 21.0)
g_s = st.sidebar.slider("Stomatal Conductance (mol/m²/s)", 0.01, 2, 0.2)
k_L_CH4 = st.sidebar.slider("CH₄ Mass Transfer Coefficient (m/s)", 0.0001, 0.1, 0.01)
k_L_O2 = st.sidebar.slider("O₂ Mass Transfer Coefficient (m/s)", 0.0001, 0.1, 0.03)

st.sidebar.header("Cellular Environment")
T = st.sidebar.slider("Temperature (°C)", 5, 45, 25)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 50)
photosynthesis_on = st.sidebar.checkbox("Photosynthetic O₂ Production", value=True)

st.sidebar.header("Enzyme Parameters")
log_vmax = st.sidebar.slider("log₁₀(Max sMMO Activity, mmol/L/s)", -3.0, math.log10(2.0), -1.0, step=0.1)
Vmax_ref = 10 ** log_vmax
Km_ref = st.sidebar.slider("Methane Affinity (Km_ref, mmol/L)", 0.1, 2.0, 0.5)

st.sidebar.header("Biomass Settings")
cellular_material = st.sidebar.slider("Cellular Material (g/L)", 0.1, 200.0, 1.0)
baseline_cell_density = 0.7
scaling_factor = cellular_material / baseline_cell_density
V_cell = 1e-15

# Time and initial conditions
time = np.linspace(0, 100, 500)
O2_init = 1.3 * np.exp(-0.02 * (T - 25)) * (1 - 0.01 * Pi) * (O2_atm / 100.0)
C0 = [0.2, 0.1, O2_init]

# Solve ODEs
sol = odeint(methane_oxidation, C0, time,
             args=(C_atm, O2_atm, g_s, Vmax_ref, Km_ref, Pi, T,
                   k_L_CH4, k_L_O2, V_cell, scaling_factor, photosynthesis_on))

# Plot concentration dynamics
fig, ax = plt.subplots()
ax.plot(time, sol[:, 0], label="Cytosolic CH₄")
ax.plot(time, sol[:, 1], label="Methanol (CH₃OH)")
ax.plot(time, sol[:, 2], label="Cytosolic O₂")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Concentration (mmol/L)")
ax.legend()
st.pyplot(fig)

# Final MMO rate
C_cyt_final = sol[-1, 0]
Km_T = Km_ref * (1 + 0.02 * (T - 25))
Vmax_T = Vmax_ref * scaling_factor * np.exp(-E_a / R * (1/(T + 273.15) - 1/T_ref))
Vmax_osm = Vmax_T * np.exp(-0.02 * (Pi / 100))
V_MMO_final = Vmax_osm * (C_cyt_final / (Km_T + C_cyt_final))

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=V_MMO_final,
    number={'suffix': " mmol/L/s"},
    title={'text': "Final CH₄ Oxidation Rate"},
    gauge={
        'axis': {'range': [0, 0.3]},
        'bar': {'color': "#ffcc00"},
        'steps': [{'range': [i*0.03, (i+1)*0.03], 'color': f"rgba(255,0,0,{0.1 + 0.1*i})"} for i in range(10)],
        'threshold': {'line': {'color': "black", 'width': 4}, 'value': V_MMO_final}
    }
))
st.plotly_chart(fig_gauge, use_container_width=True)

# Debug output
k_MeOH_scaled = k_MeOH_ref * np.exp(-E_a_MeOH / R * (1/(T + 273.15) - 1/T_ref))
st.sidebar.text(f"Temp-Adjusted k_MeOH: {k_MeOH_scaled:.6g} 1/s")
st.markdown("***Hornstein E. and Mikaelyan A., in prep.***")
