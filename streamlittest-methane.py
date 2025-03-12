import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint

# Define the model parameters
def methane_oxidation(C, t, g_s, Vmax, Km, Pi, J_ETC):
    C_atm = 1.8  # Atmospheric methane concentration (ppm)
    D_CH4 = 0.02  # Diffusion coefficient of methane
    d = 10e-6  # Distance in meters
    Y_NADH = 2  # NADH yield per electron
    k_MeOH = 0.05  # Methanol oxidation rate
    
    C_int, C_chl, CH3OH = C  # Unpacking state variables
    
    # Gas exchange through stomata
    F_CH4 = g_s * (C_atm - C_int)
    
    # Methane diffusion into chloroplast
    J_CH4 = D_CH4 * (C_int - C_chl) / d
    
    # MMO enzymatic oxidation
    V_MMO = Vmax * (C_chl / (Km + C_chl)) * (1 - Pi / 100)  # Osmolarity effect
    
    # Electron supply constraint
    V_MMO = min(V_MMO, J_ETC * Y_NADH)
    
    # Methanol formation and oxidation
    dC_int_dt = F_CH4 - J_CH4
    dC_chl_dt = J_CH4 - V_MMO
    dCH3OH_dt = V_MMO - k_MeOH * CH3OH
    
    return [dC_int_dt, dC_chl_dt, dCH3OH_dt]

# Streamlit UI
st.title("Methane Oxidation in Chloroplasts")
st.sidebar.header("Adjust Model Parameters")

g_s = st.sidebar.slider("Stomatal Conductance (g_s)", 0.01, 0.2, 0.05)
Vmax = st.sidebar.slider("Max MMO Activity (Vmax)", 0.1, 2.0, 1.0)
Km = st.sidebar.slider("Methane Affinity (Km)", 0.1, 2.0, 0.5)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 50)
J_ETC = st.sidebar.slider("Electron Transport (J_ETC)", 0.1, 3.0, 1.5)

# Solve ODEs
time = np.linspace(0, 100, 500)
C0 = [0.5, 0.2, 0.1]  # Initial concentrations
sol = odeint(methane_oxidation, C0, time, args=(g_s, Vmax, Km, Pi, J_ETC))

# Plot results
fig, ax = plt.subplots()
ax.plot(time, sol[:, 0], label="C_int (Intercellular CH4)")
ax.plot(time, sol[:, 1], label="C_chl (Chloroplast CH4)")
ax.plot(time, sol[:, 2], label="Methanol (CH3OH)")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Concentration (ppm or relative)")
ax.legend()
st.pyplot(fig)
