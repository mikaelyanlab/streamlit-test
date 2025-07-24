# Guthub model v1.0 | 07.24.2025 | Mikaelyan
# app.py ─────────────────────────────────────────────────────────
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st

# ─── CONSTANTS ─────────────────────────────────────────────────
BASE_RETENTION  = 14.0          # h, median hind-gut passage time in wood-feeders
DG_ACETATE      = 8.7e5         # J mol-1, |ΔG| of acetate oxidation (≈ –20 kJ / mol ATP)
DEFAULT_RMET    = 8.0           # J g-1 h-1, typical worker metabolic rate
BODY_DENSITY    = 1.1           # g mL-1 -> g ≈ mL for small insects

# ─── MODEL CORE ────────────────────────────────────────────────
def gut_model(
        H, CN, L, beta,
        tau, T_ret,
        alpha, J_O2, radius,
        P_H2, f_aceto,
        M, Rdot, F_acetate
    ):
    """
    Return a DataFrame of axial profiles + derived variables.
    If T_ret == 0 we use tau * BASE_RETENTION instead.
    """
    # choose retention time
    Tret = T_ret if T_ret > 0 else tau * BASE_RETENTION  # h

    # axial grid (0 = mid-gut/hind-gut junction, 1 = rectum)
    x = np.linspace(0, 1, 200)

    # phenomenological profiles (tuned exponents)
    pH = 7 + 5 * H * alpha / (alpha + 1) * np.exp(-4 * x)

    O2 = np.maximum(0.0,                # clamp at 0
                    100 * J_O2 * np.exp(-10 * x / (Tret / BASE_RETENTION)))  # µM

    H2 = np.maximum(0.0,
                    P_H2 * (1 - np.exp(-6 * (x - 0.2))))  # kPa

    Eh = -100 - 59 * (pH - 7) + 0.3 * O2 - 40 * H2        # mV

    # hind-gut volume index (very coarse)
    V = 0.15 + 0.35 * H + 0.08 * (Tret / BASE_RETENTION) + 0.05 * alpha

    # acetate production (µmol h-1) — integrate H2 flux scaled by f_aceto
    # Simplification: assume paunch mass ~ 0.4 · body mass
    gut_mass = 0.4 * M / 1000    # convert mg -> g
    A_prod = f_aceto * P_H2 * gut_mass      # µmol h-1

    # acetate need (µmol h-1) from metabolic demand
    E_need  = Rdot * (M / 1000)             # J h-1
    A_need  = (F_acetate * E_need) / DG_ACETATE * 1e6  # mol -> µmol

    energy_ok = A_prod >= A_need

    df = pd.DataFrame({
        'x'  : x,
        'pH' : pH,
        'Eh (mV)' : Eh,
        'O₂ (µM)' : O2,
        'H₂ (kPa)': H2
    })

    return df, dict(
        V=V, Tret=Tret,
        A_prod=A_prod, A_need=A_need,
        energy_ok=energy_ok,
        H2_max=H2.max(), O2_shell=(O2 > 1).mean() * 1000  # mm in 0–1 scaled length
    )

# ─── STREAMLIT UI ──────────────────────────────────────────────
st.title("Termite Hind-gut Simulator – trophic specialisation sandbox")

# LAYOUT: two columns for clarity
col1, col2 = st.columns(2)

with col1:
    st.header("Diet")
    H       = st.slider("Humification index H", 0.0, 1.0, 0.3, 0.05)
    CN      = st.slider("C : N ratio", 20, 150, 80, 5)
    L       = st.slider("Lignin fraction (%)", 10, 40, 20)
    beta    = st.slider("Buffer capacity β (mmol H⁺ L⁻¹ pH⁻¹)", 0, 50, 10)

    st.header("Host control")
    tau     = st.slider("Transit multiplier τ (× baseline)", 0.5, 4.0, 1.0, 0.1)
    T_ret   = st.number_input("Absolute retention T₍ret₎ (h) – set 0 to use τ", 0.0, 48.0, 0.0, 0.5)
    alpha   = st.slider("Alkaline secretion α (mmol eq L⁻¹ h⁻¹)", 0.0, 10.0, 5.0)

with col2:
    st.header("Gas & microbiome")
    J_O2    = st.slider("Relative O₂ influx Jₒ₂", 0.0, 1.0, 0.3)
    radius  = st.slider("Gut radius r (mm)", 0.1, 1.5, 0.6, 0.1)
    P_H2    = st.slider("H₂ production Pₕ₂ (µmol g⁻¹ h⁻¹)", 0.0, 6.0, 2.0, 0.1)
    f_aceto = st.slider("H₂ captured by acetogens (fraction)", 0.0, 1.0, 0.8, 0.05)

    st.header("Energetics")
    M       = st.slider("Body mass M (mg)", 1, 50, 12)
    Rdot    = st.slider("Specific metabolic rate Ṙ (J g⁻¹ h⁻¹)", 0.5, 25.0, DEFAULT_RMET, 0.5)
    F_acet  = st.slider("Host energy from acetate", 0.7, 1.0, 0.9, 0.05)

# ─── RUN MODEL ────────────────────────────────────────────────
df, meta = gut_model(H, CN, L, beta,
                     tau, T_ret,
                     alpha, J_O2, radius,
                     P_H2, f_aceto,
                     M, Rdot, F_acet)

# ─── PLOTS ────────────────────────────────────────────────────
st.subheader("Axial physicochemical profiles")
plot_df = df.melt('x', var_name='Variable', value_name='Value')

chart = alt.Chart(plot_df).mark_line().encode(
    x=alt.X('x', title='Axial position (0 = P1, 1 = rectum)'),
    y='Value',
    color='Variable'
).properties(height=400)
st.altair_chart(chart, use_container_width=True)

# ─── METRICS & DIAGNOSTICS ────────────────────────────────────
st.subheader("Derived metrics")

c1, c2, c3 = st.columns(3)

c1.metric("Hind-gut volume index V", f"{meta['V']:.2f} (body vol fraction)")
c2.metric("Retention time T₍ret₎", f"{meta['Tret']:.1f} h",
          help="If you set absolute Tret above, τ is ignored.")
c3.metric("Peak H₂", f"{meta['H2_max']:.2f} kPa")

c4, c5, _ = st.columns(3)
c4.metric("Acetate produced", f"{meta['A_prod']:.1f} µmol h⁻¹")
c5.metric("Acetate needed", f"{meta['A_need']:.1f} µmol h⁻¹",
          delta=None if meta['energy_ok'] else "⚠ shortfall")

if meta['energy_ok']:
    st.success("✔ Acetate supply meets or exceeds host energetic demand.")
else:
    st.error("✖ Acetate shortfall – adjust α, τ or H to hit balance.")

with st.expander("Download data"):
    st.download_button("CSV of axial profiles",
                       data=df.to_csv(index=False).encode(),
                       file_name="gut_profiles.csv",
                       mime="text/csv")

# ─────────────────────────────────────────────────────────────

