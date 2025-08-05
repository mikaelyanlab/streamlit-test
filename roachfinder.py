import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# Title of the app
st.title("Pest Infestation Visualization in Raleigh (Wake County)")

st.markdown("""
This app visualizes violations related to cockroaches, termites, or bedbugs from Wake County food inspection data on a map.
Data is sourced from local files. It focuses on commercial facilities like restaurants.
For residential data, HUD AHS provides metro-level stats: ~18-20% of Raleigh metro households reported cockroach sightings in recent surveys.
""")

# Initialize session state
if 'merged_df' not in st.session_state:
    st.session_state.merged_df = None

# Data upload section
st.subheader("Upload Data")
restaurants_upload = st.file_uploader("Upload Restaurants CSV/JSON (e.g., wake-county-restaurants.csv)", type=["csv", "json"])
violations_upload = st.file_uploader("Upload Violations CSV/JSON (e.g., Food_Inspections.csv)", type=["csv", "json"])

if restaurants_upload and violations_upload and st.session_state.merged_df is None:
    try:
        # Load restaurants data
        if restaurants_upload.name.endswith('.json'):
            restaurants_df = pd.json_normalize(json.load(restaurants_upload))
        else:
            restaurants_df = pd.read_csv(restaurants_upload)
        st.write("Restaurants DataFrame columns:", restaurants_df.columns.tolist())
        # Rename columns to match expected format
        restaurants_df = restaurants_df.rename(columns={
            'HSISID': 'HSISID', 'Name': 'NAME', 'Address 1': 'ADDRESS1', 'City': 'CITY', 
            'Postal Code': 'POSTALCODE', 'X': 'X', 'Y': 'Y'
        })

        # Load violations data
        if violations_upload.name.endswith('.json'):
            violations_df = pd.json_normalize(json.load(violations_upload))
        else:
            violations_df = pd.read_csv(violations_upload)
        st.write("Violations DataFrame columns:", violations_df.columns.tolist())
        # Rename columns to match expected format
        violations_df = violations_df.rename(columns={
            'DATE_': 'INSPECTDATE', 'DESCRIPTION': 'SHORTDESC', 'TYPE': 'COMMENTS'
        })

        # Merge data on HSISID
        merged_df = violations_df.merge(restaurants_df[['HSISID', 'NAME', 'ADDRESS1', 'CITY', 'POSTALCODE', 'X', 'Y']], 
                                      on='HSISID', how='left')
        st.write("Merged DataFrame columns:", merged_df.columns.tolist())

        st.session_state.merged_df = merged_df.copy()

        st.success("Data uploaded and processed successfully.")
    except Exception as e:
        st.error(f"Error processing uploaded files: {str(e)}")

# Use cached/processed data
merged_df = st.session_state.merged_df

# Pest selection switches
st.subheader("Select Pests")
select_cockroaches = st.checkbox("Cockroaches", value=True)
select_termites = st.checkbox("Termites")
select_bedbugs = st.checkbox("Bedbugs")

# Define keywords for each pest (expandable based on data)
pest_keywords = {
    'cockroaches': ['cockroach', 'roaches', 'pest', 'insect', 'cockroach infestation', 'roach problem', 'infestation'],
    'termites': ['termite', 'termites', 'wood-destroying', 'wood destroying', 'termite damage', 'wood pest'],
    'bedbugs': ['bedbug', 'bed bug', 'bed bugs', 'bedbug infestation', 'bed bug problem', 'infestation']
}

# Allow manual keyword adjustment
st.subheader("Custom Keywords (optional)")
cockroach_keywords = st.text_input("Add/remove Cockroach keywords (comma-separated)", value=', '.join(pest_keywords['cockroaches']))
termites_keywords = st.text_input("Add/remove Termite keywords (comma-separated)", value=', '.join(pest_keywords['termites']))
bedbugs_keywords = st.text_input("Add/remove Bedbug keywords (comma-separated)", value=', '.join(pest_keywords['bedbugs']))

# Update keywords based on input
pest_keywords['cockroaches'] = [kw.strip() for kw in cockroach_keywords.split(',') if kw.strip()]
pest_keywords['termites'] = [kw.strip() for kw in termites_keywords.split(',') if kw.strip()]
pest_keywords['bedbugs'] = [kw.strip() for kw in bedbugs_keywords.split(',') if kw.strip()]

