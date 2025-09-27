from loader import SplashScreen
from PyQt5.QtWidgets import QApplication
import sys



app=QApplication(sys.argv)
splash = SplashScreen()

splash.show()
print("loading")
from index import MainWindow
from prometheus_client import start_http_server
start_http_server(8000)
print("start prometheus http server on port 8000")
app.processEvents()
m=MainWindow()
splash.loading_complete()
splash.finish(m)
m.show()
app.exec()