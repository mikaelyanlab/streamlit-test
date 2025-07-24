import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import altair as alt

# Anatomical compartments (length mm, radius mm)
COMPARTS = {
    "P1": {"length": 3, "radius": 0.15},
    "P3": {"length": 8, "radius": 0.45},
    "P4": {"length": 6, "radius": 0.30},
    "P5": {"length": 2, "radius": 0.15}
}
THETA_RES, Z_RES = 40, 40

def axial_profiles(H, alpha, J_O2, P_H2):
    x = np.linspace(0, 1, 200)
    pH = 7 + 5 * H * alpha / (alpha + 1) * np.exp(-4 * x)
    O2 = 100 * J_O2 * np.exp(-5 * x)
    H2 = P_H2 * np.maximum(0, 1 - np.exp(-6 * (x - 0.2)))
    Eh = -100 - 59 * (pH - 7) + 0.3 * O2 - 40 * H2
    return x, pH, O2, H2, Eh

def radial_grad(R, k_r, O2_wall, H2_core):
    r_rel = np.linspace(0, 1, 50)
    O2 = O2_wall * np.exp(-k_r * (1 - r_rel))
    H2 = H2_core * (1 - np.exp(-k_r * r_rel))
    return r_rel * R, O2, H2

# Sidebar
st.sidebar.header("Inputs")
H = st.sidebar.slider("Humification H", 0.0, 1.0, 0.5)
alpha = st.sidebar.slider("Alkaline secretion α", 0.0, 10.0, 5.0)
J_O2 = st.sidebar.slider("O₂ influx", 0.0, 1.0, 0.3)
P_H2 = st.sidebar.slider("H₂ production", 0.0, 8.0, 2.0)
k_r = st.sidebar.slider("Radial decay kᵣ", 1.0, 15.0, 5.0)
var_map = st.sidebar.selectbox("Map color variable:", ["O2", "H2"])

# This ensures radial gradients are based on current production/influx
O2_wall = J_O2 * 100
H2_core = P_H2

# Calc profiles
x, pH, O2_ax, H2_ax, Eh_ax = axial_profiles(H, alpha, J_O2, P_H2)

# RADIAL GRADIENT for each compartment
rad_data = {}
for comp, d in COMPARTS.items():
    R = d["radius"]
    rv, Or, Hr = radial_grad(R, k_r, O2_wall, H2_core)
    rad_data[comp] = (rv, Or, Hr)

# Build 3D
fig = go.Figure()
z0 = 0
for comp, d in COMPARTS.items():
    L, R = d["length"], d["radius"]
    z1 = z0 + L

    theta = np.linspace(0, 2*np.pi, THETA_RES)
    z_lin = np.linspace(z0, z1, Z_RES)
    TH, ZZ = np.meshgrid(theta, z_lin)
    X, Y = R*np.cos(TH), R*np.sin(TH)

    rv, Or, Hr = rad_data[comp]
    surfvar = Or if var_map == "O2" else Hr
    surfvar2d = np.tile(surfvar, (Z_RES, 1))

    fig.add_trace(go.Surface(
        x=X, y=Y, z=ZZ,
        surfacecolor=surfvar2d,
        cmin=surfvar.min(), cmax=surfvar.max(),
        colorscale="Viridis",
        showscale=(comp == "P1"),
        name=comp, opacity=0.8, hoverinfo="none"
    ))
    z0 = z1

fig.update_layout(
    scene=dict(xaxis=dict(visible=False), yaxis=dict(visible=False),
               zaxis=dict(title="Axial (mm)")),
    margin=dict(l=0,r=0,t=30,b=0), height=550
)
st.header(f"3D Gut Cylinders — Radial {var_map} Gradient")
st.plotly_chart(fig, use_container_width=True)

# Radial slice for middle compartment (P3)
st.subheader("2D Radial slice (compartment P3)")
rv, Or, Hr = rad_data["P3"]
radial_df = pd.DataFrame({"r_mm": rv, "O2": Or, "H2": Hr})

o2_line = alt.Chart(radial_df).mark_line(color="blue").encode(x="r_mm", y="O2")
h2_line = alt.Chart(radial_df).mark_line(color="red").encode(x="r_mm", y="H2")
st.altair_chart(o2_line + h2_line, use_container_width=True)

# Full axial profiles
st.subheader("Axial profiles")
df_ax = pd.DataFrame({"Position": x, "pH": pH, "O₂": O2_ax, "H₂": H2_ax, "Eh": Eh_ax})
multi = alt.Chart(df_ax).transform_fold(
    ["pH", "O₂", "H₂", "Eh"], as_=["Param", "Value"]
).mark_line().encode(x="Position", y="Value", color="Param")
st.altair_chart(multi, use_container_width=True)
