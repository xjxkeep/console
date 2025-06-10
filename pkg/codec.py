import av
import cv2
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
import copy
import threading
from collections import deque
import time
import io
from queue import Queue
from PyQt5.QtGui import QImage, QPixmap
import asyncio

# TODO 实现一个异步的buffer 优化性能
class AsyncRingBuffer:
    def __init__(self, maxSize=0, blocked=True, timeout=None):
        self.maxSize = maxSize
        self.blocked = blocked
        self.timeout = timeout
        self.buffer = deque()
        
        # 使用线程同步原语以支持同步操作
        self.sync_semaphore = threading.Semaphore(0)
        self.sync_lock = threading.Lock()
        self.running = True
        
        # 异步版本的信号量和锁
        self._async_semaphore = None
        self._async_lock = None
        self._loop = None

    def _ensure_async_primitives(self):
        """确保异步原语在正确的事件循环中创建"""
        try:
            current_loop = asyncio.get_running_loop()
            if self._loop is None or self._loop != current_loop:
                self._loop = current_loop
                self._async_semaphore = asyncio.Semaphore(0)
                self._async_lock = asyncio.Lock()
        except RuntimeError:
            # 没有运行的事件循环
            pass

    async def _async_read(self):
        """异步读取方法"""
        self._ensure_async_primitives()
        if self._async_semaphore:
            await self._async_semaphore.acquire()
        async with self._async_lock:
            if self.buffer:
                return self.buffer.popleft()
        return b''

    def read(self, n):
        """同步读取方法，供 av.open 使用"""
        if not self.running:
            return b''
            
        acquired = self.sync_semaphore.acquire(blocking=self.blocked, timeout=self.timeout)
        if not acquired or not self.running:
            return b''
        
        with self.sync_lock:
            if self.buffer:
                data = self.buffer.popleft()
                print("sync read", n, "res:", len(data))
                return data
        return b''
    
    def size(self):
        """获取缓冲区大小"""
        with self.sync_lock:
            return len(self.buffer)
    
    async def write(self, data):
        """异步写入方法"""
        if not data:
            return
            
        print("async write", len(data))
        self._ensure_async_primitives()
        
        # 同时更新同步和异步缓冲区
        with self.sync_lock:
            self.buffer.append(data)
            current_size = len(self.buffer)
            
            # 处理最大大小限制
            if self.maxSize > 0 and current_size > self.maxSize:
                print("fifo full, dropping oldest data")
                self.buffer.popleft()
            else:
                # 释放同步信号量
                self.sync_semaphore.release()
                # 释放异步信号量
                if self._async_semaphore:
                    self._async_semaphore.release()
        
        print("async write ok")
                
    async def read_single(self):
        """异步读取单个数据"""
        return await self._async_read()
    
    def write_sync(self, data):
        """同步写入方法"""
        if not data:
            return
            
        print("sync write", len(data))
        with self.sync_lock:
            self.buffer.append(data)
            current_size = len(self.buffer)
            
            if self.maxSize > 0 and current_size > self.maxSize:
                print("fifo full, dropping oldest data")
                self.buffer.popleft()
            else:
                self.sync_semaphore.release()
        
    def close(self):
        """关闭缓冲区"""
        self.running = False
        # 释放所有等待的线程/协程
        self.sync_semaphore.release()
        if self._async_semaphore:
            self._async_semaphore.release()
    
    
class BufferStream:
    
    def __init__(self,maxSize=0,blocked=True,timeout=None):
        self.maxSize=maxSize
        self.blocked=blocked
        self.timeout=timeout
        self.buffer = deque()
        self.semaphore = threading.Semaphore(0)
        self.running = True
        self.lock = threading.Lock()  # Add a lock for buffer operations
        self.buffer_size=0

    def size(self):
        with self.lock:
            return self.buffer_size

    def __read(self):
        if not self.running:
            return None
        acquired = self.semaphore.acquire(blocking=self.blocked,timeout=self.timeout)
        if not self.running or not acquired:
            return None
        
        with self.lock:  # Use lock to ensure thread-safe access to the buffer
            self.buffer_size-=1
            return self.buffer.popleft()

    def __write(self, data):
        with self.lock:  # Use lock to ensure thread-safe access to the buffer
            self.buffer.append(data)
            self.buffer_size+=1
            if self.maxSize>0 and self.buffer_size>self.maxSize:
                print("fifo full")
                self.buffer.popleft()
                self.buffer_size-=1
            else:
                self.semaphore.release()

    def __write_front(self, data):
        with self.lock:  # Use lock to ensure thread-safe access to the buffer
            self.buffer.appendleft(data)
        self.semaphore.release()

    def readSingle(self):
        result = self.__read()
        return result
    
    # def read(self, n):
    #     data = self.__read()
    #     if not data:
    #         return data
        
    #     while len(data) < n and self.running:
    #         tmp = self.__read()
    #         if not tmp:
    #             return data
    #         data += tmp
        
    #     if len(data) > n:
    #         self.__write_front(data[n:])
    #     return data[:n]

    def read(self, n):
        
        return self.__read()
    
    def write(self, data):
        self.__write(data)

    
    def close(self):
        self.running = False
        self.semaphore.release()

