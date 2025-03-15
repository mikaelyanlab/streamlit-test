import streamlit as st
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

# Streamlit UI
st.title("Methane Emission & Livestock Growth Network Model")
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

# Create network graph
G = nx.DiGraph()

# Nodes and their sizes (proportional to their magnitude)
nodes = {
    "Methane Emission": CH4,
    "Net Energy": NE,
    "Milk Production": Milk_Yield,
    "Body Biomass": BW_gain,
    "Fecal Loss": FE,
    "Urinary Loss": UE,
    "Heat Increment": HI
}

# Add nodes to graph
for node, size in nodes.items():
    G.add_node(node, size=size)

# Define edges (energy flow)
edges = [
    ("Methane Emission", "Net Energy"),
    ("Net Energy", "Milk Production"),
    ("Net Energy", "Body Biomass"),
    ("Net Energy", "Heat Increment"),
    ("Net Energy", "Fecal Loss"),
    ("Net Energy", "Urinary Loss")
]
G.add_edges_from(edges)

# Draw the graph
fig, ax = plt.subplots(figsize=(8, 6))
node_sizes = [nodes[node] * 10 for node in G.nodes]  # Scale sizes
pos = nx.spring_layout(G, seed=42)
nx.draw(G, pos, with_labels=True, node_size=node_sizes, node_color="lightblue", edge_color="gray", font_size=10)

# Display results
st.pyplot(fig)
st.write(f"### Methane Production: {CH4:.2f} g/day")
st.write(f"### Net Energy Available: {NE:.2f} MJ/day")
st.write(f"### Weight Gain: {BW_gain:.2f} kg/day")
st.write(f"### Milk Yield: {Milk_Yield:.2f} kg/day")
