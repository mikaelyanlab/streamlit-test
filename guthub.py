import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import plotly.graph_objects as go

# ---------------------------------------------------------------------
# Base compartments (mm)
# ---------------------------------------------------------------------
BASE_COMPARTS = {
    "P1": {"length": 3.0, "radius": 0.15},
    "P3": {"length": 8.0, "radius": 0.45},  # Paunch
    "P4": {"length": 6.0, "radius": 0.30},
    "P5": {"length": 2.0, "radius": 0.15},
}

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def adjust_compartments(recalcitrance: float, selection: float):
    """Morphological evolution: enlarge P3, shrink P5."""
    comp = {k: v.copy() for k, v in BASE_COMPARTS.items()}
    scale = recalcitrance * selection
    comp["P3"]["length"] *= (1 + 0.6 * scale)
    comp["P3"]["radius"] *= (1 + 0.4 * scale)
    comp["P5"]["length"] *= (1 - 0.3 * scale)
    for k, v in comp.items():
        v["volume"] = np.pi * v["radius"] ** 2 * v["length"]
    return comp


def build_axis(comparts):
    """Return cumulative axial coordinate arrays (mm) for plotting."""
    names = list(comparts.keys())
    lengths = [comparts[n]["length"] for n in names]
    boundaries = np.cumsum([0] + lengths)
    total = boundaries[-1]
    return names, lengths, boundaries, total


# ---------------------------------------------------------------------
# Axial physicochemical profiles
# ---------------------------------------------------------------------
def axial_profiles(recalcitrance, selection, comparts):
    """
    Produce axial pH, O2, H2 shaped after Brune-style panels:
      - low recalcitrance -> no alkaline peak (panel C)
      - intermediate -> sharp spike (panel B)
      - high -> broad plateau (panel A)
    H2 peak in paunch (P3); O2 nearly constant (small), Eh computed.
    """
    names, lengths, boundaries, total = build_axis(comparts)
    x_mm = np.linspace(0, total, 400)

    # Map recalcitrance to regimes
    # amplitude of alkalinity
    alk_amp = 4.0 * recalcitrance * selection  # up to +4 pH units
    # width parameter (broad plateau at high recalcitrance)
    width = 0.3 + 1.2 * recalcitrance          # in "fraction of P1 length"

    # Center of alkaline region: middle of P1
    p1_start, p1_end = boundaries[0], boundaries[1]
    p1_center = 0.5 * (p1_start + p1_end)
    p1_len = comparts["P1"]["length"]

    # Gaussian -> plateau hybrid: at high recalcitrance width large -> flat top
    sigma = width * p1_len
    base_pH = 6.5
    alkaline = alk_amp * np.exp(-((x_mm - p1_center) ** 2) / (2 * sigma ** 2))
    # Clip: for high recalcitrance mimic plateau by smoothing
    if recalcitrance > 0.7:
        alkaline = np.minimum(alkaline, alk_amp * 0.9)

    pH = base_pH + alkaline

    # H2 axial: Gaussian in paunch (P3)
    p3_start = boundaries[names.index("P3")]
    p3_end = p3_start + comparts["P3"]["length"]
    p3_center = 0.5 * (p3_start + p3_end)
    sigma_p3 = comparts["P3"]["length"] / 3
    h2_amp = 5.0 * (1 + 0.5 * recalcitrance * selection)
    H2_ax = h2_amp * np.exp(-((x_mm - p3_center) ** 2) / (2 * sigma_p3 ** 2))

    # O2 axial: small baseline reduced by large paunch volume (diffusion sink)
    o2_base = 1.5 / (1 + 0.15 * comparts["P3"]["volume"])
    O2_ax = np.full_like(x_mm, o2_base)

    # Eh (same expression as your earlier script)
    Eh_ax = -100 - 59 * (pH - 7) + 0.3 * O2_ax - 40 * H2_ax
    return x_mm, pH, O2_ax, H2_ax, Eh_ax, boundaries, names


# ---------------------------------------------------------------------
# Radial model (P3 cross-section)
# ---------------------------------------------------------------------
def radial_profile(recalcitrance, selection, comparts):
    """
    Radial O2/H2 profile for paunch cross-section:
    Anoxic core (H2 high), microoxic annulus near wall (O2 high).
    """
    R = comparts["P3"]["radius"]
    # Thickness of microoxic band scales with recalcitrance (0.1–0.25 of R)
    band_thickness = (0.10 + 0.15 * recalcitrance) * R
    r_core_limit = R - band_thickness  # boundary between anoxic core and band

    # Build fine radial coordinate
    r = np.linspace(0, R, 300)

    # H2 high in core linearly decreasing to 0 at band start
    H2_core_amp = 5.0 * (1 + 0.5 * recalcitrance * selection)
    H2 = np.where(
        r <= r_core_limit,
        H2_core_amp * (1 - r / r_core_limit),
        0.0
    )

    # O2 zero in core, high (plateau) in microoxic band
    O2_band_amp = 5.0  # constant reference
    O2 = np.where(r >= r_core_limit, O2_band_amp, 0.0)

    return r, R, r_core_limit, H2, O2


