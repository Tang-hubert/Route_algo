# config.py

# 1. User's simulated location (Taipei Main Station)
USER_LAT = 25.0479
USER_LON = 121.5171

# 2. Routing Rules
AVG_BIKE_SPEED_KMH = 10  # Average speed for a YouBike ride
MAX_BIKE_TIME_MINS = 20  # Maximum allowed travel time from a station to an attraction

# 3. Geographic shapes for the letters "TAIPEI" over the city
# These are carefully chosen coordinates that form the letters on a map.
LETTER_SHAPES = {
    'T': [((25.05, 121.50), (25.05, 121.53)), ((25.05, 121.515), (25.03, 121.515))],
    'A': [((25.03, 121.53), (25.05, 121.54)), ((25.05, 121.54), (25.03, 121.55)), ((25.04, 121.535), (25.04, 121.545))],
    'I': [((25.03, 121.56), (25.05, 121.56))],
    'P': [((25.03, 121.57), (25.05, 121.57)), ((25.05, 121.57), (25.04, 121.58)), ((25.04, 121.58), (25.04, 121.57))],
    'E': [((25.05, 121.60), (25.03, 121.60)), ((25.05, 121.60), (25.05, 121.59)), ((25.04, 121.60), (25.04, 121.59)), ((25.03, 121.60), (25.03, 121.59))],
    'I': [((25.03, 121.61), (25.05, 121.61))]
}