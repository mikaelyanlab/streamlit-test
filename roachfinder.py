import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# Title of the app
st.title("Pest Infestation Visualization in North Carolina")

st.markdown("""
This app visualizes violations related to cockroaches, termites, or bedbugs statewide in North Carolina on a map.
Data is sourced from AHS 2023 Metropolitan files. It focuses on metro-level residential data.
HUD AHS reports ~18-20% of NC households with cockroach sightings in recent surveys.
""")

# Initialize session state
if 'merged_df' not in st.session_state:
    st.session_state.merged_df = None
if 'weights_df' not in st.session_state:
    st.session_state.weights_df = None

# Data upload section
st.subheader("Upload AHS 2023 Metropolitan Data")
puf_upload = st.file_uploader("Upload PUF CSV (e.g., ahs2023_metropolitan_puf.csv)", type=["csv"])
recode_upload = st.file_uploader("Upload Recode CSV (e.g., ahs2023_metropolitan_recode.csv)", type=["csv"])
weights_upload = st.file_uploader("Upload Weights CSV (e.g., ahs2023_metropolitan_weights.csv)", type=["csv"])

if any([puf_upload, recode_upload, weights_upload]) and st.session_state.merged_df is None:
    try:
        # Load PUF data
        if puf_upload:
            puf_df = pd.read_csv(puf_upload)
            st.write("PUF DataFrame columns:", puf_df.columns.tolist())
        else:
            st.error("PUF file is required. Please upload ahs2023_metropolitan_puf.csv.")
            st.stop()

        # Load recode data (optional for mapping codes to text)
        if recode_upload:
            recode_df = pd.read_csv(recode_upload)
            st.write("Recode DataFrame columns:", recode_df.columns.tolist())
        else:
            recode_df = None

        # Load weights data (optional for counts)
        if weights_upload:
            weights_df = pd.read_csv(weights_upload)
            st.write("Weights DataFrame columns:", weights_df.columns.tolist())
            st.session_state.weights_df = weights_df
        else:
            st.session_state.weights_df = None

        # Filter for NC (Region 37) and relevant metros
        nc_metros = [3950, 1520, 3120, 9220]  # Raleigh, Charlotte, Greensboro, Winston-Salem
        nc_df = puf_df[puf_df['REGION'] == 37]
        nc_df = nc_df[nc_df['METRO'].isin(nc_metros)]

        # Add approximate coordinates based on metro
        metro_coords = {
            3950: {'Y': 35.7796, 'X': -78.6382},  # Raleigh
            1520: {'Y': 35.2271, 'X': -80.8431},  # Charlotte
            3120: {'Y': 36.0726, 'X': -79.7920},  # Greensboro
            9220: {'Y': 36.0999, 'X': -80.2442}   # Winston-Salem
        }
        nc_df['Y'] = nc_df['METRO'].map(lambda x: metro_coords.get(x, {'Y': None})['Y'])
        nc_df['X'] = nc_df['METRO'].map(lambda x: metro_coords.get(x, {'X': None})['X'])

        # Map columns with fallbacks
        column_mapping = {
            'ROACH': 'SHORTDESC', 'CONTROL': 'COMMENTS', 'YEAR': 'INSPECTDATE',
            'CONTROLID': 'HSISID', 'STRUCTURE': 'NAME', 'CITY': 'CITY', 'ZIP': 'POSTALCODE'
        }
        nc_df = nc_df.rename(columns={k: v for k, v in column_mapping.items() if k in nc_df.columns})

        # Convert ROACH to descriptive text using recode if available
        if 'SHORTDESC' in nc_df.columns and recode_df is not None:
            # Assume recode_df has a mapping like VARIABLE='ROACH', VALUE=1 -> LABEL='Cockroach sighting'
            roach_recode = recode_df[recode_df['VARIABLE'] == 'ROACH']
            if not roach_recode.empty:
                roach_map = dict(zip(roach_recode['VALUE'], roach_recode['LABEL']))
                nc_df['SHORTDESC'] = nc_df['SHORTDESC'].map(lambda x: roach_map.get(x, 'Unknown') if pd.notna(x) else None)
            else:
                nc_df['SHORTDESC'] = nc_df['SHORTDESC'].apply(lambda x: 'Cockroach sighting' if x == 1 else None)
        elif 'SHORTDESC' in nc_df.columns:
            nc_df['SHORTDESC'] = nc_df['SHORTDESC'].apply(lambda x: 'Cockroach sighting' if x == 1 else None)

        nc_df['INSPECTDATE'] = pd.to_datetime(nc_df['INSPECTDATE'], errors='coerce').fillna(pd.Timestamp('2023-01-01'))

        # Drop rows with missing coordinates
        nc_df = nc_df.dropna(subset=['X', 'Y'])

        st.session_state.merged_df = nc_df
        st.success("Data uploaded and processed successfully.")
    except Exception as e:
        st.error(f"Error processing uploaded files: {str(e)}")

