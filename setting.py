from PyQt5.QtWidgets import *
from qfluentwidgets import *
from PyQt5.QtCore import Qt
import os
import threading
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QApplication
 # Generate QR code using qrcode library
import qrcode
from PyQt5.QtGui import QPixmap
from io import BytesIO
from view.common import BLineEdit,TLineEdit
import hid
class InfoItem(QWidget):
    def __init__(self,parent=None,label=None,info=None,secret=False):
        super().__init__(parent)
        self.label_string=label
        self.info_string=info
        self.secret=secret
        self.setupUi()

    def setupUi(self):
        self.setObjectName("InfoBox")
        layout=QHBoxLayout()
        self.label=QLabel(self.label_string or "")
        self.info=PasswordLineEdit(self) if self.secret else LineEdit(self)
        self.info.setReadOnly(True)
        self.info.setText(self.info_string or "")
        self.but=TransparentToolButton(FluentIcon.COPY.icon(),self)
        self.but.clicked.connect(self.copy)
        layout.addWidget(self.label)
        layout.addWidget(self.info)
        layout.addWidget(self.but)
        self.setLayout(layout)
    
    def copy(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.info.text())
        InfoBar.success(
            title='Success',
            content='Copied to clipboard',
            parent=self
        )



class QRCodeDisplay(QWidget):
    def __init__(self,content=None,parent=None):
        super().__init__(parent)
        self.content=content
        self.setupUi()
        
    def setupUi(self):
        self.setObjectName("QRCodeDisplay")
        self.setFixedSize(200,200)
        layout=QVBoxLayout()
        self.qrcode=QLabel()
        self.qrcode.setAlignment(Qt.AlignCenter)
        self.label=QLabel("扫描二维码绑定设备")
        self.label.setAlignment(Qt.AlignCenter)
        if self.content:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(self.content)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert PIL image to QPixmap
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_pixmap = QPixmap()
            qr_pixmap.loadFromData(buffer.getvalue())
            
            # Scale pixmap to fit label
            qr_pixmap = qr_pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.qrcode.setPixmap(qr_pixmap)
        
        layout.addWidget(self.label)
        layout.addWidget(self.qrcode)
        self.setLayout(layout)


class HIDDebug(QGroupBox):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setupUi()
        self.device=None
        self.cond=threading.Condition()
        self.cond.acquire()
        self.readThread=threading.Thread(target=self.__read_hid,daemon=True)
        self.readThread.start()
        
    def setupUi(self):
        self.setObjectName("HIDDebug")
        self.setLayout(QVBoxLayout())
        
        self.vendorIdInput=TLineEdit("Vendor ID","123")
        self.productIdInput=TLineEdit("Product ID","123")
        self.startBut=PushButton("连接")
        self.content=QTextEdit(self)
        self.content.setReadOnly(True)
        self.inputLine=BLineEdit(FluentIcon.SEND.icon(),parent=self)
        self.inputLine.but.clicked.connect(self.send)
        self.inputLine.setPlaceholderText("输入发送内容")
        self.startBut.clicked.connect(self.connect)
        self.layout().addWidget(QLabel("HID 调试"))
        self.layout().addWidget(self.vendorIdInput)
        self.layout().addWidget(self.productIdInput)
        self.layout().addWidget(self.startBut)
        self.layout().addWidget(self.content)
        self.layout().addWidget(self.inputLine)
        self.layout().setAlignment(Qt.AlignmentFlag.AlignLeft)
        

    def connect(self):
        self.startBut.setDisabled(True)
        try:
            devices = hid.enumerate(int(self.vendorIdInput.text()), int(self.productIdInput.text()))
            if devices:
                self.content.append("连接成功")
            else:
                self.content.append("连接失败 未找到指定HID设备")
                self.startBut.setEnabled(True)
        except Exception as e:
            self.content.append(str(e))
            self.startBut.setEnabled(True)
            return
        for dev_info in devices:
            if dev_info['usage_page'] == 0xff00 and dev_info['usage'] == 0x01:
                device = hid.device()
                device.open_path(dev_info['path'])
                self.device=device
                print(f"已连接: {dev_info['manufacturer_string']} {dev_info['product_string']}")
                self.cond.release()
                break
        else:
            print("未找到匹配的 HID 接口")
            return
    
    def __read_hid(self):
        self.cond.acquire()
        print("获取到hid device 开始数据读取线程")
        self.device.set_nonblocking(False)
        while True:
            data=self.device.read(16)
            if data:
                self.content.append("接收数据:" + " ".join([hex(x) for x in data]))
            else:
                print("hid no data quit")
                break
        self.startBut.setEnabled(True)
    
    def send(self):
        self.content.append(self.inputLine.text()+"\n")
        self.inputLine.clear()
        
        

class DeviceInfo(QGroupBox):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setupUi()
        
    def setupUi(self):
        self.setObjectName("DeviceInfo")        
        layout=QVBoxLayout()
        layout.addWidget(QLabel("设备信息"))
        qrCodeDisplay=QRCodeDisplay("https://www.baidu.com",self)
        layout.addWidget(qrCodeDisplay)
        infoBox=InfoItem(self,"Server Address","127.0.0.1:8080")
        serialBox=InfoItem(self,"Serial Number","1234567890")
        tokenBox=InfoItem(self,"Token","127.0.0.1:8080",secret=True)
        layout.addWidget(InfoItem(self,"设备型号","127.0.0.1:8080"))
        
        layout.addWidget(infoBox)
        layout.addWidget(serialBox)
        layout.addWidget(tokenBox)
        self.setLayout(layout)


class SettingView(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setupUi()
        
    def setupUi(self):
        self.setObjectName("Setting")               
        self.setLayout(QHBoxLayout())
        self.deviceInfo=DeviceInfo()
        self.hid=HIDDebug()
        self.layout().addWidget(self.deviceInfo)
        self.layout().addWidget(self.hid)
        
        
        
        
        
if __name__ == "__main__":
    app=QApplication([])
    settingView=SettingView()
    settingView.show()
    app.exec_()