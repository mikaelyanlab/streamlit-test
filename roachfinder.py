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

# Data upload section
st.subheader("Upload AHS 2023 Metropolitan Data")
file1_upload = st.file_uploader("Upload File 1 (e.g., PUF data)", type=["csv"])
file2_upload = st.file_uploader("Upload File 2 (e.g., Weights data)", type=["csv"])
file3_upload = st.file_uploader("Upload File 3 (e.g., Recode data)", type=["csv"])
file4_upload = st.file_uploader("Upload File 4 (e.g., Documentation or additional data)", type=["csv"])

if any([file1_upload, file2_upload, file3_upload, file4_upload]) and st.session_state.merged_df is None:
    try:
        # Initialize dataframes
        df_list = []
        weights_df = None
        recode_df = None

        # Process each uploaded file
        for i, file_upload in enumerate([file1_upload, file2_upload, file3_upload, file4_upload]):
            if file_upload:
                df = pd.read_csv(file_upload)
                st.write(f"File {i+1} DataFrame columns:", df.columns.tolist())
                if 'CONTROLID' in df.columns and 'WEIGHT' in df.columns:  # Likely weights file
                    weights_df = df
                elif 'VARIABLE' in df.columns and 'VALUE' in df.columns and 'LABEL' in df.columns:  # Likely recode file
                    recode_df = df
                else:  # Likely PUF or additional data
                    df_list.append(df)

        # Combine PUF or additional data files
        if df_list:
            merged_df = pd.concat(df_list, ignore_index=True)
        else:
            st.error("No PUF or data files uploaded. Please upload at least one data file.")
            st.stop()

        # Filter for NC (Region 37) and relevant metros
        nc_metros = [3950, 1520, 3120, 9220]  # Raleigh, Charlotte, Greensboro, Winston-Salem
        merged_df = merged_df[merged_df['REGION'] == 37]
        merged_df = merged_df[merged_df['METRO'].isin(nc_metros)]

        # Add approximate coordinates based on metro
        metro_coords = {
            3950: {'Y': 35.7796, 'X': -78.6382},  # Raleigh
            1520: {'Y': 35.2271, 'X': -80.8431},  # Charlotte
            3120: {'Y': 36.0726, 'X': -79.7920},  # Greensboro
            9220: {'Y': 36.0999, 'X': -80.2442}   # Winston-Salem
        }
        merged_df['Y'] = merged_df['METRO'].map(lambda x: metro_coords.get(x, {'Y': None})['Y'])
        merged_df['X'] = merged_df['METRO'].map(lambda x: metro_coords.get(x, {'X': None})['X'])

        # Map columns with fallbacks
        column_mapping = {
            'ROACH': 'SHORTDESC', 'CONTROL': 'COMMENTS', 'YEAR': 'INSPECTDATE',
            'CONTROLID': 'HSISID', 'STRUCTURE': 'NAME', 'CITY': 'CITY', 'ZIP': 'POSTALCODE'
        }
        merged_df = merged_df.rename(columns={k: v for k, v in column_mapping.items() if k in merged_df.columns})

        # Convert pest codes to text using recode if available
        if 'SHORTDESC' in merged_df.columns and recode_df is not None:
            pest_vars = ['ROACH', 'TERMITE', 'BEDBUG']  # Adjust based on actual variables
            for var in pest_vars:
                if var in merged_df.columns:
                    var_recode = recode_df[recode_df['VARIABLE'] == var]
                    if not var_recode.empty:
                        recode_map = dict(zip(var_recode['VALUE'], var_recode['LABEL']))
                        merged_df.loc[merged_df[var] == merged_df[var], 'SHORTDESC'] = merged_df[var].map(lambda x: recode_map.get(x, 'Unknown') if pd.notna(x) else None)
                    else:
                        merged_df['SHORTDESC'] = merged_df['SHORTDESC'].apply(lambda x: 'Pest sighting' if x == 1 else None)
        elif 'SHORTDESC' in merged_df.columns:
            merged_df['SHORTDESC'] = merged_df['SHORTDESC'].apply(lambda x: 'Pest sighting' if x == 1 else None)

        merged_df['INSPECTDATE'] = pd.to_datetime(merged_df['INSPECTDATE'], errors='coerce').fillna(pd.Timestamp('2023-01-01'))

        # Drop rows with missing coordinates
        merged_df = merged_df.dropna(subset=['X', 'Y'])

        st.session_state.merged_df = merged_df
        st.success("Data uploaded and processed successfully.")
    except Exception as e:
        st.error(f"Error processing uploaded files: {str(e)}")

# Use cached/processed data
merged_df = st.session_state.merged_df

# Initialize filtered dataframes
cockroach_df = pd.DataFrame()
termite_df = pd.DataFrame()
bedbug_df = pd.DataFrame()

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

# Filter and categorize data if data is available
if merged_df is not None:
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
    st.dataframe(pd.concat([cockroach_df, termite_df, bedbug_df])[['NAME', 'CITY', 'INSPECTDATE', 'SHORTDESC', 'COMMENTS']].head(10))
else:
    st.warning("No pest-related violations found or data not uploaded yet. Please upload at least one data file and select pests.")

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
    st.write("No data available for mapping. Please upload at least one data file and select pests.")

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
