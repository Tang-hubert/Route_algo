# route_generator.py
import numpy as np
import pandas as pd
import math
from scipy.interpolate import interp1d
from config import SHAPE_TEMPLATES
from utils import haversine_distance

def _normalize_coordinates(coords):
    """標準化座標到 [0, 1]"""
    coords = np.array(coords)
    min_vals = coords.min(axis=0)
    max_vals = coords.max(axis=0)
    range_vals = max_vals - min_vals
    range_vals[range_vals == 0] = 1
    return (coords - min_vals) / range_vals

def _shape_similarity(coords1, coords2):
    """計算形狀相似度"""
    norm1 = _normalize_coordinates(coords1)
    norm2 = _normalize_coordinates(coords2)
    
    n_points = max(len(norm1), len(norm2), 10)
    t1 = np.linspace(0, 1, len(norm1))
    t2 = np.linspace(0, 1, len(norm2))
    t_new = np.linspace(0, 1, n_points)
    
    if len(norm1) == 1:
        norm1_resampled = np.tile(norm1, (n_points, 1))
    else:
        interp1_x = interp1d(t1, norm1[:, 0], kind='linear', fill_value="extrapolate")
        interp1_y = interp1d(t1, norm1[:, 1], kind='linear', fill_value="extrapolate")
        norm1_resampled = np.column_stack([interp1_x(t_new), interp1_y(t_new)])

    if len(norm2) == 1:
        norm2_resampled = np.tile(norm2, (n_points, 1))
    else:
        interp2_x = interp1d(t2, norm2[:, 0], kind='linear', fill_value="extrapolate")
        interp2_y = interp1d(t2, norm2[:, 1], kind='linear', fill_value="extrapolate")
        norm2_resampled = np.column_stack([interp2_x(t_new), interp2_y(t_new)])

    distances = np.sqrt(np.sum((norm1_resampled - norm2_resampled)**2, axis=1))
    similarity = 1 - np.mean(distances)
    return max(0, similarity)

def _scale_template_to_geography(template, center_lat, center_lon, max_distance_km):
    """縮放模板到實際地理座標"""
    lat_per_km = 1 / 111
    lon_per_km = 1 / (111 * math.cos(math.radians(center_lat)))
    
    template_center = template.mean(axis=0)
    scale = max_distance_km * 1.5
    
    scaled = []
    for point in template:
        offset_y = (point[0] - template_center[0]) * scale * lat_per_km
        offset_x = (point[1] - template_center[1]) * scale * lon_per_km
        new_lat = center_lat + offset_y
        new_lon = center_lon + offset_x
        scaled.append([new_lat, new_lon])
    
    return np.array(scaled)

def _filter_youbike_by_time(youbike_df, center_lat, center_lon, max_time_min=20, speed_kmh=12):
    """篩選在騎行時間內的站點"""
    max_distance_km = (max_time_min / 60) * speed_kmh
    
    df_copy = youbike_df.copy()
    df_copy['distance_from_center'] = df_copy.apply(
        lambda row: haversine_distance(center_lat, center_lon, row['latitude'], row['longitude']),
        axis=1
    )
    filtered = df_copy[df_copy['distance_from_center'] <= max_distance_km].copy()
    print(f"   在 {max_time_min} 分鐘騎行範圍內篩選出 {len(filtered)}/{len(youbike_df)} 個站點")
    return filtered

def generate_shape_route(youbike_df, start_station, target_shape, config):
    """生成圖形路線"""
    print(f"\n🎨 正在生成 '{target_shape}' 形狀路線...")
    
    if target_shape not in SHAPE_TEMPLATES:
        print(f"⚠️ 不支援的圖形: {target_shape}")
        return None, 0
    
    template = SHAPE_TEMPLATES[target_shape]
    
    candidates = _filter_youbike_by_time(
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
    
    print(f"   符合車輛/空位數的可用站點: {len(candidates)} 個")
    
    if len(candidates) < len(template):
        print(f"⚠️ 可用站點不足以構成 '{target_shape}' 圖形，至少需要 {len(template)} 個站點。")
        return None, 0
    
    template_scaled = _scale_template_to_geography(
        template, 
        start_station['latitude'], 
        start_station['longitude'],
        config.max_segment_distance
    )
    
    # --- START: 修正邏輯 ---
    # 1. 強制將離使用者最近的站點設為路線的起點 (站點 1)
    print(f"   📍 將最近站點 '{start_station['sna']}' 設為路線起點 (站點 1)。")
    selected_stations_df = pd.DataFrame([start_station])
    used_sno = {start_station['sno']}

    # 2. 將起點從候選清單中移除，避免被重複選取
    candidates = candidates[candidates.sno != start_station['sno']].copy()
    
    # 3. 為剩下的 (N-1) 個模板點尋找匹配的站點
    num_points_needed = len(template) - 1
    
    for template_point in template_scaled:
        # 如果已經找滿了站點，或候選站點已用完，就提前結束
        if len(selected_stations_df) >= len(template) or candidates.empty:
            break
            
        candidates['dist_to_point'] = candidates.apply(
            lambda row: haversine_distance(
                template_point[0], template_point[1],
                row['latitude'], row['longitude']
            ), axis=1
        )
        
        # 找到離目前模板點最近、且尚未被使用的站點
        best_match = candidates.sort_values('dist_to_point').iloc[0]
        
        selected_stations_df = pd.concat([selected_stations_df, best_match.to_frame().T], ignore_index=True)
        used_sno.add(best_match['sno'])
        
        # 將已選中的站點從候選中移除
        candidates = candidates[candidates.sno != best_match['sno']].copy()
    # --- END: 修正邏輯 ---

    if selected_stations_df.empty:
        print("❌ 未能匹配任何站點。")
        return None, 0

    actual_coords = selected_stations_df[['latitude', 'longitude']].values
    template_coords = SHAPE_TEMPLATES[target_shape]
    similarity = _shape_similarity(actual_coords, template_coords)
    
    print(f"✅ 路線生成完成")
    print(f"   路線點數: {len(selected_stations_df)}")
    print(f"   形狀相似度: {similarity:.2%}")
    
    return selected_stations_df, similarity