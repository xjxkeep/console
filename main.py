import logging
from loader import SplashScreen
from PyQt5.QtWidgets import QApplication
import sys
logging.basicConfig(
    level=logging.INFO,  # 日志级别
    format="%(asctime)s - %(levelname)s - %(message)s"  # 格式
)


app=QApplication(sys.argv)
splash = SplashScreen()

splash.show()
logging.info("loading")
from index import MainWindow
from prometheus_client import start_http_server
start_http_server(8000)
logging.info("start prometheus http server on port 8000")
app.processEvents()
m=MainWindow()
splash.loading_complete()
splash.finish(m)
m.show()
app.exec()