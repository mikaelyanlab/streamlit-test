# Aram Mikaelyan, Assistant Professor, Department of Entomology and Plant Pathology, NCSU
# Contact: amikael@ncsu.edu | Methane Oxidation Model (Streamlit App)
#
import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint

# Arrhenius equation parameters for modeling the temperature dependence of enzyme kinetics
E_a = 50e3  # Activation energy in J/mol
R = 8.314  # Universal gas constant J/(mol*K)
T_ref = 298.15  # Reference temperature (25°C in Kelvin)

# Define the model parameters
def methane_oxidation(C, t, C_atm, g_s, Vmax_ref, Km_ref, Pi, O2, T, k_L, V_cell):
    C_cyt, CH3OH, O2_cyt = C  # Unpacking state variables

    # Convert temperature to Kelvin
    T_K = T + 273.15  

    # Temperature-adjusted Vmax using Arrhenius equation (adjusting reaction rates to increase exponentially with temperature)
    Vmax_T = Vmax_ref * np.exp(-E_a / R * (1/T_K - 1/T_ref))

    # Adjust Km with temperature (assumes Km increases slightly, 2% changein Km per °C is a reasonable approximation)
    Km_T = Km_ref * (1 + 0.02 * (T - 25))

    # Adjust Vmax for osmolarity effects (enzyme function is affected by osmotic stress - model assumes a simple linear relationship between osmolarity and Vmax - a 10% increase leads to a reduction of Vmax by 10%)
    k_osm = 0.02  # Osmolarity inhibition constant (adjust based on experimental data)
    Vmax = Vmax_T * np.exp(-k_osm * (Pi / 100))

    # Constants
    H_0 = 1.4  # Henry's Law constant at 25°C
    alpha = 0.02  # Temperature sensitivity coefficient for solubility
    beta = 0.01  # Osmotic effect coefficient for solubility
    k_MeOH = 0.000011  # Methanol oxidation rate adjusted to 0.000011, Gout et al. (2000) based on 0.2 umol/hr/g in Sycamore cell suspension  

    # Convert atmospheric methane from ppm to mmol/L
    C_atm_mmolL = C_atm * 0.0409

    # Adjust Henry's Law constant based on temperature and osmolarity
    H_CH4 = H_0 * np.exp(-alpha * (T - 25)) * (1 - beta * Pi)

    # Gas exchange through stomata
    P_CH4 = g_s * (C_atm / 1.0)  
    C_cyt_eq = H_CH4 * P_CH4  

    # Methane solubility-based transfer into cytosol
    J_CH4 = k_L * (C_cyt_eq - C_cyt)  

    # Enzymatic oxidation in cytosol, now temperature & osmolarity-sensitive
    V_MMO = Vmax * (C_cyt / (Km_T + C_cyt))

    # Oxygen consumption in a 1:1 molar ratio with methane oxidation
    dO2_dt = -V_MMO

    # Methanol formation and oxidation
    dC_cyt_dt = J_CH4 - V_MMO  
    dCH3OH_dt = V_MMO - k_MeOH * CH3OH  

    return [dC_cyt_dt, dCH3OH_dt, dO2_dt]

# Streamlit UI
st.title("Methane Oxidation Model with Enzyme Sensitivity")
st.sidebar.header("Adjust Model Parameters")

C_atm = st.sidebar.slider("Atmospheric CH4 (ppm)", 0.1, 10.0, 1.8)
g_s = st.sidebar.slider("Stomatal Conductance (g_s)", 0.01, 0.2, 0.05)
Vmax_ref = st.sidebar.slider("Max sMMO Activity at 25°C (Vmax_ref)", 0.1, 2.0, 1.0)
Km_ref = st.sidebar.slider("Methane Affinity at 25°C (Km_ref)", 0.1, 2.0, 0.5)
Pi = st.sidebar.slider("Cytosolic Osmolarity (%)", 0, 100, 50)
O2 = st.sidebar.slider("Cytosolic Oxygen (mmol/L)", 0.01, 2.0, 0.5)
T = st.sidebar.slider("Temperature (°C)", 5, 45, 25)
k_L = st.sidebar.slider("Mass Transfer Coefficient (k_L, m/s)", 0.001, 0.1, 0.01)

# Assume a bacterial cell volume
V_cell = 1e-15  # L

# Solve ODEs
time = np.linspace(0, 100, 500)
C0 = [0.2, 0.1, O2]  # Initial concentrations [C_cyt, CH3OH, O2_cyt]
sol = odeint(methane_oxidation, C0, time, args=(C_atm, g_s, Vmax_ref, Km_ref, Pi, O2, T, k_L, V_cell))

# Plot results
fig, ax = plt.subplots()
ax.plot(time, sol[:, 0], label="C_cyt (Cytosolic CH4)")
ax.plot(time, sol[:, 1], label="Methanol (CH3OH)")
ax.plot(time, sol[:, 2], label="O2 Consumption")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Concentration (mmol/L)")
ax.legend()
st.pyplot(fig)

# Debugging Output
st.sidebar.text(f"Temp-Adjusted Vmax: {Vmax_ref * np.exp(-E_a / R * (1/(T+273.15) - 1/T_ref)):.6f}")
st.sidebar.text(f"Temp-Adjusted Km: {Km_ref * (1 + 0.02 * (T - 25)):.6f}")

# Display equations
st.sidebar.markdown("### Model Equations")
st.sidebar.latex(r"V_{max}(T) = V_{max, ref} \cdot e^{-\frac{E_a}{R} \left(\frac{1}{T} - \frac{1}{T_{ref}}\right)}")
st.sidebar.latex(r"K_m(T) = K_{m, ref} \cdot (1 + 0.02 \cdot (T - 25))")
st.sidebar.latex(r"V_{max} = V_{max}(T) \cdot (1 - \frac{\Pi}{100})")
st.markdown("***Hornstein E. and Mikaelyan A., in prep.***")


