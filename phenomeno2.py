import streamlit as st
import numpy as np
from scipy.integrate import solve_ivp
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# --- Constants ---
E_a = 50e3  # J/mol for MMO; activation energy
E_a_MeOH = 45e3  # J/mol for methanol oxidation
R = 8.314  # Gas constant, J/mol/K
T_ref = 298.15  # Reference temperature, K
k_MeOH_ref = 0.00011  # 1/s at 25°C
H_0_CH4 = 1.4  # mmol/L/atm for CH4 at 25°C
H_0_O2 = 1.3  # mmol/L/atm for O2 at 25°C
A_V = 1e3  # m⁻¹, effective mesophyll area/volume (tunable)

# --- ODE System ---
def methane_oxidation(C, t, C_atm, O2_atm, g_s, Vmax_ref, Km_ref, Pi, T,
                      V_cell, scaling_factor, photosynthesis_on):
    C_cyt, CH3OH, O2_cyt = C
    T_K = T + 273.15

    # Temperature & osmolarity adjustments
    Vmax_T = Vmax_ref * scaling_factor * np.exp(-E_a / R * (1/T_K - 1/T_ref))
    Km_T = Km_ref * (1 + 0.02 * (T - 25))
    Vmax = Vmax_T * np.exp(-0.02 * (Pi / 100))
    k_MeOH = k_MeOH_ref * np.exp(-E_a_MeOH / R * (1/T_K - 1/T_ref))

    alpha, beta = 0.02, 0.01
    H_CH4 = H_0_CH4 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)
    H_O2 = H_0_O2 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)

    # Partial pressures (atm)
    P_CH4 = C_atm / 1e6
    P_O2 = O2_atm / 100.0

    # Equilibrium concentrations (mmol/L)
    C_cyt_eq = H_CH4 * P_CH4
    O2_eq = H_O2 * P_O2

    # Fluxes (area-to-volume scaled)
    J_CH4 = g_s * A_V * (C_cyt_eq - C_cyt)
    J_O2 = g_s * A_V * (O2_eq - O2_cyt)

    # MMO activity
    Km_O2 = 0.001  # mmol/L
    V_MMO = Vmax * (C_cyt / (Km_T + C_cyt)) * (O2_cyt / (Km_O2 + O2_cyt))

    # Photosynthetic O₂ production
    O2_prod = 0.1 if photosynthesis_on else 0

    dC_cyt_dt = J_CH4 - V_MMO
    dCH3OH_dt = V_MMO - k_MeOH * CH3OH
    dO2_dt = J_O2 - V_MMO + O2_prod
    return [dC_cyt_dt, dCH3OH_dt, dO2_dt]

# --- UI ---
st.title("Methane Oxidation Model (with Optional Photosynthetic O₂)")

st.sidebar.header("Atmosphere & Gas Transfer")
C_atm = st.sidebar.slider("Atmospheric CH₄ (ppm)", 0.1, 10.0, 1.8)
O2_atm = st.sidebar.slider("Atmospheric O₂ (%)", 1.0, 25.0, 21.0)
g_s = st.sidebar.slider("Stomatal Conductance (mol/m²/s)", 0.1, 2.0, 0.2)

st.sidebar.header("Cellular Environment")
T = st.sidebar.slider("Temperature (°C)", 5, 45, 25)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 50)
photosynthesis_on = st.sidebar.checkbox("Photosynthetic O₂ Production", value=True)

st.sidebar.header("Enzyme Parameters")
expression_percent = st.sidebar.slider("pMMO Expression (% of total cell protein)", 0.1, 5.0, 1.0, step=0.1)
baseline_vmax_at_10_percent = 0.001
Vmax_ref = baseline_vmax_at_10_percent * (expression_percent / 10.0)
Km_ref = st.sidebar.slider("Methane Affinity (Km_ref, mmol/L)", 1e-8, 1e-5, 1e-7, step=1e-8)

st.sidebar.header("Biomass Settings")
cellular_material = st.sidebar.slider("Cellular Material (g/L)", 0.1, 200.0, 1.0)
baseline_cell_density = 10
cytosol_fraction = 0.03
active_volume = cellular_material * cytosol_fraction
scaling_factor = active_volume / baseline_cell_density
V_cell = 1e-15

# Initial conditions
time = np.linspace(0, 100, 5000)
alpha, beta = 0.02, 0.01
H_CH4 = H_0_CH4 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)
P_CH4 = C_atm / 1e6
C_cyt_init = H_CH4 * P_CH4
O2_init = H_0_O2 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi) * (O2_atm / 100.0)
C0 = [C_cyt_init, 0, O2_init]

# Solve ODEs
def wrapped_ode(t, C):
    return methane_oxidation(C, t, C_atm, O2_atm, g_s, Vmax_ref, Km_ref,
                             Pi, T, V_cell, scaling_factor, photosynthesis_on)

sol_ivp = solve_ivp(
    fun=wrapped_ode,
    t_span=(time[0], time[-1]),
    y0=C0,
    t_eval=time,
    method='LSODA',
    rtol=1e-6,
    atol=1e-9
)
sol = sol_ivp.y.T

# Plots
fig_plots = make_subplots(rows=3, cols=1, shared_xaxes=True,
                          subplot_titles=("Cytosolic CH₄", "Methanol (CH₃OH)", "Cytosolic O₂"))
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 0], mode='lines'), row=1, col=1)
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 1], mode='lines'), row=2, col=1)
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 2], mode='lines'), row=3, col=1)
fig_plots.update_layout(height=800, title_text="Concentration Dynamics Over Time", showlegend=False)
fig_plots.update_xaxes(title_text="Time (s)", row=3, col=1)
fig_plots.update_yaxes(title_text="mmol/L", row=1, col=1)
fig_plots.update_yaxes(title_text="mmol/L", row=2, col=1)
fig_plots.update_yaxes(title_text="mmol/L", row=3, col=1)

# Gauge
C_cyt_final = sol[-1, 0]
Km_T = Km_ref * (1 + 0.02 * (T - 25))
Vmax_T = Vmax_ref * scaling_factor * np.exp(-E_a / R * (1/(T + 273.15) - 1/T_ref))
Vmax_osm = Vmax_T * np.exp(-0.02 * (Pi / 100))
O2_cyt_final = sol[-1, 2]
Km_O2 = 0.001
V_MMO_final = Vmax_osm * (C_cyt_final / (Km_T + C_cyt_final)) * (O2_cyt_final / (Km_O2 + O2_cyt_final))

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=V_MMO_final,
    number={'suffix': " mmol/L/s", 'valueformat': '.2e'},
    title={'text': "Final CH₄ Oxidation Rate"},
    gauge={'axis': {'range': [0, max(1e-8, V_MMO_final*2)]}}
))

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_plots, use_container_width=True)
with col2:
    st.plotly_chart(fig_gauge, use_container_width=True)
