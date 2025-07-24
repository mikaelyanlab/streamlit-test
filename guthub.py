import numpy as np
import pandas as pd
import plotly.graph_objects as go
import altair as alt
import streamlit as st

# Base gut compartments
BASE_COMPARTS = {
    "P1": {"length": 3, "radius": 0.15},
    "P3": {"length": 8, "radius": 0.45},
    "P4": {"length": 6, "radius": 0.30},
    "P5": {"length": 2, "radius": 0.15}
}

def radial_grad(radius, volume, enzyme_activity):
    r_rel = np.linspace(0, 1, 50)
    O2 = 100 * np.exp(-5 * (1 - r_rel)) / (1 + 0.3 * volume)
    H2 = 2 * enzyme_activity * (1 - np.exp(-5 * r_rel))
    return r_rel * radius, O2, H2

def adjust_compartments(recalcitrance, selection_pressure):
    comparts = BASE_COMPARTS.copy()
    comparts["P3"]["length"] *= (1 + 0.6 * recalcitrance * selection_pressure)
    comparts["P3"]["radius"] *= (1 + 0.4 * recalcitrance * selection_pressure)
    comparts["P5"]["length"] *= (1 - 0.3 * recalcitrance * selection_pressure)
    for comp in comparts:
        comparts[comp]["volume"] = np.pi * comparts[comp]["radius"]**2 * comparts[comp]["length"]
    return comparts

def axial_profiles(recalcitrance, selection_pressure, comparts):
    x = np.linspace(0, 1, 200)
    enzyme_activity = 1 + 0.5 * recalcitrance * selection_pressure
    pH = 7 + 3.5 * recalcitrance * np.exp(-4 * x) * selection_pressure
    O2 = 100 * np.exp(-5 * x) / (1 + 0.2 * comparts["P3"]["volume"])
    H2 = 2 * enzyme_activity * np.maximum(0, 1 - np.exp(-6 * (x - 0.2)))
    Eh = -100 - 59 * (pH - 7) + 0.3 * O2 - 40 * H2
    return x, pH, O2, H2, Eh, enzyme_activity

# Streamlit UI
st.sidebar.header("Evolutionary Parameters")
recalcitrance = st.sidebar.slider("Dietary Recalcitrance (0: Soil-like, 1: Wood-like)", 0.0, 1.0, 0.5)
selection_pressure = st.sidebar.slider("Selection Pressure", 0.0, 2.0, 1.0)
var_map = st.sidebar.selectbox("Color Variable", ["O2", "H2"])

comparts = adjust_compartments(recalcitrance, selection_pressure)
x, pH, O2_ax, H2_ax, Eh_ax, enzyme_activity = axial_profiles(recalcitrance, selection_pressure, comparts)
rad_data = {comp: radial_grad(d["radius"], d["volume"], enzyme_activity) for comp, d in comparts.items()}

# 3D Radial Endcap Heatmaps
fig = go.Figure()
x0 = 0
N_theta = 60
N_rad = 25
for comp, d in comparts.items():
    R = d["radius"]
    L = d["length"]
    r_array, O2_array, H2_array = rad_data[comp]
    values = {"O2": O2_array, "H2": H2_array}[var_map]

    for i in range(len(r_array)-1):
        r1, r2 = r_array[i], r_array[i+1]
        val = values[i]
        for j in range(N_theta):
            theta1 = 2 * np.pi * j / N_theta
            theta2 = 2 * np.pi * (j+1) / N_theta
            x_vals = [x0] * 4
            y_vals = [
                r1 * np.cos(theta1),
                r1 * np.cos(theta2),
                r2 * np.cos(theta2),
                r2 * np.cos(theta1)
            ]
            z_vals = [
                r1 * np.sin(theta1),
                r1 * np.sin(theta2),
                r2 * np.sin(theta2),
                r2 * np.sin(theta1)
            ]
            fig.add_trace(go.Mesh3d(
                x=x_vals,
                y=y_vals,
                z=z_vals,
                intensity=[val] * 4,
                colorscale='Viridis',
                opacity=0.9,
                showscale=False,
                hoverinfo='skip'
            ))
    x0 += L

fig.update_layout(
    scene=dict(
        xaxis_title="Axial Position (mm)",
        yaxis_title="Radial (Y)",
        zaxis_title="Radial (Z)",
        camera=dict(eye=dict(x=2.5, y=0.1, z=0.3)),
        aspectratio=dict(x=3, y=1, z=1)
    ),
    title=f"Gut Cross-Section Radial Heatmaps – {var_map}",
    margin=dict(l=0, r=0, t=40, b=0),
    height=600
)
st.header("Radial Cross-Sections of Gut Compartments")
st.plotly_chart(fig, use_container_width=True)

# 2D Radial Profile for P3
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
st.altair_chart(chart_o2 + chart_h2, use_container_width=True)

# 2D Axial Profiles
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
