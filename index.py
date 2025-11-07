
import json
import logging
import os
import sys

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QPixmap
from PyQt5.QtWidgets import QApplication, QSplashScreen, QVBoxLayout, QWidget
from qfluentwidgets import BodyLabel
from qfluentwidgets.common import FluentIcon
from qfluentwidgets.window import FluentWindow

from loader import SplashScreen
from pkg.api import API
from pkg.metric import *
from pkg.model import HIDBody, Setting
from pkg.mqtt import MQTTClient
from pkg.quic import HighwayQuicClient
from pkg.version_manager import VersionManager

# TODO
# 1. 封装下请求的host 等参数 统一管理 后面host走下发
# 2. 界面完善
# 3. OTA

class MainWindow(FluentWindow):
    
    
    def setupUi(self):
        from monitor import Monitor
        from view.video import VideoPlayer
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
        

        self.debug_monitor=VideoPlayer()
        self.debug_monitor.setWindowTitle("Camera Live")
        

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
        self.quic_client.connected.connect(self.monitor.statusBar.handle_server_connected)
        self.quic_client.connection_error.connect(self.monitor.statusBar.handle_server_disconnected)

        
        self.mqtt_client=MQTTClient(self.setting)
        # controller 发送控制消息
        self.controller.controlMessage.connect(self.quic_client.send_control_message)
        self.monitor.startSignal.connect(self.quic_client.start)
        self.monitor.startSignal.connect(self.mqtt_client.start)
        self.monitor.sendTestVideoSignal.connect(self.quic_client.start_test_video_stream)
        self.monitor.sendTestVideoSignal.connect(self.debug_monitor.show)
        
        self.monitor.sendTestDatagramSignal.connect(self.quic_client.start_test_video_datagram)
        self.monitor.sendTestDatagramSignal.connect(self.debug_monitor.show)
        
        self.monitor.sendTestCodecSignal.connect(self.quic_client.start_test_video_codec)
        self.monitor.sendTestCodecSignal.connect(self.debug_monitor.show)
        
        self.monitor.param_changed.connect(self.__handle_param_changed)
        

        self.settingView.hid_response.connect(self._handle_hid_response)
        
        # self.client.start()
        
    
    
    def __handle_param_changed(self,param:dict):
        logging.info(f"param changed {param}")
        self.mqtt_client.update_video_setting_sync(param.get("resolution","高清"),param.get("video_format","H.264"),param.get("bABR","关闭"))
        
    
    def update_debug_monitor(self):
        if self.quic_client.video_encoder_worker:
            pixmap=self.quic_client.video_encoder_worker.read_camera()
            self.debug_monitor.setPixmap(pixmap)
    
    def update_monitor(self):
        qimg=None
        if qimg is None and self.quic_client.h264_decoder_worker:
            qimg=self.quic_client.h264_decoder_worker.get_frame()
            logging.debug(f"h264 decoder worker get frame")
        if qimg is None and self.quic_client.h265_decoder_worker:
            qimg=self.quic_client.h265_decoder_worker.get_frame()
            logging.debug(f"h265 decoder worker get frame")
        if qimg is None: return
        self.monitor.setQImage(qimg)
    def _handle_hid_response(self,response:HIDBody):
        logging.info(f"hid response {response}")
        try:
            source_id = int(response.returns["id"],base=10)
            device_id = int(response.returns["sub_id"],base=10)
            self.debug.setValue("source_device_id", source_id)
            self.debug.setValue("device_id", device_id)
        except (ValueError, OverflowError) as e:
            logging.info(f"Error converting HID response IDs: {e}")
            logging.info(f"Raw id: {response.returns.get('id')}")
            logging.info(f"Raw sub_id: {response.returns.get('sub_id')}")
        except Exception as e:
            logging.info(f"Unexpected error in _handle_hid_response: {e}")

    def load_setting(self):
        try:
            if os.path.exists(".setting.json"):
                with open(".setting.json", "r") as f:
                    self.setting = Setting.model_validate_json(f.read())
                logging.info(f"load setting: {self.setting}")
        except Exception as e:
            logging.info(f"load setting error {e}")
            # self.guide=Guide(self)
            # self.guide.show()
          
    
    def quic_client_connected(self):
        logging.info("quic client connected")
    
    def quic_client_connection_error(self,error):
        logging.info(f"quic client connection error {error}")
        
    
    def closeEvent(self, a0: QCloseEvent | None) -> None:
        logging.info("mainwindow closeEvent")    
        self.setting.channels=self.controller.getChannelValues()
        self.setting.window_height,self.setting.window_width=self.height(),self.width()
        self.setting.window_x,self.setting.window_y=self.x(),self.y()
        logging.info(self.setting)
        with open(".setting.json", "w") as f:
            json.dump(self.setting.model_dump(), f)
        self.mqtt_client.close()
        logging.info("mqtt client closed")   
        self.quic_client.close()
        logging.info("quic client closed")
        
        self.controller.close()
        logging.info("controller closed")
        self.debug_monitor.close()
        # self.api.close()
        
        return super().closeEvent(a0)




