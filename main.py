from monitor import Monitor
from controller import Controller
import sys
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentWindow,FluentIcon,NavigationItemPosition
from pkg.quic import HighwayQuicClient
from protocol.highway_pb2 import Device
# TODO
# 1. 封装下请求的host 等参数 统一管理 后面host走下发
# 2. 界面完善
# 3. OTA

class MainWindow(FluentWindow):
    
    
    def setupUi(self):
        self.setWindowTitle("Monitor")
        
        
        self.monitor=Monitor()
        self.controller=Controller()
        

        self.addSubInterface(self.monitor,FluentIcon.MOVIE, "Monitor")
        self.addSubInterface(self.controller,FluentIcon.GAME, "Controller")
        
    def __init__(self):
        super().__init__()
        self.setupUi()
        self.device=Device(id=1,message_type=Device.MessageType.VIDEO)
        self.source_device_id=1
        self.client=HighwayQuicClient(self.device,
                                      host="127.0.0.1",
                                      port=30042,
                                      ca_certs="assets/tls/cert.pem",
                                      insecure=True,
                                      source_device_id=self.source_device_id)

        self.client.receive_video.connect(self.monitor.handle_video)
        self.client.upload_speed.connect(self.monitor.update_upload_speed)
        self.client.download_speed.connect(self.monitor.update_download_speed)
        self.client.connected.connect(self.quic_client_connected)
        self.client.connection_error.connect(self.quic_client_connection_error)
        
    def quic_client_connected(self):
        print("quic client connected")
    
    def quic_client_connection_error(self,error):
        print("quic client connection error",error)

app=QApplication(sys.argv)

m=MainWindow()
m.show()

app.exec()


