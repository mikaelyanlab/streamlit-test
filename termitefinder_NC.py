import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import geopandas as gpd
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import random
import re
import branca.colormap as cm
# List of User-Agents for rotation to avoid blocking
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.864.48 Safari/537.36 Edg/91.0.864.48',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1'
]
# Known termite species for extraction (expanded to include more genera and species)
known_species = [
    'eastern subterranean', 'formosan', 'west indian drywood',
    'dark southern subterranean', 'light southern subterranean', 'southeastern drywood',
    'reticulitermes flavipes', 'reticulitermes virginicus', 'reticulitermes hageni',
    'reticulitermes malletei', 'reticulitermes nelsonae',
    'coptotermes formosanus', 'formosan subterranean termite',
    'cryptotermes brevis', 'west indian powderpost termite',
    'incisitermes snyderi', 'incisitermes minor', 'eastern drywood termite',
    'kalotermes approximatus', 'dampwood termite', 'neotermes castaneus'
]
# Load US counties GeoJSON from URL and filter for NC (STATEFP == '37')
geojson_url = 'https://gist.githubusercontent.com/sdwfrost/d1c73f91dd9d175998ed166eb216994a/raw/e89c35f308cee7e2e5a784e1d3afc5d449e9e4bb/counties.geojson'
if 'gdf' not in st.session_state:
    gdf = gpd.read_file(geojson_url)
    gdf = gdf[gdf['STATEFP'] == '37'] # Filter to North Carolina
    gdf['county'] = gdf['NAME'] # Use the county name as is (title case)
    gdf['report_count'] = 0
    gdf['reports'] = [[] for _ in range(len(gdf))]
    gdf['species_summary'] = 'None'
    gdf['popup_html'] = gdf.apply(lambda row: f"<b>{row['county']}</b><br>Reports: 0<br><ul></ul>", axis=1)
    st.session_state.gdf = gdf
else:
    gdf = st.session_state.gdf
# Create popup HTML column
def generate_popup_html(row):
    html = f"<b>{row['county']}</b><br>Reports: {int(row['report_count'])}<br><ul>"
    for report in row['reports']:
        html += f"<li><a href='{report['link']}' target='_blank'>{report['link']}</a> ({report['species']})</li>"
    html += "</ul>"
    return html
