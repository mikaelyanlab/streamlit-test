import numpy as np
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import altair as alt

# ————————————————— Anatomical parameters (mm, mm)
COMPARTS = {
    "P1": {"length": 3, "radius": 0.15},
    "P3": {"length": 8, "radius": 0.45},  # paunch big
    "P4": {"length": 6, "radius": 0.30},
    "P5": {"length": 2, "radius": 0.15}
}

def axial_profiles(H, alpha, J_O2, P_H2):
    x = np.linspace(0,1,200)
    pH = 7 + 5 * H * alpha / (alpha + 1) * np.exp(-4 * x)
    O2 = 100 * J_O2 * np.exp(-5 * x)
    H2 = P_H2 * (1 - np.exp(-6*(x-0.2)))
    Eh = -100 - 59*(pH-7) + 0.3*O2 - 40*H2
    return x, pH, O2, H2, Eh

def radial_grad(R, k_r, O2w, H2c):
    r_rel = np.linspace(0,1,50)
    O2 = O2w * np.exp(-k_r*(1-r_rel))
    H2 = H2c * (1 - np.exp(-k_r*r_rel))
    return r_rel*R, O2, H2

st.sidebar.header("Inputs")
H = st.sidebar.slider("Humification H",0.,1.,0.5)
alpha = st.sidebar.slider("Alkaline secretion α",0.,10.,5.)
J_O2 = st.sidebar.slider("O₂ influx",0.,1.,0.3)
P_H2 = st.sidebar.slider("H₂ production",0.,8.,2.)
k_r = st.sidebar.slider("Radial decay",1.,15.,5.)
var_map = st.sidebar.selectbox("Map color:", ["O2","H2","Eh"])
st.sidebar.markdown("*Adjust top sliders accordingly*")

x,pH,O2_ax,H2_ax,Eh = axial_profiles(H,alpha,J_O2,P_H2)
#O2w,J_O2,P_H2  # unused placeholder

# Build 3D gut
fig = go.Figure()
z0 = 0
for name, data in COMPARTS.items():
    L = data["length"]
    R = data["radius"]
    z1 = z0 + L
    Z_lin = np.linspace(z0, z1, 50)
    TH, ZZ = np.meshgrid(np.linspace(0,2*np.pi,40), Z_lin)
    X = R*np.cos(TH); Y = R*np.sin(TH)
    idx_ax = ((ZZ - z0)/L*(len(x)-1)).astype(int)
    O2_loc = O2_ax[idx_ax]; H2_loc = H2_ax[idx_ax]; Eh_loc = Eh[idx_ax]
    surfvar = {"O2":O2_loc, "H2":H2_loc, "Eh":Eh_loc}[var_map]
    fig.add_trace(go.Surface(
        x=X,y=Y,z=ZZ,
        surfacecolor=surfvar,
        cmin=min(surfvar),cmax=max(surfvar),
        colorscale="Jet", showscale=(name=="P1"),
        name=name, opacity=0.8, hoverinfo="skip"
    ))
    z0 = z1

fig.update_layout(
    scene=dict(xaxis=dict(visible=False),yaxis=dict(visible=False),zaxis=dict(title="Axial")),
    margin=dict(l=0,r=0,t=40,b=0),height=550
)
st.header("3D Gut -> Color by " + var_map)
st.plotly_chart(fig, use_container_width=True)

# Radial cross-section quality check
st.subheader("Radial slice (compartment P3)")
Rmid = COMPARTS["P3"]["radius"]
rmm,O2r,H2r = radial_grad(Rmid,k_r,J_O2*100,P_H2)
df = pd.DataFrame({"r_mm":rmm,"O2":O2r,"H2":H2r})
p = alt.Chart(df).mark_line().encode(x="r_mm",y="O2",color=alt.value("blue"))\
    + alt.Chart(df).mark_line().encode(x="r_mm",y="H2",color=alt.value("red"))
st.altair_chart(p, use_container_width=True)

# Combined axial plots
st.subheader("Axial Profiles")
df2 = pd.DataFrame({
    "Pos": x, "pH":pH, "O₂":O2_ax, "H₂":H2_ax, "Eh":Eh
})
chart = alt.Chart(df2).transform_fold(
    ["pH","O₂","H₂","Eh"], as_=["Param","Value"]
).mark_line().encode(x="Pos", y="Value", color="Param")
st.altair_chart(chart, use_container_width=True)
