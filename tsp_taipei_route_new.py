"""
台北市圖形路線規劃系統 (Shape-Based Route Planner)
---------------------------------
以 YouBike 站點為主軸，規劃指定圖形（S、U、T等）的騎行路線
整合附近景點，考慮騎行時間限制（20分鐘/段）

核心功能：
1. 自動定位起始點（最近的 YouBike 站）
2. 以 YouBike 站點為主要路線節點
3. 每段騎行時間 ≤ 20 分鐘
4. 路線形狀符合指定字母/數字（S、U、T、8、O等）
5. 附近景點推薦

Author: Shape Route Planner
Date: 2025-11-08
"""

import requests
import pandas as pd
import folium
from folium import plugins
import webbrowser
import os
from time import sleep
import numpy as np
import math
import json
import argparse
from scipy.interpolate import interp1d
import geocoder

# ===================================================================
# 配置參數類別
# ===================================================================
class RouteConfig:
    """路線規劃配置參數"""
    def __init__(self):
        # 使用者位置（固定位置：臺大新體育館附近）
        self.user_location = {'lat': 25.021777051200228, 'lon': 121.5354050968437}
        
        # 路線形狀
        self.target_shape = 'S'
        
        # 時間與距離限制
        self.max_segment_time = 20  # 分鐘
        self.max_segment_distance = 3.0  # 公里 
        self.cycling_speed = 10  # km/h
        
        # YouBike 站點篩選
        self.min_available_bikes = 3
        self.min_available_spaces = 2
        
        # 景點篩選
        self.attraction_radius = 100  # 公尺
        # self.max_attractions_per_stop = 3
        
        # # 圖形匹配
        # self.num_waypoints = 6
        
        # # 輸出設定
        # self.output_html = "taipei_shape_route_6.html"

        # print(f"{config.min_available_bikes}，幹")
        

# NOTE: Coordinates are normalized (0..1). Each letter is a single-stroke polyline.
# Focus: readable shapes, minimal nodes, reasonable stroke order, low backtracking.

