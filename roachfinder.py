import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# Title of the app
st.title("Cockroach Infestation Visualization in Raleigh (Wake County)")

st.markdown("""
This app visualizes cockroach-related violations from Wake County food inspection data on a map.
Data is sourced from local files. It focuses on commercial facilities like restaurants.
For residential data, HUD AHS provides metro-level stats: ~18-20% of Raleigh metro households reported cockroach sightings in recent surveys.
""")

# Initialize session state
if 'merged_df' not in st.session_state:
    st.session_state.merged_df = None

# Data upload section
st.subheader("Upload Data")
data_upload = st.file_uploader("Upload Food Inspections CSV/JSON", type=["csv", "json"])

if data_upload and st.session_state.merged_df is None:
    try:
        # Load the full dataset
        if data_upload.name.endswith('.json'):
            df = pd.json_normalize(json.load(data_upload))
        else:
            df = pd.read_csv(data_upload)
        st.write("Full Dataset columns:", df.columns.tolist())

        # Extract unique restaurant data (deduplicated by HSISID)
        restaurant_cols = ['HSISID', 'NAME', 'ADDRESS1', 'CITY', 'POSTALCODE', 'X', 'Y']
        restaurants_df = df[restaurant_cols].drop_duplicates(subset=['HSISID'])
        restaurants_df.columns = [f'attributes.{col}' for col in restaurant_cols]
        st.write("Restaurants DataFrame columns:", restaurants_df.columns.tolist())

        # Keep all violation records
        violation_cols = [col for col in df.columns if col not in restaurant_cols or col == 'HSISID']
        violations_df = df[violation_cols]
        violations_df.columns = [f'attributes.{col}' if col != 'HSISID' else 'attributes.HSISID' for col in violation_cols]
        st.write("Violations DataFrame columns:", violations_df.columns.tolist())

        # Merge data on HSISID
        merged_df = violations_df.merge(restaurants_df, on='attributes.HSISID', how='left')
        st.write("Merged DataFrame columns:", merged_df.columns.tolist())

        # Filter for cockroach-related violations
        keywords = ['cockroach', 'roaches', 'pest', 'insect']
        mask = merged_df['attributes.COMMENTS'].str.contains('|'.join(keywords), case=False, na=False) | \
               merged_df['attributes.SHORTDESC'].str.contains('|'.join(keywords), case=False, na=False)
        st.session_state.merged_df = merged_df[mask].copy()

        st.success("Data uploaded and processed successfully.")
    except Exception as e:
        st.error(f"Error processing uploaded file: {str(e)}")

# Use cached/processed data
merged_df = st.session_state.merged_df

# Display summary
st.subheader("Summary")
if merged_df is not None and not merged_df.empty:
    st.write(f"Number of cockroach-related violations: {len(merged_df)}")
    st.dataframe(merged_df[['attributes.NAME', 'attributes.ADDRESS1', 'attributes.CITY',
                           'attributes.INSPECTDATE', 'attributes.SHORTDESC', 'attributes.COMMENTS']].head(10))
else:
    st.warning("No cockroach-related violations found or data not uploaded yet. Please upload the Food Inspections file.")

# Create map
if merged_df is not None and not merged_df.empty:
    # Drop rows with invalid coordinates
    merged_df = merged_df.dropna(subset=['attributes.X', 'attributes.Y'])
    merged_df = merged_df[(merged_df['attributes.X'] != 0
