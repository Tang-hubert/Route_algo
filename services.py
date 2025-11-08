# services.py
import requests

def get_osrm_route(route_df):
    """使用 OSRM 計算實際路線"""
    print("\n🗺️  使用 OSRM 計算實際路線...")
    
    if route_df.empty:
        return {'success': False, 'message': 'Route dataframe is empty.'}

    coords_str = ";".join([f"{row['longitude']},{row['latitude']}" for _, row in route_df.iterrows()])
    osrm_url = f"http://router.project-osrm.org/route/v1/cycling/{coords_str}?overview=full&geometries=geojson"
    
    try:
        response = requests.get(osrm_url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 'Ok' and data.get('routes'):
                route_data = data['routes'][0]
                route_geometry = route_data['geometry']['coordinates']
                route_coords = [(coord[1], coord[0]) for coord in route_geometry]
                distance_km = route_data['distance'] / 1000
                duration_min = route_data['duration'] / 60
                
                print(f"✅ OSRM 成功")
                print(f"   實際距離: {distance_km:.2f} 公里")
                print(f"   預估時間: {duration_min:.1f} 分鐘")
                
                return {
                    'coords': route_coords,
                    'distance': distance_km,
                    'duration': duration_min,
                    'success': True
                }
        print(f"⚠️ OSRM API 回應不正確: {response.status_code} - {response.text}")
        return {'success': False}
    except Exception as e:
        print(f"⚠️ OSRM 錯誤: {e}")
        return {'success': False}