SHAPE_TEMPLATES = {
    # T — top bar -> vertical stem
    'T': np.array([
        [0.10, 0.95], [0.90, 0.95],      # top bar (left->right)
        [0.50, 0.95], [0.50, 0.05]       # center down
    ]),
    'Ｔ': np.array([
        [0.10, 0.95], [0.90, 0.95],
        [0.50, 0.95], [0.50, 0.05]
    ]),

    # A — up left leg -> apex -> down right leg -> crossbar (left->right), slight backtrack minimized
    'A': np.array([
        [0.20, 0.05], [0.40, 0.60], [0.50, 0.95],  # left leg up to apex
        [0.60, 0.60], [0.80, 0.05],                # right leg down
        [0.32, 0.52], [0.68, 0.52]                 # crossbar (left -> right)
    ]),
    'Ａ': np.array([
        [0.20, 0.05], [0.40, 0.60], [0.50, 0.95],
        [0.60, 0.60], [0.80, 0.05],
        [0.32, 0.52], [0.68, 0.52]
    ]),

    # I — top cap -> stem -> bottom cap
    'I': np.array([
        [0.30, 0.95], [0.70, 0.95],      # top cap
        [0.50, 0.95], [0.50, 0.05],      # stem
        [0.30, 0.05], [0.70, 0.05]       # bottom cap
    ]),
    'Ｉ': np.array([
        [0.30, 0.95], [0.70, 0.95],
        [0.50, 0.95], [0.50, 0.05],
        [0.30, 0.05], [0.70, 0.05]
    ]),

    # P — left stem down -> round the bowl -> close at mid stem (no full loop; single stroke)
    # 注意：第一維是 Y（上下），第二維是 X（左右）
    'P': np.array([
        [0.05, 0.22], [0.95, 0.22],              # stem up (bottom to top)
        [0.95, 0.55], [0.86, 0.72], [0.72, 0.78],# outer top-right curve
        [0.61, 0.70], [0.55, 0.54],              # curve downward
        [0.55, 0.22]                              # close on mid stem
    ]),
    'Ｐ': np.array([
        [0.05, 0.22], [0.95, 0.22],
        [0.95, 0.55], [0.86, 0.72], [0.72, 0.78],
        [0.61, 0.70], [0.55, 0.54],
        [0.55, 0.22]
    ]),

    # E — top (right->left) -> down to mid -> mid (left->right) -> down -> bottom (left->right)
    # Drawn to minimize backtracking yet keep single stroke logic clear.
    'E': np.array([
        [0.85, 0.95], [0.20, 0.95],      # top bar (right->left for better next turn)
        [0.20, 0.65],                    # down to mid
        [0.55, 0.65], [0.20, 0.65],      # mid bar (left->right->left to stay single-stroke)
        [0.20, 0.35], [0.20, 0.05],      # down to bottom
        [0.85, 0.05]                     # bottom bar (left->right)
    ]),
    'Ｅ': np.array([
        [0.85, 0.95], [0.20, 0.95],
        [0.20, 0.65],
        [0.55, 0.65], [0.20, 0.65],
        [0.20, 0.35], [0.20, 0.05],
        [0.85, 0.05]
    ]),

    # Keep your original ones for other cases
    'S': np.array([[0.8, 0.9], [0.6, 1.0], [0.3, 0.9], [0.2, 0.7],
                   [0.3, 0.5], [0.5, 0.4], [0.7, 0.3], [0.8, 0.1], [0.6, 0.0]]),
    'U': np.array([[0.2, 1.0], [0.2, 0.6], [0.2, 0.2], [0.5, 0.0],
                   [0.8, 0.2], [0.8, 0.6], [0.8, 1.0]]),
    'O': np.array([[0.5, 1.0], [0.8, 0.9], [1.0, 0.5], [0.8, 0.1],
                   [0.5, 0.0], [0.2, 0.1], [0.0, 0.5], [0.2, 0.9], [0.5, 1.0]]),
    'L': np.array([[0.2, 1.0], [0.2, 0.7], [0.2, 0.4], [0.2, 0.1], [0.2, 0.0],
                   [0.4, 0.0], [0.6, 0.0], [0.8, 0.0]]),
}

# ===================================================================
# 資料抓取函數
# ===================================================================
def get_user_location_auto():
    """自動獲取使用者位置（使用固定位置 - 臺大新體育館附近）"""
    print("📍 使用固定位置（臺大新體育館附近）...")
    # 固定位置：臺大新體育館東南側附近
    lat, lon = 25.021777051200228, 121.5354050968437
    print(f"✅ 位置: ({lat:.4f}, {lon:.4f})")
    print(f"   地址: 臺大新體育館附近")
    return {'lat': lat, 'lon': lon, 'address': '臺大新體育館附近'}

def fetch_youbike_data():
    """抓取 YouBike 2.0 即時資料"""
    print("🚲 正在抓取 YouBike 即時資料...")
    url = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"
    data = requests.get(url).json()
    df = pd.DataFrame(data)
    df = df[['sno', 'sna', 'sarea', 'latitude', 'longitude', 'available_rent_bikes', 'available_return_bikes']]
    
    # 確保資料型態正確
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df['available_rent_bikes'] = pd.to_numeric(df['available_rent_bikes'], errors='coerce').fillna(0).astype(int)
    df['available_return_bikes'] = pd.to_numeric(df['available_return_bikes'], errors='coerce').fillna(0).astype(int)
    
    # 移除無效的座標
    df = df.dropna(subset=['latitude', 'longitude'])
    
    print(f"✅ 獲取 {len(df)} 個 YouBike 站點")
    return df

def fetch_attractions_from_csv():
    """從本地 CSV 讀取景點資料"""
    print("🏛️ 正在讀取台北景點資料...")
    try:
        df = pd.read_csv("taipei_attractions.csv")
        df = df[pd.notna(df['nlat']) & pd.notna(df['elong'])]
        print(f"✅ 讀取 {len(df)} 個景點")
        return df
    except FileNotFoundError:
        print("❌ 找不到 taipei_attractions.csv")
        return pd.DataFrame()

