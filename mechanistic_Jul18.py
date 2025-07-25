# Aram Mikaelyan, Assistant Professor, Department of Entomology and Plant Pathology, NCSU 
# Contact: amikael@ncsu.edu | Methane Oxidation Model (Streamlit App)
#
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint
import math
import plotly.graph_objects as go

# Arrhenius equation parameters for modeling the temperature dependence of enzyme kinetics
E_a = 50e3  # Activation energy in J/mol
R = 8.314  # Universal gas constant J/(mol*K)
T_ref = 298.15  # Reference temperature (25°C in Kelvin)

# Define the model parameters
def methane_oxidation(C, t, C_atm, g_s, Vmax_ref, Km_ref, Pi, O2, T, k_L, V_cell, scaling_factor):
    C_cyt, CH3OH, O2_cyt = C  # Unpacking state variables

    # Convert temperature to Kelvin
    T_K = T + 273.15  

    # Temperature-adjusted Vmax using Arrhenius equation
    Vmax_T = Vmax_ref * scaling_factor * np.exp(-E_a / R * (1/T_K - 1/T_ref))

    # Adjust Km with temperature
    Km_T = Km_ref * (1 + 0.02 * (T - 25))

    # Adjust Vmax for osmolarity effects
    k_osm = 0.02  # Osmolarity inhibition constant
    Vmax = Vmax_T * np.exp(-k_osm * (Pi / 100))

    # Constants
    H_0 = 1.4  # Henry's Law constant at 25°C
    alpha = 0.02  # Temperature sensitivity for solubility
    beta = 0.01  # Osmotic effect coefficient for solubility
    k_MeOH = 0.000011  # Methanol oxidation rate

    # Convert atmospheric methane from ppm to mmol/L
    C_atm_mmolL = C_atm * 0.0409

    # Adjust Henry's Law constant based on temperature and osmolarity
    H_CH4 = H_0 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)

    # Gas exchange through stomata
    P_CH4 = g_s * (C_atm / 1.0)  
    C_cyt_eq = H_CH4 * P_CH4  

    # Methane transfer into cytosol
    J_CH4 = k_L * (C_cyt_eq - C_cyt)  

    # Enzymatic oxidation in cytosol
    V_MMO = Vmax * (C_cyt / (Km_T + C_cyt))

    # Oxygen consumption
    dO2_dt = -V_MMO

    # Methanol dynamics
    dC_cyt_dt = J_CH4 - V_MMO  
    dCH3OH_dt = V_MMO - k_MeOH * CH3OH  

    return [dC_cyt_dt, dCH3OH_dt, dO2_dt]

# Streamlit UI
st.title("Methane Oxidation Model with Enzyme Sensitivity")
st.sidebar.header("Adjust Model Parameters")

C_atm = st.sidebar.slider("Atmospheric CH₄ (ppm)", 0.1, 10.0, 1.8)
g_s = st.sidebar.slider("Stomatal Conductance (gₛ, mol/m²/s)", 0.01, 0.2, 0.05)
log_vmax = st.sidebar.slider("log₁₀(Max sMMO Activity, mmol/L/s)", -3.0, math.log10(2.0), -1.0, step=0.1)
Vmax_ref = 10 ** log_vmax
st.sidebar.text(f"Vmax_ref = {Vmax_ref:.6f} mmol/L/s")
Km_ref = st.sidebar.slider("Methane Affinity (Km_ref, mmol/L)", 0.1, 2.0, 0.5)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 50)
O2 = st.sidebar.slider("Cytosolic O₂ (mmol/L)", 0.01, 2.0, 0.5)
T = st.sidebar.slider("Temperature (°C)", 5, 45, 25)
k_L = st.sidebar.slider("Mass Transfer Coefficient (k_L, m/s)", 0.001, 0.1, 0.01)
cellular_material = st.sidebar.slider("Cellular Material (g/L)", 0.1, 200.0, 1.0)

# Scaling Vmax based on biomass concentration
baseline_cell_density = 0.7  # g/L
scaling_factor = cellular_material / baseline_cell_density

