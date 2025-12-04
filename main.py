
# 尝试从设置文件加载日志级别
import faulthandler
import logging
from loader import SplashScreen
from PyQt5.QtWidgets import QApplication
from pkg.log_manager import log_manager
import sys
faulthandler.enable(all_threads=True)
# 使用日志管理器初始化日志
log_manager._setup_logging()
try:

    import json
    import os

    if os.path.exists(".setting.json"):
        with open(".setting.json", "r", encoding='utf-8') as f:
            settings = json.load(f)
            if "log_level" in settings:
                log_manager.set_log_level(settings["log_level"])
                logging.info(f"已从设置文件加载日志级别: {settings['log_level']}")
    app=QApplication(sys.argv)
    splash = SplashScreen()

    splash.show()
    logging.info("loading")
    from index import MainWindow
    # from qfluentwidgets import setTheme,Theme
    # setTheme(Theme.DARK)
    logging.info("start prometheus http server on port 8000")
    app.processEvents()
    m=MainWindow()
    splash.loading_complete()
    splash.finish(m)
    m.show()
    app.exec()
except Exception as e:
    logging.error(f"main error {e}")
    sys.exit(1)