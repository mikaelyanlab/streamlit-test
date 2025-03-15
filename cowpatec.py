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

# Adjust heat increment dynamically to balance losses
HI_adjusted = HI + (CH4 * 0.1)  # Increased heat loss with more methane

# Energy functions
def net_energy(GE, FE, CH4, UE, HI):
    return GE - (FE + UE + CH4 + HI)

def weight_gain_energy(NE, MEm, k_g):
# max (NE - MEm, 0) ensures that a value does not drop below 0.
    return k_g * max(NE - MEm, 0)

def milk_production_energy(NE, NEl, NE_milk):
    return max((NE - NEl) / NE_milk, 0)

# Carbon functions
def net_carbon(C_Intake, C_Fecal, CH4, C_Urinary, C_CO2):
    return C_Intake - (C_Fecal + CH4 + C_Urinary + C_CO2)

def weight_gain_carbon(C_Net, C_Maintenance, k_g):
    return k_g * max(C_Net - C_Maintenance, 0)

def milk_production_carbon(C_Net, C_Lactation, C_milk):
    return max((C_Net - C_Lactation) / C_milk, 0)

# Compute energy and carbon values
NE = net_energy(GE, FE, CH4, UE, HI_adjusted)
BW_gain_energy = weight_gain_energy(NE, MEm, k_g)
Milk_Yield_energy = milk_production_energy(NE, NEl, NE_milk)

C_Net = net_carbon(C_Intake, C_Fecal, CH4, C_Urinary, C_CO2)
BW_gain_carbon = weight_gain_carbon(C_Net, C_Maintenance, k_g)
Milk_Yield_carbon = milk_production_carbon(C_Net, C_Lactation, C_milk)

# Prepare data for stacked bar chart
energy_labels = ["Gross Energy", "Fecal Loss", "Urinary Loss", "Heat Increment", "Methane Loss"]
energy_values = [GE, -FE, -UE, -HI_adjusted, -CH4]

carbon_labels = ["Carbon Intake", "Fecal Loss", "Urinary Loss", "Respired CO2", "Methane Loss"]
carbon_values = [C_Intake, -C_Fecal, -C_Urinary, -C_CO2, -CH4]

# Stacked net energy bar
fig_energy = go.Figure()
fig_energy.add_trace(go.Bar(
    x=energy_labels,
    y=energy_values,
    marker_color=["blue", "red", "red", "red", "red"],
    name="Energy Partitioning"
))
fig_energy.add_trace(go.Bar(
    x=["Net Energy"],
    y=[BW_gain_energy],
    marker_color=["green"],
    name="Body Biomass"
))
fig_energy.add_trace(go.Bar(
    x=["Net Energy"],
    y=[Milk_Yield_energy],
    marker_color=["yellow"],
    name="Milk Production"
))
fig_energy.update_layout(title="Energy Partitioning (MJ/day)", yaxis_title="MJ/day", barmode="relative")

# Stacked net carbon bar
fig_carbon = go.Figure()
fig_carbon.add_trace(go.Bar(
    x=carbon_labels,
    y=carbon_values,
    marker_color=["blue", "red", "red", "red", "red"],
    name="Carbon Partitioning"
))
fig_carbon.add_trace(go.Bar(
    x=["Net Carbon"],
    y=[BW_gain_carbon],
    marker_color=["green"],
    name="Body Biomass"
))
fig_carbon.add_trace(go.Bar(
    x=["Net Carbon"],
    y=[Milk_Yield_carbon],
    marker_color=["yellow"],
    name="Milk Production"
))
fig_carbon.update_layout(title="Carbon Partitioning (g/day)", yaxis_title="g/day", barmode="relative")

# Display both bar charts side by side
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
