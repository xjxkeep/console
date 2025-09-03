from PyQt5.QtCore import Qt,pyqtSignal
from qfluentwidgets import FluentIcon,FluentIconBase,TransparentPushButton,TransparentToolButton,TransparentDropDownPushButton,RoundMenu,Action,PushButton  
from PyQt5.QtGui import QCloseEvent, QIcon,QColor,QImage,QPixmap
from PyQt5.QtCore import Qt,QTimer
from PyQt5.QtWidgets import *
from datetime import datetime
from pkg.quic import HighwayQuicClient
from protocol.highway_pb2 import Device,Video,DeviceParam
from pkg.codec import H264Decoder
import time
import threading
from view.wave import WaveformWidget
import numpy as np
from pkg.model import Setting
from view.video_display import VideoDisplayWidget
from view.imu import IMUWidget
class StatusBar(QWidget):
    param_changed=pyqtSignal(dict)
    def update(self):
        self.date.setText(datetime.now().strftime("%Y/%m/%d %H:%M:%S"))
    
    def update_fps(self,value:int):
        self.fps.setText(f"{value} fps")
    
    def update_upload_speed(self,value:float):
        self.upload.setText(f"{value/1024:.2f} kb/s")
    
    def update_download_speed(self,value:float):
        self.download.setText(f"{value/1024:.2f} kb/s")
    
    def update_latency(self,value:int):
        self.signal.setText(f"{value} ms")
    
    def setupUi(self):
        layout=QHBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.signal=TransparentPushButton(FluentIcon.WIFI.icon(color=QColor("green")),"10 ms")
        self.upload=TransparentPushButton(FluentIcon.UP.icon(),"100 kb/s")
        self.download=TransparentPushButton(FluentIcon.DOWN.icon(),"99 kb/s")
        self.fps=TransparentPushButton(FluentIcon.VIDEO.icon(),"30 fps")
        self.date=TransparentPushButton(FluentIcon.DATE_TIME.icon(),"2025/02/09 21:44:00")
        self.channel=TransparentDropDownPushButton(FluentIcon.IOT.icon(),"线路: 上海")
        self.resolution=TransparentDropDownPushButton(FluentIcon.VIDEO.icon(),"清晰度: 高清")
        self.video_format=TransparentDropDownPushButton(FluentIcon.VIDEO.icon(),"视频格式: H.264")
        self.bABR=TransparentPushButton(FluentIcon.VIDEO.icon(),"码率自适应: 关闭")
        self.battery=TransparentPushButton(QIcon("assets/svg/battery-full.svg"),"100%")

        switch_menu=RoundMenu(parent=self)
        switch_menu.addActions([
            Action('开启'),
            Action('关闭'),
        ])
        self.bABR.setMenu(switch_menu)
        # switch_menu.triggered.connect(self.__handle_bABR_menu_triggered)


        channel_menu = RoundMenu(parent=self)
        channel_menu.addActions([
            Action('上海'),
            Action('北京'),
        ])
        self.channel.setMenu(channel_menu)
        channel_menu.triggered.connect(self.__handle_channel_menu_triggered)


        video_format_menu=RoundMenu(parent=self)
        video_format_menu.addActions([
            Action('H.264'),
            Action('H.265'),
        ])
        self.video_format.setMenu(video_format_menu)
        video_format_menu.triggered.connect(self.__handle_video_format_menu_triggered)


        resolution_menu=RoundMenu(parent=self)
        resolution_menu.addActions([
            Action('高清'),
            Action('标清'),
            Action('流畅'),
        ])
        self.resolution.setMenu(resolution_menu)
        resolution_menu.triggered.connect(self.__handle_resolution_menu_triggered)

        self.timer=QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.sync=TransparentToolButton(FluentIcon.SYNC.icon())


        layout.addWidget(self.signal)
        layout.addWidget(self.battery)

        layout.addWidget(self.upload)
        layout.addWidget(self.download)

        layout.addWidget(self.video_format)
        layout.addWidget(self.resolution)
        layout.addWidget(self.channel)
        layout.addWidget(self.bABR)
        layout.addWidget(self.fps)
        layout.addWidget(self.date)
        layout.addWidget(self.sync)
        
        
        self.setLayout(layout)
        self.setFixedHeight(50)
        self.setStyleSheet("background-color: rgb(255,0,0)")

    def __handel_setting_changed(self):
         self.param_changed.emit({
            "resolution":self.resolution.text().split(":")[1].strip(),
            "video_format":self.video_format.text().split(":")[1].strip(),
            "channel":self.channel.text().split(":")[1].strip(),
            "bABR":self.bABR.text().split(":")[1].strip(),
        })
    
    def __handle_channel_menu_triggered(self,action:Action):
        print(action.text())
        self.channel.setText("线路: "+action.text())
        self.__handel_setting_changed()

    def __handle_video_format_menu_triggered(self,action:Action):
        print(action.text())
        self.video_format.setText("视频格式: "+action.text())
        self.__handel_setting_changed()
    def __handle_resolution_menu_triggered(self,action:Action):
        print(action.text())
        self.resolution.setText("清晰度: "+action.text())
        self.__handel_setting_changed()
    def __handle_bABR_menu_triggered(self,action:Action):
        print(action.text())
        self.bABR.setText("码率自适应: "+action.text())
        self.__handel_setting_changed()
    def __init__(self):
        super().__init__()
        self.setupUi()




