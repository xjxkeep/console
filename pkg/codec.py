import av
from collections import deque
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np

def decode_h264_stream(stream):
    # 创建一个解码器上下文
    container = av.open(stream, format='h264')
    while True: 
        # 遍历每一个帧
        for frame in container.decode(video=0):
            # 处理解码后的帧
        
            print(f"Decoded frame: {frame.height}, PTS: {frame.pts}")

            # 这里可以对frame进行进一步处理，比如显示或保存
            # 例如，使用OpenCV显示帧：
            # import cv2
            # img = frame.to_ndarray(format='bgr24')
            # cv2.imshow('Frame', img)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

class H264Decoder(QObject):
    frame_decoded = pyqtSignal(np.ndarray)
    def __init__(self):
        super().__init__()
        self.stream=H264Stream()
        self.container = av.open(self.stream,format='h264')
        self.decode_thread = threading.Thread(target=self.decode,daemon=True)
        self.decode_thread.start()

    def decode(self):
        for frame in self.container.decode(video=0):
            self.frame_decoded.emit(frame.to_ndarray(format='bgr24'))

class H264Stream:
    
    def __init__(self):
        self.buffer=deque()
        self.lock=threading.Lock()
    
    def read(self,n):
        acquired = self.lock.acquire(timeout=1)
        if not acquired:
            return bytes()
        try:
            if len(self.buffer)==0:
                return bytes()
            data=self.buffer.popleft()
            while len(data)<n and len(self.buffer)>0:
                data+=self.buffer.popleft()
            if len(data)>n:
                self.buffer.appendleft(data[n:])
            return data[:n]
        finally:
            self.lock.release()
        
    def write(self,data):
        acquired = self.lock.acquire(timeout=1)
        if not acquired:
            return
        try:
            self.buffer.append(data)
        finally:
            self.lock.release()
        


if __name__ == "__main__":
    import time
    import threading
    stream=H264Stream()

    def write_stream():
        with open('/Users/xiongjinxin/workspace/endless/console/output.h264', 'rb') as f:
            while True:
                data=f.read(1024)
                if not data:
                    break
                stream.write(data)
                time.sleep(0.1)
    threading.Thread(target=write_stream).start()

    decode_h264_stream(stream)
    print("done")