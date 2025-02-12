from monitor import Monitor
from controller import Controller
import sys
from PyQt5.QtWidgets import QApplication
from qfluentwidgets import FluentWindow,FluentIcon,NavigationItemPosition
# TODO
# 1. 封装下请求的host 等参数 统一管理 后面host走下发
# 2. 界面完善
# 3. OTA

class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Monitor")
        self.monitor=Monitor()
        self.controller=Controller()

        self.addSubInterface(self.monitor,FluentIcon.MOVIE, "Monitor")
        self.addSubInterface(self.controller,FluentIcon.GAME, "Controller")

app=QApplication(sys.argv)

m=MainWindow()
m.show()

app.exec()