def radial_cross_section_figure(r, R, r_core_limit):
    """
    Plotly figure of cross-section with microoxic annulus shading.
    Just geometry (no color scale) to mimic Brune-style diagram.
    """
    theta = np.linspace(0, 2 * np.pi, 200)
    # Outer circle
    outer_y = R * np.cos(theta)
    outer_z = R * np.sin(theta)
    # Core circle
    core_y = r_core_limit * np.cos(theta)
    core_z = r_core_limit * np.sin(theta)

    fig = go.Figure()
    # Annulus fill: construct as scatter + fill
    fig.add_trace(go.Scatter(
        x=np.concatenate([core_y, outer_y[::-1]]),
        y=np.concatenate([core_z, outer_z[::-1]]),
        fill='toself',
        fillcolor='rgba(150,150,150,0.35)',
        line=dict(color='rgba(0,0,0,0)'),
        hoverinfo='skip',
        showlegend=False
    ))
    # Outer boundary
    fig.add_trace(go.Scatter(x=outer_y, y=outer_z,
                             mode='lines', line=dict(color='black'), name='Gut wall'))
    # Core boundary
    fig.add_trace(go.Scatter(x=core_y, y=core_z,
                             mode='lines', line=dict(color='black', dash='dot'), name='Anoxic core'))

    fig.update_layout(
        title="P3 Cross-Section (Microoxic Annulus)",
        xaxis=dict(visible=False, scaleanchor='y', scaleratio=1),
        yaxis=dict(visible=False),
        margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
        height=300
    )
    return fig


def radial_line_plot(r, R, r_core_limit, H2, O2):
    """Altair radial line chart with shaded microoxic band."""
    df = pd.DataFrame({
        "r_norm": r / R,
        "O2": O2,
        "H2": H2
    })
    band_df = pd.DataFrame({
        "start": [r_core_limit / R],
        "end": [1.0]
    })

    base = alt.Chart(df).encode(x=alt.X("r_norm", title="Normalized radial distance (0=center, 1=wall)"))
    shade = alt.Chart(band_df).mark_rect(opacity=0.25, color="gray").encode(
        x='start', x2='end'
    )
    o2_line = base.mark_line(color="blue").encode(y=alt.Y("O2", title="Partial pressure (a.u.)"))
    h2_line = base.mark_line(color="red", strokeDash=[5, 4]).encode(y="H2")
    return (shade + o2_line + h2_line).properties(title="Radial O₂ (solid) and H₂ (dashed) in P3")


# ---------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------
st.sidebar.header("Evolutionary Parameters")
recalcitrance = st.sidebar.slider(
    "Dietary Recalcitrance (0: Soil-like, 1: Wood-like)", 0.0, 1.0, 0.5,
    help="Approximate: Soil ~0.2, Humus ~0.3, Grass ~0.5, Wood ~0.8"
)
selection_pressure = st.sidebar.slider("Selection Pressure", 0.0, 2.0, 1.0)

comparts = adjust_compartments(recalcitrance, selection_pressure)
x_mm, pH_ax, O2_ax, H2_ax, Eh_ax, boundaries, names = axial_profiles(
    recalcitrance, selection_pressure, comparts
)
r, R_p3, r_core_limit, H2_r, O2_r = radial_profile(recalcitrance, selection_pressure, comparts)

# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------
st.header("Termite Hindgut Microenvironment – Brune-style Model")

# Cross-section + radial profile
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(radial_cross_section_figure(r, R_p3, r_core_limit), use_container_width=True)
with col2:
    st.altair_chart(radial_line_plot(r, R_p3, r_core_limit, H2_r, O2_r), use_container_width=True)

# Axial profiles (Altair)
st.subheader("Axial Profiles")
ax_df = pd.DataFrame({
    "x_mm": x_mm,
    "pH": pH_ax,
    "O2": O2_ax,
    "H2": H2_ax,
    "Eh": Eh_ax
})

def axial_chart(var, color, title, ylab):
    c = alt.Chart(ax_df).mark_line(color=color).encode(
        x=alt.X("x_mm", title="Axial position (mm)"),
        y=alt.Y(var, title=ylab)
    ).properties(title=title, height=120)
    # compartment bars
    bars = []
    for i, name in enumerate(names):
        start = boundaries[i]; end = boundaries[i+1]
        bars.append(
            alt.Chart(pd.DataFrame({"start": [start], "end": [end], "label": [name]})).mark_rect(
                opacity=0.12, color="black").encode(
                x='start', x2='end'
            )
        )
    layer = alt.layer(c, *bars)
    return layer

charts = [
    axial_chart("pH", "green", "pH", "pH"),
    axial_chart("O2", "blue", "O₂ (axial mean)", "O₂ (a.u.)"),
    axial_chart("H2", "red", "H₂ (axial mean)", "H₂ (a.u.)"),
    axial_chart("Eh", "gray", "Redox potential", "Eh (mV)")
]
for ch in charts:
    st.altair_chart(ch, use_container_width=True)

st.caption("pH regime transitions with recalcitrance (panel C→B→A analogue); radial microoxic annulus drives inverse O₂/H₂ distributions and Eh.")