# ===================================================================
# 位置與距離計算
# ===================================================================
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
    print(f"\n🔍 尋找最近的 YouBike 站點...")
    print(f"   使用者位置: ({user_lat:.4f}, {user_lon:.4f})")
    
    available_stations = youbike_df[youbike_df['available_rent_bikes'] >= min_bikes].copy()
    if len(available_stations) == 0:
        available_stations = youbike_df.copy()
    
    available_stations['distance'] = available_stations.apply(
        lambda row: haversine_distance(user_lat, user_lon, row['latitude'], row['longitude']),
        axis=1
    )
    
    nearest = available_stations.nsmallest(1, 'distance').iloc[0]
    print(f"✅ 找到: {nearest['sna']}")
    print(f"   距離: {nearest['distance']*1000:.0f} 公尺")
    print(f"   可借: {nearest['available_rent_bikes']} 輛")
    
    return nearest

def calculate_ride_time(distance_km, speed_kmh=12):
    """計算騎行時間（分鐘）"""
    return (distance_km / speed_kmh) * 60

def filter_youbike_by_time(youbike_df, center_lat, center_lon, max_time_min=20, speed_kmh=12):
    """篩選在騎行時間內的站點"""
    max_distance_km = (max_time_min / 60) * speed_kmh
    
    youbike_df = youbike_df.copy()
    youbike_df['distance_from_center'] = youbike_df.apply(
        lambda row: haversine_distance(center_lat, center_lon, row['latitude'], row['longitude']),
        axis=1
    )
    
    youbike_df['ride_time'] = youbike_df['distance_from_center'].apply(
        lambda d: calculate_ride_time(d, speed_kmh)
    )
    
    filtered = youbike_df[youbike_df['ride_time'] <= max_time_min].copy()
    print(f"   篩選結果: {len(filtered)}/{len(youbike_df)} 個站點")
    
    return filtered

def find_nearby_attractions(lat, lon, attractions_df, radius_meters=300):
    """找附近景點"""
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

# ===================================================================
# 圖形匹配與路線生成
# ===================================================================
def normalize_coordinates(coords):
    """標準化座標到 [0, 1]"""
    coords = np.array(coords)
    min_vals = coords.min(axis=0)
    max_vals = coords.max(axis=0)
    range_vals = max_vals - min_vals
    range_vals[range_vals == 0] = 1
    normalized = (coords - min_vals) / range_vals
    return normalized

def shape_similarity(coords1, coords2):
    """計算形狀相似度"""
    norm1 = normalize_coordinates(coords1)
    norm2 = normalize_coordinates(coords2)
    
    if len(norm1) != len(norm2):
        n_points = max(len(norm1), len(norm2))
        t1 = np.linspace(0, 1, len(norm1))
        t2 = np.linspace(0, 1, len(norm2))
        t_new = np.linspace(0, 1, n_points)
        
        interp1_x = interp1d(t1, norm1[:, 0], kind='linear')
        interp1_y = interp1d(t1, norm1[:, 1], kind='linear')
        interp2_x = interp1d(t2, norm2[:, 0], kind='linear')
        interp2_y = interp1d(t2, norm2[:, 1], kind='linear')
        
        norm1 = np.column_stack([interp1_x(t_new), interp1_y(t_new)])
        norm2 = np.column_stack([interp2_x(t_new), interp2_y(t_new)])
    
    distances = np.sqrt(np.sum((norm1 - norm2)**2, axis=1))
    similarity = 1 - np.mean(distances)
    return max(0, similarity)

def scale_template_to_geography(template, center_lat, center_lon, max_distance_km):
    """縮放模板到實際地理座標"""
    lat_per_km = 1 / 111
    lon_per_km = 1 / (111 * math.cos(math.radians(center_lat)))
    
    template_center = template.mean(axis=0)
    scale = max_distance_km * 2
    
    scaled = []
    for point in template:
        offset_y = (point[0] - template_center[0]) * scale * lat_per_km
        offset_x = (point[1] - template_center[1]) * scale * lon_per_km
        new_lat = center_lat + offset_y
        new_lon = center_lon + offset_x
        scaled.append([new_lat, new_lon])
    
    return np.array(scaled)

