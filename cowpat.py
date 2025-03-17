import streamlit as st 
import numpy as np
import plotly.graph_objects as go

# Streamlit UI
st.title("Energy and Carbon Partitioning in Livestock")
st.sidebar.header("Adjust Methane Loss")

# Single slider for Methane Loss (0 to 500 g/day)
CH4 = st.sidebar.slider("Methane Loss (g/day)", 0, 500, 250)

# Constants for energy partitioning (MJ/day)
GE = 250  # Gross Energy Intake (Based on high-producing dairy cow estimates, NRC 2001)
GE_adjusted = GE - (CH4 * 0.055)  # Adjust GE after methane loss (assuming 55.5 MJ/kg CH4)
FE = 0.35 * GE_adjusted  # Fecal Energy Loss (~35% of adjusted GE)
UE = 0.07 * GE_adjusted  # Urinary Energy Loss (~7% of adjusted GE)
HI = 0.25 * GE_adjusted  # Heat Increment (~25% of adjusted GE)
MEm = 41  # Maintenance Energy (fixed at 41 MJ/day)
k_g = 0.4  # Efficiency of Growth
NEl = 50  # Fixed Energy for Lactation
NE_milk = 3  # Energy per kg of Milk

# Energy functions
def net_energy(GE, FE, CH4, UE, HI):
    CH4_energy_loss = CH4 * 0.055  # Convert CH4 (g) to MJ using 55.5 MJ/kg CH4
    return GE - (FE + UE + CH4_energy_loss + HI)  # Net Energy after accounting for losses

def weight_gain_energy(NE, MEm, k_g):
    return k_g * max(0, (NE - MEm))  # Prevent negative values

# Compute energy available after losses
NE = net_energy(GE, FE, CH4, UE, HI)

# Allocate energy to maintenance first
NE_remaining = max(0, NE - MEm)  # Maintenance energy is deducted first

# Deduct fixed NEl (50 MJ/day) for milk production
NE_remaining_after_milk = max(0, NE_remaining - NEl)

# Allocate remaining energy to biomass (growth)
BW_gain_energy = k_g * NE_remaining_after_milk  # Biomass energy after milk demand

# Pricing assumptions for milk and meat (USD)
Milk_Price = 0.47  # USD per kg of milk
Meat_Price = 5.00  # USD per kg of live weight gain

# Compute revenue (displayed below graphs)
Milk_Revenue = (NEl / NE_milk) * Milk_Price  # Fixed milk revenue from 50 MJ/day
Meat_Revenue = BW_gain_energy * Meat_Price  # Meat revenue responds dynamically

# Display results
st.write(f"### Methane Loss: {CH4:.2f} g/day")
st.write(f"### Net Energy Available: {NE:.2f} MJ/day")
st.write(f"### Weight Gain (Energy): {BW_gain_energy:.2f} kg/day")
st.write(f"### Milk Revenue: **${Milk_Revenue:.2f} per day**")
st.write(f"### Meat Revenue: **${Meat_Revenue:.2f} per day**")
