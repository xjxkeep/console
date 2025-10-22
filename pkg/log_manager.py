"""
日志管理器 - 提供动态日志级别设置功能
"""
import logging
import os
from typing import Optional

try:
    from PyQt5.QtCore import QObject, pyqtSignal
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    # 创建模拟的QObject和pyqtSignal
    class QObject:
        def __init__(self):
            pass
    
    def pyqtSignal(*args, **kwargs):
        class MockSignal:
            def emit(self, *args):
                pass
            def connect(self, *args):
                pass
        return MockSignal()


class LogManager(QObject):
    """日志管理器类"""
    
    # 信号：日志级别改变时发出
    log_level_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.current_level = logging.DEBUG
        self.log_file_path = "app.log"
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志配置"""
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # 文件处理器
        file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        
        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(self.current_level)
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        
        # 避免重复添加处理器
        if len(root_logger.handlers) > 2:
            for handler in root_logger.handlers[2:]:
                root_logger.removeHandler(handler)
    
    def set_log_level(self, level: str) -> bool:
        """
        设置日志级别
        
        Args:
            level: 日志级别字符串 ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
            
        Returns:
            bool: 设置是否成功
        """
        try:
            # 获取日志级别常量
            level_constant = getattr(logging, level.upper())
            
            # 更新根日志记录器级别
            root_logger = logging.getLogger()
            root_logger.setLevel(level_constant)
            
            # 更新所有处理器级别
            for handler in root_logger.handlers:
                handler.setLevel(level_constant)
            
            self.current_level = level_constant
            
            # 发出信号
            self.log_level_changed.emit(level.upper())
            
            logging.info(f"日志级别已设置为: {level.upper()}")
            return True
            
        except AttributeError:
            logging.error(f"无效的日志级别: {level}")
            return False
        except Exception as e:
            logging.error(f"设置日志级别时出错: {e}")
            return False
    
    def get_log_level(self) -> str:
        """获取当前日志级别"""
        level_names = {
            logging.DEBUG: 'DEBUG',
            logging.INFO: 'INFO', 
            logging.WARNING: 'WARNING',
            logging.ERROR: 'ERROR',
            logging.CRITICAL: 'CRITICAL'
        }
        return level_names.get(self.current_level, 'DEBUG')
    
    def get_available_levels(self) -> list:
        """获取可用的日志级别列表"""
        return ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    
    def clear_log_file(self):
        """清空日志文件"""
        try:
            if os.path.exists(self.log_file_path):
                with open(self.log_file_path, 'w', encoding='utf-8') as f:
                    f.write('')
                logging.info("日志文件已清空")
        except Exception as e:
            logging.error(f"清空日志文件时出错: {e}")
    
    def get_log_file_size(self) -> int:
        """获取日志文件大小（字节）"""
        try:
            if os.path.exists(self.log_file_path):
                return os.path.getsize(self.log_file_path)
            return 0
        except Exception as e:
            logging.error(f"获取日志文件大小时出错: {e}")
            return 0
    
    def rotate_log_file(self, max_size_mb: int = 10):
        """
        日志文件轮转
        
        Args:
            max_size_mb: 最大文件大小（MB）
        """
        try:
            max_size_bytes = max_size_mb * 1024 * 1024
            if self.get_log_file_size() > max_size_bytes:
                # 重命名当前日志文件
                backup_name = f"{self.log_file_path}.backup"
                if os.path.exists(backup_name):
                    os.remove(backup_name)
                os.rename(self.log_file_path, backup_name)
                
                # 重新创建日志文件
                self._setup_logging()
                logging.info(f"日志文件已轮转，大小超过 {max_size_mb}MB")
        except Exception as e:
            logging.error(f"日志文件轮转时出错: {e}")


# 全局日志管理器实例
log_manager = LogManager()
