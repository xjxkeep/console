import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import QSize
from qfluentwidgets import CardWidget


class MapWidget(CardWidget):
    """可嵌入的地图组件 - 延迟加载 WebEngine"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self.map_view = None
        self._initialized = False

    def showEvent(self, event):
        """延迟初始化 WebEngine，避免影响其他组件渲染"""
        super().showEvent(event)
        if not self._initialized:
            self._initialized = True
            # 延迟导入 QtWebEngineWidgets
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            self.map_view = QWebEngineView()
            self.map_view.setMinimumSize(QSize(200, 200))
            self.map_view.setMaximumHeight(300)
            self._layout.addWidget(self.map_view)
            self._load_map()

    def _load_map(self):
        if not self.map_view:
            return
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
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
                var map = L.map('map').setView([39.915, 116.404], 15);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; OpenStreetMap'
                }).addTo(map);
                var marker = L.marker([39.915, 116.404]).addTo(map);
            </script>
        </body>
        </html>
        '''
        self.map_view.setHtml(html_content)

    def set_location(self, lat: float, lng: float):
        """更新地图位置"""
        if self.map_view:
            js = f"map.setView([{lat}, {lng}], 15); marker.setLatLng([{lat}, {lng}]);"
            self.map_view.page().runJavaScript(js)


