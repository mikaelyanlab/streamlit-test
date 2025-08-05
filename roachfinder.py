import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static

# Title of the app
st.title("Cockroach Infestation Visualization in Raleigh (Wake County)")

st.markdown("""
This app visualizes cockroach-related violations from Wake County food inspection data on a map.
Data is sourced from public ArcGIS services. It focuses on commercial facilities like restaurants.
For residential data, HUD AHS provides metro-level stats: In the Raleigh metro area, about 18-20% of households reported cockroach sightings in recent surveys.
""")

# Cache data loading
@st.cache_data
def load_data():
    # URL for Restaurants layer (locations)
    restaurants_url = "https://maps.wakegov.com/arcgis/rest/services/Inspections/RestaurantInspectionsOpenData/MapServer/0/query?where=1=1&outFields=HSISID,NAME,ADDRESS1,CITY,POSTALCODE,X,Y&f=csv"
    restaurants_df = pd.read_csv(restaurants_url)
    
    # URL for Violations layer
    violations_url = "https://maps.wakegov.com/arcgis/rest/services/Inspections/RestaurantInspectionsOpenData/MapServer/2/query?where=1=1&outFields=*&f=csv"
    violations_df = pd.read_csv(violations_url)
    
    return restaurants_df, violations_df

restaurants_df, violations_df = load_data()

# Filter for cockroach-related violations
keywords = ['cockroach', 'roaches', 'pest', 'insect']
mask = violations_df['COMMENTS'].str.contains('|'.join(keywords), case=False, na=False) | \
       violations_df['SHORTDESC'].str.contains('|'.join(keywords), case=False, na=False)
cockroach_viol = violations_df[mask]

# Merge with locations
merged_df = cockroach_viol.merge(restaurants_df, on='HSISID', how='left')

# Drop rows without coordinates
merged_df = merged_df.dropna(subset=['X', 'Y'])

# Display summary
st.subheader("Summary")
st.write(f"Number of cockroach-related violations: {len(merged_df)}")
st.dataframe(merged_df[['NAME', 'ADDRESS1', 'CITY', 'INSPECTDATE', 'SHORTDESC', 'COMMENTS']])

# Create map
if not merged_df.empty:
    m = folium.Map(location=[35.7796, -78.6382], zoom_start=11)  # Centered on Raleigh

    for idx, row in merged_df.iterrows():
        popup_text = f"<b>{row['NAME']}</b><br>Address: {row['ADDRESS1']}, {row['CITY']}<br>Date: {row['INSPECTDATE']}<br>Violation: {row['SHORTDESC']}<br>Comments: {row['COMMENTS']}"
        folium.Marker(
            location=[row['Y'], row['X']],  # Assuming Y=lat, X=lon
            popup=popup_text,
            tooltip=row['NAME']
        ).add_to(m)

    st.subheader("Map of Infestations")
    folium_static(m)
else:
    st.write("No data available for mapping.")

# Additional filters (example: date range)
st.subheader("Filters")
min_date = pd.to_datetime(violations_df['INSPECTDATE'].min(), unit='ms') if 'INSPECTDATE' in violations_df else None
max_date = pd.to_datetime(violations_df['INSPECTDATE'].max(), unit='ms') if 'INSPECTDATE' in violations_df else None
if min_date and max_date:
    date_range = st.date_input("Select date range", [min_date, max_date])
    # You can add logic to filter based on date_range here
else:
    st.write("Date data not available.")
