from PyQt5.QtWidgets import *
from qfluentwidgets import *
from PyQt5.QtCore import Qt
import os
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QApplication
 # Generate QR code using qrcode library
import qrcode
from PyQt5.QtGui import QPixmap
from io import BytesIO
from view.common import BLineEdit,TLineEdit
import hid
from pkg.hid_caller import HID
from pkg.model import HIDBody
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
        self.label=BodyLabel(self.label_string or "")
        self.info=PasswordLineEdit(self) if self.secret else LineEdit(self)
        self.info.setReadOnly(True)
        self.info.setText(self.info_string or "")
        self.but=TransparentToolButton(FluentIcon.COPY.icon(),self)
        self.but.clicked.connect(self.copy)
        layout.addWidget(self.label)
        layout.addWidget(self.info)
        layout.addWidget(self.but)
        self.setLayout(layout)
    
    def setValue(self,value):
        self.info.setText(value)

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
    

    def setContent(self,content):
        self.content=content
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

    def setupUi(self):
        self.setObjectName("QRCodeDisplay")
        self.setFixedSize(200,200)
        layout=QVBoxLayout()
        self.qrcode=QLabel()
        self.qrcode.setAlignment(Qt.AlignCenter)
        self.label=BodyLabel("扫描二维码绑定设备")
        self.label.setAlignment(Qt.AlignCenter)
        self.setContent(self.content)
        layout.addWidget(self.label)
        layout.addWidget(self.qrcode)
        self.setLayout(layout)


class HIDDebug(HeaderCardWidget):
    hid_response=pyqtSignal(HIDBody)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setupUi()
        self.hid=HID(0x2207,0x0019)
        self.hid.connected.connect(self.__connected)
        self.hid.disconnected.connect(self.__disconnected)
        self.hid.data_received.connect(self.__data_received)
    
    def __connected(self):
        self.content.append("连接成功")
        self.startBut.setEnabled(True)
    
    def __disconnected(self):
        self.content.append("连接失败")
        self.startBut.setEnabled(True)
    
    def __data_received(self,data:HIDBody):
        self.content.append("接收数据:" + str(data.model_dump()))
        self.hid_response.emit(data)

    def setupUi(self):
        self.setObjectName("HIDDebug")
        self.setTitle("HID 调试")
        self.vboxLayout=QVBoxLayout()
        
        self.vendorIdInput=TLineEdit("Vendor ID","0x2207")
        self.productIdInput=TLineEdit("Product ID","0x0019")
        self.startBut=PushButton("发送请求")
        self.content=QTextEdit(self)
        self.content.setReadOnly(True)
        self.inputLine=BLineEdit(FluentIcon.SEND.icon(),parent=self)
        self.inputLine.but.clicked.connect(self.send)
        self.inputLine.setPlaceholderText("输入发送内容")
        self.startBut.clicked.connect(self.call_function)
        self.vboxLayout.addWidget(self.vendorIdInput)
        self.vboxLayout.addWidget(self.productIdInput)
        self.vboxLayout.addWidget(self.startBut)
        self.vboxLayout.addWidget(self.content)
        self.vboxLayout.addWidget(self.inputLine)
        self.vboxLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.viewLayout.addLayout(self.vboxLayout)


    def call_function(self):
        try:
            request_id=self.hid.call_function("get_device_info",{})
            print("request_id:",request_id)
        except Exception as e:
            self.content.append("响应:" + str(e))
     
    
    
    
    def send(self):
        self.content.append(self.inputLine.text()+"\n")
        self.inputLine.clear()
        
        

class DeviceInfo(HeaderCardWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setupUi()
        
    def setupUi(self):
        self.setObjectName("DeviceInfo")        
        self.setTitle("设备信息")
        layout=QVBoxLayout()
        self.qrCodeDisplay=QRCodeDisplay("https://www.baidu.com",self)
        layout.addWidget(self.qrCodeDisplay)
        self.nameBox=InfoItem(self,"设备名称","127.0.0.1:8080")
        self.versionBox=InfoItem(self,"版本号","1234567890")
        self.macBox=InfoItem(self,"设备序列号","127.0.0.1:8080")
        layout.addWidget(self.nameBox)
        layout.addWidget(self.versionBox)
        layout.addWidget(self.macBox)
        self.viewLayout.addLayout(layout)
    
    def handler_hid_response(self,response:HIDBody):
        self.qrCodeDisplay.setContent(response.returns["id"]+":"+response.returns["sub_id"])
        self.nameBox.setValue(response.returns["name"])
        self.versionBox.setValue(response.returns["version"])
        self.macBox.setValue(response.returns["mac"])



class SettingView(QWidget):
    hid_response=pyqtSignal(HIDBody)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setupUi()
        
    def setupUi(self):
        self.setObjectName("Setting")               
        self.setLayout(QHBoxLayout())
        self.deviceInfo=DeviceInfo()
        self.hid=HIDDebug()
        self.hid.hid_response.connect(self.hid_response)
        self.hid.hid_response.connect(self.deviceInfo.handler_hid_response)
        self.layout().addWidget(self.deviceInfo)
        self.layout().addWidget(self.hid)
        
        
        
        
        
if __name__ == "__main__":
    app=QApplication([])
    settingView=SettingView()
    settingView.show()
    app.exec_()