import streamlit as st
import numpy as np
from scipy.integrate import solve_ivp
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# --- Constants ---
E_a = 50e3   # J/mol for MMO; activation energy
E_a_MeOH = 45e3  # J/mol for methanol oxidation
R = 8.314   # Gas constant, J/mol/K
T_ref = 298.15  # Reference temperature, K
k_MeOH_ref = 0.00011  # 1/s at 25°C
H_0_CH4 = 1.4  # mmol/L/atm for CH4 at 25°C
H_0_O2 = 1.3   # mmol/L/atm for O2 at 25°C
g_s_ref = 0.2  # mol/m²/s
V_cell = 1e-15  # L; typical plant cell volume

# --- ODE System (per cytosol liter) ---
def methane_oxidation(C, t, C_atm, O2_atm, g_s, Vmax_ref, Km_ref, Pi, T,
                      k_L_CH4, k_L_O2, photosynthesis_on, expression_percent):
    C_cyt, CH3OH, O2_cyt = C
    T_K = T + 273.15
    # Vmax and Km adjustments
    Vmax_T = Vmax_ref * (expression_percent / 100) * np.exp(-E_a / R * (1/T_K - 1/T_ref))
    Km_T = Km_ref * (1 + 0.02 * (T - 25))
    Vmax = Vmax_T * np.exp(-0.02 * (Pi / 100))
    k_MeOH = k_MeOH_ref * np.exp(-E_a_MeOH / R * (1/T_K - 1/T_ref))
    # Henry’s constants
    alpha, beta = 0.02, 0.01
    H_CH4 = H_0_CH4 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)
    H_O2 = H_0_O2 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)
    # Partial pressures
    P_CH4 = C_atm / 1e6
    P_O2 = O2_atm / 100.0
    # Equilibria
    C_cyt_eq = H_CH4 * P_CH4
    O2_eq = H_O2 * P_O2
    # Fluxes
    g_s_scale = g_s / g_s_ref
    J_CH4 = k_L_CH4 * g_s_scale * (C_cyt_eq - C_cyt)
    J_O2 = k_L_O2 * g_s_scale * (O2_eq - O2_cyt)
    # MMO
    Km_O2 = 0.001
    V_MMO = Vmax * (C_cyt / (Km_T + C_cyt)) * (O2_cyt / (Km_O2 + O2_cyt))
    # Photosynthesis
    O2_prod = 0.005 if photosynthesis_on else 0.0
    # ODEs
    dC_cyt_dt = J_CH4 - V_MMO
    dCH3OH_dt = V_MMO - k_MeOH * CH3OH
    dO2_dt = J_O2 - V_MMO + O2_prod
    return [dC_cyt_dt, dCH3OH_dt, dO2_dt]

# --- UI ---
st.title("Methane Oxidation Model (Bulk-Scaled Output)")

# Sidebar inputs
st.sidebar.header("Atmosphere & Gas Transfer")
C_atm = st.sidebar.slider("Atmospheric CH₄ (ppm)", 0.1, 10.0, 1.8)
O2_atm = st.sidebar.slider("Atmospheric O₂ (%)", 1.0, 25.0, 21.0)
g_s = st.sidebar.slider("Stomatal Conductance (mol/m²/s)", 0.05, 2.0, 0.5)
k_L_CH4 = st.sidebar.slider("CH₄ Mass Transfer Coefficient (1/s)", 0.0001, 0.1, 0.1)
k_L_O2 = st.sidebar.slider("O₂ Mass Transfer Coefficient (1/s)", 0.0001, 0.1, 0.03)

st.sidebar.header("Cellular Environment")
T = st.sidebar.slider("Temperature (°C)", 5, 45, 25)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 50)
photosynthesis_on = st.sidebar.checkbox("Photosynthetic O₂ Production", value=True)

st.sidebar.header("Enzyme Parameters")
expression_percent = st.sidebar.slider("pMMO Expression (% of protein)", 0.1, 20.0, 1.0, step=0.1)
Vmax_ref = st.sidebar.slider("Vmax_ref (mmol·L_cyt⁻¹·s⁻¹)", 0.001, 0.5, 0.01, step=0.001)
Km_ref = st.sidebar.slider("Methane Affinity (Km_ref, mmol/L)", 0.00001, 0.005, 0.005, step=0.00001)

st.sidebar.header("Biomass Settings")
cytosol_fraction = st.sidebar.slider("Cytosol Fraction (% cell volume)", 1, 100, 5) / 100
cells_per_L_bulk = st.sidebar.number_input("Cells per liter bulk", value=1e11, format="%.2e")

# Derived bulk scaling factor
phi = cells_per_L_bulk * V_cell * cytosol_fraction  # L_cyt per L_bulk

# Initial conditions
time = np.linspace(0, 1000, 5000)
O2_init = H_0_O2 * np.exp(-0.02 * (T - 25)) * (1 - 0.01 * Pi) * (O2_atm / 100.0)
C0 = [0.0001, 0.0001, O2_init]

# Solve
def wrapped_ode(t, C):
    return methane_oxidation(C, t, C_atm, O2_atm, g_s, Vmax_ref, Km_ref,
                             Pi, T, k_L_CH4, k_L_O2, photosynthesis_on, expression_percent)

sol_ivp = solve_ivp(fun=wrapped_ode, t_span=(time[0], time[-1]),
                    y0=C0, t_eval=time, method='LSODA', rtol=1e-6, atol=1e-9)
sol = sol_ivp.y.T

# Final MMO rate (cytosol)
C_cyt_final = sol[-1, 0]
Km_T = Km_ref * (1 + 0.02 * (T - 25))
Vmax_T = Vmax_ref * (expression_percent / 100) * np.exp(-E_a / R * (1/(T + 273.15) - 1/T_ref))
Vmax_osm = Vmax_T * np.exp(-0.02 * (Pi / 100))
O2_cyt_final = sol[-1, 2]
Km_O2 = 0.001
V_MMO_cyt = Vmax_osm * (C_cyt_final / (Km_T + C_cyt_final)) * (O2_cyt_final / (Km_O2 + O2_cyt_final))

# Scale to bulk
V_MMO_bulk = V_MMO_cyt * phi

# Plots
fig_plots = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                          subplot_titles=("Cytosolic CH₄", "Methanol", "Cytosolic O₂"))
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 0], mode='lines', name="CH₄"), row=1, col=1)
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 1], mode='lines', name="MeOH"), row=2, col=1)
fig_plots.add_trace(go.Scatter(x=time, y=sol[:, 2], mode='lines', name="O₂"), row=3, col=1)
fig_plots.update_layout(height=800, title_text="Cytosolic Dynamics", showlegend=False)
fig_plots.update_xaxes(title_text="Time (s)", row=3, col=1)

# Final MMO rate gauge (bulk-scaled)
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=V_MMO_bulk,
    number={'suffix': " mmol/L_bulk/s", 'valueformat': '.3g'},
    title={'text': "Final CH₄ Oxidation Rate (bulk-scaled)"},
    gauge={
        'axis': {'range': [0, 1e-6]},
        'bar': {'color': "#ffcc00"},
        'steps': [
            {'range': [i*1e-7, (i+1)*1e-7], 
             'color': f"rgba(255,0,0,{0.1 + 0.1*i})"} for i in range(10)
        ],
        'threshold': {
            'line': {'color': "black", 'width': 4},
            'value': V_MMO_bulk
        }
    }
))


col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_plots, use_container_width=True)
with col2:
    st.plotly_chart(fig_gauge, use_container_width=True)

st.sidebar.text(f"Bulk scaling φ = {phi:.2e} L_cyt per L_bulk")