# Dictionary of cities to counties (lowercase, partial list of major municipalities)
city_to_counties = {
    'aberdeen': ['moore'],
    'ahoskie': ['hertford'],
    'alamance': ['alamance'],
    'albemarle': ['stanly'],
    'albertson': ['duplin'],
    'alliance': ['pamlico'],
    'andrews': ['cherokee'],
    'angier': ['harnett', 'wake'],
    'ansonville': ['anson'],
    'apex': ['wake'],
    'arapahoe': ['pamlico'],
    'archdale': ['randolph'],
    'archer lodge': ['johnston'],
    'asheboro': ['randolph'],
    'asheville': ['buncombe'],
    'askewville': ['bertie'],
    'atkinson': ['pender'],
    'atlantic beach': ['carteret'],
    'aulander': ['bertie'],
    'aurora': ['beaufort'],
    'autryville': ['sampson'],
    'ayden': ['pitt'],
    'badin': ['stanly'],
    'bailey': ['nash'],
    'bakersville': ['mitchell'],
    'bald head island': ['brunswick'],
    'banner elk': ['avery'],
    'bath': ['beaufort'],
    'bayboro': ['pamlico'],
    'bear grass': ['martin'],
    'beaufort': ['carteret'],
    'beech mountain': ['watauga'],
    'belhaven': ['beaufort'],
    'belmont': ['gaston'],
    'belville': ['brunswick'],
    'belwood': ['cleveland'],
    'benson': ['johnston'],
    'bermuda run': ['davie'],
    'bessemer city': ['gaston'],
    'bethania': ['forsyth'],
    'bethel': ['pitt'],
    'beulaville': ['duplin'],
    'biltmore forest': ['buncombe'],
    'biscoe': ['montgomery'],
    'black creek': ['wilson'],
    'black mountain': ['buncombe'],
    'bladenboro': ['bladen'],
    'blowing rock': ['watauga'],
    'boardman': ['columbus'],
    'bogue': ['carteret'],
    'boiling spring lakes': ['brunswick'],
    'boiling springs': ['cleveland'],
    'bolivia': ['brunswick'],
    'bolton': ['columbus'],
    'boone': ['watauga'],
    'boonville': ['yadkin'],
    'bostic': ['rutherford'],
    'brevard': ['transylvania'],
    'bridgeton': ['craven'],
    'broadway': ['harnett', 'lee'],
    'brookford': ['catawba'],
    'brunswick': ['columbus'],
    'bryson city': ['swain'],
    'bunn': ['franklin'],
    'burgaw': ['pender'],
    'burlington': ['alamance'],
    'burnsville': ['yancey'],
    'butner': ['granville'],
    "cajah's mountain": ['caldwell'],
    'calabash': ['brunswick'],
    'calypso': ['duplin'],
    'cameron': ['moore'],
    'candor': ['montgomery'],
    'canton': ['haywood'],
    'cape carteret': ['carteret'],
    'carolina beach': ['new hanover'],
    'carolina shores': ['brunswick'],
    'carrboro': ['orange'],
    'carthage': ['moore'],
    'cary': ['wake', 'chatham'],
    'casar': ['cleveland'],
    'cashiers': ['jackson'],
    'castalia': ['nash'],
    'caswell beach': ['brunswick'],
    'catawba': ['catawba'],
    'cedar point': ['carteret'],
    'cedar rock': ['caldwell'],
    'centerville': ['franklin'],
    'cerro gordo': ['columbus'],
    'chadbourn': ['columbus'],
    'chapel hill': ['orange', 'durham'],
    'charlotte': ['mecklenburg'],
    'cherryville': ['gaston'],
    'china grove': ['rowan'],
    'chocowinity': ['beaufort'],
    'claremont': ['catawba'],
    'clarkton': ['bladen'],
    'clayton': ['johnston', 'wake'],
    'clemmons': ['forsyth'],
    'cleveland': ['rowan'],
    'clinton': ['sampson'],
    'clyde': ['haywood'],
    'coats': ['harnett'],
    'cofield': ['hertford'],
    'colerain': ['bertie'],
    'columbia': ['tyrrell'],
    'columbus': ['polk'],
    'como': ['hertford'],
    'concord': ['cabarrus'],
    'conetoe': ['edgecombe'],
    'connelly springs': ['burke'],
    'conover': ['catawba'],
    'conway': ['northampton'],
    'cooleemee': ['davie'],
    'cornelius': ['mecklenburg'],
    'cove city': ['craven'],
    'cramerton': ['gaston'],
    'creedmoor': ['granville'],
    'creswell': ['washington'],
    'crossnore': ['avery'],
    'dallas': ['gaston'],
    'danbury': ['stokes'],
    'davidson': ['mecklenburg'],
    'denton': ['davidson'],
    'denver': ['lincoln'],
    'dillsboro': ['jackson'],
    'dobson': ['surry'],
    'dortches': ['nash'],
    'dover': ['craven'],
    'drexel': ['burke'],
    'dublin': ['bladen'],
    'duck': ['dare'],
    'dunn': ['harnett'],
    'durham': ['durham', 'wake', 'orange'],
    'earl': ['cleveland'],
    'east arcadia': ['bladen'],
    'east bend': ['yadkin'],
    'east laurinburg': ['scotland'],
    'east spencer': ['rowan'],
    'eastover': ['cumberland'],
    'eden': ['rockingham'],
    'edenton': ['chowan'],
    'elizabeth city': ['pasquotank', 'camden'],
    'elizabethtown': ['bladen'],
    'elkin': ['surry', 'wilkes'],
    'elk park': ['avery'],
    'ellenboro': ['rutherford'],
    'ellerbe': ['richmond'],
    'elm city': ['wilson'],
    'elon': ['alamance'],
    'emerald isle': ['carteret'],
    'enfield': ['halifax'],
    'erwin': ['harnett'],
    'eureka': ['wayne'],
    'everetts': ['martin'],
    'fair bluff': ['columbus'],
    'fairmont': ['robeson'],
    'fairview': ['buncombe'],
    'faison': ['duplin'],
    'faith': ['rowan'],
    'falcon': ['cumberland', 'sampson'],
    'falkland': ['pitt'],
    'fallston': ['cleveland'],
    'farmville': ['pitt'],
    'fayetteville': ['cumberland'],
    'flat rock': ['henderson'],
    'fletcher': ['henderson'],
    'forest city': ['rutherford'],
    'forest hills': ['jackson'],
    'fountain': ['pitt'],
    'four oaks': ['johnston'],
    'foxfire': ['moore'],
    'franklin': ['macon'],
    'franklinton': ['franklin'],
    'franklinville': ['randolph'],
    'fremont': ['wayne'],
    'fuquay-varina': ['wake'],
    'garland': ['sampson'],
    'garner': ['wake'],
    'garysburg': ['northampton'],
    'gaston': ['northampton'],
    'gastonia': ['gaston'],
    'gatesville': ['gates'],
    'gibson': ['scotland'],
    'gibsonville': ['alamance', 'guilford'],
    'glen alpine': ['burke'],
    'godwin': ['cumberland'],
    'goldston': ['chatham'],
    'goldsboro': ['wayne'],
    'graham': ['alamance'],
    'granite falls': ['caldwell'],
    'granite quarry': ['rowan'],
    'green level': ['alamance'],
    'greenevers': ['duplin'],
    'greensboro': ['guilford'],
    'greenville': ['pitt'],
    'grifton': ['pitt'],
    'grimesland': ['pitt'],
    'grover': ['cleveland'],
    'halifax': ['halifax'],
    'hamilton': ['martin'],
    'hamlet': ['richmond'],
    'harkers island': ['carteret'],
    'harmony': ['iredell'],
    'harrells': ['sampson'],
    'harrellsville': ['hertford'],
    'harrisburg': ['cabarrus'],
    'hassell': ['martin'],
    'havelock': ['craven'],
    'haw river': ['alamance'],
    'hayesville': ['clay'],
    'hays': ['wilkes'],
    'henderson': ['vance'],
    'hendersonville': ['henderson'],
    'hertford': ['perquimans'],
    'hickory': ['catawba', 'burke', 'caldwell'],
    'high point': ['guilford', 'randolph', 'davidson', 'forsyth'],
    'high shoals': ['gaston'],
    'highlands': ['macon'],
    'hillsborough': ['orange'],
    'hobgood': ['halifax'],
    'hoffman': ['richmond'],
    'holden beach': ['brunswick'],
    'holly ridge': ['onslow'],
    'holly springs': ['wake'],
    'hookerton': ['greene'],
    'hope mills': ['cumberland'],
    'hot springs': ['madison'],
    'hudson': ['caldwell'],
    'huntersville': ['mecklenburg'],
    'indian beach': ['carteret'],
    'indian trail': ['union'],
    'jackson': ['northampton'],
    'jackson heights': ['lenoir'],
    'jacksonville': ['onslow'],
    'jamestown': ['guilford'],
    'jamesville': ['martin'],
    'jefferson': ['ashe'],
    'jonesville': ['yadkin'],
    'kannapolis': ['cabarrus', 'rowan'],
    'kenansville': ['duplin'],
    'kenly': ['johnston', 'wilson'],
    'kernersville': ['forsyth', 'guilford'],
    'kill devil hills': ['dare'],
    'king': ['stokes'],
    'kings mountain': ['cleveland', 'gaston'],
    'kinston': ['lenoir'],
    'kitty hawk': ['dare'],
    'knightdale': ['wake'],
    'kure beach': ['new hanover'],
    'la grange': ['lenoir'],
    'lake lure': ['rutherford'],
    'lake park': ['union'],
    'lake santeetlah': ['graham'],
    'lake waccamaw': ['columbus'],
    'landis': ['rowan'],
    'lansing': ['ashe'],
    'lattice': ['iredell'],
    'laurel park': ['henderson'],
    'laurinburg': ['scotland'],
    'lawndale': ['cleveland'],
    'leggett': ['edgecombe'],
    'leland': ['brunswick'],
    'lenoir': ['caldwell'],
    'lewiston woodville': ['bertie'],
    'lewisville': ['forsyth'],
    'lexington': ['davidson'],
    'liberty': ['randolph'],
    'lilesville': ['anson'],
    'lillington': ['harnett'],
    'lincolnton': ['lincoln'],
    'linden': ['cumberland'],
    'littleton': ['halifax'],
    'locust': ['stanly'],
    'long view': ['burke', 'catawba'],
    'louisburg': ['franklin'],
    'love valley': ['iredell'],
    'lowell': ['gaston'],
    'lucama': ['wilson'],
    'lumber bridge': ['robeson'],
    'lumberton': ['robeson'],
    'macclesfield': ['edgecombe'],
    'macon': ['warren'],
    'madison': ['rockingham'],
    'maggie valley': ['haywood'],
    'magnolia': ['duplin'],
    'maiden': ['catawba', 'lincoln'],
    'manteo': ['dare'],
    'marietta': ['robeson'],
    'marion': ['mcdowell'],
    'mars hill': ['madison'],
    'marshville': ['union'],
    'marvin': ['union'],
    'matthews': ['mecklenburg'],
    'maxton': ['robeson'],
    'mayodan': ['rockingham'],
    'maysville': ['jones'],
    'mcadenville': ['gaston'],
    'mcdonald': ['robeson'],
    'mcfarlan': ['anson'],
    'mebane': ['alamance', 'orange'],
    'mesic': ['pamlico'],
    'micro': ['johnston'],
    'middleburg': ['vance'],
    'middlesex': ['nash'],
    'midland': ['cabarrus'],
    'midway': ['davidson'],
    'mills river': ['henderson'],
    'milton': ['caswell'],
    'mineral springs': ['union'],
    'minnesott beach': ['pamlico'],
    'mint hill': ['mecklenburg', 'union'],
    'misenheimer': ['stanly'],
    'mocksville': ['davie'],
    'momeyer': ['nash'],
    'monroe': ['union'],
    'montreat': ['buncombe'],
    'mooresboro': ['cleveland'],
    'mooresville': ['iredell'],
    'morehead city': ['carteret'],
    'morganton': ['burke'],
    'morrisville': ['wake', 'durham'],
    'morven': ['anson'],
    'mount airy': ['surry'],
    'mount gilead': ['montgomery'],
    'mount holly': ['gaston'],
    'mount olive': ['wayne', 'duplin'],
    'mount pleasant': ['cabarrus'],
    'murphy': ['cherokee'],
    'murraysville': ['new hanover'],
    'myrtle grove': ['new hanover'],
    'nags head': ['dare'],
    'nashville': ['nash'],
    'navassa': ['brunswick'],
    'new bern': ['craven'],
    'new london': ['stanly'],
    'newland': ['avery'],
    'newport': ['carteret'],
    'newton': ['catawba'],
    'newton grove': ['sampson'],
    'norlina': ['warren'],
    'norman': ['richmond'],
    'north topsail beach': ['onslow'],
    'north wilkesboro': ['wilkes'],
    'northlakes': ['caldwell'],
    'norwood': ['stanly'],
    'oak city': ['martin'],
    'oak island': ['brunswick'],
    'oak ridge': ['guilford'],
    'oakboro': ['stanly'],
    'ocean isle beach': ['brunswick'],
    'ogden': ['new hanover'],
    'old fort': ['mcdowell'],
    'oriental': ['pamlico'],
    'orrum': ['robeson'],
    'ossipee': ['alamance'],
    'oxford': ['granville'],
    'pantego': ['beaufort'],
    'parkton': ['robeson'],
    'parmele': ['martin'],
    'patterson springs': ['cleveland'],
    'peachland': ['anson'],
    'peletier': ['carteret'],
    'pembroke': ['robeson'],
    'pikeville': ['wayne'],
    'pilot mountain': ['surry'],
    'pine knoll shores': ['carteret'],
    'pine level': ['johnston'],
    'pinebluff': ['moore'],
    'pinehurst': ['moore'],
    'pinetops': ['edgecombe'],
    'pineville': ['mecklenburg'],
    'pink hill': ['lenoir'],
    'pittsboro': ['chatham'],
    'pleasant garden': ['guilford'],
    'plymouth': ['washington'],
    'polkton': ['anson'],
    'pollocksville': ['jones'],
    'powellsville': ['bertie'],
    'princeville': ['edgecombe'],
    'princeton': ['johnston'],
    'proctorville': ['robeson'],
    'raeford': ['hoke'],
    'ramseur': ['randolph'],
    'randleman': ['randolph'],
    'ranlo': ['gaston'],
    'raynham': ['robeson'],
    'red oak': ['nash'],
    'red springs': ['robeson'],
    'reidsville': ['rockingham'],
    'rennert': ['robeson'],
    'rhandle': ['union'],
    'rich square': ['northampton'],
    'richfield': ['stanly'],
    'richlands': ['onslow'],
    'river bend': ['craven'],
    'roanoke rapids': ['halifax'],
    'robbins': ['moore'],
    'robbinsville': ['graham'],
    'robersonville': ['martin'],
    'rockingham': ['richmond'],
    'rockwell': ['rowan'],
    'rocky mount': ['edgecombe', 'nash'],
    'rolesville': ['wake'],
    'ronda': ['wilkes'],
    'ronda': ['wilkes'],  # duplicate? 
    'rose hill': ['duplin'],
    'roseboro': ['sampson'],
    'rosman': ['transylvania'],
    'rowland': ['robeson'],
    'roxboro': ['person'],
    'roxobel': ['bertie'],
    'ruffin': ['rockingham'],
    'rural hall': ['forsyth'],
    'ruth': ['rutherford'],
    'rutherford college': ['burke'],
    'rutherfordton': ['rutherford'],
    'salem': ['burke'],
    'salemburg': ['sampson'],
    'salisbury': ['rowan'],
    'saluda': ['polk'],
    'sanford': ['lee'],
    'saratoga': ['wilson'],
    'sawmills': ['caldwell'],
    'scotland neck': ['halifax'],
    'seaboard': ['northampton'],
    'seagrove': ['randolph'],
    'sedalia': ['guilford'],
    'selma': ['johnston'],
    'seven devils': ['watauga'],
    'seven springs': ['wayne'],
    'severn': ['northampton'],
    'shallotte': ['brunswick'],
    'sharpsburg': ['nash'],
    'shelby': ['cleveland'],
    'siler city': ['chatham'],
    'silver city': ['hoke'],
    'simpson': ['pitt'],
    'sims': ['wilson'],
    'sky valley': ['jackson'],
    'smithfield': ['johnston'],
    'sneads ferry': ['onslow'],
    'snow hill': ['greene'],
    'southern pines': ['moore'],
    'southern shores': ['dare'],
    'southport': ['brunswick'],
    'sparta': ['alleghany'],
    'spencer': ['rowan'],
    'spencer mountain': ['gaston'],
    'spindale': ['rutherford'],
    'spring hope': ['nash'],
    'spring lake': ['cumberland'],
    'spruce pine': ['mitchell'],
    'st. helena': ['pender'],
    'st. james': ['brunswick'],
    'st. pauls': ['robeson'],
    'stallings': ['union'],
    'stanfield': ['stanly'],
    'stanley': ['gaston'],
    'stantonsburg': ['wilson'],
    'star': ['montgomery'],
    'statesville': ['iredell'],
    'stedman': ['cumberland'],
    'stem': ['granville'],
    'stokesdale': ['guilford'],
    'stoneville': ['rockingham'],
    'stonewall': ['pamlico'],
    'stovall': ['granville'],
    'sugar mountain': ['avery'],
    'summerfield': ['guilford'],
    'sunset beach': ['brunswick'],
    'surf city': ['pender'],
    'swansboro': ['onslow'],
    'swepsonville': ['alamance'],
    'sylva': ['jackson'],
    'tabor city': ['columbus'],
    'tar heel': ['bladen'],
    'tarboro': ['edgecombe'],
    'taylorsville': ['alexander'],
    'taylortown': ['moore'],
    'teachey': ['duplin'],
    'thomasville': ['davidson', 'randolph'],
    'tobaccoville': ['forsyth'],
    'topsail beach': ['pender'],
    'trent woods': ['craven'],
    'trenton': ['jones'],
    'trinity': ['randolph'],
    'troutman': ['iredell'],
    'troy': ['montgomery'],
    'tryon': ['polk'],
    'turkey': ['sampson'],
    'unionville': ['union'],
    'valdese': ['burke'],
    'vanceboro': ['craven'],
    'vandemere': ['pamlico'],
    'vass': ['moore'],
    'vienna': ['forsyth'],
    'waco': ['cleveland'],
    'wade': ['cumberland'],
    'wadesboro': ['anson'],
    'wagram': ['scotland'],
    'wake forest': ['wake', 'franklin'],
    'wakulla': ['robeson'],
    'walkertown': ['forsyth'],
    'wallace': ['duplin'],
    'walnut cove': ['stokes'],
    'walnut creek': ['wayne'],
    'walstonburg': ['greene'],
    'warrenton': ['warren'],
    'warsaw': ['duplin'],
    'washington': ['beaufort'],
    'washington park': ['beaufort'],
    'watha': ['pender'],
    'waxhaw': ['union'],
    'waynesville': ['haywood'],
    'weaverville': ['buncombe'],
    'webster': ['jackson'],
    'weddington': ['union'],
    'wendell': ['wake'],
    'wentworth': ['rockingham'],
    'wesley chapel': ['union'],
    'west jefferson': ['ashe'],
    'westport': ['lincoln'],
    'whispering pines': ['moore'],
    'white lake': ['bladen'],
    'white oak': ['bladen'],
    'whiteville': ['columbus'],
    'whitakers': ['edgecombe', 'nash'],
    'whitsett': ['guilford'],
    'wilkesboro': ['wilkes'],
    'williamston': ['martin'],
    'wilmington': ['new hanover'],
    'wilson': ['wilson'],
    'windsor': ['bertie'],
    'winfall': ['perquimans'],
    'wingate': ['union'],
    'winston-salem': ['forsyth'],
    'winterville': ['pitt'],
    'winton': ['hertford'],
    'woodland': ['northampton'],
    'woodlawn': ['alamance'],
    'woodville': ['bertie'],
    'wrightsville beach': ['new hanover'],
    'yadkinville': ['yadkin'],
    'yanceyville': ['caswell'],
    'youngsville': ['franklin'],
    'zebulon': ['wake']
}
# Function to search web for new reports and extract species using Bing with rotation and delay
def trawl_for_reports():
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    st.session_state.logs.append(f"Starting trawl at {datetime.now()}")
    query = "termite infestation North Carolina pest control site:gov OR site:edu OR site:com -site:wikipedia.org -site:reddit.com -site:fandom.com -site:steamcommunity.com -site:ign.com -site:thegamer.com -site:gamerant.com -site:screenrant.com -game -grounded -waft -emitter -\"termite king\" -GroundedGame -\"grounded game\""
    headers = {'User-Agent': random.choice(user_agents)}
    try:
        response = requests.get(f"https://www.bing.com/search?q={requests.utils.quote(query)}&count=50", headers=headers)
        st.session_state.logs.append(f"Response Status: {response.status_code}")
        st.session_state.logs.append(f"Response Length: {len(response.text)}")
        st.session_state.logs.append(f"Response Preview: {response.text[:500]}...")
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('li', class_='b_algo')
        st.session_state.logs.append(f"Found {len(results)} raw 'b_algo' elements")
        new_links = []
        for result in results:
            time.sleep(1) # Delay to avoid rate limiting
            h2 = result.find('h2')
            if h2:
                link_tag = h2.find('a')
                if link_tag:
                    actual_url = link_tag['href']
                    if any(actual_url in r['link'] for reports in gdf['reports'] for r in reports):
                        st.session_state.logs.append(f"Skipping duplicate link: {actual_url}")
                        continue
                    new_links.append(actual_url)
                    st.session_state.logs.append(f"Found link: {actual_url}")
                    snippet_tag = result.find('p')
                    snippet = snippet_tag.text.lower() if snippet_tag else ''
                    title = h2.text.lower()
                    st.session_state.logs.append(f"Title for {actual_url}: {title}")
                    st.session_state.logs.append(f"Snippet for {actual_url}: {snippet}")
                    found_species = [s for s in known_species if s in snippet or s in title]
                    species_str = ', '.join(found_species) if found_species else 'Unknown'
                    county_matched = False
                    for county in gdf['county'].unique():
                        county_lower = county.lower()
                        if (re.search(r'\b' + re.escape(county_lower) + r'\b', actual_url.lower()) or
                            re.search(r'\b' + re.escape(county_lower) + r'\b', title) or
                            re.search(r'\b' + re.escape(county_lower) + r'\b', snippet)):
                            match = gdf[gdf['county'] == county]
                            if not match.empty:
                                idx = match.index[0]
                                gdf.at[idx, 'report_count'] += 1
                                gdf.at[idx, 'reports'].append({'link': actual_url, 'species': species_str})
                                all_species = set()
                                for r in gdf.at[idx, 'reports']:
                                    if r['species'] != 'Unknown':
                                        all_species.update([s.strip() for s in r['species'].split(',')])
                                gdf.at[idx, 'species_summary'] = ', '.join(sorted(all_species)) if all_species else 'None'
                                gdf.at[idx, 'popup_html'] = generate_popup_html(gdf.loc[idx])
                                st.session_state.logs.append(f"Added report to {county}: {actual_url} (Species: {species_str})")
                                county_matched = True
                    if not county_matched:
                        city_matched = False
                        for city, counties in city_to_counties.items():
                            if (re.search(r'\b' + re.escape(city) + r'\b', actual_url.lower()) or
                                re.search(r'\b' + re.escape(city) + r'\b', title) or
                                re.search(r'\b' + re.escape(city) + r'\b', snippet)):
                                for county_lower in counties:
                                    match = gdf[gdf['county'].str.lower() == county_lower]
                                    if not match.empty:
                                        idx = match.index[0]
                                        gdf.at[idx, 'report_count'] += 1
                                        gdf.at[idx, 'reports'].append({'link': actual_url, 'species': species_str})
                                        all_species = set()
                                        for r in gdf.at[idx, 'reports']:
                                            if r['species'] != 'Unknown':
                                                all_species.update([s.strip() for s in r['species'].split(',')])
                                        gdf.at[idx, 'species_summary'] = ', '.join(sorted(all_species)) if all_species else 'None'
                                        gdf.at[idx, 'popup_html'] = generate_popup_html(gdf.loc[idx])
                                        st.session_state.logs.append(f"Added report to {county_lower.capitalize()} via city {city}: {actual_url} (Species: {species_str})")
                                        city_matched = True
                        if not city_matched:
                            st.session_state.logs.append(f"No county or city matched for {actual_url}")
        st.session_state.logs.append(f"Finished trawl at {datetime.now()}: Found {len(new_links)} potential new links.")
        st.session_state.gdf = gdf # Save updates back to session_state
    except Exception as e:
        st.session_state.logs.append(f"Search error at {datetime.now()}: {e}")
