import numpy as np
import matplotlib.pyplot as plt
import streamlit as st

st.set_page_config(layout="wide")

# ------------------------------------------------------------------
# Base morphology (radii in mm). These are *baseline* cross sections.
# ------------------------------------------------------------------
BASE = {
    "P1": {"radius": 0.15},
    "P3": {"radius": 0.45},  # paunch
    "P4": {"radius": 0.30},
    "P5": {"radius": 0.15},
}

# ---------------------------
# Sidebar: user input sliders
# ---------------------------
st.sidebar.header("Inputs")
humification = st.sidebar.slider(
    "Humification (0 = least humified, 1 = most humified)",
    0.0, 1.0, 0.5,
    help="0 represents fresh wood (high lignocellulose), 1 represents soil-like (high humification)."
)
selection_pressure = st.sidebar.slider("Selection Pressure", 0.0, 2.0, 1.0)
var = st.sidebar.selectbox("Radial gradient to display", ["O₂", "H₂"])

# ------------------------------------------------------------------
# Morphological response to humification
# (adjusted scaling: P3 increases at low humification, decreases at high)
# ------------------------------------------------------------------
def adjust_radii(humification, selection_pressure):
    comparts = BASE.copy()
    H_sq = humification ** 2
    comparts["P1"]["radius"] *= (1 + 0.10 * H_sq * selection_pressure)
    comparts["P3"]["radius"] *= (1 + 0.70 * (1 - H_sq) * selection_pressure - 0.70 * H_sq * selection_pressure)
    comparts["P4"]["radius"] *= (1 + 0.20 * H_sq * selection_pressure)
    comparts["P5"]["radius"] *= (1 + 0.50 * H_sq * selection_pressure)
    # Prevent collapse
    for k in comparts:
        comparts[k]["radius"] = max(comparts[k]["radius"], 0.05)
    return comparts

scaled_radii = adjust_radii(humification, selection_pressure)

# ------------------------------------------------------------------
# Radial microoxic geometry
# Microoxic annulus thickness decreases with humification (more anoxic in soil).
# ------------------------------------------------------------------
microoxic_frac = 0.30 - 0.20 * humification
microoxic_frac = max(microoxic_frac, 0.1)

def build_field(R, humification, selection_pressure, n=220):
    """Return (X,Y,mask,r,core_limit,O2,H2) with real units."""
    x = np.linspace(-R, R, n)
    y = np.linspace(-R, R, n)
    X, Y = np.meshgrid(x, y)
    r = np.sqrt(X**2 + Y**2)
    mask = r <= R

    band_thickness = microoxic_frac * R
    core_limit = R - band_thickness
    if core_limit < 0:
        core_limit = 0.0

    # O2 gradient: max 50 µM at periphery, decays to 0 µM at core
    decay_rate = 5 * (1 + humification * selection_pressure)  # Increases with humification
    O2 = 50 * np.exp(-decay_rate * (r / R))  # High at periphery, low at core
    O2[~mask] = np.nan
    wall_zone = r > (1 - 0.02) * R
    O2[wall_zone] *= 0.6  # Slight decay near wall

    # H2 gradient: 0 µM at periphery, increases to H2_max at core
    H2_max = 100 + 100 * humification * selection_pressure
    H2 = H2_max * (1 - np.exp(-decay_rate * (r / R)))  # Low at periphery, high at core
    H2[~mask] = np.nan

    # Clip to realistic ranges
    O2 = np.clip(O2, 0, 50)
    H2 = np.clip(H2, 0, 300)

    return X, Y, mask, r, core_limit, O2, H2

# ------------------------------------------------------------------
# Plot four circles with selected gradient
# ------------------------------------------------------------------
fig, axes = plt.subplots(1, 4, figsize=(16, 3))
plt.subplots_adjust(wspace=0.4)

for ax, compartment in zip(axes, ["P1", "P3", "P4", "P5"]):
    R = scaled_radii[compartment]["radius"]
    X, Y, mask, r, core_limit, O2_field, H2_field = build_field(R, humification, selection_pressure)

    field = O2_field if var == "O₂" else H2_field
    plot_field = np.ma.array(field, mask=~mask)

    cmap = "viridis_r" if var == "O₂" else "magma"  # Reversed viridis for O₂
    im = ax.imshow(
        plot_field,
        extent=(-R, R, -R, R),
        origin="lower",
        cmap=cmap,
        vmin=0,
        vmax=50 if var == "O₂" else 300,
    )

    circ_outer = plt.Circle((0, 0), R, edgecolor="black", facecolor="none", linewidth=1)
    ax.add_patch(circ_outer)
    if core_limit > 0:
        circ_core = plt.Circle((0, 0), core_limit, edgecolor="black",
                               linestyle="--", facecolor="none", linewidth=0.8)
        ax.add_patch(circ_core)

    ax.set_title(f"{compartment}\nR = {R:.2f} mm\nArea = {np.pi*R**2:.3f} mm²")
    ax.set_xticks([])
    set_yticks([])
    ax.set_aspect("equal")
    ax.set_xlim(-R - 0.1, R + 0.1)
    ax.set_ylim(-R - 0.1, R + 0.1)

cbar = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.04)
cbar.set_label(f"{var} (µM)")

st.pyplot(fig)

st.markdown(
    f"""
**Humification:** {humification:.2f}  
**Selection Pressure:** {selection_pressure:.2f}  
Microoxic annulus thickness = {microoxic_frac*100:.1f}% of radius (dashed circle = anoxic core boundary).  
Selected gradient: **{var}** (O₂ high at periphery, H₂ high in core).
"""
)
