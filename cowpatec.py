import streamlit as st
import numpy as np
import plotly.graph_objects as go

# Streamlit UI
st.title("Energy and Carbon Partitioning in Livestock")
st.sidebar.header("Adjust Methane Loss")

# Single slider for Methane Loss (0 to 500 g/day)
CH4 = st.sidebar.slider("Methane Loss (g/day)", 0, 500, 250)

# Constants for energy partitioning (MJ/day)
GE = 400  # Gross Energy Intake
FE = 100  # Fecal Energy Loss
UE = 15   # Urinary Energy Loss
HI = 50   # Heat Increment
MEm = 60  # Maintenance Energy
k_g = 0.4 # Efficiency of Growth
NEl = 40  # Energy for Lactation
NE_milk = 5  # Energy per kg of Milk

# Constants for carbon partitioning (g/day)
C_Intake = 2500  # Carbon Intake
C_Fecal = 600  # Fecal Carbon Loss
C_Urinary = 50  # Urinary Carbon Loss
C_CO2 = 1200  # Respired CO2
C_Maintenance = 300  # Carbon for Maintenance
C_Lactation = 200  # Carbon for Milk
C_milk = 5  # Carbon per kg of Milk

# Energy functions
def net_energy(GE, FE, CH4, UE, HI):
    return GE - (FE + UE + CH4 + HI)

def weight_gain_energy(NE, MEm, k_g):
    NEg = max(NE - MEm, 0)
    return k_g * NEg

def milk_production_energy(NE, NEl, NE_milk):
    return max((NE - NEl) / NE_milk, 0)

# Carbon functions
def net_carbon(C_Intake, C_Fecal, CH4, C_Urinary, C_CO2):
    return C_Intake - (C_Fecal + CH4 + C_Urinary + C_CO2)

def weight_gain_carbon(C_Net, C_Maintenance, k_g):
    C_Gain = max(C_Net - C_Maintenance, 0)
    return k_g * C_Gain

def milk_production_carbon(C_Net, C_Lactation, C_milk):
    return max((C_Net - C_Lactation) / C_milk, 0)

# Compute energy and carbon values
NE = net_energy(GE, FE, CH4, UE, HI)
BW_gain_energy = weight_gain_energy(NE, MEm, k_g)
Milk_Yield_energy = milk_production_energy(NE, NEl, NE_milk)

C_Net = net_carbon(C_Intake, C_Fecal, CH4, C_Urinary, C_CO2)
BW_gain_carbon = weight_gain_carbon(C_Net, C_Maintenance, k_g)
Milk_Yield_carbon = milk_production_carbon(C_Net, C_Lactation, C_milk)

# Define nodes and links for Energy Sankey
en_labels = ["Gross Energy", "Fecal Loss", "Urinary Loss", "Heat Increment", "Methane Loss", "Net Energy", "Body Biomass", "Milk Production"]
en_values = [GE, FE, UE, HI, CH4, NE, BW_gain_energy, Milk_Yield_energy]
en_source = [0, 0, 0, 0, 0, 0, 5, 5]  # Ensure Gross Energy always connects to Net Energy
en_target = [1, 2, 3, 4, 5, 6, 7, 8]

fig_energy = go.Figure(go.Sankey(
    node=dict(
        pad=20,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=en_labels,
    ),
    link=dict(
        source=en_source,
        target=en_target,
        value=en_values,
    )
))
fig_energy.update_layout(title_text="Energy Partitioning in Livestock", font_size=10)

# Define nodes and links for Carbon Sankey
carbon_labels = ["Carbon Intake", "Fecal Loss", "Urinary Loss", "Respired CO2", "Methane Loss", "Net Carbon", "Body Biomass", "Milk Production"]
carbon_values = [C_Intake, C_Fecal, C_Urinary, C_CO2, CH4, C_Net, BW_gain_carbon, Milk_Yield_carbon]
carbon_source = [0, 0, 0, 0, 0, 0, 5, 5]  # Ensure Carbon Intake always connects to Net Carbon
carbon_target = [1, 2, 3, 4, 5, 6, 7, 8]

fig_carbon = go.Figure(go.Sankey(
    node=dict(
        pad=20,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=carbon_labels,
    ),
    link=dict(
        source=carbon_source,
        target=carbon_target,
        value=carbon_values,
    )
))
fig_carbon.update_layout(title_text="Carbon Partitioning in Livestock", font_size=10)

# Display both Sankey diagrams side by side
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_energy)
with col2:
    st.plotly_chart(fig_carbon)

# Display results
st.write(f"### Methane Loss: {CH4:.2f} g/day")
st.write(f"### Net Energy Available: {NE:.2f} MJ/day")
st.write(f"### Weight Gain (Energy): {BW_gain_energy:.2f} kg/day")
st.write(f"### Milk Yield (Energy): {Milk_Yield_energy:.2f} kg/day")
st.write(f"### Net Carbon Available: {C_Net:.2f} g/day")
st.write(f"### Weight Gain (Carbon): {BW_gain_carbon:.2f} g/day")
st.write(f"### Milk Yield (Carbon): {Milk_Yield_carbon:.2f} kg/day")
