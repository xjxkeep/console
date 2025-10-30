import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pkg.codec import H264Encoder, VideoDecoder
from PyQt5.QtCore import QCoreApplication, QObject, QThread, pyqtSlot, QTimer
from PyQt5.QtWidgets import QApplication
import time
import threading
from queue import Queue
import cv2
import numpy as np

class CodecTest(QObject):
    def __init__(self):
        super().__init__()
        self.encoder = H264Encoder()
        self.decoder = VideoDecoder()
        self.test_running = False
        self.decode_frame_count = 0
        self.encode_frame_count = 0
        self.encoded_data_queue = Queue()
        
        # 连接信号
        self.encoder.frame_encoded.connect(self.on_frame_encoded)
        self.decoder.frame_decoded.connect(self.on_frame_decoded)
        
        # 设置定时器来转发数据
        self.timer = QTimer()
        self.timer.timeout.connect(self.forward_encoded_data)
        
    def on_frame_encoded(self):
        """编码完成回调"""
        try:
            data = self.encoder.read_frame()
            if data:
                self.encode_frame_count += 1
                self.encoded_data_queue.put(data)
                print(f"编码帧 #{self.encode_frame_count}, 数据大小: {len(data)} bytes")
        except Exception as e:
            print(f"读取编码数据错误: {e}")
    
    def on_frame_decoded(self):
        """解码完成回调"""
        try:
            frame = self.decoder.get_frame()
            if frame:
                self.decode_frame_count += 1
                print(f"解码帧 #{self.decode_frame_count}, 尺寸: {frame.width()}x{frame.height()}")
        except Exception as e:
            print(f"获取解码帧错误: {e}")
    
    def forward_encoded_data(self):
        """转发编码数据到解码器"""
        try:
            while not self.encoded_data_queue.empty():
                data = self.encoded_data_queue.get_nowait()
                self.decoder.write(data)
        except:
            pass
    
    def test_camera_encode_decode(self):
        """测试摄像头编码解码"""
        print("开始摄像头编解码测试...")
        self.test_running = True
        
        # 启动编码线程
        encode_thread = QThread()
        self.encoder.moveToThread(encode_thread)
        encode_thread.started.connect(self.encoder.frame_encode_task)
        encode_thread.start()
        
        # 启动解码线程
        decode_thread = QThread()
        self.decoder.moveToThread(decode_thread)
        decode_thread.started.connect(self.decoder.frame_decode_task)
        decode_thread.start()
        
        # 启动定时器转发数据
        self.timer.start(10)  # 每10ms转发一次数据
        
        # 运行10秒
        start_time = time.time()
        while time.time() - start_time < 10:
            QCoreApplication.processEvents()  # 处理事件循环
            time.sleep(0.01)
        
        # 停止测试
        self.test_running = False
        self.timer.stop()
        self.encoder.close()
        self.decoder.close()
        
        print(f"总共编码了 {self.encode_frame_count} 帧")
        print(f"测试完成! 总共解码了 {self.decode_frame_count} 帧")
        print(f"编码帧率: {self.encode_frame_count / 10:.2f} fps")
        print(f"解码帧率: {self.decode_frame_count / 10:.2f} fps")
        
        # 清理线程
        encode_thread.quit()
        decode_thread.quit()
        encode_thread.wait()
        decode_thread.wait()


def main():
    app = QApplication(sys.argv)
    
    test = CodecTest()
    test.test_camera_encode_decode()
    
    app.quit()

if __name__ == "__main__":
    main()
