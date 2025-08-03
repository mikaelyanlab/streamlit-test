#######################################################################################################################
# Created by Aram Mikaelyan (amikael@ncsu.edu), Department of Entomology and Plant Pathology, NCSU (mikaelyanlab.com) #
#######################################################################################################################
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import geopandas as gpd
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

# ------------------------------
# Species aliases
# ------------------------------
species_aliases = {
    "Reticulitermes flavipes": ["reticulitermes flavipes", "eastern subterranean termite", "r. flavipes"],
    "Reticulitermes virginicus": ["reticulitermes virginicus", "virginian subterranean termite", "r. virginicus"],
    "Reticulitermes hageni": ["reticulitermes hageni", "hagen's subterranean termite", "r. hageni"],
    "Reticulitermes malletei": ["reticulitermes malletei", "malletei subterranean termite", "r. malletei"],
    "Reticulitermes nelsonae": ["reticulitermes nelsonae", "nelsonae subterranean termite", "r. nelsonae"],
    "Coptotermes formosanus": ["coptotermes formosanus", "formosan termite", "formosan subterranean termite"],
    "Cryptotermes brevis": ["cryptotermes brevis", "west indian drywood termite", "powderpost termite", "drywood termite"],
    "Incisitermes minor": ["incisitermes minor", "western drywood termite", "drywood termite"],
    "Incisitermes snyderi": ["incisitermes snyderi", "eastern drywood termite", "drywood termite"],
    "Kalotermes approximatus": ["kalotermes approximatus", "dampwood termite"],
    "Neotermes castaneus": ["neotermes castaneus", "neotermes", "castaneus termite"]
}

# ------------------------------
# City-to-county mapping
# ------------------------------
city_to_county = {
    "wilmington": "New Hanover",
    "fayetteville": "Cumberland",
    "charlotte": "Mecklenburg",
    "raleigh": "Wake",
    "durham": "Durham",
    "asheville": "Buncombe",
    "jacksonville": "Onslow",
    "greensboro": "Guilford",
    "cary": "Wake",
    "chapel hill": "Orange",
    "hendersonville": "Henderson",
    "morehead city": "Carteret",
    "new bern": "Craven"
}

# ------------------------------
# Species detection
# ------------------------------
def detect_species(text):
    text_lower = text.lower()
    text_norm = text_lower.replace("termites", "termite")  # normalize plural

    found = []
    for sci_name, aliases in species_aliases.items():
        if any(alias.lower() in text_norm for alias in aliases):
            found.append(sci_name)

    # Generic fallback cases
    if "drywood termite" in text_norm and not any(
        "cryptotermes" in s.lower() or "incisitermes" in s.lower() for s in found
    ):
        return ["Drywood termite (Genus/species unknown)"]

    if "subterranean termite" in text_norm and not any(
        "reticulitermes" in s.lower() or "coptotermes" in s.lower() for s in found
    ):
        return ["Subterranean termite (Genus/species unknown)"]

    if not found and "termite" in text_norm:
        return ["Termite (Genus/species unknown)"]

    return found if found else ["Unknown"]

