# main.py
import data_loader
import route_generator
import map_creator
import services
import config

def main():
    # --- CONFIGURATION ---
    # 1. Choose the letter to draw ('T', 'A', 'I', 'P', 'E')
    LETTER_TO_DRAW = 'T'
    
    # 2. Set the desired number of attraction stops for the route
    MAX_ATTRACTIONS = 6  # <-- This is the new control variable (5-8 is a good range)

    # 3. Your attractions CSV path
    TAIPEI_ATTRACTIONS_CSV = r'.\taipei_attractions.csv' # !!! UPDATE THIS PATH !!!


    # --- 1. Load All Necessary Data ---
    print("Loading data...")
    attractions_df = data_loader.load_attractions(TAIPEI_ATTRACTIONS_CSV)
    
    youbike_api_data = services.fetch_youbike_data()
    all_youbike_stations_df = data_loader.load_youbike_data_from_api(youbike_api_data)

    if attractions_df.empty or all_youbike_stations_df.empty:
        print("Exiting: Could not load required attraction or YouBike data.")
        return
        
    active_youbike_df = all_youbike_stations_df[all_youbike_stations_df['available_bikes'] > 0].copy()

    # --- 2. Generate the Creative Route ---
    print(f"\nGenerating route for the letter '{LETTER_TO_DRAW}' with a max of {MAX_ATTRACTIONS} stops...")
    final_route = route_generator.generate_taipei_letter_route(
        attractions_df, 
        active_youbike_df, 
        LETTER_TO_DRAW,
        MAX_ATTRACTIONS  # <-- Pass the new variable to the function
    )

    if not final_route or len(final_route) <= 2:
        print(f"Exiting: Route generation for letter '{LETTER_TO_DRAW}' failed or found no valid points.")
        return
        
    print("\n--- Final Route Sequence ---")
    for i, point in enumerate(final_route):
        print(f"{i}. [{point['type'].upper()}] {point['name']}")

    # --- 3. Create the Map ---
    output_filename = f'taipei_letter_route_{LETTER_TO_DRAW}.html'
    map_creator.create_letter_route_map(final_route, output_path=output_filename)

if __name__ == '__main__':
    main()