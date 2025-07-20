# blowfly_lpi_app.py
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Lucilia cuprina LPI Comparator",
                   layout="wide")

st.title("🌱 Lucilia cuprina Larval Performance Comparator")

###############################################################################
# Helper: Larval Performance Index (multiplicative, 0–1 scale)
###############################################################################
def lpi(h, g, w, d, p, e):
    """Return Larval Performance Index (H·G·W·D·P·E)."""
    return h * g * w * d * p * e


###############################################################################
# Two‑column layout
###############################################################################
colA, colB = st.columns(2, gap="large")

# ---------- Condition A sliders & plot ----------
with colA:
    st.header("Condition A")
    hA = st.slider("Hatch rate (H)",              0.0, 1.0, 0.95, 0.01)
    gA = st.slider("Growth rate (G, normalized)", 0.0, 1.0, 0.80, 0.01)
    wA = st.slider("Peak larval weight (W)",      0.0, 1.0, 0.85, 0.01)
    dA = st.slider("Final‑instar fraction (D)",   0.0, 1.0, 0.90, 0.01)
    pA = st.slider("Pupation rate (P)",           0.0, 1.0, 0.75, 0.01)
    eA = st.slider("Eclosion rate (E)",           0.0, 1.0, 0.60, 0.01)

    lpi_A = lpi(hA, gA, wA, dA, pA, eA)
    st.metric("LPI (A)", f"{lpi_A:.3f}")

    # Radar plot for A
    metrics_A = [hA, gA, wA, dA, pA, eA]
    labels    = ["H", "G", "W", "D", "P", "E"]
    figA = go.Figure(go.Scatterpolar(r=metrics_A,
                                     theta=labels,
                                     fill='toself',
                                     name='A'))
    figA.update_layout(polar=dict(radialaxis=dict(range=[0, 1], visible=True)),
                       margin=dict(l=10, r=10, t=10, b=10),
                       showlegend=False)
    st.plotly_chart(figA, use_container_width=True)


# ---------- Condition B sliders & plot ----------
with colB:
    st.header("Condition B")
    hB = st.slider("Hatch rate (H)",              0.0, 1.0, 0.95, 0.01, key="HB")
    gB = st.slider("Growth rate (G, normalized)", 0.0, 1.0, 0.80, 0.01, key="GB")
    wB = st.slider("Peak larval weight (W)",      0.0, 1.0, 0.85, 0.01, key="WB")
    dB = st.slider("Final‑instar fraction (D)",   0.0, 1.0, 0.90, 0.01, key="DB")
    pB = st.slider("Pupation rate (P)",           0.0, 1.0, 0.75, 0.01, key="PB")
    eB = st.slider("Eclosion rate (E)",           0.0, 1.0, 0.60, 0.01, key="EB")

    lpi_B = lpi(hB, gB, wB, dB, pB, eB)
    st.metric("LPI (B)", f"{lpi_B:.3f}")

    # Radar plot for B
    metrics_B = [hB, gB, wB, dB, pB, eB]
    figB = go.Figure(go.Scatterpolar(r=metrics_B,
                                     theta=labels,
                                     fill='toself',
                                     name='B',
                                     marker=dict(color="indianred")))
    figB.update_layout(polar=dict(radialaxis=dict(range=[0, 1], visible=True)),
                       margin=dict(l=10, r=10, t=10, b=10),
                       showlegend=False)
    st.plotly_chart(figB, use_container_width=True)


###############################################################################
# Summary comparison
###############################################################################
st.subheader("Δ LPI (B − A)")
delta = lpi_B - lpi_A
st.write(f"**Difference:** {delta:+.3f}")

st.caption(
    "LPI = H × G × W × D × P × E • All sliders take 0–1 values. "
    "Extend the model later by adding exploratory variables (e.g., pH, ammonia) "
    "and correlating them with LPI."
)
