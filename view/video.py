import logging
from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLabel, QVBoxLayout
from PyQt5.QtWidgets import QSizePolicy
from qfluentwidgets import GroupHeaderCardWidget,TransparentPushButton,FluentIcon,ComboBox

class VideoPanel(GroupHeaderCardWidget):
    fps_collected=pyqtSignal(int)
    param_changed=pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self.initUI()
    def initUI(self):
        self.setTitle("视频监控")
        self.videoPlayer=VideoPlayer()
        self.fps=TransparentPushButton(FluentIcon.VIDEO.icon(),"30 fps")
        self.resolution=ComboBox()
        self.resolution.addItems(["清晰度: 高清","清晰度: 标清","清晰度: 流畅"])
        self.resolution.setCurrentIndex(0)
        self.videoPlayer.fps_collected.connect(self.fps_collected.emit)
        self.videoPlayer.fps_collected.connect(lambda x: self.fps.setText(f"{x} fps"))
        self.vBoxLayout.addWidget(self.videoPlayer)
        self.video_format=ComboBox()
        self.video_format.addItems(["视频格式: H.264","视频格式: H.265"])
        self.video_format.setCurrentIndex(0)
        self.bABR=ComboBox()
        self.bABR.addItems(["码率自适应: 开启","码率自适应: 关闭"])
        self.bABR.setCurrentIndex(0)
        self.resolution.currentTextChanged.connect(self.__handle_resolution_menu_triggered)
        self.video_format.currentTextChanged.connect(self.__handle_video_format_menu_triggered)
        self.bABR.currentTextChanged.connect(self.__handle_bABR_menu_triggered)
        self.headerLayout.addWidget(self.fps)
        self.headerLayout.addWidget(self.resolution)
        self.headerLayout.addWidget(self.video_format)
        self.headerLayout.addWidget(self.bABR)
    def setPixmap(self, pixmap: QtGui.QPixmap) -> None:
        self.videoPlayer.setPixmap(pixmap)
    
    def __handel_setting_changed(self):
        self.param_changed.emit({
        "resolution":self.resolution.currentText().split(":")[1].strip(),
        "video_format":self.video_format.currentText().split(":")[1].strip(),
        "bABR":self.bABR.currentText().split(":")[1].strip(),
    })
    
    def __handle_video_format_menu_triggered(self,text:str):
        logging.info(text)
        self.__handel_setting_changed()
    def __handle_resolution_menu_triggered(self,text:str):
        logging.info(text)
        self.__handel_setting_changed()
    def __handle_bABR_menu_triggered(self,text:str):
        logging.info(text)
        self.__handel_setting_changed()

class VideoPlayer(QLabel):
    fps_collected=pyqtSignal(int)
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fps=0
        self.timer=QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_fps)
        self.timer.start()
        self.setupUi()
    def setupUi(self):
        self.setObjectName("Player")
        self.setText("无信号，等待客户端连接...")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        self.setStyleSheet("background-color: rgb(0,0,0);color: rgb(255,255,255);")
    
    def setPixmap(self, pixmap: QtGui.QPixmap) -> None:
        self.fps+=1
        scaled_pixmap = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return super().setPixmap(scaled_pixmap)

    def update_fps(self):
        self.fps_collected.emit(self.fps)
        self.fps=0