# Bacterial cell volume
V_cell = 1e-15  # L

# Solve ODEs
time = np.linspace(0, 100, 500)
C0 = [0.2, 0.1, O2]  # Initial concentrations [C_cyt, CH3OH, O2_cyt]
sol = odeint(methane_oxidation, C0, time, args=(C_atm, g_s, Vmax_ref, Km_ref, Pi, O2, T, k_L, V_cell, scaling_factor))

# Plot results
fig, ax = plt.subplots()
ax.plot(time, sol[:, 0], label="C_cyt (Cytosolic CH₄)")
ax.plot(time, sol[:, 1], label="Methanol (CH₃OH)")
ax.plot(time, sol[:, 2], label="O₂ Consumption")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Concentration (mmol/L)")
ax.legend()
#st.pyplot(fig)

# Debugging output
Vmax_temp_only = Vmax_ref * np.exp(-E_a / R * (1/(T + 273.15) - 1/T_ref))
Vmax_scaled = Vmax_temp_only * scaling_factor
st.sidebar.text(f"Temp-Only Adjusted Vmax: {Vmax_temp_only:.6f} mmol/L/s")
st.sidebar.text(f"Scaled Vmax (with cell density): {Vmax_scaled:.6f} mmol/L/s")
st.sidebar.text(f"Temp-Adjusted Km: {Km_ref * (1 + 0.02 * (T - 25)):.6f} mmol/L")

# Display equations
st.sidebar.markdown("### Model Equations")
st.sidebar.latex(r"V_{max}(T) = V_{max,ref} \cdot \text{scaling} \cdot e^{-\frac{E_a}{R} \left( \frac{1}{T} - \frac{1}{T_{ref}} \right)}")
st.sidebar.latex(r"K_m(T) = K_{m,ref} \cdot (1 + 0.02 \cdot (T - 25))")
st.sidebar.latex(r"V_{max} = V_{max}(T) \cdot e^{-k_{osm} \cdot (\Pi / 100)}")

# Compute final V_MMO value at the last time point
Km_T = Km_ref * (1 + 0.02 * (T - 25))
Vmax_T = Vmax_ref * scaling_factor * np.exp(-E_a / R * (1 / (T + 273.15) - 1 / T_ref))
Vmax_osm = Vmax_T * np.exp(-0.02 * (Pi / 100))
C_cyt_final = sol[-1, 0]
V_MMO_final = Vmax_osm * (C_cyt_final / (Km_T + C_cyt_final))

# Plotly gauge to show final CH₄ oxidation rate
fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=V_MMO_final,
    number={'suffix': " mmol/L/s"},
    title={'text': "Final CH₄ Oxidation Rate"},
    gauge={
        'axis': {'range': [0, 0.3], 'tickwidth': 1, 'tickcolor': "gray"},
        'bar': {'color': "#ffcc00"},
        'steps': [
            {'range': [0, 0.03], 'color': "#ffd5d5"},
            {'range': [0.03, 0.06], 'color': "#ffaaaa"},
            {'range': [0.06, 0.09], 'color': "#ff8080"},
            {'range': [0.09, 0.12], 'color': "#ff5555"},
            {'range': [0.12, 0.15], 'color': "#ff2a2a"},
            {'range': [0.15, 0.18], 'color': "#ff0000"},
            {'range': [0.18, 0.21], 'color': "#d40000"},
            {'range': [0.21, 0.24], 'color': "#aa0000"},
            {'range': [0.24, 0.27], 'color': "#800000"},
            {'range': [0.27, 0.30], 'color': "#550000"},
        ],
        'threshold': {
            'line': {'color': "black", 'width': 4},
            'thickness': 0.75,
            'value': V_MMO_final
        }
    }
))

# Display the gauge in the main app view
col1, col2 = st.columns([2, 1])  # Wider chart, narrower gauge

with col1:
    st.pyplot(fig)

with col2:
    st.plotly_chart(fig_gauge, use_container_width=True)

st.markdown("***Hornstein E. and Mikaelyan A., in prep.***")
