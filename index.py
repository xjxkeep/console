
import json
import os
import sys

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QApplication, QSplashScreen, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel
from qfluentwidgets.common import FluentIcon
from qfluentwidgets.window import FluentWindow

from loader import SplashScreen
from pkg.api import API
from pkg.model import HIDBody, Setting
from pkg.mqtt import MQTTClient
from pkg.quic import HighwayQuicClient
from pkg.version_manager import VersionManager
from pkg.metric import *

# TODO
# 1. 封装下请求的host 等参数 统一管理 后面host走下发
# 2. 界面完善
# 3. OTA

class MainWindow(FluentWindow):
    
    
    def setupUi(self):
        from monitor import Monitor
        from controller import Controller
        from debug import Debug
        from about import About
        from setting import SettingView    
        self.monitor=Monitor(self.setting)
        self.controller=Controller(self.setting)
        self.debug=Debug(self.setting)
        self.about=About()
        self.settingView=SettingView()
        self.resize(self.setting.window_width,self.setting.window_height)
        if self.setting.window_x != 0 and self.setting.window_y != 0:
            self.move(self.setting.window_x,self.setting.window_y)
        

        self.debug_monitor=Monitor(self.setting)
        

        self.addSubInterface(self.monitor,FluentIcon.MOVIE, "Monitor")
        self.addSubInterface(self.controller,FluentIcon.GAME, "Controller")
        self.addSubInterface(self.settingView,FluentIcon.SETTING,"Setting")
        self.addSubInterface(self.debug,FluentIcon.DEVELOPER_TOOLS, "Debug")
        self.addSubInterface(self.about,FluentIcon.FEEDBACK,"About")
        
    

        
    def __init__(self):
        super().__init__()

        self.setting = Setting()
        self.load_setting()
        self.setupUi() 
        # 初始化 API 实例
        self.api = API(self.setting,self)
        # self.device=self.api.get_device_info()
        # if self.device is not None: 
        #     self.setting.source_device_id=self.device.device_id
        #     self.setting.token=self.device.token
        #     self.setting.device_id=self.device.subscribe_id
            
        
            
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
        self.quic_client.device_param_ready.connect(self.monitor.update_device_param)
        
        
        
        self.quic_client.video_encoder_worker.frame_collected.connect(self.update_debug_monitor)

        
        self.mqtt_client=MQTTClient(self.setting)
        # controller 发送控制消息
        self.controller.controlMessage.connect(self.quic_client.send_control_message)
        self.monitor.startSignal.connect(self.quic_client.start)
        self.monitor.startSignal.connect(self.mqtt_client.start)
        self.monitor.sendTestVideoSignal.connect(self.quic_client.send_video_test)
        self.monitor.sendTestVideoSignal.connect(self.debug_monitor.show)
        self.monitor.param_changed.connect(self.__handle_param_changed)
        # debug 发送文件 更新进度
        self.debug.uploader.fileToSend.connect(self.quic_client.send_file)
        self.quic_client.file_send_progress.connect(self.debug.uploader.updateProgress)

        self.settingView.hid_response.connect(self._handle_hid_response)
        
        # self.client.start()
        
    
    
    def __handle_param_changed(self,param:dict):
        print("param changed",param)
        self.quic_client.change_video_format(param.get("video_format","H.264"))
        self.mqtt_client.update_video_setting_sync(param.get("resolution","高清"),param.get("video_format","H.264"),param.get("bABR","关闭"))
        
    
    def update_debug_monitor(self):
        if self.quic_client.video_encoder_worker:
            pixmap=self.quic_client.video_encoder_worker.read_camera()
            self.debug_monitor.setPixmap(pixmap)
    
    def update_monitor(self):
        if self.quic_client.video_decoder_worker:
            pixmap=self.quic_client.video_decoder_worker.get_frame()
            self.monitor.setPixmap(pixmap)
            DISPLAY_FRAME_COUNT.inc()
            
    def _handle_hid_response(self,response:HIDBody):
        print("hid response",response)
        try:
            source_id = int(response.returns["id"],base=10)
            device_id = int(response.returns["sub_id"],base=10)
            self.debug.setValue("source_device_id", source_id)
            self.debug.setValue("device_id", device_id)
        except (ValueError, OverflowError) as e:
            print(f"Error converting HID response IDs: {e}")
            print(f"Raw id: {response.returns.get('id')}")
            print(f"Raw sub_id: {response.returns.get('sub_id')}")
        except Exception as e:
            print(f"Unexpected error in _handle_hid_response: {e}")

    def load_setting(self):
        try:
            if os.path.exists(".setting.json"):
                with open(".setting.json", "r") as f:
                    self.setting = Setting.model_validate_json(f.read())
                print("load setting:",self.setting)
        except Exception as e:
            print("load setting error",e)
            # self.guide=Guide(self)
            # self.guide.show()
          
    
    def quic_client_connected(self):
        print("quic client connected")
    
    def quic_client_connection_error(self,error):
        print("quic client connection error",error)
        
    
    def closeEvent(self, a0: QCloseEvent | None) -> None:
        print("mainwindow closeEvent")    
        self.setting.channels=self.controller.getChannelValues()
        self.setting.window_height,self.setting.window_width=self.height(),self.width()
        self.setting.window_x,self.setting.window_y=self.x(),self.y()
        print(self.setting)
        with open(".setting.json", "w") as f:
            json.dump(self.setting.model_dump(), f)
        self.mqtt_client.close()
        print("mqtt client closed")   
        self.quic_client.close()
        print("quic client closed")
        
        self.controller.close()
        print("controller closed")
        self.debug_monitor.close()
        # self.api.close()
        
        return super().closeEvent(a0)




