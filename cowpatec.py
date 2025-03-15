import streamlit as st
import numpy as np
import plotly.graph_objects as go

# Streamlit UI
st.title("Methane Emission & Livestock Growth Sankey Models")
st.sidebar.header("Adjust Methane Production")

# Single slider for Methane Production
CH4 = st.sidebar.slider("Methane Production (g/day)", 50, 500, 250)

# Constants for energy partitioning
GE = 400  # Fixed Gross Energy Intake (MJ/day)
FE = 100  # Fixed Fecal Energy Loss (MJ/day)
UE = 15   # Fixed Urinary Energy Loss (MJ/day)
HI = 50   # Fixed Heat Increment (MJ/day)
MEm = 60  # Fixed Maintenance Energy (MJ/day)
k_g = 0.4 # Efficiency of Growth
NEl = 40  # Fixed Energy for Lactation (MJ/day)
NE_milk = 5  # Energy per kg of Milk (MJ/kg)

# Function for Net Energy calculation
def net_energy(GE, FE, CH4, UE, HI):
    return GE - (FE + UE + CH4 + HI)

# Function for weight gain
def weight_gain(NE, MEm, k_g):
    NEg = max(NE - MEm, 0)
    return k_g * NEg

# Function for milk production
def milk_production(NE, NEl, NE_milk):
    return max((NE - NEl) / NE_milk, 0)

# Calculations
NE = net_energy(GE, FE, CH4, UE, HI)
BW_gain = weight_gain(NE, MEm, k_g)
Milk_Yield = milk_production(NE, NEl, NE_milk)

# Ensure non-negative values for Sankey inputs
NE = max(NE, 0)
BW_gain = max(BW_gain, 0)
Milk_Yield = max(Milk_Yield, 0)

# Debugging: Print the lists before passing to Sankey
print("Energy Sankey Data:")
print("Sources:", [0, 1])
print("Targets:", [1, 2])
print("Values:", [GE, NE])

# Minimal Working Example (MWE) for Energy Sankey
energy_sankey = go.Figure(go.Sankey(
    node=dict(
        pad=20,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=["Gross Energy", "Net Energy", "Body Biomass"],
        color="lightgray",
        font=dict(color="black", size=14)
    ),
    link=dict(
        source=[0, 1],  # Ensure indices exist in label
        target=[1, 2],  # Ensure indices exist in label
        value=[GE, NE],
    )
))
energy_sankey.update_layout(title_text="Simplified Energy Partitioning in Livestock", font_size=10)

# Display the simplified Sankey diagram first
st.plotly_chart(energy_sankey)

# Debugging: If this works, add back complexity gradually
st.write(f"### Methane Production: {CH4:.2f} g/day")
st.write(f"### Net Energy Available: {NE:.2f} MJ/day")
st.write(f"### Weight Gain: {BW_gain:.2f} kg/day")
st.write(f"### Milk Yield: {Milk_Yield:.2f} kg/day")
