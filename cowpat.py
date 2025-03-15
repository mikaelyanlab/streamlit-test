import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

# Streamlit UI
st.title("Methane Emission & Livestock Growth Model")
st.sidebar.header("Adjust Parameters")

# Sliders for inputs
CH4 = st.sidebar.slider("Methane Production (g/day)", 50, 500, 250)
GE = st.sidebar.slider("Gross Energy Intake (MJ/day)", 100, 400, 250)
FE = st.sidebar.slider("Fecal Energy Loss (MJ/day)", 30, 200, 100)
UE = st.sidebar.slider("Urinary Energy Loss (MJ/day)", 5, 30, 15)
HI = st.sidebar.slider("Heat Increment (MJ/day)", 20, 100, 50)
MEm = st.sidebar.slider("Maintenance Energy (MJ/day)", 30, 120, 60)
k_g = st.sidebar.slider("Efficiency of Growth (k_g)", 0.2, 0.6, 0.4)
NEl = st.sidebar.slider("Energy for Lactation (MJ/day)", 10, 80, 40)
NE_milk = st.sidebar.slider("Energy per kg of Milk (MJ/kg)", 2, 10, 5)

# Function for Net Energy calculation
# NE = GE - (FE + UE + CH4 + HI)
def net_energy(GE, FE, CH4, UE, HI):
    return GE - (FE + UE + CH4 + HI)

# Function for weight gain
# BW = k_g * NEg
def weight_gain(NE, MEm, k_g):
    NEg = max(NE - MEm, 0)  # Energy left for growth
    return k_g * NEg

# Function for milk production
# MY = NE_L / NE_milk
def milk_production(NE, NEl, NE_milk):
    return max((NE - NEl) / NE_milk, 0)

# Calculations
NE = net_energy(GE, FE, CH4, UE, HI)
BW_gain = weight_gain(NE, MEm, k_g)
Milk_Yield = milk_production(NE, NEl, NE_milk)

# Plot results
fig, ax = plt.subplots()
ax.plot([CH4], [BW_gain], 'bo-', label="Weight Gain (kg)")
ax.plot([CH4], [Milk_Yield], 'ro-', label="Milk Yield (kg)")
ax.set_xlabel("Methane Production (g/day)")
ax.set_ylabel("Production Output")
ax.set_title("Effects of Methane on Biomass and Milk Production")
ax.legend()

# Display results
st.pyplot(fig)
st.write(f"### Net Energy Available: {NE:.2f} MJ/day")
st.write(f"### Weight Gain: {BW_gain:.2f} kg/day")
st.write(f"### Milk Yield: {Milk_Yield:.2f} kg/day")
