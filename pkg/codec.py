import av
import cv2
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
import copy
import threading
from collections import deque
import time

class H264Stream:
    
    def __init__(self):
        self.buffer = deque()
        self.semaphore = threading.Semaphore(0)
        self.running = True

    def __read(self):
        acquired = self.semaphore.acquire(timeout=0.1)
        if not self.running or not acquired:
            return bytes()
        return self.buffer.popleft()

    def __write(self, data):
        self.buffer.append(data)
        self.semaphore.release()

    def __write_front(self, data):
        self.buffer.appendleft(data)
        self.semaphore.release()

    def read(self, n):
        data = self.__read()
        if not data:
            return data
        while len(data) < n and self.running:
            tmp=self.__read()
            if not tmp:
                return data
            data += tmp
        
        if len(data) > n:
            self.__write_front(data[n:])
        return data[:n]

    def write(self, data):
        self.__write(data)
    
    def close(self):
        self.running = False

class H264Decoder(QObject):
    frame_decoded = pyqtSignal(np.ndarray)
    def __init__(self, frame_height=1080, frame_width=1920, frame_size=None):
        super().__init__()
        self.stream=H264Stream()
        self.container = av.open(self.stream,format='h264')
        self.frame_height = frame_height
        self.frame_width = frame_width
        self.frame_size = frame_height * frame_width * 3
        self.decode_thread = threading.Thread(target=self.__decode_frames,daemon=True)
        self.has_data = False
        self.running = True
        self.decode_thread.start()

    def close(self):
        self.running = False
        self.stream.close()
        self.decode_thread.join()

    def write(self, data):
        if len(data)==0:
            return
        self.stream.write(data)
        self.has_data = True
    
    def __decode_frames(self):
        while self.running:
            if not self.has_data:
                time.sleep(0.01)
                continue
            print("start decode")
            for frame in self.container.decode(video=0):
                self.frame_decoded.emit(frame.to_ndarray(format='rgb24'))
                if not self.running:
                    print("decode thread exit")
                    return
 
        


if __name__ == "__main__":
    import time
    import threading

    def decode_h264_stream(stream):
        # 创建一个解码器上下文
        container = av.open(stream, format='h264')
        while True: 
            # 遍历每一个帧
            for frame in container.decode(video=0):
                # 处理解码后的帧
                # 这里可以对frame进行进一步处理，比如显示或保存
                # 例如，使用OpenCV显示帧：
                
                img = frame.to_ndarray(format='bgr24')
                cv2.imshow('Frame', img)
                if cv2.waitKey(1000//30) & 0xFF == ord('q'):
                    break

    stream=H264Stream()
    
    def write_stream():
        with open(r'C:\Users\xjx201\Desktop\console\pkg\output.h264', 'rb') as f:
            while True:
                data=f.read(10240)
                if not data:
                    break
                stream.write(data)
                time.sleep(0.01)
    threading.Thread(target=write_stream,daemon=True).start()
    decode_h264_stream(stream)
    # decode_h264_stream(open(r'C:\Users\xjx201\Desktop\console\pkg\output.h264', 'rb'))
    print("done")