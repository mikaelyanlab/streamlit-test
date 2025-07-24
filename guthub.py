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
H = st.sidebar.slider(
    "Humification (0 = soil-like, 1 = wood-like)",
    0.0, 1.0, 0.5,
    help="Increases fermentation demand and enlarges paunch; shrinks terminal segment."
)
var = st.sidebar.selectbox("Radial gradient to display", ["O₂", "H₂"])

# ------------------------------------------------------------------
# Morphological response to humification
# (simple phenomenological rules)
# ------------------------------------------------------------------
# Paunch (P3) expands most; distal P5 shrinks; P4 modest expansion
scaled_radii = {
    "P1": BASE["P1"]["radius"] * (1 + 0.05 * H),
    "P3": BASE["P3"]["radius"] * (1 + 0.40 * H),
    "P4": BASE["P4"]["radius"] * (1 + 0.15 * H),
    "P5": BASE["P5"]["radius"] * (1 - 0.25 * H),
}
# Prevent collapse
for k in scaled_radii:
    scaled_radii[k] = max(scaled_radii[k], 0.05)

# ------------------------------------------------------------------
# Radial microoxic geometry
# Microoxic annulus thickness increases with humification.
# We use the SAME fractional rule for all compartments for simplicity.
# ------------------------------------------------------------------
microoxic_frac = 0.10 + 0.20 * H  # fraction of radius occupied by the annulus
microoxic_frac = min(microoxic_frac, 0.8)  # cap so core does not vanish

def build_field(R, n=220):
    """Return (X,Y,mask,r,core_limit,O2,H2) for a compartment of radius R."""
    x = np.linspace(-R, R, n)
    y = np.linspace(-R, R, n)
    X, Y = np.meshgrid(x, y)
    r = np.sqrt(X**2 + Y**2)
    mask = r <= R

    band_thickness = microoxic_frac * R
    core_limit = R - band_thickness
    if core_limit < 0:  # degenerate case if annulus swallows core
        core_limit = 0.0

    # O2 high only in microoxic annulus; H2 inverse (high in core)
    O2 = np.zeros_like(r)
    annulus = (r >= core_limit) & (r <= R)
    O2[annulus] = 1.0
    # Slight decay right at the wall (optional aesthetic)
    wall_zone = (r > 0.98 * R) & annulus
    O2[wall_zone] *= 0.6

    H2 = 1.0 - O2  # perfect inverse for clarity
    return X, Y, mask, r, core_limit, O2, H2

# ------------------------------------------------------------------
# Plot four circles with selected gradient
# ------------------------------------------------------------------
fig, axes = plt.subplots(1, 4, figsize=(12, 3))
plt.subplots_adjust(wspace=0.25)

for ax, compartment in zip(axes, ["P1", "P3", "P4", "P5"]):
    R = scaled_radii[compartment]
    X, Y, mask, r, core_limit, O2_field, H2_field = build_field(R)

    field = O2_field if var == "O₂" else H2_field
    # Mask outside region
    plot_field = np.ma.array(field, mask=~mask)

    cmap = "viridis" if var == "O₂" else "magma"
    im = ax.imshow(
        plot_field,
        extent=(-R, R, -R, R),
        origin="lower",
        cmap=cmap,
        vmin=0,
        vmax=1,
    )

    # Draw boundaries: core + outer wall
    circ_outer = plt.Circle((0, 0), R, edgecolor="black", facecolor="none", linewidth=1)
    ax.add_patch(circ_outer)
    if core_limit > 0:
        circ_core = plt.Circle((0, 0), core_limit, edgecolor="black",
                               linestyle="--", facecolor="none", linewidth=0.8)
        ax.add_patch(circ_core)

    ax.set_title(f"{compartment}\nR = {R:.2f} mm\nArea = {np.pi*R**2:.3f} mm²")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_aspect("equal")

# Shared colorbar
cbar = fig.colorbar(im, ax=axes, fraction=0.025, pad=0.04)
cbar.set_label(f"{var} (relative units)")

st.pyplot(fig)

st.markdown(
    f"""
**Humification:** {H:.2f}  
Microoxic annulus thickness = {microoxic_frac*100:.1f}% of radius (dashed circle = anoxic core boundary).  
Selected gradient: **{var}** (O₂ high only in annulus; H₂ inverse).
"""
)