# Build the combined keywords based on selections
keywords = []
if select_cockroaches:
    keywords += pest_keywords['cockroaches']
if select_termites:
    keywords += pest_keywords['termites']
if select_bedbugs:
    keywords += pest_keywords['bedbugs']

# Filter for selected pest-related violations
if merged_df is not None and keywords:
    mask = merged_df['SHORTDESC'].str.contains('|'.join(keywords), case=False, na=False) | \
           merged_df['COMMENTS'].str.contains('|'.join(keywords), case=False, na=False)
    filtered_df = merged_df[mask].copy()
    # Debug: Show all violation texts for debugging
    if st.checkbox("Show all violation texts for debugging"):
        st.write("All violation texts (first 50 rows):")
        st.write(merged_df[['SHORTDESC', 'COMMENTS']].head(50))
else:
    filtered_df = pd.DataFrame()

# Display summary
st.subheader("Summary")
if not filtered_df.empty:
    st.write(f"Number of selected pest-related violations: {len(filtered_df)}")
    st.dataframe(filtered_df[['NAME', 'ADDRESS1', 'CITY', 'INSPECTDATE', 'SHORTDESC', 'COMMENTS']].head(10))
else:
    st.warning("No selected pest-related violations found or data not uploaded yet. Please upload both files and select pests.")

# Create map
if not filtered_df.empty:
    # Drop rows with invalid coordinates
    map_df = filtered_df.dropna(subset=['X', 'Y'])
    map_df = map_df[(map_df['X'] != 0) & (map_df['Y'] != 0)]

    # Initialize map centered on Raleigh
    m = folium.Map(location=[35.7796, -78.6382], zoom_start=11)

    # Add markers
    for idx, row in map_df.iterrows():
        popup_text = f"<b>{row['NAME']}</b><br>Address: {row['ADDRESS1']}, {row['CITY']}<br>Date: {row['INSPECTDATE']}<br>Violation: {row['SHORTDESC']}<br>Comments: {row['COMMENTS']}"
        try:
            folium.Marker(
                location=[row['Y'], row['X']],  # Y=latitude, X=longitude
                popup=popup_text,
                tooltip=row['NAME']
            ).add_to(m)
        except Exception as e:
            st.warning(f"Skipping invalid marker for {row['NAME']}: {str(e)}")

    st.subheader("Map of Infestations")
    folium_static(m)
else:
    st.write("No data available for mapping. Please upload both files and select pests.")

# Date filter
st.subheader("Filters")
if not filtered_df.empty and 'INSPECTDATE' in filtered_df.columns:
    try:
        filtered_df['INSPECTDATE'] = pd.to_datetime(filtered_df['INSPECTDATE'], errors='coerce')
        min_date = filtered_df['INSPECTDATE'].min().date()
        max_date = filtered_df['INSPECTDATE'].max().date()
        if pd.notna(min_date) and pd.notna(max_date):
            date_range = st.date_input("Select date range", [min_date, max_date])
            date_filtered_df = filtered_df[(filtered_df['INSPECTDATE'].dt.date >= date_range[0]) & 
                                           (filtered_df['INSPECTDATE'].dt.date <= date_range[1])]
            st.write(f"Filtered violations: {len(date_filtered_df)}")
            if not date_filtered_df.empty:
                map_df = date_filtered_df.dropna(subset=['X', 'Y'])
                map_df = map_df[(map_df['X'] != 0) & (map_df['Y'] != 0)]
                m = folium.Map(location=[35.7796, -78.6382], zoom_start=11)
                for idx, row in map_df.iterrows():
                    popup_text = f"<b>{row['NAME']}</b><br>Address: {row['ADDRESS1']}, {row['CITY']}<br>Date: {row['INSPECTDATE']}<br>Violation: {row['SHORTDESC']}<br>Comments: {row['COMMENTS']}"
                    try:
                        folium.Marker(
                            location=[row['Y'], row['X']],
                            popup=popup_text,
                            tooltip=row['NAME']
                        ).add_to(m)
                    except Exception as e:
                        st.warning(f"Skipping invalid marker for {row['NAME']}: {str(e)}")
                st.subheader("Filtered Map")
                folium_static(m)
    except Exception as e:
        st.error(f"Error processing dates: {str(e)}")
else:
    st.write("Inspection date data not available or no data uploaded.")
