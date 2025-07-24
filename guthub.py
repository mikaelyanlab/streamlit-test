# app.py  ────────────────────────────────────────────────────────────────────
import numpy as np, pandas as pd, altair as alt, streamlit as st

# ───── CONSTANTS ────────────────────────────────────────────────────────────
BASE_RETENTION = 14.0               # h (wood-feeder median P1-P5)
DG_ACETATE     = 8.7e5              # J mol-1  |ΔG| per mol acetate oxidised
DEFAULT_RMET   = 8.0                # J g-1 h-1 resting metabolic power

COMPART = {"P1 (mixed)": 0.00, "P3 (paunch)": .35,
           "P4 (colon)": .70, "P5 (rectum)": 1.00}

# ───── UTILS ────────────────────────────────────────────────────────────────
def o2_solubility_uM_per_kPa(T):
    """Linear interp of published solubility: 25 °C → 12.56; 37 °C → 10.56 µM kPa⁻¹"""
    return 12.56 - 0.1667*(T-25)         # good ±1 % over 15-40 °C

def axial_profiles(H, tau, T_ret, α, J_O2, P_H2):
    Tret = T_ret if T_ret>0 else tau*BASE_RETENTION
    x = np.linspace(0, 1, 200)
    pH = 7 + 5*H*α/(α+1)*np.exp(-4*x)
    O2 = np.maximum(0., 100*J_O2*np.exp(-10*x/(Tret/BASE_RETENTION)))   # µM
    H2 = np.maximum(0., P_H2*(1-np.exp(-6*(x-.2))))                     # kPa
    Eh = -100 - 59*(pH-7) + .3*O2 - 40*H2
    return pd.DataFrame({"x":x,"pH":pH,"O2_uM":O2,"H2_kPa":H2,"Eh":Eh})

def radial_profile(O2_wall_uM, H2_core_kPa, pH_core,
                   r_rel, k_r, sol_kPa_per_uM):
    O2_kPa = (O2_wall_uM*sol_kPa_per_uM)*np.exp(-k_r*(1-r_rel))
    H2_kPa = H2_core_kPa*(1-np.exp(-k_r*r_rel))
    pH     = pH_core - .5*(1-r_rel)
    return O2_kPa, H2_kPa, pH

def acetate_balance(P_H2, f_aceto, gut_mass_g, Mmg, Rdot, F_acet):
    A_prod = f_aceto*P_H2*gut_mass_g                         # µmol h-1
    E_need = Rdot*(Mmg/1000)                                 # J h-1
    A_need = F_acet*E_need/DG_ACETATE*1e6                    # µmol h-1
    return A_prod, A_need

# ───── STREAMLIT UI ─────────────────────────────────────────────────────────
st.title("Termite hind-gut simulator – axial + radial 2-D gradients")

with st.sidebar:
    st.header("Diet & host")
    H     = st.slider("Humification H", 0., 1., .3, .05)
    τ     = st.slider("Transit multiplier τ", .5, 4., 1.)
    Tret  = st.number_input("Absolute retention (h, 0=use τ)", 0., 48., 0.)
    α     = st.slider("Alkaline secretion α", 0.,10.,5.)
    tempC = st.slider("Gut temperature (°C)", 15, 40, 30)

    st.header("Gas / microbiome")
    J_O2    = st.slider("Relative O2 influx", 0.,1.,.3)
    P_H2    = st.slider("H2 production (µmol g⁻¹ h⁻¹)", 0.,6.,2.)
    f_aceto = st.slider("Acetogen share of H2", 0.,1.,.8)

    st.header("Energetics")
    Mmg   = st.slider("Body mass (mg)", 1, 50, 12)
    Rdot  = st.slider("Metabolic rate J g⁻¹ h⁻¹", .5,25., DEFAULT_RMET)
    Facet = st.slider("Fraction ATP from acetate", .7,1., .9)

    st.header("Geometry")
    radius_mm = st.slider("Gut radius (mm)", .1,1.5,.6)
    k_r       = st.slider("Radial decay coeff kᵣ", 3.0, 10.0, 6.0)

# ───── 1. AXIAL PROFILES ───────────────────────────────────────────────────
ax = axial_profiles(H, τ, Tret, α, J_O2, P_H2)

# Henry conversion
sol = o2_solubility_uM_per_kPa(tempC)       # µM kPa⁻¹
uM_to_kPa = 1/sol

# micro-oxic threshold 1 µM → kPa
O2_thr_kPa = 1*uM_to_kPa

# ───── 2. 2-D FIELD (x × r) ────────────────────────────────────────────────
x_grid = ax['x'].values
r_grid = np.linspace(0,1,80)                     # relative radius
data2d = {"x":[], "r":[], "O2_kPa":[], "pH":[]}

