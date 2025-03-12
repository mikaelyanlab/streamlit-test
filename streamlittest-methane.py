import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint

# Define the model parameters
def methane_oxidation(C, t, g_s, Vmax, Km, Pi, J_ETC, n_MMO, T, k_L):
    C_cyt, CH3OH = C  # Unpacking state variables
    
    C_atm = 1.8  # Atmospheric methane concentration (ppm)
    P_atm = 1.0  # Atmospheric pressure (atm)
    H_0 = 1.4  # Henry's Law constant at reference temperature (25C)
    alpha = 0.02  # Temperature sensitivity coefficient
    beta = 0.01  # Osmotic effect coefficient
    Y_NADH = 2  # NADH yield per electron
    k_MeOH = 0.05  # Methanol oxidation rate
    
    # Adjust Henry's Law constant based on temperature and osmolarity
    H_CH4 = H_0 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)
    
    # Gas exchange through stomata
    P_CH4 = g_s * (C_atm / P_atm)  # Partial pressure of CH4
    C_cyt_eq = H_CH4 * P_CH4  # Equilibrium dissolved CH4 concentration
    
    # Methane solubility-based transfer into cytosol with buffering effect
    J_CH4 = (k_L * (C_cyt_eq - C_cyt)) / (1 + k_L)
    
    # sMMO enzymatic oxidation in cytosol, constrained by methane availability
    V_MMO = min(n_MMO * Vmax * (C_cyt / (Km + C_cyt)) * (1 - Pi / 100), J_CH4)
    
    # Electron supply constraint
    V_MMO = min(V_MMO, J_ETC * Y_NADH)
    
    # Methanol formation and oxidation
    dC_cyt_dt = J_CH4 - V_MMO  # Cytosolic CH4 consumption
    dCH3OH_dt = V_MMO - k_MeOH * CH3OH  # Methanol dynamics
    
    return [dC_cyt_dt, dCH3OH_dt]

# Streamlit UI
st.title("Methane Oxidation in Cytosol (sMMO) with Solubility")
st.sidebar.header("Adjust Model Parameters")

g_s = st.sidebar.slider("Stomatal Conductance (g_s)", 0.01, 0.2, 0.05)
Vmax = st.sidebar.slider("Max sMMO Activity (Vmax)", 0.1, 2.0, 1.0)
Km = st.sidebar.slider("Methane Affinity (Km)", 0.1, 2.0, 0.5)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 50)
J_ETC = st.sidebar.slider("Electron Transport (J_ETC)", 0.1, 3.0, 1.5)
n_MMO = st.sidebar.slider("Number of sMMO Molecules per Cell", 1, 10000, 1000)
T = st.sidebar.slider("Temperature (°C)", 5, 45, 25)
k_L = st.sidebar.slider("Mass Transfer Coefficient (k_L, m/s)", 0.001, 0.1, 0.01)

# Solve ODEs
time = np.linspace(0, 100, 500)
C0 = [0.2, 0.1]  # Initial concentrations [C_cyt, CH3OH]
sol = odeint(methane_oxidation, C0, time, args=(g_s, Vmax, Km, Pi, J_ETC, n_MMO, T, k_L))

# Plot results
fig, ax = plt.subplots()
ax.plot(time, sol[:, 0], label="C_cyt (Cytosolic CH4)")
ax.plot(time, sol[:, 1], label="Methanol (CH3OH)")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Concentration (mmol/L)")
ax.legend()
ax.set_title("Methane Oxidation in Cytosol - Aram Mikaelyan")
st.pyplot(fig)

# Display equations
st.sidebar.markdown("### Model Equations")
st.sidebar.latex(r"H_{CH_4} = H_0 \cdot e^{-\alpha (T - 25)} \cdot (1 - \beta \Pi)")
st.sidebar.latex(r"P_{CH_4} = g_s \cdot \frac{C_{atm}}{P_{atm}}")
st.sidebar.latex(r"C_{cyt, eq} = H_{CH_4} \cdot P_{CH_4}")
st.sidebar.latex(r"J_{CH_4} = \frac{k_L \cdot (C_{cyt, eq} - C_{cyt})}{1 + k_L}")
st.sidebar.latex(r"V_{MMO} = \min\left(n_{MMO} \cdot V_{max} \cdot \frac{C_{cyt}}{K_M + C_{cyt}} \cdot (1 - \frac{\Pi}{100}), J_{CH_4}\right)")
st.sidebar.latex(r"V_{MMO} = \min(V_{MMO}, J_{ETC} \cdot Y_{NADH})")
st.sidebar.latex(r"\frac{d[CH_3OH]}{dt} = V_{MMO} - k_{MeOH} [CH_3OH]")
