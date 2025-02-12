from PyQt5.QtCore import QObject,pyqtSignal,QTimer
import pygame
import threading
import time

class ControllerBase(QObject):
    signal=pyqtSignal(int,int) # (channel,value)
    def __init__(self) -> None:
        super().__init__()
        

class JoyStick(ControllerBase):
    def __init__(self) -> None:
        super().__init__()
        # 初始化 pygame
        
        self.running=True
        self.joystick = None
        self.device_id= None
        
        self.timer=QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(50)
        
    def get_device_list(self):
        """获取所有已连接的手柄设备列表"""
        devices = []
        for i in range(pygame.joystick.get_count()):
            joy = pygame.joystick.Joystick(i)
            devices.append({
                'id': i,
                'name': joy.get_name()
            })
        return devices
    
    def init(self):
        pygame.init()
        pygame.joystick.init()
        
    def select_device(self, device_id: int):
        if self.device_id==device_id:
            return
        self.device_id=device_id
        try:
            if self.joystick:
                self.joystick.quit()
            
            if self.device_id >= pygame.joystick.get_count():
                return False
                
            self.joystick = pygame.joystick.Joystick(self.device_id)
            self.joystick.init()
            return True
        except pygame.error:
            return False
        

    def update(self):
        if not self.joystick or self.device_id is None:
            return

        pygame.event.pump()  # 更新事件状态
        # 获取所有轴的值
        if self.joystick:
            for axis in range(self.joystick.get_numaxes()):
                value = self.joystick.get_axis(axis)
                current_value = int(value * 50) + 50
                self.signal.emit(axis + 1, current_value)
            
            # 获取按钮状态
            for button in range(self.joystick.get_numbuttons()):
                value = self.joystick.get_button(button)
                channel = button + self.joystick.get_numaxes() + 1
                self.signal.emit(channel, value * 100)
    def close(self):
        self.running=False
        self.thread.join()
        pygame.quit()


