# app.py ──────────────────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

# ─── CONSTANTS ───────────────────────────────────────────────────────────────
BASE_RETENTION = 14.0       # h   (median P1-P5 passage in a wood-feeder)
DG_ACETATE     = 8.7e5      # J mol-1 (|ΔG| per mol acetate oxidised -> ATP)
DEFAULT_RMET   = 8.0        # J g-1 h-1 (resting metabolic power)
μM_TO_kPa_O2   = 0.0001     # very rough conversion for plotting consistency

COMPARTMENTS = {
    "P1 (mixed segment)": 0.00,
    "P3 (paunch centre)": 0.35,
    "P4 (colon)":         0.70,
    "P5 (rectum)":        1.00
}

# ─── MODEL FUNCTIONS ─────────────────────────────────────────────────────────
def axial_profiles(H, tau, T_ret, alpha, J_O2, P_H2):
    """Return axial arrays (200 points) of pH, Eh, O2, H2."""
    Tret = T_ret if T_ret > 0 else tau * BASE_RETENTION
    x    = np.linspace(0, 1, 200)

    pH = 7 + 5 * H * alpha / (alpha + 1) * np.exp(-4 * x)
    O2 = np.maximum(0.0, 100 * J_O2 * np.exp(-10 * x / (Tret / BASE_RETENTION)))  # µM
    H2 = np.maximum(0.0, P_H2 * (1 - np.exp(-6 * (x - 0.2))))                     # kPa
    Eh = -100 - 59 * (pH - 7) + 0.3 * O2 - 40 * H2                                # mV

    df = pd.DataFrame({"x": x, "pH": pH, "Eh (mV)": Eh,
                       "O₂ (µM)": O2, "H₂ (kPa)": H2})
    return df

def radial_profiles(pH_core, O2_wall, H2_core, k_r=6):
    """
    Simple radial diffusion–consumption approximation:
        centre r=0 … gut wall r=1
    O2 decays exponentially toward the core; H2 the inverse.
    pH gently drops (0.5 pH units) toward the wall.
    """
    r = np.linspace(0, 1, 100)
    O2 = O2_wall * np.exp(-k_r * (1 - r))
    H2 = H2_core * (1 - np.exp(-k_r * r))
    pH = pH_core - 0.5 * (1 - r)               # centre alkaline, periphery lower

    df = pd.DataFrame({"r": r, "pH": pH, "O₂ (µM)": O2, "H₂ (kPa)": H2})
    return df

def acetate_balance(P_H2, f_aceto, gut_mass, M, Rdot, F_acet):
    A_prod = f_aceto * P_H2 * gut_mass                    # µmol h-1
    E_need = Rdot * (M / 1000)                            # J h-1
    A_need = (F_acet * E_need) / DG_ACETATE * 1e6         # µmol h-1
    return A_prod, A_need

# ─── STREAMLIT PANEL ─────────────────────────────────────────────────────────
st.title("Termite hind-gut sandbox — axial & radial gradients")

# ── Sidebar for input variables
with st.sidebar:
    st.header("Diet / host / microbiome")

    H       = st.slider("Humification index H", 0.0, 1.0, 0.3, 0.05)
    tau     = st.slider("Transit multiplier τ", 0.5, 4.0, 1.0, .1)
    T_ret   = st.number_input("Absolute retention Tret (h)\n(0 = use τ×14 h)",
                              0.0, 48.0, 0.0, 0.5)
    alpha   = st.slider("Alkaline secretion α (mmol eq L⁻¹ h⁻¹)", 0.0, 10.0, 5.0)
    J_O2    = st.slider("Relative O₂ influx Jₒ₂", 0.0, 1.0, 0.3)
    P_H2    = st.slider("H₂ production Pₕ₂ (µmol g⁻¹ h⁻¹)", 0.0, 6.0, 2.0, 0.1)
    f_aceto = st.slider("H₂ captured by acetogens", 0.0, 1.0, 0.8, 0.05)

    st.subheader("Energetics")
    M       = st.slider("Body mass M (mg)", 1, 50, 12)
    Rdot    = st.slider("Metabolic rate Ṙ (J g⁻¹ h⁻¹)", 0.5, 25.0, DEFAULT_RMET)
    F_acet  = st.slider("Fraction ATP from acetate", 0.7, 1.0, 0.9, 0.05)

