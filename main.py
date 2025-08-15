from PyQt5.QtGui import QCloseEvent
from PyQt5.QtCore import QTimer, Qt
from monitor import Monitor
from controller import Controller
from debug import Debug
from about import About
from setting import SettingView
# from guide import Guide
import sys
from PyQt5.QtWidgets import QApplication,QDialog,QInputDialog,QSizePolicy
from qfluentwidgets.window import FluentWindow
from qfluentwidgets.common import FluentIcon
from pkg.mqtt import MQTTClient
from pkg.quic import HighwayQuicClient
from pkg.api import API
from pkg.version_manager import VersionManager
from protocol.highway_pb2 import Device
import json
import os
from pkg.model import HIDBody
# TODO
# 1. 封装下请求的host 等参数 统一管理 后面host走下发
# 2. 界面完善
# 3. OTA

class MainWindow(FluentWindow):
    
    
    def setupUi(self):
     
        
        self.monitor=Monitor(self.setting)
        self.controller=Controller(self.setting)
        self.debug=Debug(self.setting)
        self.about=About()
        self.settingView=SettingView()
        

        self.addSubInterface(self.monitor,FluentIcon.MOVIE, "Monitor")
        self.addSubInterface(self.controller,FluentIcon.GAME, "Controller")
        self.addSubInterface(self.settingView,FluentIcon.SETTING,"Setting")
        self.addSubInterface(self.debug,FluentIcon.DEVELOPER_TOOLS, "Debug")
        self.addSubInterface(self.about,FluentIcon.FEEDBACK,"About")
        
    

        
    def __init__(self):
        super().__init__()

        
        self.load_setting()
        self.setupUi() 
        # 初始化 API 实例
        self.api = API(self.setting)
        self.device=self.api.get_device_info()
        if self.device is not None: 
            self.setting["source_device_id"]=self.device.device_id
            self.setting["token"]=self.device.token
            self.setting["device_id"]=self.device.subscribe_id
            
        
            
        # self.version_manager=VersionManager(self.setting,self.api,self)
        # self.version_manager.check_update()
        self.quic_client=HighwayQuicClient(self.setting)
    
        self.quic_client.upload_speed.connect(self.monitor.update_upload_speed)
        self.quic_client.download_speed.connect(self.monitor.update_download_speed)
        self.quic_client.connected.connect(self.quic_client_connected)
        self.quic_client.connection_error.connect(self.quic_client_connection_error)
        self.quic_client.receive_video.connect(self.update_monitor)
        self.quic_client.latency.connect(self.monitor.update_latency)
        self.quic_client.input_wave_data.connect(self.monitor.update_wave_form)  
        
        
        
        self.mqtt_client=MQTTClient(self.setting)
        # controller 发送控制消息
        self.controller.controlMessage.connect(self.quic_client.send_control_message)
        self.monitor.startSignal.connect(self.quic_client.start)
        self.monitor.startSignal.connect(self.mqtt_client.start)
        self.monitor.sendTestVideoSignal.connect(self.quic_client.send_video_test)
        self.monitor.param_changed.connect(self.__handle_param_changed)
        # debug 发送文件 更新进度
        self.debug.uploader.fileToSend.connect(self.quic_client.send_file)
        self.quic_client.file_send_progress.connect(self.debug.uploader.updateProgress)

        self.settingView.hid_response.connect(self._handle_hid_response)
        # self.client.start()
        
    
    
    def __handle_param_changed(self,param:dict):
        print("param changed",param)
        self.quic_client.change_video_format(param.get("video_format","H.264"))
        self.mqtt_client.update_video_setting_sync(param.get("resolution","高清"),param.get("video_format","H.264"))
        
        
    def update_monitor(self):
        pixmap=self.quic_client.decoder.get_frame()
        self.monitor.setPixmap(pixmap)
    
    def _handle_hid_response(self,response:HIDBody):
        print("hid response",response)
        self.debug.setValue("source_device_id",response.returns["id"])
        self.debug.setValue("device_id",response.returns["sub_id"])

    def load_setting(self):
        if os.path.exists(".setting.json"):
            with open(".setting.json", "r") as f:
                self.setting = json.load(f)
            print("load setting:",self.setting)
        else:
            
            self.setting = {
                "host":"stream.api.andless.tech",
                "port":30042,
                "insecure":True,
                "source_device_id":"0",
                "channel_count":10,
                "device_id":"1",
                "mqtt_port":31883,
                "mqtt_setting_topic":"demo/aiomqtt",
                "mqtt_host":"stream.api.andless.tech",
            }
            # self.guide=Guide(self)
            # self.guide.show()
          
    
    def quic_client_connected(self):
        print("quic client connected")
    
    def quic_client_connection_error(self,error):
        print("quic client connection error",error)
        
    
    def closeEvent(self, a0: QCloseEvent | None) -> None:
        print("mainwindow closeEvent")    
        print(self.setting)
        with open(".setting.json", "w") as f:
            json.dump(self.setting, f)
        self.quic_client.close()
        self.mqtt_client.close()
        print("client closed")    
        self.controller.close()
        print("controller closed")
        
        return super().closeEvent(a0)

app=QApplication(sys.argv)

m=MainWindow()
m.show()

app.exec()


