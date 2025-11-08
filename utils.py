# utils.py
import math
import pandas as pd

def haversine_distance(lat1, lon1, lat2, lon2):
    """計算地球表面距離（公里）"""
    R = 6371
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def find_nearest_youbike(user_lat, user_lon, youbike_df, min_bikes=3):
    """找最近的 YouBike 站點"""
    print(f"\n🔍 正在尋找最近的 YouBike 站點...")
    print(f"   您的位置: ({user_lat:.4f}, {user_lon:.4f})")
    
    available_stations = youbike_df[youbike_df['available_rent_bikes'] >= min_bikes].copy()
    if len(available_stations) == 0:
        print("⚠️ 找不到符合最低車輛數的站點，將使用所有站點進行搜尋。")
        available_stations = youbike_df.copy()
    
    available_stations['distance'] = available_stations.apply(
        lambda row: haversine_distance(user_lat, user_lon, row['latitude'], row['longitude']),
        axis=1
    )
    
    nearest = available_stations.nsmallest(1, 'distance').iloc[0]
    print(f"✅ 最近站點: {nearest['sna']}")
    print(f"   距離: {nearest['distance']*1000:.0f} 公尺")
    print(f"   可借車輛: {nearest['available_rent_bikes']} 輛")
    
    return nearest

def find_nearby_attractions(lat, lon, attractions_df, radius_meters=300):
    """找附近景點"""
    if attractions_df.empty:
        return []
        
    nearby = []
    for _, attraction in attractions_df.iterrows():
        distance = haversine_distance(lat, lon, attraction['nlat'], attraction['elong']) * 1000
        if distance <= radius_meters:
            nearby.append({
                'name': attraction.get('name', '未知景點'),
                'address': attraction.get('address', '無地址'),
                'distance': distance,
                'lat': attraction['nlat'],
                'lon': attraction['elong']
            })
    
    nearby.sort(key=lambda x: x['distance'])
    return nearby