# Use cached/processed data
merged_df = st.session_state.merged_df
weights_df = st.session_state.weights_df

# Pest selection switches
st.subheader("Select Pests to Display")
select_cockroaches = st.checkbox("Cockroaches (Red)", value=True)
select_termites = st.checkbox("Termites (Blue)")
select_bedbugs = st.checkbox("Bedbugs (Green)")

# Define keywords for each pest
pest_keywords = {
    'cockroaches': ['cockroach', 'roaches', 'pest', 'insect', 'cockroach sighting', 'roach problem', 'infestation'],
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

# Filter and categorize data
if merged_df is not None:
    # Initialize filtered dataframes
    cockroach_df = pd.DataFrame()
    termite_df = pd.DataFrame()
    bedbug_df = pd.DataFrame()

    if select_cockroaches:
        mask = merged_df['SHORTDESC'].str.contains('|'.join(pest_keywords['cockroaches']), case=False, na=False) | \
               merged_df['COMMENTS'].str.contains('|'.join(pest_keywords['cockroaches']), case=False, na=False)
        cockroach_df = merged_df[mask].copy()
    if select_termites:
        mask = merged_df['SHORTDESC'].str.contains('|'.join(pest_keywords['termites']), case=False, na=False) | \
               merged_df['COMMENTS'].str.contains('|'.join(pest_keywords['termites']), case=False, na=False)
        termite_df = merged_df[mask].copy()
    if select_bedbugs:
        mask = merged_df['SHORTDESC'].str.contains('|'.join(pest_keywords['bedbugs']), case=False, na=False) | \
               merged_df['COMMENTS'].str.contains('|'.join(pest_keywords['bedbugs']), case=False, na=False)
        bedbug_df = merged_df[mask].copy()

    # Debug: Show all violation texts
    if st.checkbox("Show all violation texts for debugging"):
        st.write("All violation texts (first 50 rows):")
        st.write(merged_df[['SHORTDESC', 'COMMENTS']].head(50))

# Display summary
st.subheader("Summary")
if not cockroach_df.empty or not termite_df.empty or not bedbug_df.empty:
    st.write(f"Cockroach violations: {len(cockroach_df)}")
    st.write(f"Termite violations: {len(termite_df)}")
    st.write(f"Bedbug violations: {len(bedbug_df)}")
    if weights_df is not None and 'CONTROLID' in weights_df.columns and 'CONTROLID' in merged_df.columns:
        weighted_count = weights_df[weights_df['CONTROLID'].isin(merged_df['HSISID'])].sum().sum()
        st.write(f"Weighted total violations (if applicable): {weighted_count}")
    st.dataframe(pd.concat([cockroach_df, termite_df, bedbug_df])[['NAME', 'CITY', 'INSPECTDATE', 'SHORTDESC', 'COMMENTS']].head(10))
else:
    st.warning("No pest-related violations found or data not uploaded yet. Please upload the PUF file and select pests.")

# Create map
if not cockroach_df.empty or not termite_df.empty or not bedbug_df.empty:
    # Initialize map centered on NC
    m = folium.Map(location=[35.7596, -79.0193], zoom_start=7)  # NC center

    # Add markers for each pest type with different colors
    if select_cockroaches and not cockroach_df.empty:
        for idx, row in cockroach_df.iterrows():
            folium.Marker(
                location=[row['Y'], row['X']],
                popup=f"<b>{row['NAME']}</b><br>City: {row['CITY']}<br>Date: {row['INSPECTDATE']}<br>Violation: {row['SHORTDESC']}<br>Comments: {row['COMMENTS']}",
                tooltip=row['NAME'],
                icon=folium.Icon(color="red")
            ).add_to(m)

    if select_termites and not termite_df.empty:
        for idx, row in termite_df.iterrows():
            folium.Marker(
                location=[row['Y'], row['X']],
                popup=f"<b>{row['NAME']}</b><br>City: {row['CITY']}<br>Date: {row['INSPECTDATE']}<br>Violation: {row['SHORTDESC']}<br>Comments: {row['COMMENTS']}",
                tooltip=row['NAME'],
                icon=folium.Icon(color="blue")
            ).add_to(m)

    if select_bedbugs and not bedbug_df.empty:
        for idx, row in bedbug_df.iterrows():
            folium.Marker(
                location=[row['Y'], row['X']],
                popup=f"<b>{row['NAME']}</b><br>City: {row['CITY']}<br>Date: {row['INSPECTDATE']}<br>Violation: {row['SHORTDESC']}<br>Comments: {row['COMMENTS']}",
                tooltip=row['NAME'],
                icon=folium.Icon(color="green")
            ).add_to(m)

    st.subheader("Map of Infestations")
    folium_static(m)
else:
    st.write("No data available for mapping. Please upload the PUF file and select pests.")

# Date filter
st.subheader("Filters")
if not cockroach_df.empty or not termite_df.empty or not bedbug_df.empty:
    try:
        combined_df = pd.concat([cockroach_df, termite_df, bedbug_df]).drop_duplicates()
        if 'INSPECTDATE' in combined_df.columns:
            combined_df['INSPECTDATE'] = pd.to_datetime(combined_df['INSPECTDATE'], errors='coerce')
            min_date = combined_df['INSPECTDATE'].min().date()
            max_date = combined_df['INSPECTDATE'].max().date()
            if pd.notna(min_date) and pd.notna(max_date):
                date_range = st.date_input("Select date range", [min_date, max_date])
                date_filtered_df = combined_df[(combined_df['INSPECTDATE'].dt.date >= date_range[0]) & 
                                               (combined_df['INSPECTDATE'].dt.date <= date_range[1])]
                st.write(f"Filtered violations: {len(date_filtered_df)}")
                if not date_filtered_df.empty:
                    m = folium.Map(location=[35.7596, -79.0193], zoom_start=7)
                    if select_cockroaches and not cockroach_df.empty:
                        for idx, row in date_filtered_df[date_filtered_df.index.isin(cockroach_df.index)].iterrows():
                            folium.Marker(
                                location=[row['Y'], row['X']],
                                popup=f"<b>{row['NAME']}</b><br>City: {row['CITY']}<br>Date: {row['INSPECTDATE']}<br>Violation: {row['SHORTDESC']}<br>Comments: {row['COMMENTS']}",
                                tooltip=row['NAME'],
                                icon=folium.Icon(color="red")
                            ).add_to(m)
                    if select_termites and not termite_df.empty:
                        for idx, row in date_filtered_df[date_filtered_df.index.isin(termite_df.index)].iterrows():
                            folium.Marker(
                                location=[row['Y'], row['X']],
                                popup=f"<b>{row['NAME']}</b><br>City: {row['CITY']}<br>Date: {row['INSPECTDATE']}<br>Violation: {row['SHORTDESC']}<br>Comments: {row['COMMENTS']}",
                                tooltip=row['NAME'],
                                icon=folium.Icon(color="blue")
                            ).add_to(m)
                    if select_bedbugs and not bedbug_df.empty:
                        for idx, row in date_filtered_df[date_filtered_df.index.isin(bedbug_df.index)].iterrows():
                            folium.Marker(
                                location=[row['Y'], row['X']],
                                popup=f"<b>{row['NAME']}</b><br>City: {row['CITY']}<br>Date: {row['INSPECTDATE']}<br>Violation: {row['SHORTDESC']}<br>Comments: {row['COMMENTS']}",
                                tooltip=row['NAME'],
                                icon=folium.Icon(color="green")
                            ).add_to(m)
                    st.subheader("Filtered Map")
                    folium_static(m)
    except Exception as e:
        st.error(f"Error processing dates: {str(e)}")
else:
    st.write("Inspection date data not available or no data uploaded.")