# ── 1 AXIAL PROFILES ─────────────────────────────────────────────────────────
ax_df = axial_profiles(H, tau, T_ret, alpha, J_O2, P_H2)

# choose compartment centre for radial slice
compartment = st.selectbox(
    "Choose axial position for radial cut",
    list(COMPARTMENTS.keys()),
    index=1
)
slice_idx = int(COMPARTMENTS[compartment] * (len(ax_df) - 1))
row = ax_df.iloc[slice_idx]

rad_df = radial_profiles(pH_core=row["pH"],
                         O2_wall=row["O₂ (µM)"],
                         H2_core=row["H₂ (kPa)"])

# ── Energy balance
gut_mass = 0.4 * M / 1000          # g (0.4 × body mass assumption)
A_prod, A_need = acetate_balance(P_H2, f_aceto, gut_mass, M, Rdot, F_acet)
energy_ok = A_prod >= A_need

# ── TABS for axial versus radial visualisation
tab1, tab2 = st.tabs(["Axial gradients", "Radial gradients"])

with tab1:
    st.subheader("Axial profiles (centre line P1 → P5)")
    plot_df = ax_df.melt('x', var_name="Variable", value_name="Value")
    ax_chart = alt.Chart(plot_df).mark_line().encode(
        x=alt.X('x', title='Relative axial position'),
        y='Value',
        color='Variable'
    ).properties(height=400)
    # add compartment markers
    for name, xpos in COMPARTMENTS.items():
        ax_chart += alt.Chart(pd.DataFrame({"x": [xpos], "name": [name]})).mark_rule(
            strokeDash=[4,4], strokeOpacity=0.4
        ).encode(x='x')
    st.altair_chart(ax_chart, use_container_width=True)

with tab2:
    st.subheader(f"Radial slice at {compartment}")
    rad_plot = rad_df.melt('r', var_name="Variable", value_name="Value")
    rad_chart = alt.Chart(rad_plot).mark_line().encode(
        x=alt.X('r', title='Relative radius (0 = centre, 1 = wall)'),
        y='Value',
        color='Variable'
    ).properties(height=400)
    st.altair_chart(rad_chart, use_container_width=True)

# ── Metrics
c1, c2, c3 = st.columns(3)
c1.metric("Peak pH", f"{ax_df['pH'].max():.2f}")
c2.metric("Peak H₂", f"{ax_df['H₂ (kPa)'].max():.2f} kPa")
c3.metric("O₂ shell (µm)",
          f"{(rad_df[rad_df['O₂ (µM)']>1]['r'].max()*1000):.0f}"
          if (rad_df['O₂ (µM)'] > 1).any() else "<150")

c4, c5 = st.columns(2)
c4.metric("Acetate produced", f"{A_prod:.1f} µmol h⁻¹")
c5.metric("Acetate needed",   f"{A_need:.1f} µmol h⁻¹",
          delta=None if energy_ok else "⚠ shortfall")

if energy_ok:
    st.success("✔ Acetate supply ≥ demand")
else:
    st.error("✖ Shortfall – increase α, τ or H")

with st.expander("Download axial + radial CSV"):
    full = pd.concat({"axial": ax_df, "radial": rad_df},
                     names=["profile"]).reset_index(level=0)
    st.download_button("Download", full.to_csv(index=False).encode(),
                       "gut_simulation.csv", "text/csv")
# ─────────────────────────────────────────────────────────────────────────────
