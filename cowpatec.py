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
GE_adjusted = GE - (CH4 * 0.055)  # Adjust GE after methane loss (assuming 55.5 MJ/kg CH4), though alternative models may apply fecal/urinary loss first  # Adjust Gross Energy after methane loss
FE = 0.35 * GE_adjusted  # Fecal Energy Loss (~35% of adjusted GE), value estimated from NRC (2001) and empirical data from Arndt et al. (2015)  # Fecal Energy Loss (~35% of adjusted GE)  # Fecal Energy Loss (~35% of GE)  # Fecal Energy Loss
UE = 0.07 * GE_adjusted  # Urinary Energy Loss (~7% of adjusted GE), consistent with NRC (2001) estimates for cattle  # Urinary Energy Loss (~7% of adjusted GE)  # Urinary Energy Loss (~7% of GE)   # Urinary Energy Loss
HI = 0.25 * GE_adjusted  # Heat Increment (~25% of adjusted GE), based on maintenance metabolism estimates from Ferrell & Jenkins (1984)  # Heat Increment (~25% of adjusted GE)  # Heat Increment (~25% of GE)   # Heat Increment (Now Constant)
MEm = 41  # Maintenance Energy (Derived from NRC 2001 and Cooper-Prado et al. 2014 for a 600 kg cow) (fixed for now, but could be dynamic based on BW)  # Maintenance Energy
k_g = 0.4 # Efficiency of Growth
NEl = 50  # Energy for Lactation
NE_milk = 3  # Energy per kg of Milk

# Constants for carbon partitioning (g/day)
C_Intake = 6000  # Carbon Intake
C_Fecal = 0.30 * C_Intake  # Fecal Carbon Loss (~30% of Intake), estimated from Morse et al. (1994) and Vtoryi et al. (2022)  # Fecal Carbon Loss (~30% of Intake)  # 30% of Carbon Intake lost as feces
C_Urinary = 0.05 * C_Intake  # Urinary Carbon Loss (~5% of Intake), estimated from NRC (2001)  # Urinary Carbon Loss (~5% of Intake)  # Urinary Carbon Loss (~5% of Intake)
C_CO2 = 0.45 * C_Intake  # Respired CO2 (~45% of Intake), based on metabolic CO2 fluxes from VandeHaar & St. Pierre (2006)  # Respired CO2 (~45% of Intake)  # 45% Respired CO2
C_Maintenance = 300  # Carbon for Maintenance
C_Lactation = 200  # Carbon for Milk
C_milk = 5  # Carbon per kg of Milk

# Methane Carbon Loss (dynamically adjusted based on CH4 loss and 9% GE energy loss)
C_CH4 = CH4 * (12/16)  # Convert CH4 (g) to carbon equivalent (g), based on molecular composition of methane (C = 12/16 of CH4)  # Convert CH4 (g) to carbon equivalent (g), assuming 55 MJ/kg CH4

# Energy functions
def net_energy(GE, FE, CH4, UE, HI):
    CH4_energy_loss = CH4 * 0.055  # Convert CH4 (g) to MJ using 55.5 MJ/kg CH4
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
CH4_energy_loss = CH4 * 0.055  # Ensure this is defined before use
energy_values = [GE, -FE, -UE, -HI, -CH4_energy_loss]

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
