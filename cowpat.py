import streamlit as st 
import numpy as np
import plotly.graph_objects as go

# Streamlit UI
st.title("Energy Partitioning in Livestock")
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
Milk_Price = 0.47  # USD per kg
Meat_Price = 5.00  # USD per kg live weight gain (market dependent)

# Compute revenue (now dynamically responding to methane)
Milk_Revenue = (NEl / NE_milk) * Milk_Price  # Milk revenue based on fixed 50 MJ/day NEl
Meat_Revenue = BW_gain_energy * Meat_Price  # Meat revenue responds to methane loss

# Prepare data for stacked bar chart (Energy)
energy_labels = ["Body Biomass", "Milk Production"]
energy_values = [BW_gain_energy, NEl]  # Green for body biomass, Yellow for Milk

# Energy partitioning stacked bar chart (Fixing Display Issue)
fig_energy = go.Figure()
fig_energy.add_trace(go.Bar(
    x=energy_labels,
    y=energy_values,
    marker_color=["green", "yellow"],
    name="Energy Allocation"
))
fig_energy.update_layout(title="Energy Partitioning (MJ/day)", yaxis_title="MJ/day", barmode="stack")

# Revenue comparison bar charts
fig_milk_revenue = go.Figure()
fig_milk_revenue.add_trace(go.Bar(
    x=["Milk Revenue"],
    y=[Milk_Revenue],
    marker_color=["yellow"],
    name="Milk Revenue ($)"
))
fig_milk_revenue.update_layout(title="Milk Revenue ($/day)", yaxis_title="USD/day")

fig_meat_revenue = go.Figure()
fig_meat_revenue.add_trace(go.Bar(
    x=["Meat Revenue"],
    y=[Meat_Revenue],
    marker_color=["green"],
    name="Meat Revenue ($)"
))
fig_meat_revenue.update_layout(title="Meat Revenue ($/day)", yaxis_title="USD/day")

# Display energy chart and revenue charts in separate panels
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_energy)

with col2:
    st.plotly_chart(fig_milk_revenue)
    st.plotly_chart(fig_meat_revenue)

# Display results
st.write(f"### Methane Loss: {CH4:.2f} g/day")
st.write(f"### Net Energy Available: {NE:.2f} MJ/day")
st.write(f"### Weight Gain (Energy): {BW_gain_energy:.2f} kg/day")
st.write(f"### Milk Revenue: ${Milk_Revenue:.2f} per day")
st.write(f"### Meat Revenue: ${Meat_Revenue:.2f} per day")
