# config.py
import numpy as np

class RouteConfig:
    """路線規劃配置參數"""
    def __init__(self):
        # 預設位置（臺大新體育館附近），當自動定位失敗時使用
        self.user_location = {'lat': 25.021777051200228, 'lon': 121.5354050968437}
        
        # 路線形狀
        self.target_shape = 'T'
        
        # 時間與距離限制
        self.max_segment_time = 20  # 分鐘
        self.max_segment_distance = 3.0  # 公里 
        self.cycling_speed = 10  # km/h
        
        # YouBike 站點篩選
        self.min_available_bikes = 3
        self.min_available_spaces = 2
        
        # 景點篩選
        self.attraction_radius = 100  # 公尺
        
        # 輸出設定
        self.output_html = "taipei_shape_route.html"

# NOTE: 已精簡，只保留大寫半形字母
SHAPE_TEMPLATES = {
    'T': np.array([[0.10, 0.95], [0.90, 0.95], [0.50, 0.95], [0.50, 0.05]]),
    'A': np.array([[0.20, 0.05], [0.40, 0.60], [0.50, 0.95], [0.60, 0.60], [0.80, 0.05], [0.32, 0.52], [0.68, 0.52]]),
    'I': np.array([[0.30, 0.95], [0.70, 0.95], [0.50, 0.95], [0.50, 0.05], [0.30, 0.05], [0.70, 0.05]]),
    'P': np.array([[0.05, 0.22], [0.95, 0.22], [0.95, 0.55], [0.86, 0.72], [0.72, 0.78], [0.61, 0.70], [0.55, 0.54], [0.55, 0.22]]),
    'E': np.array([[0.85, 0.95], [0.20, 0.95], [0.20, 0.65], [0.55, 0.65], [0.20, 0.65], [0.20, 0.35], [0.20, 0.05], [0.85, 0.05]]),
}