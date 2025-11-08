# map_creator.py
import folium
import services

def create_letter_route_map(route, output_path='taipei_letter_route.html'):
    """
    Creates a clean map with a single, unified OSRM route and no background shapes.
    """
    if not route:
        print("Cannot create map. The generated route is empty.")
        return

    # Center the map on the user's starting location
    start_lat, start_lon = route[0]['lat'], route[0]['lon']
    m = folium.Map(location=[start_lat, start_lon], zoom_start=13)

    # --- The gray background letter shapes have been removed as requested. ---

    # --- Draw a single, unified OSRM route for the entire journey ---
    print("\nFetching a single, continuous road route from OSRM...")
    
    # Pass the entire list of points to the OSRM service at once
    osrm_path = services.get_osrm_route(route)
    
    if osrm_path:
        # Draw the full path with one, consistent color
        folium.PolyLine(
            osrm_path,
            color="#3388ff",  # A standard "leaflet blue" color
            weight=5,
            opacity=0.8
        ).add_to(m)
    else:
        # This is a fallback in case the OSRM service is down
        print("Could not fetch the OSRM route. Drawing straight lines as a fallback.")
        route_coords = [(point['lat'], point['lon']) for point in route]
        folium.PolyLine(route_coords, color="red", weight=3, opacity=0.8, dash_array='5, 10').add_to(m)

    # --- Add markers for each point in the route (this logic is unchanged) ---
    for i, point in enumerate(route):
        color_map = {'user': 'red', 'ubike': 'orange', 'attraction': 'green'}
        folium.Marker(
            location=(point['lat'], point['lon']),
            popup=f"<b>{i}. {point['name']}</b><br>({point['type']})",
            icon=folium.Icon(color=color_map.get(point['type'], 'blue'), icon='info-sign')
        ).add_to(m)
        
    m.save(output_path)
    print(f"\nMap has been saved to {output_path}")