
import json
import logging
import os
import sys

from PyQt5.QtCore import QThread, Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QCloseEvent, QPixmap, QIcon
from qfluentwidgets import BodyLabel, setTheme, Theme, isDarkTheme
from qfluentwidgets.common import FluentIcon
from qfluentwidgets.window import FluentWindow
from qfluentwidgets.components.navigation import NavigationItemPosition

from pkg.api import API
from pkg.model import HIDBody, Setting
from pkg.mqtt import MQTTClient
from pkg.quic import HighwayQuicClient
from pkg.version import get_window_title
from monitor import Monitor
from components.video import VideoPlayer
from controller import Controller
from debug import Debug
from about import About
from setting import SettingView
# TODO
# 1. 封装下请求的host 等参数 统一管理 后面host走下发
# 2. 界面完善
# 3. OTA

class MainWindow(FluentWindow):


    def setupUi(self):
        # 设置窗口图标和标题
        icon_path = os.path.join(os.path.dirname(__file__), "assets/images/logo.jpg")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setWindowTitle(get_window_title())

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


        self.addSubInterface(self.monitor,FluentIcon.HOME, "主页")
        self.addSubInterface(self.controller,FluentIcon.GAME, "遥控")
        self.addSubInterface(self.settingView,FluentIcon.SETTING,"设置")
        self.addSubInterface(self.debug,FluentIcon.DEVELOPER_TOOLS, "调试")
        self.addSubInterface(self.about,FluentIcon.FEEDBACK,"关于")

        # 在导航栏底部添加主题切换按钮
        self.navigationInterface.addItem(
            routeKey='theme',
            icon=FluentIcon.CONSTRACT,
            text='主题',
            onClick=self.toggleTheme,
            selectable=False,
            position=NavigationItemPosition.BOTTOM
        )

    def toggleTheme(self):
        """切换明暗主题"""
        if isDarkTheme():
            setTheme(Theme.LIGHT)
            self._saveThemeSetting("LIGHT")
        else:
            setTheme(Theme.DARK)
            self._saveThemeSetting("DARK")

    def _saveThemeSetting(self, theme: str):
        """保存主题设置"""
        from pkg.settings_manager import settings_manager
        settings_manager.set("appearance/theme", theme)
        settings_manager.sync()

    def _loadThemeSetting(self):
        """加载主题设置"""
        from pkg.settings_manager import settings_manager
        theme = settings_manager.get("appearance/theme", "LIGHT")
        if theme == "DARK":
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.LIGHT)
        
    

        
    def __init__(self):
        super().__init__()

        self.setting = Setting()
        self.load_setting()
        self._loadThemeSetting()  # 加载并应用主题设置
        self.setupUi() 
        
        # 初始化运行时间计时器
        self.uptime_timer = QTimer(self)
        self.uptime_seconds = 0  # 记录总秒数
        self.uptime_timer.timeout.connect(self.update_uptime)
        self.uptime_timer.start(1000)  # 每秒更新一次
        # 初始化 API 实例
        self.api = API(self.setting,self)
        # self.device=self.api.get_device_info()
        # if self.device is not None: 
        #     self.setting.subscribe_id=self.device.device_id
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

        # 连接设备选择信号：当选择模拟摇杆时激活 ControlPanel 中的摇杆
        self.controller.detector.virtual_joystick_selected.connect(
            self.monitor.controlPanel.setJoystickActive
        )

        # 同步遥控页面的通道值到主页的 ChannelDisp
        self.controller.controlMessage.connect(
            self.monitor.controlPanel.setChannelValues
        )

        # 同步设备选择：遥控页面 -> 主页
        self.controller.detector.devices_refreshed.connect(
            self.monitor.controlPanel.setDeviceList
        )
        self.controller.detector.device_index_changed.connect(
            self.monitor.controlPanel.setCurrentDevice
        )

        # 同步设备选择：主页 -> 遥控页面
        self.monitor.controlPanel.device_selected.connect(
            self.controller.detector.setCurrentDevice
        )

        # 主页刷新按钮触发遥控页面的刷新
        self.monitor.controlPanel.setRefreshCallback(
            self.controller.detector.refreshDevices
        )

        # 初始化主页的设备列表
        self.monitor.controlPanel.setDeviceList(
            self.controller.detector.getDevices()
        )

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
            self.debug.setValue("subscribe_id", source_id)
            self.debug.setValue("device_id", device_id)
        except (ValueError, OverflowError) as e:
            logging.info(f"Error converting HID response IDs: {e}")
            logging.info(f"Raw id: {response.returns.get('id')}")
            logging.info(f"Raw sub_id: {response.returns.get('sub_id')}")
        except Exception as e:
            logging.info(f"Unexpected error in _handle_hid_response: {e}")

    def load_setting(self):
        """加载设置 - 如果存在旧的 JSON 文件则迁移到 QSettings"""
        try:
            if os.path.exists(".setting.json"):
                with open(".setting.json", "r") as f:
                    self.setting = Setting.model_validate_json(f.read())
                logging.info(f"Migrated settings from .setting.json")
                # 迁移后删除旧文件
                os.rename(".setting.json", ".setting.json.bak")
                logging.info("Renamed .setting.json to .setting.json.bak")
        except Exception as e:
            logging.info(f"load setting error {e}")

    def quic_client_connected(self):
        logging.info("quic client connected")

    def quic_client_connection_error(self,error):
        logging.info(f"quic client connection error {error}")

    def update_uptime(self):
        """更新运行时间"""
        self.uptime_seconds += 1
        hours = self.uptime_seconds // 3600
        minutes = (self.uptime_seconds % 3600) // 60
        seconds = self.uptime_seconds % 60

        # 更新 StatusPanel 中的运行时间
        self.monitor.statusPanel.update_uptime(hours, minutes, seconds)

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        logging.info("mainwindow closeEvent")
        # 保存配置到 QSettings
        self.setting.channels = self.controller.getChannelValues()
        self.setting.window_height = self.height()
        self.setting.window_width = self.width()
        self.setting.window_x = self.x()
        self.setting.window_y = self.y()
        self.setting.sync()  # 同步到磁盘
        logging.info(f"Settings saved: {self.setting}")

        self.mqtt_client.close()
        logging.info("mqtt client closed")
        self.quic_client.close()
        logging.info("quic client closed")

        self.controller.close()
        logging.info("controller closed")
        self.debug_monitor.close()
        # self.api.close()

        return super().closeEvent(a0)




