# main.py
import argparse
import traceback

# 從各模組導入函式和類別
from config import RouteConfig
from data_loader import fetch_youbike_data, fetch_attractions_from_csv, get_user_location_auto
from utils import find_nearest_youbike, find_nearby_attractions
from route_generator import generate_shape_route
from services import get_osrm_route
from map_creator import create_shape_route_map

def main():
    parser = argparse.ArgumentParser(description='台北市圖形路線規劃系統')
    parser.add_argument('--shape', type=str, default='T', help='目標圖形 (T/P/E/A/I)')
    parser.add_argument('--lat', type=float, default=None, help='手動指定緯度')
    parser.add_argument('--lon', type=float, default=None, help='手動指定經度')
    parser.add_argument('--max-time', type=int, default=20, help='單段最大騎行時間（分鐘）')
    parser.add_argument('--output', type=str, default='taipei_shape_route.html', help='輸出地圖檔名')
    # 新增 --auto-location 選項
    parser.add_argument('--auto-location', action='store_true', help='自動偵測目前位置')
    
    args = parser.parse_args()
    
    config = RouteConfig()
    config.target_shape = args.shape.upper()
    config.max_segment_time = args.max_time
    config.output_html = args.output
    
    # 更新位置決策邏輯
    if args.auto_location:
        location = get_user_location_auto()
        config.user_location = {'lat': location['lat'], 'lon': location['lon']}
    elif args.lat is not None and args.lon is not None:
        print(f"📍 使用您手動指定的座標: ({args.lat}, {args.lon})")
        config.user_location = {'lat': args.lat, 'lon': args.lon}
    else:
        print("📍 未指定位置，使用設定檔中的預設位置（臺大新體育館附近）。")
        # 此處會使用 config.py 中已定義的預設值
    
    print("=" * 70)
    print(f"  台北市圖形路線規劃系統 - 開始規劃 '{config.target_shape}' 形路線")
    print("=" * 70)
    
    try:
        youbike_df = fetch_youbike_data()
        attractions_df = fetch_attractions_from_csv()
        
        # [項目 D] 增強穩健性：檢查 YouBike 資料是否成功獲取
        if youbike_df.empty:
            print("\n❌ 無法獲取 YouBike 資料，可能是網路問題或 API 異常。程式終止。")
            return

        start_station = find_nearest_youbike(
            config.user_location['lat'],
            config.user_location['lon'],
            youbike_df,
            config.min_available_bikes
        )
        
        route_df, similarity = generate_shape_route(
            youbike_df,
            start_station,
            config.target_shape,
            config
        )
        
        if route_df is None or route_df.empty:
            print("\n❌ 路線生成失敗，可能附近符合條件的 YouBike 站點不足。程式終止。")
            return
        
        print("\n🏛️  正在為路線站點搜尋附近景點...")
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
        
        osrm_result = get_osrm_route(route_df)
        
        print()
        create_shape_route_map(route_df, attractions_dict, osrm_result, config, similarity)
        
        print("\n" + "=" * 70)
        print("🗺️  路線摘要")
        print("=" * 70)
        for idx, (_, station) in enumerate(route_df.iterrows(), 1):
            print(f"{idx}. 🚲 {station['sna']} (可借: {station['available_rent_bikes']})")
            if idx in attractions_dict and attractions_dict[idx]:
                for attr in attractions_dict[idx][:2]: # 最多顯示2個
                    print(f"     📍 {attr['name']} ({attr['distance']:.0f}m)")
        print("=" * 70)
        
        print("\n🎉 規劃完成！")
        print(f"💡 圖形: {config.target_shape}")
        print(f"💡 形狀相似度: {similarity:.1%}")
        if osrm_result and osrm_result['success']:
            print(f"💡 OSRM 總距離: {osrm_result['distance']:.2f} 公里")
            print(f"💡 OSRM 預估時間: {osrm_result['duration']:.1f} 分鐘")
        
    except Exception as e:
        print(f"\n❌ 發生未預期的錯誤: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()