import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import geopandas as gpd
import requests
from bs4 import BeautifulSoup
import threading
import time
from datetime import datetime

# Sample initial data (compiled from web searches; county, report_count, links as comma-separated string)
# Counties in title case to match GeoJSON
data = {
    'county': ['Alamance', 'Alexander', 'Beaufort', 'Brunswick', 'Buncombe', 'Burke', 'Cumberland', 'Dare', 'Durham', 'Gaston', 'Guilford', 'Mecklenburg', 'New Hanover', 'Rutherford', 'Sampson', 'Wake'],
    'report_count': [1, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1, 2, 1, 3],  # Example counts
    'links': [
        'https://www.youtube.com/watch?v=iGTUmm5AydI',  # Alamance (Burlington video)
        'https://qualitycontrolinc.com/termite-control-alexander-county-nc/termite-reports/',  # Alexander
        'https://www.researchgate.net/publication/23233402',  # Beaufort (drywood mention)
        'https://www.ncagr.gov/divisions/structural-pest-control-and-pesticides/structural/consumer-information/homeowners-guide-wood-destroying-insect-report,https://pmc.ncbi.nlm.nih.gov/articles/PMC9316241/',  # Brunswick
        'https://egrove.olemiss.edu/cgi/viewcontent.cgi?article=1023&context=biology_facpubs',  # Buncombe
        'https://www.trustterminix.com/nc-termites-what-every-north-carolina-homeowner-needs-to-know/,https://egrove.olemiss.edu/cgi/viewcontent.cgi?article=1023&context=biology_facpubs',  # Burke
        'https://www.researchgate.net/publication/23233402',  # Cumberland
        'https://outerbanks-pestcontrol.com/category/termites/',  # Dare
        'https://neusetermiteandpest.com/termite-treatment-in-durham-nc',  # Durham
        'https://www.trustterminix.com/nc-termites-what-every-north-carolina-homeowner-needs-to-know/',  # Gaston
        'https://www.go-forth.com/resource-center/let-s-chat-about-termites-in-greensboro/',  # Guilford (Greensboro)
        'https://www.trustterminix.com/nc-termites-what-every-north-carolina-homeowner-needs-to-know/',  # Mecklenburg (Huntersville)
        'https://www.researchgate.net/publication/23233402',  # New Hanover
        'https://pmc.ncbi.nlm.nih.gov/articles/PMC9316241/,https://egrove.olemiss.edu/cgi/viewcontent.cgi?article=1023&context=biology_facpubs',  # Rutherford
        'https://www.researchgate.net/publication/23233402',  # Sampson
        'https://www.reddit.com/r/raleigh/comments/58ajs6/termites/,https://urbanentomology.tamu.edu/wp-content/uploads/sites/19/2018/07/Parman_and_Vargo_JEE_2008.pdf,https://content.ces.ncsu.edu/monitoring-management-of-eastern-subterranean-termites'  # Wake
    ]
}
df = pd.DataFrame(data)
df['links'] = df['links'].apply(lambda x: x.split(','))  # Convert to lists

# Load US counties GeoJSON from URL and filter for NC (STATEFP == '37')
geojson_url = 'https://gist.githubusercontent.com/sdwfrost/d1c73f91dd9d175998ed166eb216994a/raw/e89c35f308cee7e2e5a784e1d3afc5d449e9e4bb/counties.geojson'
gdf = gpd.read_file(geojson_url)
gdf = gdf[gdf['STATEFP'] == '37']  # Filter to North Carolina
gdf['county'] = gdf['NAME']  # Use the county name as is (title case)

# Merge data with GeoDataFrame
gdf = gdf.merge(df, on='county', how='left')

# Handle NaNs separately
gdf['report_count'] = gdf['report_count'].fillna(0)
gdf['links'] = [x if not pd.isnull(x) else [] for x in gdf['links']]

# Create popup HTML column
gdf['popup_html'] = gdf.apply(
    lambda row: f"<b>{row['county']}</b><br>Reports: {int(row['report_count'])}<br><ul>" + 
    "".join([f'<li><a href="{link.strip()}" target="_blank">{link.strip()}</a></li>' for link in row['links']]) + "</ul>",
    axis=1
)

# Function to search web for new reports (placeholder; enhance with API or better parsing)
def trawl_for_reports():
    global gdf
    query = "termite infestation North Carolina site:gov OR site:edu OR site:com -site:wikipedia.org"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(f"https://www.google.com/search?q={query}&num=20", headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        new_links = []
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and 'url=' in href and 'termite' in href.lower():
                # Extract actual URL from Google redirect
                actual_url = href.split('url=')[1].split('&')[0]
                new_links.append(actual_url)
                # Parse for county (simple keyword match; improve with NLP)
                for county in gdf['county'].unique():
                    if county.lower() in actual_url.lower() or county.lower() in link.text.lower():
                        # Update GDF
                        idx = gdf[gdf['county'] == county].index[0]
                        gdf.at[idx, 'report_count'] += 1
                        gdf.at[idx, 'links'].append(actual_url)
                        # Update popup_html
                        gdf.at[idx, 'popup_html'] = f"<b>{county}</b><br>Reports: {int(gdf.at[idx, 'report_count'])}<br><ul>" + \
                            "".join([f'<li><a href="{l.strip()}" target="_blank">{l.strip()}</a></li>' for l in gdf.at[idx, 'links']]) + "</ul>"
        st.write(f"Updated at {datetime.now()}: Found {len(new_links)} potential new links.")
    except Exception as e:
        st.write(f"Search error: {e}")

# Background thread for constant trawling (every 30 minutes)
def background_trawler():
    while True:
        trawl_for_reports()
        time.sleep(1800)  # 30 minutes

# Start trawler thread
if 'trawler_started' not in st.session_state:
    st.session_state['trawler_started'] = True
    thread = threading.Thread(target=background_trawler, daemon=True)
    thread.start()

# Streamlit app
st.title("NC Termite Infestation Heatmap")

# Create Folium map
m = folium.Map(location=[35.5, -79.5], zoom_start=7)  # Center on NC

# Add choropleth
folium.Choropleth(
    geo_data=gdf,
    data=gdf,
    columns=['county', 'report_count'],
    key_on='feature.properties.NAME',
    fill_color='YlOrRd',
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name='Report Count',
    nan_fill_color='white'
).add_to(m)

# Add tooltips (hover) and popups (click)
style_function = lambda x: {'fillOpacity': 0.0, 'weight': 0.1}
highlight_function = lambda x: {'fillColor': '#0000ff', 'color': '#0000ff', 'fillOpacity': 0.50, 'weight': 0.1}

folium.GeoJson(
    gdf,
    style_function=style_function,
    highlight_function=highlight_function,
    tooltip=folium.GeoJsonTooltip(
        fields=['county', 'report_count'],
        aliases=['County:', 'Reports:'],
        localize=True
    ),
    popup=folium.GeoJsonPopup(
        fields=['popup_html'],
        parse_html=True
    )
).add_to(m)

# Display map
folium_static(m, width=800, height=600)

# Auto-refresh every 60 seconds
time.sleep(60)
st.rerun()
