from monitor import Monitor
import sys
from PyQt5.QtWidgets import QApplication

# TODO
# 1. 封装下请求的host 等参数 统一管理 后面host走下发
# 2. 界面完善
# 3. OTA

app=QApplication(sys.argv)

m=Monitor()
m.show()

app.exec()