class Monitor(QWidget):
    # TODO 视频解码卡顿
    startSignal=pyqtSignal()
    sendTestVideoSignal=pyqtSignal()
    param_changed=pyqtSignal(dict)
    def setupUi(self):
        self.setObjectName("Monitor")
        self.resize(800,600)
        
        # 使用QGridLayout来实现IMU控件在display右下角的布局
        main_layout = QVBoxLayout()
        self.statusBar = StatusBar()
        main_layout.addWidget(self.statusBar)

        # 创建display和IMU的组合布局
        display_imu_layout = QGridLayout()
        display_imu_layout.setSpacing(5)  # 减小控件间距，为400x400的IMU控件留出空间
        display_imu_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        self.display = QLabel("无信号，等待客户端连接...")
        self.display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.display.setStyleSheet("background-color: rgb(0,0,0);color: rgb(255,255,255);")
        
        self.imu = IMUWidget()
        
        # 将display放在(0,0)位置，占据大部分空间
        # 将IMU放在(1,1)位置，即右下角，大小为400x400
        display_imu_layout.addWidget(self.display, 0, 0, 2, 2)  # 跨越2行2列
        display_imu_layout.addWidget(self.imu, 1, 1, 1, 1)      # 放在右下角
        
        # 设置IMU控件的对齐方式为右下角
        display_imu_layout.setAlignment(self.imu, Qt.AlignRight | Qt.AlignBottom)
        
        # 设置display的拉伸因子，让它占据大部分空间
        # 由于IMU控件较大(400x400)，需要调整拉伸比例
        display_imu_layout.setRowStretch(0, 3)  # 第一行占据更多空间
        display_imu_layout.setRowStretch(1, 1)  # 第二行占据较少空间
        display_imu_layout.setColumnStretch(0, 3)  # 第一列占据更多空间
        display_imu_layout.setColumnStretch(1, 1)  # 第二列占据较少空间
        
        main_layout.addLayout(display_imu_layout)
        
        self.waveform = WaveformWidget()
        main_layout.addWidget(self.waveform)
        
        self.testButton = PushButton("测试本地视频解码")
        self.testButton.clicked.connect(self.test)
        self.startButton = PushButton("连接服务器")
        self.startButton.clicked.connect(self.startSignal.emit)
        self.sendTestVideoButton = PushButton("发送摄像头视频")
        self.sendTestVideoButton.clicked.connect(self.sendTestVideoSignal.emit)
        main_layout.addWidget(self.testButton)
        main_layout.addWidget(self.startButton)
        main_layout.addWidget(self.sendTestVideoButton)
        
        self.setLayout(main_layout)
        
        self.__frame = None



    def __init__(self,setting:Setting,parent=None) -> None:
        super().__init__(parent)
        self.setting=setting
        self.setupUi()
        self.fps=0
        self.timer=QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_fps)
        self.timer.start()
        self.decoder=H264Decoder()
        self.latency=0
        self.statusBar.param_changed.connect(self.param_changed)
    
    def update_device_param(self,data:DeviceParam):
        print(data)
        self.imu.update_imu_data(data.imu_param)

    def update_wave_form(self,value:np.ndarray):
        self.waveform.set_data(value)
    
    def update_upload_speed(self,value:float):
        self.statusBar.update_upload_speed(value)
    
    def update_download_speed(self,value:float):
        self.statusBar.update_download_speed(value)
    
    def test(self):
        threading.Thread(target=self.videoDecodeTest,daemon=True).start()
    
    def videoDecodeTest(self):
        with open(r"output.h264","rb") as f:
            while True:
                data=f.read(9600)
                if not data:
                    break
                self.decoder.write(data)
                time.sleep(0.005)
  
    def update_latency(self,value:int):
        self.statusBar.update_latency(value)
    
    def update_fps(self):
        self.statusBar.update_fps(self.fps)
        self.fps=0
    
    
    def setPixmap(self, pixmap:QPixmap):
        try:
            # Increment the frame count
            self.fps += 1
            # 直接设置图像，VideoDisplayWidget会自动处理缩放
            self.display.setPixmap(pixmap)
        
        except Exception as e:
            print(f"Error displaying video: {str(e)}")

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        self.decoder.close()
        print("decoder closed")
        return super().closeEvent(a0)

if __name__=="__main__":
    import sys
    # TODO
    # 1. 封装下请求的host 等参数 统一管理 后面host走下发
    # 2. 界面完善
    # 3. OTA

    app=QApplication(sys.argv)

    m=Monitor(Setting())
    m.show()

    app.exec()