def generate_shape_route(youbike_df, start_station, target_shape, config):
    """生成圖形路線"""
    print(f"\n🎨 生成 '{target_shape}' 形狀路線...")
    
    if target_shape not in SHAPE_TEMPLATES:
        print(f"⚠️ 不支援的圖形: {target_shape}")
        return None, 0
    
    template = SHAPE_TEMPLATES[target_shape]
    
    # 篩選可用站點
    candidates = filter_youbike_by_time(
        youbike_df, 
        start_station['latitude'], 
        start_station['longitude'],
        config.max_segment_time,
        config.cycling_speed
    )
    
    candidates = candidates[
        (candidates['available_rent_bikes'] >= config.min_available_bikes) &
        (candidates['available_return_bikes'] >= config.min_available_spaces)
    ].copy()
    
    print(f"   可用站點: {len(candidates)} 個")
    
    if len(candidates) < 4:
        print(f"⚠️ 可用站點不足")
        return None, 0
    
    # 縮放模板
    template_scaled = scale_template_to_geography(
        template, 
        start_station['latitude'], 
        start_station['longitude'],
        config.max_segment_distance
    )
    
    # 為每個模板點找最近的站點
    selected_stations = []
    used_indices = set()
    
    # 首先加入起始站點（確保從使用者附近開始）
    start_idx = None
    for idx in candidates.index:
        if (candidates.loc[idx]['sno'] == start_station['sno']):
            selected_stations.append(candidates.loc[idx])
            used_indices.add(idx)
            start_idx = idx
            print(f"   ✅ 起始站點: {start_station['sna']}")
            break
    
    # 如果起始站點不在候選列表中，找最近的候選站點作為起始點
    if start_idx is None:
        distances_from_start = candidates.apply(
            lambda row: haversine_distance(
                start_station['latitude'], start_station['longitude'],
                row['latitude'], row['longitude']
            ),
            axis=1
        )
        start_idx = distances_from_start.idxmin()
        selected_stations.append(candidates.loc[start_idx])
        used_indices.add(start_idx)
        print(f"   ✅ 起始站點（替代）: {candidates.loc[start_idx]['sna']}")
    
    for template_point in template_scaled:
        distances = candidates.apply(
            lambda row: haversine_distance(
                template_point[0], template_point[1],
                row['latitude'], row['longitude']
            ),
            axis=1
        )
        
        for idx in distances.nsmallest(10).index:
            if idx not in used_indices:
                selected_stations.append(candidates.loc[idx])
                used_indices.add(idx)
                break
    
    route_df = pd.DataFrame(selected_stations)
    
    # 計算相似度
    actual_coords = route_df[['latitude', 'longitude']].values
    similarity = shape_similarity(actual_coords, template)
    
    print(f"✅ 路線生成完成")
    print(f"   路線點數: {len(route_df)}")
    print(f"   形狀相似度: {similarity:.2%}")
    
    return route_df, similarity

