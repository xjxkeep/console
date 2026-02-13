
# 尝试从设置文件加载日志级别
import logging
import multiprocessing
import os
import sys
import time

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

# 必须在 QApplication 创建之前设置属性
QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
QApplication.setAttribute(Qt.AA_UseDesktopOpenGL)

# 必须在任何 QApplication 创建之前导入 QtWebEngineWidgets
from PyQt5 import QtWebEngineWidgets

from PyQt5.QtGui import QIcon

from pkg.log_manager import log_manager


if __name__ == '__main__':
    multiprocessing.freeze_support()

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
        app.processEvents()
        logging.info("loading")

        # 后台线程导入 index 模块（含重量级依赖），splash 保持动画
        import importlib
        from threading import Thread

        result = {}

        def do_import():
            result['module'] = importlib.import_module('index')
            splash.loading_thread.set_data_loaded()

        import_thread = Thread(target=do_import, daemon=True)
        import_thread.start()

        while import_thread.is_alive():
            app.processEvents()
            time.sleep(0.01)

        m = result['module'].MainWindow()
        splash.finish(m)
        
        m.show()
        app.exec()
    except Exception as e:
        logging.error(f"main error {e}")
        sys.exit(1)
