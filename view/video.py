from PyQt5 import QtGui
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLabel, QVBoxLayout
from PyQt5.QtWidgets import QSizePolicy
from qfluentwidgets import GroupHeaderCardWidget

class VideoPanel(GroupHeaderCardWidget):
    fps_collected=pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self.initUI()
    def initUI(self):
        self.setTitle("视频监控")
        self.videoPlayer=VideoPlayer()
        self.videoPlayer.fps_collected.connect(self.fps_collected.emit)
        self.vBoxLayout.addWidget(self.videoPlayer)
    
    def setPixmap(self, pixmap: QtGui.QPixmap) -> None:
        self.videoPlayer.setPixmap(pixmap)

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