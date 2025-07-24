import numpy as np, pandas as pd, streamlit as st
import altair as alt
import pyvista as pv
from pyvista import themes

# --- Physiology & model functions (as before) ---
BASE_RETENTION, DG_ACETATE, DEFAULT_RMET = 14.0, 8.7e5, 8.0
COMPART = {"P1":0.2, "P3":0.3, "P4":0.3, "P5":0.2}

def o2_sol(T): return 12.56 - 0.1667 * (T - 25)

def axial(H, T_ret, α, J_O2, P_H2):
    x=np.linspace(0,1,200)
    pH=7 + 5*H*α/(α+1)*np.exp(-4*x)
    O2=100*J_O2*np.exp(-10*x/(T_ret/BASE_RETENTION))
    H2=P_H2*(1-np.exp(-6*(x-0.2)))
    Eh=-100-59*(pH-7)+0.3*O2-40*H2
    return x,pH,O2,H2,Eh

def compute_Tret(Mmg, GutFrac, FeedRate, Dig, Mot):
    V=Mmg*GutFrac/1000
    Q=FeedRate*Dig*Mot
    return V/Q if Q>0 else np.nan

# --- Streamlit UI ---
st.sidebar.header("Inputs")
Mmg=st.sidebar.slider("Body mass (mg)",1,200,12)
GutFrac=st.sidebar.slider("Hindgut fraction",0.05,0.5,0.2)
FeedRate=st.sidebar.slider("Feeding rate (mg/h)",0.1,50.0,5.0)
Dig=st.sidebar.slider("Digestibility",0.2,1.0,0.6)
Mot=st.sidebar.slider("Motility",0.1,1.0,0.5)
H=st.sidebar.slider("H",0.0,1.0,0.5)
α=st.sidebar.slider("Alpha (alkaline)",0.0,10.0,5.0)
tempC=st.sidebar.slider("Temp (°C)",15,40,30)
J_O2=st.sidebar.slider("O₂ influx",0.0,1.0,0.3)
P_H2=st.sidebar.slider("H₂ prod (µmol/g/h)",0.0,8.0,2.0)
Rdot=st.sidebar.slider("Metabolic rate",0.5,50.0,DEFAULT_RMET)
Facet=st.sidebar.slider("ATP fraction",0.5,1.0,0.9)
radius_mm=st.sidebar.slider("Gut radius (mm)",0.1,1.5,0.5)

T_ret=compute_Tret(Mmg,GutFrac,FeedRate,Dig,Mot)
st.sidebar.metric("T_ret (h)",f"{T_ret:.2f}")

# --- compute profile ---
x,pH,O2,H2,Eh = axial(H,T_ret,α,J_O2,P_H2)
sol=o2_sol(tempC)
uM2kPa=1/sol

# --- 3D cylinders ---
plotter = pv.Plotter(off_screen=True, notebook=False)
zstart=0
n_caps=50
colormap="viridis"

for name, frac in COMPART.items():
    height=frac*100  # scaling factor
    cyl = pv.Cylinder(center=(0,0,zstart+height/2),
                      direction=(0,0,1),
                      radius=radius_mm,
                      height=height,
                      resolution=60)
    # Map axial color (pH) along z
    zcoords = cyl.points[:,2]
    idx = np.round((zcoords/height)*(len(pH)-1)).astype(int)
    vals = pH[idx]
    cyl["pH"] = vals
    plotter.add_mesh(cyl, scalars="pH", cmap=colormap, show_scalar_bar=True)
    zstart += height

# --- render 3D ---
st.header("🔬 3D Gut Compartment Model")
st.write("Colored by **axial pH gradient** on the surface of each cylinder.")
stpy = st.pyplot if False else None
st.write(plotter.show(jupyter=False, return_viewer=True))

# --- fallback 2D plots ---
st.header("2D Axial Profiles")
df = pd.DataFrame({"x":x,"pH":pH,"O₂":O2,"H₂":H2,"Eh":Eh})
plot = alt.Chart(df).transform_fold(["pH","O₂","H₂","Eh"], as_=["metric","value"])\
    .mark_line().encode(x="x",y="value",color="metric")
st.altair_chart(plot,use_container_width=True)

st.info("3D model above is the main focus. Rotate it to inspect and see how pH varies along gut depth.")
