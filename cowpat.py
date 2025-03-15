import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import odeint

# Function for methane production
# CH4 (g/day) = a * DMI + b * NDF - c * Fat
def methane_production(DMI, NDF, Fat):
    a, b, c = 20, 15, 10  # Coefficients for demonstration
    return a * DMI + b * NDF - c * Fat

# Function for Net Energy calculation
# NE = ME - HI
# ME = GE - (UE + CH4)
def net_energy(GE, CH4, UE, HI):
    ME = GE - (UE + CH4)
    return ME - HI

# Function for weight gain
# BW = k_g * NEg
def weight_gain(NE, MEm, kg):
    NEg = max(NE - MEm, 0)  # Energy left for growth
    return kg * NEg

# Function for milk production
# MY = NE_L / NE_milk
def milk_production(NE, NEl, NE_milk):
    return max((NE - NEl) / NE_milk, 0)

# Streamlit UI
st.title("Methane Emission & Livestock Growth Model")
st.sidebar.header("Adjust Parameters")

# Sliders for inputs
DMI = st.sidebar.slider("Dry Matter Intake (kg/day)", 5, 30, 15)
NDF = st.sidebar.slider("Neutral Detergent Fiber (kg/day)", 10, 40, 20)
Fat = st.sidebar.slider("Fat Content (%)", 0, 10, 2)
GE = st.sidebar.slider("Gross Energy Intake (MJ/day)", 100, 400, 250)
UE = st.sidebar.slider("Urinary Energy Loss (MJ/day)", 5, 30, 15)
HI = st.sidebar.slider("Heat Increment (MJ/day)", 20, 100, 50)
MEm = st.sidebar.slider("Maintenance Energy (MJ/day)", 30, 120, 60)
k_g = st.sidebar.slider("Efficiency of Growth (k_g)", 0.2, 0.6, 0.4)
NEl = st.sidebar.slider("Energy for Lactation (MJ/day)", 10, 80, 40)
NE_milk = st.sidebar.slider("Energy per kg of Milk (MJ/kg)", 2, 10, 5)

# Calculations
CH4 = methane_production(DMI, NDF, Fat)
NE = net_energy(GE, CH4, UE, HI)
BW_gain = weight_gain(NE, MEm, k_g)
Milk_Yield = milk_production(NE, NEl, NE_milk)

# Plot results
fig, ax = plt.subplots()
ax.bar(["Methane (g/day)", "Weight Gain (kg)", "Milk Yield (kg)"], [CH4, BW_gain, Milk_Yield])
ax.set_ylabel("Output Values")
ax.set_title("Effects of Feed Composition on Methane & Production")

# Display results
st.pyplot(fig)
st.write(f"### Methane Production: {CH4:.2f} g/day")
st.write(f"### Weight Gain: {BW_gain:.2f} kg/day")
st.write(f"### Milk Yield: {Milk_Yield:.2f} kg/day")
