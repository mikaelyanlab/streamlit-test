import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Ammonia–Temperature Dashboard", layout="wide")

st.title("💨 Ammonia Flux and Thermal Profiles During Decomposition")

# --- File upload ---
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # --- Data cleaning ---
    df.columns = [c.strip().replace(" ", "_").replace("(", "").replace(")", "").replace("°C", "C") for c in df.columns]
    if 'Date/Time' in df.columns:
        df['Date/Time'] = pd.to_datetime(df['Date/Time'])
        df = df.sort_values('Date/Time')

    st.subheader("Data Preview")
    st.dataframe(df.head())

    # --- Correlation matrix ---
    st.markdown("### 🔗 Correlation between Ammonia and Thermal Variables")
    corr_values = df[['Ammonia_ppm', 'Thermal_min_C', 'Thermal_mean_C', 'Thermal_max_C']].corr().iloc[0, 1:]
    corr_df = corr_values.to_frame(name="Correlation with Ammonia (r)").reset_index()
    corr_df.columns = ["Thermal Variable", "r"]
    st.dataframe(corr_df.style.background_gradient(cmap='RdYlGn', axis=0))

    # --- Line plot: Ammonia + Thermal envelope ---
    st.markdown("### 📈 Time-Series Trends")
    fig_line = px.line(df, x='Date/Time', y=['Ammonia_ppm', 'Thermal_mean_C'],
                       labels={'value': 'Value', 'variable': 'Parameter'},
                       color_discrete_map={'Ammonia_ppm':'blue', 'Thermal_mean_C':'red'})
    fig_line.update_traces(line=dict(width=2))
    fig_line.update_layout(yaxis_title="Temperature (°C) / Ammonia (ppm)",
                           legend_title_text=None)
    st.plotly_chart(fig_line, use_container_width=True)

    # --- Thermal envelope area plot ---
    st.markdown("### 🌡️ Thermal Envelope vs. Ammonia Flux")
    df['Thermal_range'] = df['Thermal_max_C'] - df['Thermal_min_C']
    fig_area = px.area(df, x='Date/Time', y='Thermal_range',
                       labels={'Thermal_range': 'Thermal Range (°C)'}, opacity=0.4)
    fig_area.add_scatter(x=df['Date/Time'], y=df['Ammonia_ppm'] * 10,
                         mode='lines', name='Ammonia (x10 scaled)',
                         line=dict(color='blue', width=2))
    fig_area.update_layout(yaxis_title="Thermal Range (°C)",
                           legend_title_text=None)
    st.plotly_chart(fig_area, use_container_width=True)

    # --- Scatter plot: Ammonia vs. Thermal mean ---
    st.markdown("### 🔥 Relationship Between Thermal Mean and Ammonia")
    fig_scatter = px.scatter(df, x='Thermal_mean_C', y='Ammonia_ppm',
                             color='Date/Time',
                             color_continuous_scale='Turbo',
                             trendline='lowess',
                             labels={'Thermal_mean_C': 'Thermal Mean (°C)',
                                     'Ammonia_ppm': 'Ammonia (ppm)'})
    st.plotly_chart(fig_scatter, use_container_width=True)

    # --- Summary interpretation ---
    st.markdown("""
    **Interpretation Guide:**
    - Rising ammonia levels often coincide with thermal peaks caused by microbial metabolism.
    - Correlation values help identify whether ammonia tracks minimum, mean, or maximum temperatures more closely.
    - Narrowing thermal range with sustained ammonia suggests internal heat buffering within the decomposing substrate.
    """)
else:
    st.info("Upload a CSV file containing columns for Ammonia and Thermal min/mean/max values.")