# ===================================================================
# OSRM 路線計算
# ===================================================================
def get_osrm_route(route_df):
    """使用 OSRM 計算實際路線"""
    print("\n🗺️  使用 OSRM 計算實際路線...")
    
    coords_str = ";".join([f"{row['longitude']},{row['latitude']}" for _, row in route_df.iterrows()])
    osrm_url = f"http://router.project-osrm.org/route/v1/cycling/{coords_str}?overview=full&geometries=geojson"
    
    try:
        response = requests.get(osrm_url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 'Ok':
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
        return {'success': False}
    except Exception as e:
        print(f"⚠️ OSRM 錯誤: {e}")
        return {'success': False}

# ===================================================================
# 地圖繪製
# ===================================================================
def create_shape_route_map(route_df, attractions_dict, osrm_result, config, similarity):
    """創建圖形路線地圖"""
    
    # 地圖中心
    center_lat = route_df['latitude'].mean()
    center_lon = route_df['longitude'].mean()
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14, tiles='OpenStreetMap')
    
    # 繪製路線
    if osrm_result and osrm_result['success']:
        route_coords = osrm_result['coords']
        popup_text = f"距離: {osrm_result['distance']:.2f} km\n時間: {osrm_result['duration']:.1f} 分"
        line_color = 'darkblue'
    else:
        route_coords = [(row['latitude'], row['longitude']) for _, row in route_df.iterrows()]
        popup_text = f"路線圖形: {config.target_shape}"
        line_color = 'blue'
    
    folium.PolyLine(route_coords, color=line_color, weight=4, opacity=0.7, popup=popup_text).add_to(m)
    
    # 添加 YouBike 站點標記
    for idx, (_, station) in enumerate(route_df.iterrows(), 1):
        color = 'green' if station['available_rent_bikes'] >= 10 else 'orange'
        
        popup_html = f"""
        <div style="width: 220px;">
            <h4 style="color: {color};">🚲 站點 {idx}: {station['sna']}</h4>
            <hr>
            <b>可借車輛：</b>{station['available_rent_bikes']} 輛<br>
            <b>可還空位：</b>{station['available_return_bikes']} 位
        """
        
        # 添加附近景點
        if idx in attractions_dict:
            popup_html += "<hr><b>附近景點：</b><br>"
            for attr in attractions_dict[idx][:3]:
                popup_html += f"📍 {attr['name']} ({attr['distance']:.0f}m)<br>"
        
        popup_html += "</div>"
        
        folium.Marker(
            location=[station['latitude'], station['longitude']],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"站點 {idx}",
            icon=folium.Icon(color=color, icon='bicycle', prefix='fa')
        ).add_to(m)
        
        # 添加編號
        folium.Marker(
            location=[station['latitude'], station['longitude']],
            icon=folium.DivIcon(html=f"""
                <div style="font-size: 14px; font-weight: bold; color: white; 
                     background-color: {color}; border-radius: 50%; 
                     width: 25px; height: 25px; display: flex; 
                     align-items: center; justify-content: center; 
                     border: 2px solid white;">{idx}</div>
            """)
        ).add_to(m)
    
    # 圖例
    if osrm_result and osrm_result['success']:
        legend_html = f'''
        <div style="position: fixed; bottom: 50px; right: 50px; width: 280px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px; border-radius: 5px;">
            <h4 style="margin-top:0;">🗺️ {config.target_shape} 形路線</h4>
            <p><span style="color: darkblue;">━━</span> OSRM 實際路線</p>
            <p><span style="color: green;">🚲</span> YouBike 站點</p>
            <hr>
            <p><b>實際距離：</b>{osrm_result['distance']:.2f} 公里</p>
            <p><b>預估時間：</b>{osrm_result['duration']:.1f} 分鐘</p>
            <p><b>停靠點數：</b>{len(route_df)} 個</p>
            <p><b>形狀相似度：</b>{similarity:.1%}</p>
        </div>
        '''
    else:
        legend_html = f'''
        <div style="position: fixed; bottom: 50px; right: 50px; width: 250px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px; border-radius: 5px;">
            <h4 style="margin-top:0;">🗺️ {config.target_shape} 形路線</h4>
            <p><span style="color: blue;">━━</span> 規劃路線</p>
            <p><span style="color: green;">🚲</span> YouBike 站點</p>
            <hr>
            <p><b>停靠點數：</b>{len(route_df)} 個</p>
            <p><b>形狀相似度：</b>{similarity:.1%}</p>
        </div>
        '''
    
    m.get_root().html.add_child(folium.Element(legend_html))
    
    plugins.Fullscreen(position='topright', title='全螢幕', title_cancel='退出全螢幕').add_to(m)
    
    m.save(config.output_html)
    print(f"\n✅ 地圖已生成：{config.output_html}")
    
    webbrowser.open('file://' + os.path.realpath(config.output_html))
    print("🌐 已在瀏覽器開啟")

