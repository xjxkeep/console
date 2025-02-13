from PyQt5.QtGui import QCloseEvent
from monitor import Monitor
from controller import Controller
from debug import Debug
from about import About
import sys
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentWindow,FluentIcon,NavigationItemPosition
from pkg.quic import HighwayQuicClient
from protocol.highway_pb2 import Device
import json
import os
# TODO
# 1. 封装下请求的host 等参数 统一管理 后面host走下发
# 2. 界面完善
# 3. OTA

class MainWindow(FluentWindow):
    
    
    def setupUi(self):
        self.setWindowTitle("Monitor")
        
        
        self.monitor=Monitor(self.setting)
        self.controller=Controller(self.setting)
        self.debug=Debug(self.setting)
        self.about=About()

        self.addSubInterface(self.monitor,FluentIcon.MOVIE, "Monitor")
        self.addSubInterface(self.controller,FluentIcon.GAME, "Controller")
        self.addSubInterface(self.debug,FluentIcon.DEVELOPER_TOOLS, "Debug")
        self.addSubInterface(self.about,FluentIcon.FEEDBACK,"About")
        
        
        
        
    def __init__(self):
        super().__init__()
        self.load_setting()
        self.setupUi()
        self.device=Device(id=1,message_type=Device.MessageType.VIDEO)
        self.source_device_id=1
        self.client=HighwayQuicClient(self.device,
                                      host=self.setting.get("host","127.0.0.1"),
                                      port=self.setting.get("port",30042),
                                      insecure=self.setting.get("insecure",True),
                                      source_device_id=self.setting.get("source_device_id",1))
    
        self.client.receive_video.connect(self.monitor.handle_video)
        self.client.upload_speed.connect(self.monitor.update_upload_speed)
        self.client.download_speed.connect(self.monitor.update_download_speed)
        self.client.connected.connect(self.quic_client_connected)
        self.client.connection_error.connect(self.quic_client_connection_error)
        # controller 发送控制消息
        self.controller.controlMessage.connect(self.client.send_control_message)
        
        # self.client.start()
    def load_setting(self):
        if os.path.exists("setting.json"):
            with open("setting.json", "r") as f:
                self.setting = json.load(f)
        else:
            self.setting = {
                "host":"127.0.0.1",
                "port":30042,
                "insecure":True,
                "source_device_id":1,
                "channel_count":10
            }
    
    def quic_client_connected(self):
        print("quic client connected")
    
    def quic_client_connection_error(self,error):
        print("quic client connection error",error)
        
    def closeEvent(self, a0: QCloseEvent | None) -> None:
        self.controller.close()
        self.monitor.close()
        self.debug.close()
        print("mainwindow closeEvent")    
        print(self.setting)
        with open("setting.json", "w") as f:
            json.dump(self.setting, f)
        return super().closeEvent(a0)

app=QApplication(sys.argv)

m=MainWindow()
m.show()

app.exec()


