import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Ammonia–Temperature Comparative Dashboard", layout="wide")
st.title("🧪 Comparative Ammonia–Temperature Dashboard")

# --- Multi-file upload ---
uploaded_files = st.file_uploader("Upload one or more CSV files", type=["csv"], accept_multiple_files=True)

if uploaded_files:
    dfs = []
    for file in uploaded_files:
        df = pd.read_csv(file)
        df.columns = [c.strip().replace(" ", "_").replace("(", "").replace(")", "").replace("°C", "C") for c in df.columns]
        if 'Date/Time' in df.columns:
            df['Date/Time'] = pd.to_datetime(df['Date/Time'])
            df = df.sort_values('Date/Time')
        df['source'] = file.name
        df['Thermal_range'] = pd.to_numeric(df['Thermal_max_C'], errors='coerce') - pd.to_numeric(df['Thermal_min_C'], errors='coerce')
        dfs.append(df)

    all_data = pd.concat(dfs, ignore_index=True)
    st.subheader("Data Preview")
    st.dataframe(all_data.head())

    # --- Correlation summary table ---
    st.markdown("### 🔗 Correlation Comparison (Ammonia vs Thermal Variables)")
    corr_list = []
    for src, df in all_data.groupby("source"):
        vals = {
            "Source": src,
            "Thermal min": df["Ammonia_ppm"].corr(df["Thermal_min_C"]),
            "Thermal mean": df["Ammonia_ppm"].corr(df["Thermal_mean_C"]),
            "Thermal max": df["Ammonia_ppm"].corr(df["Thermal_max_C"]),
        }
        corr_list.append(vals)
    corr_df = pd.DataFrame(corr_list)
    st.dataframe(corr_df.style.background_gradient(cmap='RdYlGn', axis=None))

    # --- Plot: Time-series comparison ---
    st.markdown("### 📈 Time Series: Ammonia vs Thermal Mean")
    fig = go.Figure()
    colors = px.colors.qualitative.Bold
    for i, (src, df) in enumerate(all_data.groupby("source")):
        fig.add_trace(go.Scatter(x=df['Date/Time'], y=df['Ammonia_ppm'],
                                 mode='lines', name=f'{src} – Ammonia',
                                 line=dict(color=colors[i % len(colors)], width=2)))
        fig.add_trace(go.Scatter(x=df['Date/Time'], y=df['Thermal_mean_C'],
                                 mode='lines', name=f'{src} – Thermal mean',
                                 line=dict(color=colors[i % len(colors)], width=1, dash='dot')))
    fig.update_layout(yaxis_title="Value", legend_title_text=None)
    st.plotly_chart(fig, use_container_width=True)

    # --- Plot: Thermal envelope comparison ---
    st.markdown("### 🌡️ Thermal Envelope vs Ammonia Flux")
    fig2 = go.Figure()
    for i, (src, df) in enumerate(all_data.groupby("source")):
        fig2.add_trace(go.Scatter(x=df['Date/Time'], y=df['Thermal_range'],
                                  fill='tozeroy', mode='none',
                                  name=f'{src} – Thermal range',
                                  fillcolor=colors[i % len(colors)]+'33'))
        fig2.add_trace(go.Scatter(x=df['Date/Time'], y=df['Ammonia_ppm']*10,
                                  mode='lines', name=f'{src} – Ammonia (×10)',
                                  line=dict(color=colors[i % len(colors)], width=2)))
    fig2.update_layout(yaxis_title="Thermal Range (°C)", legend_title_text=None)
    st.plotly_chart(fig2, use_container_width=True)

    # --- Scatter: Thermal mean vs Ammonia ---
    st.markdown("### 🔥 Scatter: Thermal Mean vs Ammonia (Chronological Gradient)")
    fig3 = px.scatter(all_data, x="Thermal_mean_C", y="Ammonia_ppm",
                      color="Date/Time", facet_col="source",
                      color_continuous_scale="Turbo", trendline="lowess")
    fig3.update_layout(showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

    # --- Interpretation block ---
    st.markdown("""
    **Interpretation Guide**
    - Compare how ammonia rises with internal heat buildup across profiles.
    - Observe if one profile stabilizes sooner (suggesting faster decay or drier substrate).
    - The shaded envelopes show microbial heat buffering; shrinking envelopes imply equilibrium reached.
    """)
else:
    st.info("Upload one or more CSVs with columns for Date/Time, Ammonia (ppm), and Thermal min/mean/max (°C).")