# Sidebar for trawling status (enhanced console)
st.sidebar.title("Trawling Console (Debug Logs)")
if 'logs' not in st.session_state:
    st.session_state.logs = []
for log in st.session_state.logs[-20:]: # Show last 20 logs for more detail
    st.sidebar.write(log)
# Manual trawl button
if st.sidebar.button("Manual Trawl Now"):
    trawl_for_reports()
# Streamlit app
st.title("NC Termite Infestation Heatmap")
# Create Folium map
m = folium.Map(location=[35.5, -79.5], zoom_start=7) # Center on NC
# Compute max report count, ensure scale starts at 0 and goes to at least 1 to avoid legend artifacts
max_count = gdf['report_count'].max()
colormap = cm.linear.YlOrRd_09.scale(0, max(1, max_count))
colormap.caption = 'Report Count'
colormap.add_to(m)
# Add tooltips (hover) and popups (click) with colored fill
style_function = lambda feature: {
    'fillColor': colormap(feature['properties']['report_count']) if 'report_count' in feature['properties'] else 'white',
    'color': 'black',
    'weight': 0.2,
    'fillOpacity': 0.7
}
highlight_function = lambda x: {'fillColor': '#0000ff', 'color': '#0000ff', 'fillOpacity': 0.50, 'weight': 0.1}
folium.GeoJson(
    gdf,
    style_function=style_function,
    highlight_function=highlight_function,
    tooltip=folium.GeoJsonTooltip(
        fields=['county', 'report_count', 'species_summary'],
        aliases=['County:', 'Reports:', 'Species:'],
        localize=True
    ),
    popup=folium.GeoJsonPopup(
        fields=['popup_html'],
        parse_html=True
    )
).add_to(m)
# Display map
st_folium(m, width=800, height=600, returned_objects=[])
# Auto-refresh every 60 seconds
time.sleep(60)
st.rerun()
