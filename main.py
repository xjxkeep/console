
# 尝试从设置文件加载日志级别
import faulthandler
import logging
import os
import sys

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from pkg.log_manager import log_manager

faulthandler.enable(all_threads=True)
# 使用日志管理器初始化日志
log_manager._setup_logging()

try:
    app = QApplication(sys.argv)

    # 设置应用程序图标
    icon_path = os.path.join(os.path.dirname(__file__), "assets/images/logo.jpg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 从 QSettings 加载日志级别
    from pkg.settings_manager import settings_manager
    log_level = settings_manager.log_level
    if log_level:
        log_manager.set_log_level(log_level)
        logging.info(f"Loaded log level from settings: {log_level}")

    from loader import SplashScreen
    splash = SplashScreen()

    splash.show()
    logging.info("loading")
    from index import MainWindow
    # from qfluentwidgets import setTheme,Theme
    # setTheme(Theme.DARK)
    logging.info("start prometheus http server on port 8000")
    app.processEvents()
    m = MainWindow()
    splash.loading_complete()
    splash.finish(m)
    m.show()
    app.exec()
except Exception as e:
    logging.error(f"main error {e}")
    sys.exit(1)