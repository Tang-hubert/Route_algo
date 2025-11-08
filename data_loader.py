# data_loader.py
import requests
import pandas as pd
import geocoder

def get_user_location_auto():
    """
    使用 geocoder 自動獲取使用者當前位置。
    如果失敗，則返回預設的固定位置。
    """
    print("📍 正在自動獲取您的目前位置...")
    g = geocoder.ip('me')
    
    if g.ok and g.latlng:
        lat, lon = g.latlng
        address = g.address or "未知地址"
        print(f"✅ 位置獲取成功: ({lat:.4f}, {lon:.4f})")
        print(f"   地址: {address}")
        return {'lat': lat, 'lon': lon, 'address': address}
    else:
        print("⚠️ 自動定位失敗，將使用預設位置（臺大新體育館附近）。")
        # 返回預設位置
        lat, lon = 25.021777051200228, 121.5354050968437
        return {'lat': lat, 'lon': lon, 'address': '臺大新體育館附近 (預設)'}

def fetch_youbike_data():
    """抓取 YouBike 2.0 即時資料"""
    print("🚲 正在抓取 YouBike 即時資料...")
    url = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status() # 如果請求失敗 (如 404, 500)，會拋出異常
        data = response.json()
        
        df = pd.DataFrame(data)
        df = df[['sno', 'sna', 'sarea', 'latitude', 'longitude', 'available_rent_bikes', 'available_return_bikes']]
        
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df['available_rent_bikes'] = pd.to_numeric(df['available_rent_bikes'], errors='coerce').fillna(0).astype(int)
        df['available_return_bikes'] = pd.to_numeric(df['available_return_bikes'], errors='coerce').fillna(0).astype(int)
        
        df = df.dropna(subset=['latitude', 'longitude'])
        
        print(f"✅ 成功獲取 {len(df)} 個 YouBike 站點")
        return df
    except requests.exceptions.RequestException as e:
        print(f"❌ 抓取 YouBike 資料失敗: 網路錯誤 ({e})")
        return pd.DataFrame() # 返回空 DataFrame
    except Exception as e:
        print(f"❌ 處理 YouBike 資料時發生未知錯誤: {e}")
        return pd.DataFrame()


def fetch_attractions_from_csv(filepath="taipei_attractions.csv"):
    """從本地 CSV 讀取景點資料"""
    print("🏛️ 正在讀取台北景點資料...")
    try:
        df = pd.read_csv(filepath)
        df = df[pd.notna(df['nlat']) & pd.notna(df['elong'])]
        print(f"✅ 成功讀取 {len(df)} 個景點")
        return df
    except FileNotFoundError:
        print(f"❌ 找不到景點資料檔案: {filepath}")
        return pd.DataFrame()