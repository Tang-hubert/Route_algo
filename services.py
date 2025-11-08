# services.py
import requests

def fetch_youbike_data(api_url="https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"):
    """
    Fetches real-time YouBike station data from the Taipei open data v2 API.
    """
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        print("🚲 Successfully fetched YouBike v2 data.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching YouBike data: {e}")
        return None

def get_osrm_route(points):
    """
    Gets a realistic biking route from the OSRM API for a sequence of points.
    'points' should be a list of dicts with 'lat' and 'lon' keys.
    """
    if len(points) < 2:
        return None
    
    # OSRM expects coordinates as 'longitude,latitude'
    coords_str = ";".join([f"{p['lon']},{p['lat']}" for p in points])
    
    # Using the public OSRM demo server
    url = f"http://router.project-osrm.org/route/v1/bike/{coords_str}?geometries=geojson"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if data['code'] == 'Ok' and data['routes']:
            # OSRM returns [lon, lat], but Folium needs [lat, lon], so we swap them.
            route_geometry = [[coord[1], coord[0]] for coord in data['routes'][0]['geometry']['coordinates']]
            print(f"  -> Successfully fetched OSRM route of length {len(route_geometry)} points.")
            return route_geometry
    except requests.exceptions.RequestException as e:
        print(f"  -> OSRM API error: {e}")
        return None
    
    return None