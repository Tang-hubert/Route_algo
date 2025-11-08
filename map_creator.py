# map_creator.py
import folium
from folium import plugins # 引入 plugins
import webbrowser
import os

def create_shape_route_map(route_df, attractions_dict, osrm_result, config, similarity):
    """創建圖形路線地圖（增強版：獨立顯示景點）"""
    if route_df.empty:
        print("❌ 無法建立地圖，因為沒有路線資料。")
        return
        
    center_lat = route_df['latitude'].mean()
    center_lon = route_df['longitude'].mean()
    
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14, tiles='OpenStreetMap')
    
    # --- START: 新增景點圖層 (MarkerCluster) ---
    # 建立一個景點聚合圖層，當地圖縮小時，鄰近的景點會自動聚合
    attraction_cluster = plugins.MarkerCluster(name="觀光景點").add_to(m)
    
    print("📷 正在將觀光景點標示到地圖上...")
    # 遍歷從主程式傳來的 attractions_dict
    for station_idx, attractions in attractions_dict.items():
        for attr in attractions:
            # 為每個景點建立一個獨立的紫色相機圖示
            folium.Marker(
                location=[attr['lat'], attr['lon']],
                popup=f"<b>{attr['name']}</b><br>{attr.get('address', '無地址資訊')}",
                tooltip=attr['name'],
                icon=folium.Icon(color='purple', icon='camera', prefix='fa')
            ).add_to(attraction_cluster) # 將景點圖示加入到 "聚合圖層" 中
    # --- END: 新增景點圖層 ---

    # 繪製 YouBike 路線
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
        # 顏色邏輯：綠色代表車多(>=10)，橘色代表車少(<10)
        color = 'green' if station['available_rent_bikes'] >= 10 else 'orange'
        
        popup_html = f"""
        <div style="width: 220px;">
            <h4 style="color: {color};">🚲 站點 {idx}: {station['sna']}</h4>
            <hr>
            <b>可借車輛：</b>{station['available_rent_bikes']} 輛<br>
            <b>可還空位：</b>{station['available_return_bikes']} 位
        """
        
        # 彈出視窗中仍然保留附近的景點列表，作為文字補充
        if idx in attractions_dict:
            popup_html += "<hr><b>附近景點列表：</b><br>"
            for attr in attractions_dict[idx][:3]:
                popup_html += f"📍 {attr['name']} ({attr['distance']:.0f}m)<br>"
        
        popup_html += "</div>"
        
        folium.Marker(
            location=[station['latitude'], station['longitude']],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"站點 {idx}: {station['sna']}",
            icon=folium.Icon(color=color, icon='bicycle', prefix='fa')
        ).add_to(m)
        
        # 添加站點編號
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
    legend_html = f'''
    <div style="position: fixed; bottom: 50px; left: 50px; width: 280px; 
                background-color: rgba(255, 255, 255, 0.9); border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 10px; border-radius: 5px;">
        <h4 style="margin-top:0;">🗺️ {config.target_shape} 形路線圖例</h4>
        <p><span style="color: darkblue;">━━</span> <b>騎行路線</b></p>
        <p><i class="fa fa-bicycle" style="color: green;"></i> <b>YouBike 站 (車輛充足 ≥ 10)</b></p>
        <p><i class="fa fa-bicycle" style="color: orange;"></i> <b>YouBike 站 (車輛較少 &lt; 10)</b></p>
        <p><i class="fa fa-camera" style="color: purple;"></i> <b>附近觀光景點</b></p>
        <hr>
    '''
    if osrm_result and osrm_result['success']:
        legend_html += f'''
        <p><b>總距離：</b>{osrm_result['distance']:.2f} 公里</p>
        <p><b>預估時間：</b>{osrm_result['duration']:.1f} 分鐘</p>
        '''
    legend_html += f'''
        <p><b>停靠點數：</b>{len(route_df)} 個</p>
        <p><b>形狀相似度：</b>{similarity:.1%}</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # 新增圖層控制器，可以自由開關「觀光景點」圖層
    folium.LayerControl().add_to(m)
    plugins.Fullscreen(position='topright', title='全螢幕', title_cancel='退出全螢幕').add_to(m)
    
    m.save(config.output_html)
    print(f"\n✅ 地圖已生成：{config.output_html}")
    
    try:
        webbrowser.open('file://' + os.path.realpath(config.output_html))
        print("🌐 已在瀏覽器開啟")
    except Exception as e:
        print(f"⚠️ 無法自動開啟瀏覽器: {e}")