import av
import cv2
from PyQt5.QtCore import QObject, pyqtSignal,pyqtSlot
import numpy as np
import copy
import threading
from collections import deque
import time
import io
from queue import Queue
from PyQt5.QtGui import QImage, QPixmap

from pkg.buffer import BufferStream
from pkg.metric import *


class H264Decoder(QObject):
    frame_decoded = pyqtSignal()
    def __init__(self,format='h264'):
        super().__init__()
        self.transform_map={
            "H.264":"h264",
            "H.265":"hevc",
            "h264":"h264",
            "hevc":"hevc",
        }
        self.stream=BufferStream()
        self.frames=Queue()
        self.format=format
        self.has_data = False
        self.running = True
        self.frame_count=0
        

    def close(self):
        self.running = False
        self.stream.close()

    def write(self, data):
        if len(data)==0:
            return
        # if data.startswith(b"\x00\x00\x00\x01"):
        #     print("get decoder v1 nal",data[4]&0x1f)
        # elif data.startswith(b"\x00\x00\x01"):
        #     print("get decoder v2 nal",data[3]&0x1f)
        # else:
        #     print("get decoder illegal nal",len(data))
        self.stream.write(data)

    def get_frame(self):
        DECODER_FIFO_SIZE.dec()
        return self.frames.get()
    

    def frame_decode_task(self):
        if not self.running:
            return
        print("start decode video with format",self.transform_map[self.format])

        self.container = av.open(self.stream,format=self.transform_map[self.format],buffer_size=1024*1024*10)
        try:
            while self.running:
                for frame in self.container.decode(video=0):
                    print("decode frame",self.frame_count,"time:",time.time())
                    self.frame_count+=1
                    DECODE_FRAME_COUNT.inc()
                    image=frame.to_ndarray(format='rgb24')
                    height, width, _ = image.shape
                    bytes_per_line = 3 * width
                    q_img = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
                    # Convert QImage to QPixmap
                    pixmap = QPixmap.fromImage(q_img)
                    self.frames.put(pixmap)
                    DECODER_FIFO_SIZE.inc()
                    self.frame_decoded.emit()
                    if not self.running:
                        print("video decode thread exit")
                        return
        except Exception as e:
            print("video decode error",e)
            pass
        self.stream.close()
        if self.container:
            self.container.close()
        print("video decode thread exit")
        
class H264Encoder(QObject):
    frame_encoded = pyqtSignal()
    frame_collected = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.buffer=BufferStream()
        self.running = True
        self.frame_count=0
        self.camera_buffer=Queue()
        
      
    def close(self):
        self.running = False
        self.buffer.close()
        
        
    def write(self,data:bytes):
        # 这里写入并不是一个完整的NALU
        self.buffer.write(data)
        self.frame_encoded.emit()
        
    
    def read_frame(self):
        return self.buffer.readSingle()
    
    def read_camera(self):
        return self.camera_buffer.get()
    


    @pyqtSlot()
    def frame_encode_task(self):
        if not self.running:
            return
        print("start encode")
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("无法打开摄像头")
                return

            # 获取视频属性
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            if fps == 0:
                fps = 30
            print("width:",width,"height:",height,"fps:",fps)


            # 创建输出容器
            output_container = av.open(self, 'w',format='h264')
            stream = output_container.add_stream('h264', rate=fps)
            stream.width = width
            stream.height = height
            stream.pix_fmt = 'yuv420p'
            stream.codec_context.gop_size=30

            
            while self.running:
                # if self.frame_count>0:
                #     time.sleep(1)
                self.frame_count+=1
                ret, frame = cap.read()
                if not ret:
                    print("无法读取视频帧")
                    break
                
                # 将OpenCV帧(frame)转换为QPixmap
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                self.camera_buffer.put(pixmap)
                self.frame_collected.emit()
                
                # 创建 PyAV 视频帧
                video_frame = av.VideoFrame.from_ndarray(frame, format='bgr24')
                # 正确设置PTS（使用帧计数）
                video_frame.pts = self.frame_count
                
                # 编码并写入输出文件
                for packet in stream.encode(video_frame):
                    output_container.mux(packet)
                # print("encode frame",self.frame_count,"time:",time.time())
                
                
            
        except Exception as e:
            print("video encode error",e)
            pass
        output_container.close()
        cap.release()
        print("video encode thread exit")



