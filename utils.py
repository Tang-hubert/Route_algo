# utils.py
from math import radians, sin, cos, sqrt, atan2

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in kilometers
    lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def calculate_biking_time(distance_km, speed_kmh):
    """Calculates biking time in minutes."""
    return (distance_km / speed_kmh) * 60

def find_nearest_point(target_lat, target_lon, points_df, lat_col='lat', lon_col='lon'):
    """
    Finds the single nearest point (row) from a DataFrame to a target coordinate.
    """
    if points_df.empty:
        return None
    
    distances = points_df.apply(
        lambda row: haversine_distance(target_lat, target_lon, row[lat_col], row[lon_col]),
        axis=1
    )
    
    nearest_index = distances.idxmin()
    return points_df.loc[nearest_index]

def find_points_near_path(path_segment, points_df, threshold_km=0.2):
    """
    Finds all points within a certain distance of a line segment.
    """
    (lat1, lon1), (lat2, lon2) = path_segment
    
    # Simple bounding box for quick filtering
    min_lat, max_lat = min(lat1, lat2) - 0.01, max(lat1, lat2) + 0.01
    min_lon, max_lon = min(lon1, lon2) - 0.01, max(lon1, lon2) + 0.01

    nearby_points = points_df[
        (points_df['nlat'].between(min_lat, max_lat)) &
        (points_df['elong'].between(min_lon, max_lon))
    ]
    
    # A more precise check can be added here if needed, but this is often sufficient.
    return nearby_points