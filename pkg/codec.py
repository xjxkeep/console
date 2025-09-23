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
        

    def close(self):
        self.running = False
        self.stream.close()

    def write(self, data):
        if len(data)==0:
            return
        self.stream.write(data)

    def get_frame(self):
        return self.frames.get()
    
    @pyqtSlot()
    def frame_decode_task(self):
        print("start decode video with format",self.transform_map[self.format])
        self.container = av.open(self.stream,format=self.transform_map[self.format],buffer_size=1024*1024*10)
        
        try:
            while self.running:
                for frame in self.container.decode(video=0):
                    image=frame.to_ndarray(format='rgb24')
                    height, width, _ = image.shape
                    bytes_per_line = 3 * width
                    q_img = QImage(image.data, width, height, bytes_per_line, QImage.Format_RGB888)
                    # Convert QImage to QPixmap
                    pixmap = QPixmap.fromImage(q_img)
                    self.frames.put(pixmap)
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
    def __init__(self):
        super().__init__()
        self.buffer=BufferStream()
        self.running = True
        
      
    def close(self):
        self.running = False
        self.buffer.close()
        
        
    def write(self,data):
        self.buffer.write(data)
        self.frame_encoded.emit()
    
    def read_frame(self):
        return self.buffer.readSingle()
    
    @pyqtSlot()
    def frame_encode_task(self):
        self.running = True
        while self.running:
            print("start encode")
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
            stream.gop_size=30

            while self.running:
                ret, frame = cap.read()
                if not ret:
                    print("无法读取视频帧")
                    break
                # 创建 PyAV 视频帧
                video_frame = av.VideoFrame.from_ndarray(frame, format='bgr24')
                video_frame.pts = int((1 / fps) * av.time_base)
                # 编码并写入输出文件
                for packet in stream.encode(video_frame):
                    output_container.mux(packet)
            output_container.close()
            cap.release()



def main():
    # 初始化摄像头
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("无法打开摄像头")
        return

    # 获取视频属性
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # 创建输出容器
    output_container = av.open('output_test.h264', 'w',format='h264')
    stream = output_container.add_stream('h264', rate=fps)
    stream.width = width
    stream.height = height
    stream.pix_fmt = 'yuv420p'

    print("开始采集并编码视频...")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法读取视频帧")
            break

        # 将 OpenCV 的 BGR 格式转换为 RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # 创建 PyAV 视频帧
        video_frame = av.VideoFrame.from_ndarray(frame_rgb, format='rgb24')
        video_frame.pts = int((1 / fps) * av.time_base)

        # 编码并写入输出文件
        for packet in stream.encode(video_frame):
            output_container.mux(packet)

        # 显示实时视频
        cv2.imshow('Frame', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # 写入剩余的帧并关闭容器
    for packet in stream.encode():
        output_container.mux(packet)
    output_container.close()

    # 释放资源
    cap.release()
    cv2.destroyAllWindows()
    print("视频采集和编码完成，保存为 output.h264")


def test_encode_decode():
    import io
    # 初始化摄像头
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("无法打开摄像头")
        return

    # 获取视频属性
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    buffer=BufferStream()
    # 创建输出容器
    output_container = av.open(buffer, 'w',format='hevc')
    stream = output_container.add_stream('hevc', rate=fps)
    stream.width = width
    stream.height = height
    stream.pix_fmt = 'yuv420p'

    def read_frame():
        print("开始采集并编码视频...")
        while True:
            ret, frame = cap.read()
            if not ret:
                print("无法读取视频帧")
                break

            # 将 OpenCV 的 BGR 格式转换为 RGB
            # frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # 创建 PyAV 视频帧
            video_frame = av.VideoFrame.from_ndarray(frame, format='bgr24')
            video_frame.pts = int((1 / fps) * av.time_base)
            # 编码并写入输出文件
            for packet in stream.encode(video_frame):
                output_container.mux(packet)

    threading.Thread(target=read_frame,daemon=True).start()
    def decode_h264_stream(stream):
            # 创建一个解码器上下文
            container = av.open(stream, format='hevc')
            while True: 
                # 遍历每一个帧
                for frame in container.decode(video=0):
                    # 处理解码后的帧
                    # 这里可以对frame进行进一步处理，比如显示或保存
                    # 例如，使用OpenCV显示帧：
                    
                    img = frame.to_ndarray(format='bgr24')
                    cv2.imshow('Frame', img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("decode exit")
                        return

    decode_h264_stream(buffer)
    # 释放资源
    cap.release()
    cv2.destroyAllWindows()


def test_hevc_encode_decode():
    def decode_h265_stream(stream):
            # 创建一个解码器上下文
            container = av.open(stream, format='hevc')
            while True: 
                # 遍历每一个帧
                for frame in container.decode(video=0):
                    # 处理解码后的帧
                    # 这里可以对frame进行进一步处理，比如显示或保存
                    # 例如，使用OpenCV显示帧：
                    
                    img = frame.to_ndarray(format='bgr24')
                    cv2.imshow('Frame', img)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        print("decode exit")
                        return
    decode_h265_stream("pkg/4k2.hevc")

def buffer_benchmark():
    buffer = HighBuffer()
    
    # 创建大量测试数据
    test_data = b'x' * 1024 * 1024  # 1MB 的数据
    iterations = 100  # 测试100次
    
    # 测试写入性能
    write_start = time.time()
    for i in range(iterations):
        buffer.write(test_data)
    write_end = time.time()
    write_time = write_end - write_start
    
    # 测试读取性能
    read_start = time.time() 
    for i in range(iterations):
        buffer.read(len(test_data))
    read_end = time.time()
    read_time = read_end - read_start
    
    total_mb = iterations * (len(test_data) / (1024 * 1024))
    
    print(f"写入 {total_mb:.2f}MB 数据:")
    print(f"总时间: {write_time:.4f}秒")
    print(f"平均速度: {total_mb/write_time:.2f}MB/s")
    print(f"每次写入平均延迟: {write_time/iterations*1000:.2f}ms")
    
    print(f"\n读取 {total_mb:.2f}MB 数据:")
    print(f"总时间: {read_time:.4f}秒") 
    print(f"平均速度: {total_mb/read_time:.2f}MB/s")
    print(f"每次读取平均延迟: {read_time/iterations*1000:.2f}ms")

def test_high_buffer():
    buffer=HighBuffer()
    buffer.write(b'1234567890')
    buffer.write(b'1234567890')
    print(buffer.read(20))
    print(buffer.read(5))

if __name__ == "__main__":
    import time
    import threading
    def test_decode():
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

        stream=BufferStream()
        
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

    # buffer_benchmark()
    test_hevc_encode_decode()
    # test_high_buffer()
    print("done")