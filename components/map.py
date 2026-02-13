import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QSize

class OSMMapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt + OpenStreetMap 免费地图")
        self.setGeometry(100, 100, 1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)  # 移除边距

        # 创建Web视图
        self.map_view = QWebEngineView()
        self.map_view.setMinimumSize(QSize(800, 600))
        self.load_osm_map()

        layout.addWidget(self.map_view)

    def load_osm_map(self):
        # 使用Leaflet.js加载OpenStreetMap（完全免费，无需密钥）
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>OpenStreetMap 示例</title>
            <!-- 引入Leaflet.js（开源地图前端库） -->
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                html, body {width:100%;height:100%;margin:0;padding:0;}
                #map {width:100%;height:100%;}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script type="text/javascript">
                // 初始化OSM地图（中心点：北京天安门）
                var map = L.map('map').setView([39.915, 116.404], 15);
                
                // 加载OSM地图瓦片（免费）
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                }).addTo(map);

                // 添加中心点标记
                var centerMarker = L.marker([39.915, 116.404]).addTo(map);
                centerMarker.bindPopup("中心点：天安门").openPopup();

                // 添加附近位置标记
                var nearbyPoints = [
                    {lat: 39.910, lng: 116.400, name: "餐厅A"},
                    {lat: 39.920, lng: 116.410, name: "便利店B"},
                    {lat: 39.918, lng: 116.395, name: "地铁站C"}
                ];

                nearbyPoints.forEach(function(item) {
                    var marker = L.marker([item.lat, item.lng]).addTo(map);
                    marker.bindPopup(item.name);
                    // 点击标记高亮
                    marker.on('click', function() {
                        this.openPopup();
                    });
                });
            </script>
        </body>
        </html>
        '''
        self.map_view.setHtml(html_content)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OSMMapWindow()
    window.show()
    sys.exit(app.exec_())