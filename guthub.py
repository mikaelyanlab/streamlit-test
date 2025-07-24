import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import altair as alt

# ——————————————————————————————————— CONSTANTS & ANATOMY
DG_ACETATE = 8.7e5
DEFAULT_RMET = 8.0
COMPARTMENTS = [
    ("P1", 0.1, 5),
    ("P3", 0.25, 20),
    ("P4", 0.2, 15),
    ("P5", 0.15, 10)
]
CYL_RES_THETA = 40
CYL_RES_Z = 40

# ——————————————————————————————————— MODEL FUNCTIONS

def axial_profiles(H, alpha, J_O2, P_H2):
    x = np.linspace(0,1,200)
    pH = 7 + 5 * H * alpha / (alpha + 1) * np.exp(-4 * x)
    O2 = 100 * J_O2 * np.exp(-5 * x)
    H2 = P_H2 * (1 - np.exp(-6 * (x - .2)))
    Eh = -100 - 59*(pH - 7) + 0.3 * O2 - 40 * H2
    return x, pH, O2, H2, Eh

def radial_gradients(R, k_r, O2_wall, H2_core):
    r_rel = np.linspace(0,1,50)
    O2 = O2_wall * np.exp(-k_r * (1 - r_rel))
    H2 = H2_core * (1 - np.exp(-k_r * r_rel))
    return r_rel * R, O2, H2

# ——————————————————————————————————— APP UI

st.sidebar.header("Inputs")
H = st.sidebar.slider("Humification H",0.,1.,0.5)
alpha = st.sidebar.slider("Alkaline secretion α",0.,10.,5.)
J_O2 = st.sidebar.slider("O₂ influx (arb)",0.,1.,0.3)
P_H2 = st.sidebar.slider("H₂ prod rate",0.,6.,2.)
k_r = st.sidebar.slider("Radial decay (kᵣ)",1.,15.,5.)
R_mult = st.sidebar.slider("Size scale",0.2,2.0,1.0)

# ——————————————————————————————— COMPUTE PROFILES

x, pH, O2_ax, H2_ax, Eh = axial_profiles(H,alpha,J_O2,P_H2)
O2_wall = J_O2 * 100
H2_core = P_H2

# ——————————————————————————————— 3D CYLINDERS + RADIAL

st.header("🌐 Gut shape + radial chemistry")

fig = go.Figure()
z_offset = 0
for name, rel_R, rel_len in COMPARTMENTS:
    R = rel_R * R_mult
    L = rel_len * R_mult * 5
    z_lin = np.linspace(z_offset, z_offset + L, CYL_RES_Z)
    theta = np.linspace(0,2*np.pi,CYL_RES_THETA)
    TH, ZZ = np.meshgrid(theta, z_lin)
    X = R * np.cos(TH)
    Y = R * np.sin(TH)
    idx_ax = np.round((ZZ - z_offset)/L*(len(x)-1)).astype(int)
    O2_ax_loc = O2_ax[idx_ax]
    rad_r, rad_O2, rad_H2 = radial_gradients(R, k_r, O2_wall, H2_core)
    col = np.interp(rad_r, rad_r, rad_O2)
    fig.add_trace(go.Surface(
        x=X, y=Y, z=ZZ,
        surfacecolor=O2_ax_loc,
        colorscale="Blues",
        cmin=0, cmax=max(O2_ax),
        showscale=(name=="P1"),
        name=name,
        hoverinfo="skip",
        opacity=0.7
    ))
    z_offset += L

fig.update_layout(scene=dict(xaxis=dict(visible=False),
                             yaxis=dict(visible=False),
                             zaxis=dict(title="Axial")),
                  margin=dict(l=0,r=0,b=0,t=50), height=600)
st.plotly_chart(fig, use_container_width=True)

# ——————————————————————————————— RADIAL CROSS-SECTION

st.subheader("2D radial slice (current axial midpoint)")

R_mid = COMPARTMENTS[1][1] * R_mult
rad_r, rad_O2, rad_H2 = radial_gradients(R_mid, k_r, O2_wall, H2_core)
df_rad = pd.DataFrame({"r_mm": rad_r, "O2": rad_O2, "H2": rad_H2})
base = alt.Chart(df_rad).mark_line().encode(
    x="r_mm", y="O2", color=alt.value("blue")
) + alt.Chart(df_rad).mark_line().encode(
    x="r_mm", y="H2", color=alt.value("red")
)
st.altair_chart(base.properties(width=400, height=300), use_container_width=True)

# ——————————————————————————————— AXIAL BLOCK PLOTS

st.subheader("Axial profiles")
df_ax = pd.DataFrame({"Position": x, "pH": pH, "O₂": O2_ax, "H₂": H2_ax, "Eh": Eh})
chart = alt.Chart(df_ax).transform_fold(
    ["pH", "pH", "O₂", "H₂", "Eh"],
    as_=["Param","Value"]
).mark_line().encode(x="Position", y="Value", color="Param")

st.altair_chart(chart.properties(width=600, height=200), use_container_width=True)
