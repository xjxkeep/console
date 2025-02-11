from PyQt5.QtCore import QObject,pyqtSignal
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
        
        self.thread=threading.Thread(target=self.update,daemon=True)
        self.thread.start()
        
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
        pygame.init()
        pygame.joystick.init()
        while self.running:
            if not self.joystick or self.device_id is None:
                time.sleep(0.1)
                continue
            time.sleep(0.02)
            for event in pygame.event.get():
                if event.type == pygame.JOYAXISMOTION:
                    # 获取摇杆值（范围从-1到1）并转换为0到100
                    axis_id = event.axis + 1  # 通道号从1开始
                    current_value = int(event.value * 50) + 50
                    self.signal.emit(axis_id, current_value)
                
                elif event.type == pygame.JOYBUTTONDOWN:
                    # 按钮按下时发送值100
                    channel = event.button + self.joystick.get_numaxes() + 1
                    self.signal.emit(channel, 100)
                    
                elif event.type == pygame.JOYBUTTONUP:
                    # 按钮释放时发送值0
                    channel = event.button + self.joystick.get_numaxes() + 1
                    self.signal.emit(channel, 0)
    def close(self):
        self.running=False
        self.thread.join()
        pygame.quit()


