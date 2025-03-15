import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go

# Streamlit UI
st.title("Carbon Partitioning in Livestock")
st.sidebar.header("Adjust Methane Carbon Loss")

# Single slider for Methane Carbon Loss
CH4_C = st.sidebar.slider("Methane Carbon Loss (g/day)", 10, 500, 50)

# Constants for carbon partitioning (g/day)
C_Intake = 2500  # Fixed Carbon Intake (g/day)
C_Fecal = 600  # Fixed Fecal Carbon Loss (g/day)
C_Urinary = 50  # Fixed Urinary Carbon Loss (g/day)
C_CO2 = 1200  # Fixed Respired Carbon as CO2 (g/day)
C_Maintenance = 300  # Carbon used for Maintenance (g/day)
k_g = 0.4  # Efficiency of Carbon into Growth
C_Lactation = 200  # Carbon allocated to Milk (g/day)
C_milk = 5  # Carbon per kg of Milk (g/kg)

# Function for Net Carbon calculation
def net_carbon(C_Intake, C_Fecal, CH4_C, C_Urinary, C_CO2):
    return C_Intake - (C_Fecal + CH4_C + C_Urinary + C_CO2)

# Function for weight gain
def weight_gain(C_Net, C_Maintenance, k_g):
    C_Gain = max(C_Net - C_Maintenance, 0)
    return k_g * C_Gain

# Function for milk production
def milk_production(C_Net, C_Lactation, C_milk):
    return max((C_Net - C_Lactation) / C_milk, 0)

# Recalculate based on user input
C_Net = net_carbon(C_Intake, C_Fecal, CH4_C, C_Urinary, C_CO2)
BW_gain = weight_gain(C_Net, C_Maintenance, k_g)
Milk_Yield = milk_production(C_Net, C_Lactation, C_milk)

# Update values dynamically
values = [C_Intake, C_Fecal, C_Urinary, C_CO2, CH4_C, C_Net, BW_gain, Milk_Yield]

# Define nodes and links for Sankey diagram
labels = [
    "Carbon Intake", "Fecal Loss", "Urinary Loss", "Respired CO2", "Methane Loss", "Net Carbon",
    "Body Biomass", "Milk Production"
]
source = [0, 0, 0, 0, 0, 5, 5]  # From Carbon Intake & Net Carbon
target = [1, 2, 3, 4, 5, 6, 7]  # To losses & productivity

# Create Sankey diagram
fig = go.Figure(go.Sankey(
    node=dict(
        pad=20,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=labels,
    ),
    link=dict(
        source=source,
        target=target,
        value=values,
    )
))

fig.update_layout(title_text="Carbon Partitioning in Livestock", font_size=10)

# Display results
st.plotly_chart(fig)
st.write(f"### Methane Carbon Loss: {CH4_C:.2f} g/day")
st.write(f"### Net Carbon Available: {C_Net:.2f} g/day")
st.write(f"### Weight Gain: {BW_gain:.2f} g/day")
st.write(f"### Milk Yield: {Milk_Yield:.2f} kg/day")
