import streamlit as st 
import numpy as np
import plotly.graph_objects as go

# Streamlit UI
st.title("Energy and Carbon Partitioning in Livestock")
st.sidebar.header("Adjust Methane Loss")

# Single slider for Methane Loss (0 to 500 g/day)
CH4 = st.sidebar.slider("Methane Loss (g/day)", 0, 500, 250)

# Constants for energy partitioning (MJ/day)
GE = 250  # Gross Energy Intake
FE = 63  # Fecal Energy Loss
UE = 10   # Urinary Energy Loss
HI = 50   # Heat Increment (Now Constant)
MEm = 41  # Maintenance Energy
k_g = 0.4 # Efficiency of Growth
NEl = 41  # Energy for Lactation
NE_milk = 3  # Energy per kg of Milk

# Constants for carbon partitioning (g/day)
C_Intake = 6000  # Carbon Intake
C_Fecal = 1800  # 30% of Carbon Intake lost as feces
C_Urinary = 300  # Urinary Carbon Loss (~5% of Intake)
C_CO2 = 2700  # 45% Respired CO2
C_Maintenance = 300  # Carbon for Maintenance
C_Lactation = 200  # Carbon for Milk
C_milk = 5  # Carbon per kg of Milk

# Methane Carbon Loss (dynamically adjusted based on CH4 loss and 9% GE energy loss)
C_CH4 = CH4 * (12/16)  # Convert CH4 (g) to carbon equivalent (g), assuming 55 MJ/kg CH4

# Energy functions
def net_energy(GE, FE, CH4, UE, HI):
    CH4_energy_loss = (CH4 / 16) * 55.5  # Convert CH4 (g) to MJ using 55.5 MJ/kg CH4
    return GE - (FE + UE + CH4_energy_loss + HI)  # Methane energy loss fixed at 9% of GE

def weight_gain_energy(NE, MEm, k_g):
    return k_g * (NE - MEm)  # Allow negative values

def milk_production_energy(NE, NEl, NE_milk):
    return (NE - NEl) / NE_milk  # Allow negative values

# Carbon functions
def net_carbon(C_Intake, C_Fecal, C_CH4, C_Urinary, C_CO2):
    return C_Intake - (C_Fecal + C_CH4 + C_Urinary + C_CO2)

def weight_gain_carbon(C_Net, C_Maintenance, k_g):
    return k_g * (C_Net - C_Maintenance)  # Allow negative values

def milk_production_carbon(C_Net, C_Lactation, C_milk):
    return (C_Net - C_Lactation) / C_milk  # Allow negative values

# Compute energy and carbon values
NE = net_energy(GE, FE, CH4, UE, HI)
BW_gain_energy = weight_gain_energy(NE, MEm, k_g)
Milk_Yield_energy = milk_production_energy(NE, NEl, NE_milk)

C_Net = net_carbon(C_Intake, C_Fecal, C_CH4, C_Urinary, C_CO2)
BW_gain_carbon = weight_gain_carbon(C_Net, C_Maintenance, k_g)
Milk_Yield_carbon = milk_production_carbon(C_Net, C_Lactation, C_milk)

# Prepare data for stacked bar chart
energy_labels = ["Gross Energy", "Fecal Loss", "Urinary Loss", "Heat Increment", "Methane Loss"]
energy_values = [GE, -FE, -UE, -HI, -(0.09 * GE)]

carbon_labels = ["Carbon Intake", "Fecal Loss", "Urinary Loss", "Respired CO2", "Methane Loss"]
carbon_values = [C_Intake, -C_Fecal, -C_Urinary, -C_CO2, -C_CH4]

# Stacked net energy bar
fig_energy = go.Figure()
fig_energy.add_trace(go.Bar(
    x=energy_labels,
    y=energy_values,
    marker_color=["blue", "red", "red", "red", "red"],
    name="Total Gross Energy"
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
    name="Total Carbon Intake"
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
st.write(f"### Milk Yield (Carbon): {Milk_Yield_carbon:.2f} g/day")
