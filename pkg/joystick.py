import importlib
import logging
import threading
import time

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
class ControllerBase(QObject):
    signal=pyqtSignal(list) # (values)
    def __init__(self) -> None:
        super().__init__()
        

class JoyStick(ControllerBase):
    def __init__(self) -> None:
        super().__init__()
        # 初始化 pygame
        
        self.running=True
        self.joystick = None
        self.device_id= None
        self._pygame_initialized = False
        self._lock = threading.Lock()  # 添加线程锁保护pygame操作
        
        self.timer=QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)
    
    
    def _lazy_init_internal(self):
        """内部初始化方法（不带锁，由调用者持有锁）"""
        global pygame
        pygame = importlib.import_module('pygame')
        pygame.init()
        pygame.joystick.init()
        self._pygame_initialized = True
        logging.info("pygame initialized")

    def lazy_init(self):
        """延迟初始化 pygame（线程安全）"""
        with self._lock:
            if not self._pygame_initialized:
                self._lazy_init_internal()
    
    def get_device_list(self):
        """获取所有已连接的手柄设备列表"""
        devices = []
        try:
            with self._lock:
                # 自动初始化 pygame（如果尚未初始化）
                if not self._pygame_initialized:
                    self._lazy_init_internal()

                # 重新初始化 joystick 子系统以检测新设备
                pygame.joystick.quit()
                pygame.joystick.init()

                for i in range(pygame.joystick.get_count()):
                    try:
                        joy = pygame.joystick.Joystick(i)
                        devices.append({
                            'id': i,
                            'name': joy.get_name()
                        })
                    except Exception as e:
                        logging.info(f"Error accessing joystick {i}: {e}")
        except Exception as e:
            logging.info(f"Error getting device list: {e}")
        return devices
    
        
    def select_device(self, device_id: int):
        if self.device_id==device_id:
            return True

        try:
            with self._lock:
                # 先关闭当前手柄
                if self.joystick:
                    try:
                        self.joystick.quit()
                    except Exception as e:
                        logging.info(f"Error quitting joystick: {e}")
                    self.joystick = None

                # 自动初始化 pygame（如果尚未初始化）
                if not self._pygame_initialized:
                    self._lazy_init_internal()

                if device_id >= pygame.joystick.get_count():
                    logging.info(f"Device ID {device_id} out of range")
                    return False

                self.joystick = pygame.joystick.Joystick(device_id)
                self.joystick.init()
                self.device_id = device_id
                logging.info(f"Selected joystick device {device_id}: {self.joystick.get_name()}")
                return True
        except pygame.error as e:
            logging.info(f"Pygame error selecting device: {e}")
            return False
        except Exception as e:
            logging.info(f"Error selecting device: {e}")
            return False
        

    def update(self):
        if not self.running or not self.joystick or self.device_id is None:
            return

        try:
            with self._lock:
                if not self.joystick:
                    return
                    
                pygame.event.pump()  # 更新事件状态
                # 获取所有轴的值
                values=[]
                for axis in range(self.joystick.get_numaxes()):
                    value = self.joystick.get_axis(axis)
                    current_value = int(value * 50) + 50
                    values.append(current_value)
                
                # 获取按钮状态
                for button in range(self.joystick.get_numbuttons()):
                    value = self.joystick.get_button(button)
                    values.append(value * 100)
                self.signal.emit(values)
        except Exception as e:
            logging.info(f"Error in joystick update: {e}")
            # 如果出现错误，尝试重新初始化手柄
            self._handle_joystick_error()
    
    def _handle_joystick_error(self):
        """处理手柄错误，尝试重新连接"""
        try:
            with self._lock:
                if self.joystick:
                    try:
                        self.joystick.quit()
                    except:
                        pass
                    self.joystick = None
                
                # 尝试重新选择设备
                if self.device_id is not None:
                    self.select_device(self.device_id)
        except Exception as e:
            logging.info(f"Error handling joystick error: {e}")
    
    def close(self):
        """优雅关闭手柄组件"""
        logging.info("Closing joystick...")
        
        # 停止定时器
        if self.timer:
            self.timer.stop()
            logging.info("joystick timer stop")
        
        # 设置运行标志为False
        self.running = False
        
        try:
            with self._lock:
                # 关闭当前手柄
                if self.joystick:
                    try:
                        self.joystick.quit()
                        logging.info("joystick device quit")
                    except Exception as e:
                        logging.info(f"Error quitting joystick device: {e}")
                    self.joystick = None
                
                # 关闭pygame
                if self._pygame_initialized:
                    try:
                        pygame.quit()
                        self._pygame_initialized = False
                        logging.info("pygame quit")
                    except Exception as e:
                        logging.info(f"Error quitting pygame: {e}")
        except Exception as e:
            logging.info(f"Error in joystick close: {e}")
        
        logging.info("joystick close completed")


if __name__=="__main__":
    logging.basicConfig(level=logging.INFO)
    joystick=JoyStick()

    devices = joystick.get_device_list()
    logging.info(f"Found devices: {devices}")

    if devices:
        joystick.select_device(0)
        time.sleep(2)

    joystick.close()
