from loader import SplashScreen
from PyQt5.QtWidgets import QApplication
import sys



app=QApplication(sys.argv)
splash = SplashScreen()

splash.show()
print("loading")
from index import MainWindow
app.processEvents()
m=MainWindow()
splash.loading_complete()
splash.finish(m)
m.show()
app.exec()