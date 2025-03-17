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
MEm = 41  # Maintenance Energy (Derived from NRC 2001 for a 600 kg cow)
k_g = 0.4  # Efficiency of Growth
NEl = 50  # Energy for Lactation
NE_milk = 3  # Energy per kg of Milk

# Constants for carbon partitioning (g/day)
C_Intake = 6000  # Carbon Intake
C_Fecal = 0.30 * C_Intake  # Fecal Carbon Loss (~30% of Intake)
C_Urinary = 0.05 * C_Intake  # Urinary Carbon Loss (~5% of Intake)
C_CO2 = 0.45 * C_Intake  # Respired CO2 (~45% of Intake)
C_Maintenance = 300  # Carbon for Maintenance
C_Lactation = 200  # Carbon for Milk
C_milk = 5  # Carbon per kg of Milk

# Methane Carbon Loss (dynamically adjusted based on CH4 loss and 9% GE energy loss)
C_CH4 = CH4 * (12/16)  # Convert CH4 (g) to carbon equivalent (g), based on molecular composition

# Energy functions
def net_energy(GE, FE, CH4, UE, HI):
    CH4_energy_loss = CH4 * 0.055  # Convert CH4 (g) to MJ using 55.5 MJ/kg CH4
    return GE - (FE + UE + CH4_energy_loss + HI)

def weight_gain_energy(NE, MEm, k_g):
    return k_g * max(0, (NE - MEm))  # Prevent negative weight gain

def milk_production_energy(NE, NEl, NE_milk):
    return max(0, (NE - NEl) / NE_milk)  # Prevent negative milk yield

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

# Pricing assumptions for milk and meat
Milk_Price = 0.47  # $ per liter of milk
Meat_Price = 5.00  # $ per kg of live weight gain

# Revenue calculations
Milk_Revenue_per_cow = (Milk_Yield_energy * Milk_Price)
Meat_Revenue_per_cow = (BW_gain_energy * Meat_Price)

# Scale revenue for 1 cow, 100 cows, and 1000 cows
Milk_Revenue_100 = Milk_Revenue_per_cow * 100
Milk_Revenue_1000 = Milk_Revenue_per_cow * 1000

# Prepare data for stacked energy bar chart
energy_labels = ["Gross Energy", "Fecal Loss", "Urinary Loss", "Heat Increment", "Methane Loss"]
CH4_energy_loss = CH4 * 0.055
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

# Revenue bar chart (Milk vs. Meat Revenue per cow)
fig_revenue = go.Figure()
fig_revenue.add_trace(go.Bar(
    x=["Milk Revenue", "Meat Revenue"],
    y=[Milk_Revenue_per_cow, Meat_Revenue_per_cow],
    marker_color=["yellow", "green"],
    name="Revenue ($/day)"
))
fig_revenue.update_layout(title="Daily Revenue from Milk and Meat (Per Cow)", yaxis_title="USD/day")

# Milk revenue loss/gain for 1 cow, 100 cows, 1000 cows
fig_milk_revenue = go.Figure()
fig_milk_revenue.add_trace(go.Bar(
    x=["1 Cow", "100 Cows", "1000 Cows"],
    y=[Milk_Revenue_per_cow, Milk_Revenue_100, Milk_Revenue_1000],
    marker_color=["yellow", "orange", "red"],
    name="Milk Revenue Loss/Gain"
))
fig_milk_revenue.update_layout(title="Milk Revenue Comparison", yaxis_title="USD/day")

# Display three graphs side by side
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(fig_energy)
with col2:
    st.plotly_chart(fig_carbon)

# Second row for revenue graphs
col3, col4 = st.columns(2)
with col3:
    st.plotly_chart(fig_revenue)
with col4:
    st.plotly_chart(fig_milk_revenue)

# Display total revenue calculations
st.write(f"### Methane Loss: {CH4:.2f} g/day")
st.write(f"### Milk Revenue per Cow: **${Milk_Revenue_per_cow:.2f} per day**")
st.write(f"### Meat Revenue per Cow: **${Meat_Revenue_per_cow:.2f} per day**")
st.write(f"### Milk Revenue for 100 Cows: **${Milk_Revenue_100:.2f} per day**")
st.write(f"### Milk Revenue for 1000 Cows: **${Milk_Revenue_1000:.2f} per day**")