# ===================================================================
# 主程式
# ===================================================================
def main():
    # 解析命令列參數
    parser = argparse.ArgumentParser(description='台北市圖形路線規劃系統')
    parser.add_argument('--shape', type=str, default='S', help='目標圖形 (S/U/T/O/L)')
    parser.add_argument('--lat', type=float, default=None, help='使用者緯度（不指定則自動定位）')
    parser.add_argument('--lon', type=float, default=None, help='使用者經度（不指定則自動定位）')
    parser.add_argument('--max-time', type=int, default=20, help='每段最大騎行時間（分鐘）')
    parser.add_argument('--output', type=str, default='taipei_shape_route.html', help='輸出檔案')
    parser.add_argument('--auto-location', action='store_true', help='自動獲取當前位置')
    
    args = parser.parse_args()
    
    # 設定配置
    config = RouteConfig()
    config.target_shape = args.shape.upper()
    config.max_segment_time = args.max_time
    config.output_html = args.output
    
    # 判斷使用者位置
    if args.auto_location or (args.lat is None and args.lon is None):
        # 自動定位
        location = get_user_location_auto()
        config.user_location = {'lat': location['lat'], 'lon': location['lon']}
    elif args.lat is not None and args.lon is not None:
        # 使用指定座標
        config.user_location = {'lat': args.lat, 'lon': args.lon}
    else:
        # 使用預設值（臺大新體育館附近）
        config.user_location = {'lat': 25.021777051200228, 'lon': 121.5354050968437}
    
    print("=" * 70)
    print(f"  台北市圖形路線規劃系統 - {config.target_shape} 形路線")
    print("=" * 70)
    print()
    
    try:
        # 1. 抓取資料
        youbike_df = fetch_youbike_data()
        attractions_df = fetch_attractions_from_csv()
        
        # 2. 找最近的 YouBike 站點作為起點
        start_station = find_nearest_youbike(
            config.user_location['lat'],
            config.user_location['lon'],
            youbike_df,
            config.min_available_bikes
        )
        
        # 3. 生成圖形路線
        route_df, similarity = generate_shape_route(
            youbike_df,
            start_station,
            config.target_shape,
            config
        )
        
        if route_df is None:
            print("❌ 路線生成失敗")
            return
        
        # 4. 為每個站點找附近景點
        print("\n🏛️  尋找附近景點...")
        attractions_dict = {}
        for idx, (_, station) in enumerate(route_df.iterrows(), 1):
            nearby = find_nearby_attractions(
                station['latitude'],
                station['longitude'],
                attractions_df,
                config.attraction_radius
            )
            if nearby:
                attractions_dict[idx] = nearby
                print(f"   站點 {idx}: 找到 {len(nearby)} 個景點")
        
        # 5. 使用 OSRM 計算實際路線
        osrm_result = get_osrm_route(route_df)
        
        # 6. 繪製地圖
        print()
        create_shape_route_map(route_df, attractions_dict, osrm_result, config, similarity)
        
        # 7. 輸出路線摘要
        print("\n" + "=" * 70)
        print("🗺️  路線摘要")
        print("=" * 70)
        for idx, (_, station) in enumerate(route_df.iterrows(), 1):
            ride_time = calculate_ride_time(
                haversine_distance(
                    start_station['latitude'], start_station['longitude'],
                    station['latitude'], station['longitude']
                )
            )
            print(f"{idx}. 🚲 {station['sna']} ({station['available_rent_bikes']}輛) - {ride_time:.1f}分鐘")
            if idx in attractions_dict and attractions_dict[idx]:
                for attr in attractions_dict[idx][:2]:
                    print(f"     📍 {attr['name']} ({attr['distance']:.0f}m)")
        print("=" * 70)
        
        print("\n🎉 完成！")
        print(f"💡 圖形: {config.target_shape}")
        print(f"💡 相似度: {similarity:.1%}")
        if osrm_result and osrm_result['success']:
            print(f"💡 總距離: {osrm_result['distance']:.2f} 公里")
            print(f"💡 預估時間: {osrm_result['duration']:.1f} 分鐘")
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
