import streamlit as st 
import numpy as np
import plotly.graph_objects as go

# Streamlit UI
st.title("Energy Partitioning in Livestock")
st.sidebar.header("Adjust Methane Loss and Milk Demand")

# Sliders for Methane Loss and Milk Demand
CH4 = st.sidebar.slider("Methane Loss (g/day)", 0, 500, 250)
Milk_Demand = st.sidebar.slider("Milk Demand (kg/day)", 0, 50, 45)  # Now represents desired milk output

# Constants for energy partitioning (MJ/day)
GE = 250  # Gross Energy Intake (Based on high-producing dairy cow estimates, NRC 2001)
GE_adjusted = GE - (CH4 * 0.055)  # Adjust GE after methane loss (assuming 55.5 MJ/kg CH4)
FE = 0.35 * GE_adjusted  # Fecal Energy Loss (~35% of adjusted GE)
UE = 0.07 * GE_adjusted  # Urinary Energy Loss (~7% of adjusted GE)
HI = 0.25 * GE_adjusted  # Heat Increment (~25% of adjusted GE)
MEm = 41  # Maintenance Energy (fixed at 41 MJ/day)
k_g = 0.4  # Efficiency of Growth
NE_milk = 3  # Energy per kg of Milk

# Energy functions
def net_energy(GE, FE, CH4, UE, HI):
    CH4_energy_loss = CH4 * 0.055  # Convert CH4 (g) to MJ using 55.5 MJ/kg CH4
    return GE - (FE + UE + CH4_energy_loss + HI)  # Net Energy after accounting for losses

# Compute energy available after losses
NE = net_energy(GE, FE, CH4, UE, HI)

# Allocate energy to maintenance first
NE_remaining = max(0, NE - MEm)  # Maintenance energy is deducted first

# Allocate energy to milk production based on available energy
Milk_Production = min(Milk_Demand, NE_remaining / NE_milk)  # Energy must support demand
NEl = Milk_Production * NE_milk  # Energy used for lactation

# Allocate remaining energy to biomass (growth)
NE_remaining_after_milk = max(0, NE_remaining - NEl)
BW_gain_energy = k_g * NE_remaining_after_milk  # Biomass energy after milk demand

# Pricing assumptions for milk and meat (USD)
Milk_Price = 0.47  # USD per kg
Meat_Price = 5.00  # USD per kg live weight gain (market dependent)

# Compute revenue (now dynamically responding to methane & milk demand)
Milk_Revenue = Milk_Production * Milk_Price
Meat_Revenue = BW_gain_energy * Meat_Price

# Prepare data for stacked bar chart (Energy)
energy_labels = ["Gross Energy", "Fecal Loss", "Urinary Loss", "Heat Increment", "Methane Loss"]
CH4_energy_loss = CH4 * 0.055  # Ensure this is defined before use
energy_values = [GE, -FE, -UE, -HI, -CH4_energy_loss]

# Energy partitioning bar chart
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
    y=[Milk_Production * NE_milk],  # Energy allocated to milk
    marker_color=["yellow"],
    name="Milk Production"
))
fig_energy.update_layout(title="Energy Partitioning (MJ/day)", yaxis_title="MJ/day", barmode="relative")

# Revenue comparison bar chart
fig_revenue = go.Figure()
fig_revenue.add_trace(go.Bar(
    x=["Milk Revenue", "Meat Revenue"],
    y=[Milk_Revenue, Meat_Revenue],
    marker_color=["yellow", "green"],
    name="Revenue ($)"
))
fig_revenue.update_layout(title="Revenue from Milk vs. Meat ($/day)", yaxis_title="USD/day")

# Display charts side by side
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_energy)
with col2:
    st.plotly_chart(fig_revenue)

# Display results
st.write(f"### Methane Loss: {CH4:.2f} g/day")
st.write(f"### Milk Production (Adjusted to Energy Available): {Milk_Production:.2f} kg/day")
st.write(f"### Net Energy Available: {NE:.2f} MJ/day")
st.write(f"### Weight Gain (Energy): {BW_gain_energy:.2f} kg/day")
st.write(f"### Milk Revenue: ${Milk_Revenue:.2f} per day")
st.write(f"### Meat Revenue: ${Meat_Revenue:.2f} per day")