# ------------------------------
# Updated fetch_species_from_page
# ------------------------------
def fetch_species_from_page(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        page = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(page.text, "html.parser")

        # Extract only visible text from <p> and heading tags
        text_parts = [
            t.get_text(separator=" ", strip=True)
            for t in soup.find_all(["p", "h1", "h2", "h3", "h4"])
        ]
        text = " ".join(text_parts)
        return detect_species(text)
    except:
        return ["Unknown"]

# ------------------------------
# County detection
# ------------------------------
def find_county(text, url):
    text_lower = (text + " " + url).lower()
    for county in st.session_state.gdf["county"]:
        if county.lower() in text_lower:
            return county
    for city, county in city_to_county.items():
        if city in text_lower:
            return county
    return None

# ------------------------------
# GeoJSON loader
# ------------------------------
@st.cache_data
def load_geojson():
    url = "https://gist.githubusercontent.com/sdwfrost/d1c73f91dd9d175998ed166eb216994a/raw/e89c35f308cee7e2e5a784e1d3afc5d449e9e4bb/counties.geojson"
    gdf = gpd.read_file(url)
    gdf = gdf[gdf["STATEFP"] == "37"]
    gdf["county"] = gdf["NAME"]
    return gdf

# ------------------------------
# Popup & summary
# ------------------------------
def generate_popup_html(row):
    html = f"<b>{row['county']}</b><br>Reports: {int(row['report_count'])}<br><ul>"
    for report in row["reports"]:
        html += f"<li><a href='{report['link']}' target='_blank'>{report['link']}</a> ({report['species']})</li>"
    html += "</ul>"
    return html

def update_species_summary(df):
    df["species_summary"] = df["reports"].apply(
        lambda r: ", ".join(sorted(set(x["species"] for x in r if x["species"] not in [None, "Unknown"]))) if r else "None"
    )
    df["popup_html"] = df.apply(generate_popup_html, axis=1)
    return df

# ------------------------------
# Species updater
# ------------------------------
def update_species_for_all_reports(df):
    for idx, reports in df["reports"].items():
        updated_reports = []
        for r in reports:
            if not r.get("species") or r["species"] in [None, "Unknown"]:
                r["species"] = ", ".join(fetch_species_from_page(r["link"]))
            updated_reports.append(r)
        df.at[idx, "reports"] = updated_reports
    return update_species_summary(df)

# ------------------------------
# Web trawler
# ------------------------------
def trawl_for_reports():
    st.session_state.logs.append(f"Trawl started at {datetime.now()}")
    query = "termite infestation North Carolina site:gov OR site:edu OR site:com -site:wikipedia.org"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        r = requests.get(f"https://www.bing.com/search?q={requests.utils.quote(query)}&count=20", headers=headers)
        soup = BeautifulSoup(r.text, "html.parser")
        results = soup.find_all("li", class_="b_algo")

        new_links = 0
        for result in results:
            h2 = result.find("h2")
            if not h2 or not h2.find("a"):
                continue

            url = h2.find("a")["href"]
            snippet = (result.find("p").text if result.find("p") else "") + " " + h2.text

            county_match = find_county(snippet, url)
            if county_match:
                idx = st.session_state.gdf[st.session_state.gdf["county"] == county_match].index[0]
                st.session_state.gdf.at[idx, "report_count"] += 1
                st.session_state.gdf.at[idx, "reports"].append({"link": url, "species": None})
                new_links += 1

        st.session_state.gdf = update_species_for_all_reports(st.session_state.gdf)
        st.session_state.logs.append(f"Trawl finished at {datetime.now()} – {new_links} new links added.")
        st.session_state.last_trawl = datetime.now()

    except Exception as e:
        st.session_state.logs.append(f"Error during trawl: {e}")

# ------------------------------
# Initial sample data
# ------------------------------
initial_data = {
    "county": ["Alamance", "Alexander", "Beaufort", "Brunswick", "Buncombe", "Burke", "Cumberland", "Dare", "Durham", "Gaston", "Guilford", "Mecklenburg", "New Hanover", "Rutherford", "Sampson", "Wake"],
    "report_count": [1, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1, 2, 1, 3],
    "reports": [
        [{"link": "https://www.youtube.com/watch?v=iGTUmm5AydI", "species": None}],
        [{"link": "https://qualitycontrolinc.com/termite-control-alexander-county-nc/termite-reports/", "species": None}],
        [{"link": "https://www.researchgate.net/publication/23233402", "species": None}],
        [{"link": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9316241/", "species": None}],
        [{"link": "https://egrove.olemiss.edu/cgi/viewcontent.cgi?article=1023&context=biology_facpubs", "species": None}],
        [{"link": "https://www.trustterminix.com/nc-termites-what-every-north-carolina-homeowner-needs-to-know/", "species": None}],
        [{"link": "https://www.researchgate.net/publication/23233402", "species": None}],
        [{"link": "https://outerbanks-pestcontrol.com/category/termites/", "species": None}],
        [{"link": "https://neusetermiteandpest.com/termite-treatment-in-durham-nc", "species": None}],
        [{"link": "https://www.trustterminix.com/nc-termites-what-every-north-carolina-homeowner-needs-to-know/", "species": None}],
        [{"link": "https://www.go-forth.com/resource-center/let-s-chat-about-termites-in-greensboro/", "species": None}],
        [{"link": "https://www.trustterminix.com/nc-termites-what-every-north-carolina-homeowner-needs-to-know/", "species": None}],
        [{"link": "https://www.researchgate.net/publication/23233402", "species": None}],
        [{"link": "https://pmc.ncbi.nlm.nih.gov/articles/PMC9316241/", "species": None}],
        [{"link": "https://www.researchgate.net/publication/23233402", "species": None}],
        [{"link": "https://www.reddit.com/r/raleigh/comments/58ajs6/termites/", "species": None}]
    ]
}

# ------------------------------
# Session state initialization
# ------------------------------
if "logs" not in st.session_state:
    st.session_state.logs = []

if "gdf" not in st.session_state:
    gdf_base = load_geojson()
    df_init = pd.DataFrame(initial_data)
    gdf_merged = gdf_base.merge(df_init, on="county", how="left")
    gdf_merged["report_count"] = gdf_merged["report_count"].fillna(0)
    gdf_merged["reports"] = gdf_merged["reports"].apply(lambda x: x if isinstance(x, list) else [])
    st.session_state.gdf = update_species_for_all_reports(gdf_merged)

if "last_trawl" not in st.session_state:
    st.session_state.last_trawl = datetime.min

# ------------------------------
# Sidebar
# ------------------------------
st.sidebar.title("Trawling Console")
if st.sidebar.button("Manual Trawl Now"):
    trawl_for_reports()

st.sidebar.write(f"Last trawl: {st.session_state.last_trawl}")
for log in st.session_state.logs[-20:]:
    st.sidebar.write(log)

# Auto-trawl every 24h
if datetime.now() - st.session_state.last_trawl > timedelta(hours=24):
    trawl_for_reports()

# Optional: Change refresh frequency (e.g., 600 = 10 minutes)
st.markdown("<meta http-equiv='refresh' content='600'>", unsafe_allow_html=True)

# ------------------------------
# Map Display
# ------------------------------
st.title("NC Termite Infestation Heatmap")
m = folium.Map(location=[35.5, -79.5], zoom_start=7)

folium.Choropleth(
    geo_data=st.session_state.gdf,
    data=st.session_state.gdf,
    columns=["county", "report_count"],
    key_on="feature.properties.NAME",
    fill_color="YlOrRd",
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name="Report Count",
    nan_fill_color="white"
).add_to(m)

folium.GeoJson(
    st.session_state.gdf,
    style_function=lambda x: {"fillOpacity": 0.0, "weight": 0.1},
    highlight_function=lambda x: {"fillColor": "#0000ff", "color": "#0000ff", "fillOpacity": 0.5, "weight": 0.1},
    tooltip=folium.GeoJsonTooltip(fields=["county", "report_count", "species_summary"],
                                  aliases=["County:", "Reports:", "Species:"],
                                  localize=True),
    popup=folium.GeoJsonPopup(fields=["popup_html"], parse_html=True)
).add_to(m)

st_folium(m, width=800, height=600, returned_objects=[])

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Created by [Mikaelyan Lab](https://mikaelyanlab.com)**  \n"
    "Digest. Cooperate. Decompose."
)
