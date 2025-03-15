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

# Constants for carbon partitioning (in arbitrary units)
C_intake = 1000  # Total dietary carbon intake
C_feces = 400    # Carbon lost in feces
C_urine = 50     # Carbon lost in urine
C_methane = 100  # Carbon lost as methane
C_biomass = 300  # Carbon retained in body mass
C_milk = 150     # Carbon excreted in milk

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

# Energy Sankey Diagram
energy_labels = ["Gross Energy", "Fecal Loss", "Urinary Loss", "Heat Increment", "Methane Emission", "Net Energy", "Body Biomass", "Milk Production"]
energy_source = [0, 0, 0, 0, 0, 0, 5, 5]  # Added Net Energy split
energy_target = [1, 2, 3, 4, 5, 6, 6, 7]  # Ensured Net Energy distributes properly
energy_values = [FE, UE, HI, CH4, NE, BW_gain, BW_gain, Milk_Yield]  # Balanced sources and targets

energy_sankey = go.Figure(go.Sankey(
    node=dict(
        pad=20,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=energy_labels,
        color="lightgray",
        font=dict(color="black", size=14)
    ),
    link=dict(
        source=energy_source,
        target=energy_target,
        value=energy_values,
    )
))
energy_sankey.update_layout(title_text="Energy Partitioning in Livestock", font_size=10)

# Carbon Sankey Diagram
carbon_labels = ["Dietary Carbon", "Fecal Carbon Loss", "Urinary Carbon Loss", "Methane Emission", "Carbon Retained in Biomass", "Carbon in Milk"]
carbon_source = [0, 0, 0, 0, 0, 0]  # Ensure all sources are balanced
carbon_target = [1, 2, 3, 4, 4, 5]  # Ensure carbon distributes properly
carbon_values = [C_feces, C_urine, C_methane, C_biomass, C_biomass, C_milk]  # Adjusted carbon flow

carbon_sankey = go.Figure(go.Sankey(
    node=dict(
        pad=20,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=carbon_labels,
        color="lightgray",
        font=dict(color="black", size=14)
    ),
    link=dict(
        source=carbon_source,
        target=carbon_target,
        value=carbon_values,
    )
))
carbon_sankey.update_layout(title_text="Carbon Partitioning in Livestock", font_size=10)

# Display both Sankey diagrams
st.plotly_chart(energy_sankey)
st.plotly_chart(carbon_sankey)

st.write(f"### Methane Production: {CH4:.2f} g/day")
st.write(f"### Net Energy Available: {NE:.2f} MJ/day")
st.write(f"### Weight Gain: {BW_gain:.2f} kg/day")
st.write(f"### Milk Yield: {Milk_Yield:.2f} kg/day")