class HighBuffer:
    def __init__(self):
        self.buffer=io.BytesIO()
        self.semaphore = threading.Semaphore(0)
        self.running = True
        self.lock = threading.Lock()
        self.read_pos=0
        self.read_count=0
        self.buffer_size=0
        self.read_latency=0.0
        self.write_count=0
        self.write_latency=0.0
        
    
    
    def read(self,n):
        start_time=time.time()
        for _ in range(n):
            self.semaphore.acquire()
        with self.lock:
            self.buffer.seek(self.read_pos)
            data=self.buffer.read(n)
            self.buffer_size-=len(data)
            self.read_pos+=len(data)
            if self.read_pos>1024*1024*1024:
                self.buffer=io.BytesIO(self.buffer.getvalue()[self.read_pos:])
                self.read_pos=0
        self.read_latency+=time.time()-start_time
        self.read_count+=1
        
        return data
    def write(self,data):
        start_time=time.time()
        with self.lock:
            self.buffer.seek(0,io.SEEK_END)
            self.buffer.write(data)
            self.semaphore.release(len(data))
            self.buffer_size+=len(data)
            self.write_count+=1
            self.write_latency+=time.time()-start_time

class H264Decoder(QObject):
    frame_decoded = pyqtSignal()
    def __init__(self,format='h264'):
        super().__init__()
        self.stream=BufferStream()
        self.frames=Queue()
        self.lock=threading.Lock()
        self.decode_thread = threading.Thread(target=self.__decode_frames,daemon=True)
        self.has_data = False
        self.running = True
        self.format=format
        self.decode_thread.start()

    def close(self):
        self.running = False
        
        if self.decode_thread.is_alive():
            self.decode_thread.join()

    def write(self, data):
        if len(data)==0:
            return
        self.stream.write(data)

    def get_frame(self):
        return self.frames.get()
    
    def change_format(self,format):
        with self.lock:
            self.format=format
            self.container.close()
            self.container = av.open(self.stream,format=self.format)
            
        

    def __decode_frames(self):
        self.container = av.open(self.stream,format=self.format)
        print("start decode")
        while self.running:
            try:
                with self.lock:
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
                            print("decode thread exit")
                            return
            except Exception as e:
                pass
        self.stream.close()
        self.container.close()
        
class H264Encoder(QObject):
    frame_encoded = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.buffer=BufferStream()
        self.running = True
        
        self.encode_thread = threading.Thread(target=self.__encode_frames,daemon=True)
    def start(self):
        self.running = True
        self.encode_thread.start()
    def close(self):
        self.running = False
        self.buffer.close()
        if self.encode_thread.is_alive():
            self.encode_thread.join()
        
    def write(self,data):
        self.buffer.write(data)
        self.frame_encoded.emit()
    
    def read_frame(self):
        return self.buffer.readSingle()
    
    
    def __encode_frames(self):
        
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
            print("width:",width,"height:",height,"fps:",fps)

            # 创建输出容器
            output_container = av.open(self, 'w',format='h264')
            stream = output_container.add_stream('h264', rate=fps)
            stream.width = width
            stream.height = height
            stream.pix_fmt = 'yuv420p'
            stream.gop_size=30
            # def read_frame():
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
    output_container = av.open(buffer, 'w',format='h264')
    stream = output_container.add_stream('h264', rate=fps)
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
            container = av.open(stream, format='h264')
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
    test_encode_decode()
    # test_high_buffer()
    print("done")