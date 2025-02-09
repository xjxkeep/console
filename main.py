from view.monitor import Monitor
import sys
from PyQt5.QtWidgets import QApplication



app=QApplication(sys.argv)
m=Monitor()
m.show()
app.exec()


