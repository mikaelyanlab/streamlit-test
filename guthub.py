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
CYL_THETA_RES = 40
CYL_Z_RES = 40

# Model functions
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

# Sidebar inputs
st.sidebar.header("Inputs")
H = st.sidebar.slider("Humification H", 0.0, 1.0, 0.5)
alpha = st.sidebar.slider("Alkaline secretion α", 0.0, 10.0, 5.0)
J_O2 = st.sidebar.slider("O₂ influx", 0.0, 1.0, 0.3)
P_H2 = st.sidebar.slider("H₂ production", 0.0, 8.0, 2.0)
k_r = st.sidebar.slider("Radial decay kᵣ", 1.0, 15.0, 5.0)
var_map = st.sidebar.selectbox("Color map variable", ["O2", "H2", "Eh"])

# Compute profiles
x, pH, O2_ax, H2_ax, Eh_ax = axial_profiles(H, alpha, J_O2, P_H2)

# Build 3D model
fig = go.Figure()
z0 = 0
for comp, data in COMPARTS.items():
    L = data["length"]
    R = data["radius"]
    z1 = z0 + L
    z_lin = np.linspace(z0, z1, CYL_Z_RES)
    theta = np.linspace(0, 2 * np.pi, CYL_THETA_RES)
    TH, ZZ = np.meshgrid(theta, z_lin)
    X = R * np.cos(TH)
    Y = R * np.sin(TH)

    idx_ax = ((ZZ - z0) / L * (len(x) - 1)).astype(int)
    O2_loc = O2_ax[idx_ax]
    H2_loc = H2_ax[idx_ax]
    Eh_loc = Eh_ax[idx_ax]

    surfvar = {"O2": O2_loc, "H2": H2_loc, "Eh": Eh_loc}[var_map]
    cmin = float(np.nanmin(surfvar))
    cmax = float(np.nanmax(surfvar))

    fig.add_trace(go.Surface(
        x=X, y=Y, z=ZZ,
        surfacecolor=surfvar,
        cmin=cmin, cmax=cmax,
        colorscale="Jet",
        showscale=(comp == "P1"),
        name=comp,
        opacity=0.8,
        hoverinfo="skip"
    ))
    z0 = z1

fig.update_layout(
    scene=dict(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        zaxis=dict(title="Axial length (mm)")
    ),
    margin=dict(l=0, r=0, t=40, b=0),
    height=550
)
st.header(f"3D Gut (color = {var_map})")
st.plotly_chart(fig, use_container_width=True)

# Radial slice (P3)
st.subheader("2D Radial slice (P3): O₂ vs H₂")
Rmid = COMPARTS["P3"]["radius"]
rmm, O2r, H2r = radial_grad(Rmid, k_r, J_O2 * 100, P_H2)
df_rad = pd.DataFrame({"r_mm": rmm, "O2": O2r, "H2": H2r})
rad_chart = alt.Chart(df_rad).transform_fold(
    ["O2", "H2"], as_=["Param", "Value"]
).mark_line().encode(x="r_mm", y="Value", color="Param")
st.altair_chart(rad_chart, use_container_width=True)

# Axial profiles
st.subheader("Axial Stack: pH, O₂, H₂, Eh")
df_ax = pd.DataFrame({
    "Position": x,
    "pH": pH,
    "O₂": O2_ax,
    "H₂": H2_ax,
    "Eh": Eh_ax
})
multi = alt.Chart(df_ax).transform_fold(
    ["pH", "O₂", "H₂", "Eh"], as_=["Param", "Value"]
).mark_line().encode(x="Position", y="Value", color="Param")
st.altair_chart(multi, use_container_width=True)