for xi,(O2_wall_uM, H2_core, pH_core) in ax[['O2_uM','H2_kPa','pH']].iterrows():
    for r_rel in r_grid:
        O2k,H2k, pH = radial_profile(
            O2_wall_uM, H2_core, pH_core,
            r_rel, k_r, uM_to_kPa
        )
        data2d["x"].append(x_grid[xi])
        data2d["r"].append(r_rel*radius_mm*1_000)   # µm
        data2d["O2_kPa"].append(O2k)
        data2d["pH"].append(pH)

field = pd.DataFrame(data2d)

# δ(x): shell where O2>1 µM
shell_df = field[field["O2_kPa"]>O2_thr_kPa].groupby("x")["r"].min().reset_index()
shell_df["r"] = shell_df["r"]

# ───── 3. ENERGY BALANCE ───────────────────────────────────────────────────
A_prod, A_need = acetate_balance(P_H2,f_aceto,.4*Mmg/1000,Mmg,Rdot,Facet)
energy_ok = A_prod>=A_need

# ───── 4. VISUALS ──────────────────────────────────────────────────────────
tab_ax, tab_rad, tab_2dO2, tab_2dpH = st.tabs(
    ["Axial profiles","Radial slice","2-D O2 heat-map","2-D pH heat-map"])

with tab_ax:
    ax_plot = ax.melt('x', value_vars=['pH','Eh','O2_uM','H2_kPa']
              ).rename(columns={'variable':'Var','value':'Val'})
    ch = alt.Chart(ax_plot).mark_line().encode(
        x=alt.X('x', title='Axial (relative)'),
        y='Val', color='Var')
    for name,pos in COMPART.items():
        ch += alt.Chart(pd.DataFrame({"x":[pos]})).mark_rule(
              strokeDash=[4,4], opacity=.4).encode(x='x')
    st.altair_chart(ch.properties(height=350), use_container_width=True)

with tab_rad:
    comp = st.selectbox("Slice at", list(COMPART.keys()), index=1)
    idx  = int(COMPART[comp]*(len(ax)-1))
    core = ax.iloc[idx]
    r_rel = np.linspace(0,1,150)
    O2k,H2k,pHr = radial_profile(core.O2_uM,core.H2_kPa,core.pH,
                                 r_rel,k_r,uM_to_kPa)
    rad_df = pd.DataFrame({"μm":r_rel*radius_mm*1000,
                           "O2_kPa":O2k,"H2_kPa":H2k})
    micro = rad_df[rad_df.O2_kPa>O2_thr_kPa]
    shell_rect = alt.Chart(pd.DataFrame({
        "x":[micro.μm.min()],"x2":[micro.μm.max()],
        "y":[0],"y2":[P_H2*1.1]
    })).mark_rect(opacity=.15,color='grey').encode(x='x',x2='x2',y='y',y2='y2')

    base = alt.Chart(rad_df).encode(
        x=alt.X('μm', title='Radial distance (µm)'),
        y=alt.Y('O2_kPa', title='Partial pressure (kPa)')
    )
    O2l = base.mark_line().encode(y='O2_kPa')
    H2l = base.mark_line(strokeDash=[6,4]).encode(y='H2_kPa')
    st.altair_chart( (shell_rect+O2l+H2l).properties(height=300),
                     use_container_width=True)

with tab_2dO2:
    st.subheader("O2 partial pressure (kPa)")
    ch2 = alt.Chart(field).mark_rect().encode(
        x=alt.X('x:Q', title='Axial (rel)'),
        y=alt.Y('r:Q', title='Radial µm'),
        color=alt.Color('O2_kPa:Q', scale=alt.Scale(scheme='blues'))
    )
    shell_line = alt.Chart(shell_df).mark_line(color='black').encode(
        x='x', y='r')
    st.altair_chart((ch2+shell_line).properties(height=350),
                     use_container_width=True)

with tab_2dpH:
    st.subheader("pH field")
    ch3 = alt.Chart(field).mark_rect().encode(
        x='x:Q', y='r:Q',
        color=alt.Color('pH:Q', scale=alt.Scale(scheme='plasma')))
    st.altair_chart(ch3.properties(height=350), use_container_width=True)

# ───── METRICS ──────────────────────────────────────────────────────────────
m1,m2,m3 = st.columns(3)
m1.metric("O2 shell δₘₐₓ", f"{shell_df.r.max():.0f} µm")
m2.metric("Acetate prod", f"{A_prod:.1f} µmol h⁻¹")
m3.metric("Needed", f"{A_need:.1f}", delta=None if energy_ok else "⚠ short")

if energy_ok: st.success("✔ acetate supply ≥ demand")
else:          st.error("✖ shortfall – raise α, τ or H")

with st.expander("Download axial + 2-D CSV"):
    full = pd.concat({"axial":ax, "field":field},
                     names=['grid']).reset_index(level=0)
    st.download_button("CSV", full.to_csv(index=False).encode(),
                       "gut_profiles.csv","text/csv")
# ────────────────────────────────────────────────────────────────────────────
