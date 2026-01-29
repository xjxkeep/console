import logging
import os
from PyQt5 import QtGui
from PyQt5 import QtCore
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget
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
        self.videoPlayer=FastVideoPlayer()
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
    def setQImage(self, qimage: QtGui.QImage) -> None:
        self.videoPlayer.setImage(qimage)
    
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
        
        
        
class FastVideoPlayer(QWidget):
    fps_collected=pyqtSignal(int)
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fps=0
        self.current_image = None  # 保存当前要显示的图像
        self.placeholder_image = None  # 占位图像
        self.timer=QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_fps)
        self.timer.start()
        self.setupUi()
        self._load_placeholder()

    def _load_placeholder(self):
        """加载占位图像"""
        # 获取项目根目录
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        placeholder_path = os.path.join(base_dir, "assets/images/background.png")
        if os.path.exists(placeholder_path):
            self.placeholder_image = QtGui.QImage(placeholder_path)
            logging.info(f"Loaded placeholder image: {placeholder_path}")
        else:
            logging.warning(f"Placeholder image not found: {placeholder_path}")

    def setupUi(self):
        # self.setFixedSize(200,200)
        self.setObjectName("Player")
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        self.setStyleSheet("background-color: rgb(0,0,0);color: rgb(255,255,255);")

    def paintEvent(self, event):
        """重写 paintEvent，在这里绘制图像"""
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        rect = self.rect()

        # 选择要显示的图像：优先显示视频帧，否则显示占位图
        image_to_draw = self.current_image if self.current_image is not None else self.placeholder_image

        if image_to_draw is not None:
            # 调整 rect 使得图像长宽比例不变的情况下 图像居中
            img_width = image_to_draw.width()
            img_height = image_to_draw.height()
            wnd_width = rect.width()
            wnd_height = rect.height()

            if img_width > 0 and img_height > 0:
                img_ratio = img_width / img_height
                wnd_ratio = wnd_width / wnd_height

                if wnd_ratio > img_ratio:
                    # 限制高，算宽
                    scaled_height = wnd_height
                    scaled_width = int(img_ratio * scaled_height)
                else:
                    # 限制宽，算高
                    scaled_width = wnd_width
                    scaled_height = int(scaled_width / img_ratio)

                x = rect.x() + (wnd_width - scaled_width) // 2
                y = rect.y() + (wnd_height - scaled_height) // 2

                target_rect = QtCore.QRect(x, y, scaled_width, scaled_height)
                painter.drawImage(target_rect, image_to_draw)
                painter.end()
                return
            painter.drawImage(self.rect(), image_to_draw)
            painter.end()
        else:
            # 没有图像时显示文字提示
            painter.fillRect(rect, QtGui.QColor(0, 0, 0))
            painter.setPen(QtGui.QColor(255, 255, 255))
            painter.setFont(QtGui.QFont("Arial", 14))
            painter.drawText(rect, Qt.AlignCenter, "无信号，等待连接...")
            painter.end()
   
    def setImage(self,image:QtGui.QImage)->None:
        """设置要显示的图像"""
        self.fps+=1
        if image is not None:
            # 缩放图像并保存
            self.current_image=image
            # 触发重绘
            self.update()
        
    def update_fps(self):
        self.fps_collected.emit(self.fps)
        self.fps=0
    