# data_loader.py
import pandas as pd

def load_youbike_data_from_api(api_data):
    """
    Processes the raw JSON data from the YouBike v2 API into a clean pandas DataFrame.
    It standardizes column names for consistent use throughout the application.
    """
    if not isinstance(api_data, list):
        print("Invalid or empty API data received.")
        return pd.DataFrame()

    # Chain all pandas operations for a cleaner, more readable workflow
    df = (
        pd.DataFrame(api_data)
        # 1. Select and rename the columns we care about in one step
        .rename(columns={
            'sna': 'name',
            'latitude': 'lat',
            'longitude': 'lon',
            'available_rent_bikes': 'available_bikes'
        })
        # 2. Keep only the columns we need
        [['name', 'lat', 'lon', 'available_bikes']]
        # 3. Convert data types, create new columns, or clean data
        .assign(
            lat=lambda x: pd.to_numeric(x['lat'], errors='coerce'),
            lon=lambda x: pd.to_numeric(x['lon'], errors='coerce'),
            available_bikes=lambda x: pd.to_numeric(x['available_bikes'], errors='coerce').fillna(0).astype(int)
        )
        # 4. Drop any rows that couldn't be parsed correctly
        .dropna(subset=['lat', 'lon'])
    )
    
    print(f"✅ Processed {len(df)} YouBike stations.")
    return df


def load_attractions(csv_path):
    """
    Loads Taipei attractions data from a CSV file.
    (This function remains the same)
    """
    try:
        df = pd.read_csv(csv_path)
        df['nlat'] = pd.to_numeric(df['nlat'], errors='coerce')
        df['elong'] = pd.to_numeric(df['elong'], errors='coerce')
        df.dropna(subset=['nlat', 'elong'], inplace=True)
        return df
    except FileNotFoundError:
        print(f"Error: The file at {csv_path} was not found.")
        return pd.DataFrame()