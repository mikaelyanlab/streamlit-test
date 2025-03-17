import streamlit as st 
import numpy as np
import plotly.graph_objects as go

# Streamlit UI
st.title("Energy Partitioning in Livestock")
st.sidebar.header("Adjust Methane Loss and Milk Production")

# Sliders for Methane Loss and Milk Production
CH4 = st.sidebar.slider("Methane Loss (g/day)", 0, 500, 250)
Milk_Production = st.sidebar.slider("Milk Production (kg/day)", 0, 50, 45)  # Dynamic milk production slider

# Constants for energy partitioning (MJ/day)
GE = 250  # Gross Energy Intake (Based on high-producing dairy cow estimates, NRC 2001)
GE_adjusted = GE - (CH4 * 0.055)  # Adjust GE after methane loss (assuming 55.5 MJ/kg CH4)
FE = 0.35 * GE_adjusted  # Fecal Energy Loss (~35% of adjusted GE), based on NRC (2001) and Arndt et al. (2015)
UE = 0.07 * GE_adjusted  # Urinary Energy Loss (~7% of adjusted GE), based on NRC (2001)
HI = 0.25 * GE_adjusted  # Heat Increment (~25% of adjusted GE), based on Ferrell & Jenkins (1984)
MEm = 41  # Maintenance Energy (fixed at 41 MJ/day, based on NRC 2001 & Cooper-Prado et al. 2014)
k_g = 0.4  # Efficiency of Growth
NE_milk = 3  # Energy per kg of Milk
NEl = NE_milk * Milk_Production  # Energy for Lactation (Dynamic based on milk yield)

# Milk price assumption (USD per kg)
Milk_Price = 0.47  # USD per kg
Milk_Revenue = Milk_Production * Milk_Price  # Daily revenue in USD

# Energy functions
def net_energy(GE, FE, CH4, UE, HI):
    CH4_energy_loss = CH4 * 0.055  # Convert CH4 (g) to MJ using 55.5 MJ/kg CH4
    return GE - (FE + UE + CH4_energy_loss + HI)  # Net Energy after accounting for losses

def weight_gain_energy(NE, MEm, k_g):
    return k_g * max(0, (NE - MEm))  # Prevent negative values

def milk_production_energy(NE, NEl, NE_milk):
    return max(0, (NE - NEl)) / NE_milk  # Prevent negative values

# Compute energy values
NE = net_energy(GE, FE, CH4, UE, HI)
BW_gain_energy = weight_gain_energy(NE, MEm, k_g)
Milk_Yield_energy = milk_production_energy(NE, NEl, NE_milk)

# Prepare data for stacked bar chart
energy_labels = ["Gross Energy", "Fecal Loss", "Urinary Loss", "Heat Increment", "Methane Loss"]
CH4_energy_loss = CH4 * 0.055  # Ensure this is defined before use
energy_values = [GE, -FE, -UE, -HI, -CH4_energy_loss]

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
fig_energy.add_trace(go.Bar(
    x=["Net Energy"],
    y=[Milk_Revenue],  # Revenue bar
    marker_color=["gold"],
    name="Milk Revenue ($)"
))
fig_energy.update_layout(title="Energy Partitioning (MJ/day) & Milk Revenue", yaxis_title="MJ or USD", barmode="relative")

# Display bar chart
st.plotly_chart(fig_energy)

# Display results
st.write(f"### Methane Loss: {CH4:.2f} g/day")
st.write(f"### Milk Production: {Milk_Production:.2f} kg/day")
st.write(f"### Milk Revenue: ${Milk_Revenue:.2f} per day")
st.write(f"### Net Energy Available: {NE:.2f} MJ/day")
st.write(f"### Weight Gain (Energy): {BW_gain_energy:.2f} kg/day")
st.write(f"### Milk Yield (Energy): {Milk_Yield_energy:.2f} kg/day")
