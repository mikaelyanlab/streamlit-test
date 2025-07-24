import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import altair as alt

# Define base gut compartments
BASE_COMPARTS = {
    "P1": {"length": 3, "radius": 0.15, "volume": None},
    "P3": {"length": 8, "radius": 0.45},  # Paunch
    "P4": {"length": 6, "radius": 0.30},
    "P5": {"length": 2, "radius": 0.15}
}
THETA_RES, Z_RES = 50, 50

# Calculate base volumes
for comp in BASE_COMPARTS:
    BASE_COMPARTS[comp]["volume"] = np.pi * BASE_COMPARTS[comp]["radius"]**2 * BASE_COMPARTS[comp]["length"]

# Function to adjust gut morphology based on diet
def adjust_compartments(recalcitrance, selection_pressure):
    comparts = BASE_COMPARTS.copy()
    # Correlated progression: higher recalcitrance -> larger P3, higher enzyme activity
    comparts["P3"]["length"] *= (1 + 0.6 * recalcitrance * selection_pressure)
    comparts["P3"]["radius"] *= (1 + 0.4 * recalcitrance * selection_pressure)
    # P5 shrinks with less recalcitrant diets (less need for nitrogen recycling)
    comparts["P5"]["length"] *= (1 - 0.3 * recalcitrance * selection_pressure)
    # Update volumes
    for comp in comparts:
        comparts[comp]["volume"] = np.pi * comparts[comp]["radius"]**2 * comparts[comp]["length"]
    return comparts

# Function to compute axial profiles
def axial_profiles(recalcitrance, selection_pressure, comparts):
    x = np.linspace(0, 1, 200)
    enzyme_activity = 1 + 0.5 * recalcitrance * selection_pressure  # Enzyme activity scales with diet
    pH = 7 + 3.5 * recalcitrance * np.exp(-4 * x) * selection_pressure  # pH rises with recalcitrance
    O2 = 100 * np.exp(-5 * x) / (1 + 0.2 * comparts["P3"]["volume"])  # O₂ reduced by gut volume
    H2 = 2 * enzyme_activity * np.maximum(0, 1 - np.exp(-6 * (x - 0.2)))  # H₂ tied to enzyme activity
    Eh = -100 - 59 * (pH - 7) + 0.3 * O2 - 40 * H2  # Redox potential
    return x, pH, O2, H2, Eh, enzyme_activity

# Function to compute radial gradients (emphasizing microoxic periphery)
def radial_grad(radius, volume, enzyme_activity):
    r_rel = np.linspace(0, 1, 50)
    O2 = 100 * np.exp(-5 * (1 - r_rel)) / (1 + 0.3 * volume)  # O₂ high at periphery
    H2 = 2 * enzyme_activity * (1 - np.exp(-5 * r_rel))  # H₂ high at center
    return r_rel * radius, O2, H2

# Sidebar inputs
st.sidebar.header("Evolutionary Parameters")
recalcitrance = st.sidebar.slider(
    "Dietary Recalcitrance (0: Soil-like, 1: Wood-like)",
    0.0, 1.0, 0.5,
    help="Approximate ranges: Soil (~0.2), Humus (~0.3), Grass (~0.5), Wood (~0.8)"
)
selection_pressure = st.sidebar.slider("Selection Pressure", 0.0, 2.0, 1.0)
var_map = st.sidebar.selectbox("3D Color Variable", ["O2", "H2", "pH", "Eh"])

# Compute morphology and profiles
comparts = adjust_compartments(recalcitrance, selection_pressure)
x, pH, O2_ax, H2_ax, Eh_ax, enzyme_activity = axial_profiles(recalcitrance, selection_pressure, comparts)
rad_data = {comp: radial_grad(d["radius"], d["volume"], enzyme_activity) for comp, d in comparts.items()}

# 3D Gut Visualization (corrected annotations)
fig = go.Figure()
z0 = 0
for comp, d in comparts.items():
    L, R = d["length"], d["radius"]
    z1 = z0 + L
    theta = np.linspace(0, 2 * np.pi, THETA_RES)
    z_lin = np.linspace(z0, z1, Z_RES)
    TH, ZZ = np.meshgrid(theta, z_lin)
    X, Y = R * np.cos(TH), R * np.sin(TH)
    # Color by selected variable
    surf = {"pH": pH, "O2": O2_ax, "H2": H2_ax, "Eh": Eh_ax}[var_map]
    surf2d = np.tile(surf[:Z_RES], (THETA_RES, 1)).T
    fig.add_trace(go.Surface(
        x=X, y=Y, z=ZZ,
        surfacecolor=surf2d,
        cmin=surf.min(), cmax=surf.max(),
        colorscale="Viridis",
        showscale=(comp == "P1"),
        name=comp,
        opacity=0.85,
        hovertemplate=f"{comp}<br>{var_map}: %{{surfacecolor:.2f}}<extra></extra>"
    ))
    z0 = z1
fig.update_layout(
    scene=dict(
        xaxis_visible=False,
        yaxis_visible=False,
        zaxis_title="Axial Position (mm)",
        aspectratio=dict(x=1, y=1, z=3),
        annotations=[
            dict(
                text=f"Diet Recalcitrance: {recalcitrance:.2f}",
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.95,
                showarrow=False,
                font=dict(size=12, color="black")
            )
        ]
    ),
    margin=dict(l=0, r=0, t=50, b=0),
    height=600
)
st.header(f"3D Gut Model – {var_map}")
st.plotly_chart(fig, use_container_width=True)

# 2D Radial Profile for P3 (Brune-style with microoxic periphery)
st.subheader("Radial Profile in P3 (Paunch)")
rv, O2_rad, H2_rad = rad_data["P3"]
radial_df = pd.DataFrame({"Radius (mm)": rv, "O₂ (µM)": O2_rad, "H₂ (µM)": H2_rad})
chart_o2 = alt.Chart(radial_df).mark_line(color="blue").encode(
    x=alt.X("Radius (mm)", title="Radius (mm)"),
    y=alt.Y("O₂ (µM)", title="Concentration (µM)")
).properties(title="O₂ and H₂ Radial Profiles")
chart_h2 = alt.Chart(radial_df).mark_line(color="red").encode(
    x="Radius (mm)", y="H₂ (µM)"
)
# Add microoxic periphery shading
microoxic = alt.Chart(pd.DataFrame({"x": [0, comparts["P3"]["radius"]]})).mark_rect(opacity=0.2, color="blue").encode(
    x="x", x2=alt.value(comparts["P3"]["radius"]), y=alt.value(0), y2=alt.value(O2_rad.max())
)
st.altair_chart(microoxic + chart_o2 + chart_h2, use_container_width=True)

# 2D Axial Profiles (Brune-style)
st.subheader("Axial Profiles")
def plot_line(y, col, title, ylab):
    df = pd.DataFrame({"Position": x, title: y})
    return alt.Chart(df).mark_line(color=col).encode(
        x=alt.X("Position", title="Normalized Axial Position"),
        y=alt.Y(title, title=ylab)
    ).properties(title=title)

charts = [
    plot_line(pH, "green", "pH", "pH"),
    plot_line(O2_ax, "blue", "O₂", "O₂ (µM)"),
    plot_line(H2_ax, "red", "H₂", "H₂ (µM)"),
    plot_line(Eh_ax, "gray", "Eh", "Eh (mV)")
]
for ch in charts:
    st.altair_chart(ch, use_container_width=True)
