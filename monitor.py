from PyQt5.QtCore import Qt
from qfluentwidgets import FluentIcon,FluentIconBase,TransparentPushButton,TransparentToolButton,TransparentDropDownPushButton,RoundMenu,Action
from PyQt5.QtGui import QCloseEvent, QIcon,QColor,QImage,QPixmap
from PyQt5.QtCore import Qt,QTimer
from PyQt5.QtWidgets import *
from datetime import datetime
from pkg.quic import HighwayQuicClient
from protocol.highway_pb2 import Device,Video
from pkg.codec import H264Decoder
import time
import threading
class StatusBar(QWidget):
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
        self.battery=TransparentPushButton(QIcon("assets/svg/battery-full.svg"),"100%")
        menu = RoundMenu(parent=self)
        menu.addActions([
            Action('线路: 上海'),
            Action('线路: 北京'),
        ])
        self.channel.setMenu(menu)

        self.timer=QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update)
        self.timer.start()
        self.sync=TransparentToolButton(FluentIcon.SYNC.icon())


        layout.addWidget(self.signal)
        layout.addWidget(self.battery)

        layout.addWidget(self.upload)
        layout.addWidget(self.download)
        layout.addWidget(self.channel)
        layout.addWidget(self.fps)
        layout.addWidget(self.date)
        layout.addWidget(self.sync)
        
        
        self.setLayout(layout)
        self.setFixedHeight(50)
        self.setStyleSheet("background-color: rgb(255,0,0)")

    
    def __init__(self):
        super().__init__()
        self.setupUi()


class Monitor(QWidget):
    # TODO 视频解码卡顿

    def setupUi(self):
        self.setObjectName("Monitor")
        self.resize(800,600)
        layout=QVBoxLayout()
        self.statusBar=StatusBar()
        
        layout.addWidget(self.statusBar)

        self.display=QLabel()
        self.display.setScaledContents(True)
        self.display.setStyleSheet("background-color: rgb(255,0,0)")
        layout.addWidget(self.display)

        self.setLayout(layout)



    def __init__(self,parent=None) -> None:
        super().__init__(parent)
        
        self.setupUi()
        self.fps=0
        self.timer=QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_fps)
        self.timer.start()
        self.client=HighwayQuicClient(Device(id=1,message_type=Device.MessageType.VIDEO),host="127.0.0.1",port=30042,ca_certs="assets/tls/cert.pem",insecure=True,source_device_id=1)
        self.client.connected.connect(self.connected)
        self.decoder=H264Decoder()
        self.client.video_stream.connect(self.handle_video)
        self.decoder.frame_decoded.connect(self.display_video)
        self.client.upload_speed.connect(self.statusBar.update_upload_speed)
        self.client.download_speed.connect(self.statusBar.update_download_speed)
        self.latency=0
        self.connectDevice()
        # threading.Thread(target=self.videoDecodeTest,daemon=True).start()
    
    def videoDecodeTest(self):
        with open(r"C:\Users\xjx201\Desktop\console\pkg\output.h264","rb") as f:
            while True:
                data=f.read(9600)
                if not data:
                    break
                self.decoder.write(data)
                time.sleep(0.005)
    
    def handle_video(self,video:Video):
        self.decoder.write(video.raw)
       
        self.latency=int(time.time()*1000)%1000-video.timestamp
    
    def update_fps(self):
        self.statusBar.update_fps(self.fps)
        self.fps=0
        self.statusBar.update_latency(self.latency)
    
    def connectDevice(self):
        self.client.start()
    
    def connected(self):
        print("connected")

    def display_video(self, image):
        try:
            # 将 numpy 数组转换为 QImage
            self.fps+=1
            height, width, _ = image.shape
            bytes_per_line = 3 * width
            q_img = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
            # 将 QImage 显示在 QLabel 上
            pixmap = QPixmap.fromImage(q_img)
            self.display.setPixmap(pixmap)
        except Exception as e:
            print(f"Error displaying video: {str(e)}")

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        print("close")
        self.client.stop()
        print("client stopped")
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

    m=Monitor()
    m.show()

    app.exec()

