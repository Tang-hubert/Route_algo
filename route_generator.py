# route_generator.py
import utils
import config
import pandas as pd
import math

def generate_taipei_letter_route(attractions_df, youbike_df, letter_to_draw='T', max_attractions=7):
    """
    Generates a clean, ordered route that correctly follows the drawing path
    of a single letter, then downsamples the attractions to a specified number.
    """
    letter = letter_to_draw.upper()
    segments = config.LETTER_SHAPES.get(letter)
    if not segments:
        print(f"Error: Letter '{letter}' is not defined in config.py.")
        return []

    print(f"--- Processing Letter: {letter} ---")

    # --- Step 1: Build a master list of attractions by following the strokes IN ORDER ---
    ordered_attractions_full = []
    seen_names = set()

    for segment in segments:
        (lat1, lon1), _ = segment
        nearby_attractions = utils.find_points_near_path(segment, attractions_df, threshold_km=0.35)
        
        if nearby_attractions.empty:
            continue
        
        # Sort attractions along the current stroke
        projections = []
        for _, row in nearby_attractions.iterrows():
            dist = utils.haversine_distance(lat1, lon1, row['nlat'], row['elong'])
            projections.append({'dist': dist, 'attraction': row})
        
        projections.sort(key=lambda x: x['dist'])
        
        # Add the sorted attractions from this stroke to the master list, avoiding duplicates
        for p in projections:
            attraction = p['attraction']
            if attraction['name'] not in seen_names:
                ordered_attractions_full.append(attraction)
                seen_names.add(attraction['name'])

    if not ordered_attractions_full:
        print(f"No attractions found along the path for letter {letter}.")
        return []

    # --- Step 2: Downsample the correctly ordered list to the desired number of stops ---
    if len(ordered_attractions_full) > max_attractions:
        print(f"Found {len(ordered_attractions_full)} attractions. Selecting ~{max_attractions} evenly spaced points to form the shape.")
        step = len(ordered_attractions_full) / max_attractions
        indices = [int(i * step) for i in range(max_attractions)]
        selected_attractions = [ordered_attractions_full[i] for i in indices]
    else:
        selected_attractions = ordered_attractions_full
    
    print(f"Using {len(selected_attractions)} attractions for the final route.")

    # --- Step 3: Build the final route sequence with bike stations ---
    full_route = []
    user_location = {'type': 'user', 'name': 'Your Location', 'lat': config.USER_LAT, 'lon': config.USER_LON}
    full_route.append(user_location)
    
    last_bike_station = utils.find_nearest_point(config.USER_LAT, config.USER_LON, youbike_df)
    full_route.append({'type': 'ubike', 'name': last_bike_station['name'], 'lat': last_bike_station['lat'], 'lon': last_bike_station['lon']})

    for attraction in selected_attractions:
        attraction_name = attraction['name_zh'] if pd.notna(attraction['name_zh']) else attraction['name']
        attraction_point = {'type': 'attraction', 'name': attraction_name, 'lat': attraction['nlat'], 'lon': attraction['elong']}
        
        next_bike_station = utils.find_nearest_point(attraction['nlat'], attraction['elong'], youbike_df)
        
        dist_km = utils.haversine_distance(next_bike_station['lat'], next_bike_station['lon'], attraction['nlat'], attraction['elong'])
        biking_time = utils.calculate_biking_time(dist_km, config.AVG_BIKE_SPEED_KMH)

        if biking_time <= config.MAX_BIKE_TIME_MINS:
            print(f"  - Adding '{attraction_name}' to route (Bike time: {biking_time:.1f} mins)")
            full_route.append(attraction_point)
            full_route.append({'type': 'ubike', 'name': next_bike_station['name'], 'lat': next_bike_station['lat'], 'lon': next_bike_station['lon']})
        else:
            print(f"  - Skipping '{attraction_name}' (Bike time: {biking_time:.1f} mins > {config.MAX_BIKE_TIME_MINS})")
            
    return full_route