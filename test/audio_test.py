import av
import pyaudio
import numpy as np
from pkg.buffer import RingBytesIO,BufferStream
import threading
from queue import Queue

class AudioRecorder:
    def __init__(self,scale=1,format="g726"):
        self.buffer=BufferStream(maxSize=1)
        self.p=pyaudio.PyAudio()
        self.ai=self.p.open(format=pyaudio.paInt16, channels=1, rate=8000, input=True,start=False)
        self.running=False
        self.scale=1
        self.thread=None
        self.format=format

    def start(self):
        self.running=True
        self.ai.start_stream()
        self.thread=threading.Thread(target=self.__run,daemon=True)
        self.thread.start()

    def read(self,n):
        t=time.time()
        data=self.buffer.read(n)
        print("want read",n,"get",len(data),"cost",time.time()-t,"buffer size:",self.buffer.size())
        return  data

    def __run(self):
        container=av.open(self.buffer,"w",format=self.format)
        stream=container.add_stream(self.format,rate=8000)
        assert isinstance(stream,av.AudioStream)
        stream.layout="mono"
        stream.bit_rate=32000
        pts = 0
        while self.running:
            pcm=self.ai.read(1024)
            pcm=np.frombuffer(pcm,dtype=np.int16)
            pcm=np.clip(pcm*self.scale, -32768, 32767)
            frame=av.AudioFrame(samples=len(pcm)).from_ndarray(pcm.reshape(1, -1),format="s16",layout="mono")
            frame.sample_rate=8000
            frame.pts=pts
            pts+=len(pcm)
            for packet in stream.encode(frame):
                container.mux(packet)
        container.close()
        self.ai.close()
        self.p.terminate()

    def close(self):
        self.running=False
        self.ai.stop_stream()
        self.ai.close()
        self.p.terminate()
        if self.thread:
            self.thread.join()

class AudioPlayer:
    def __init__(self,reader,format="g726",scale=1):
        self.reader=reader
        self.p=pyaudio.PyAudio()
        self.ao=self.p.open(format=pyaudio.paInt16, channels=1, rate=8000, output=True,start=False)
        self.running=False
        self.format=format
        self.scale=scale
        self.thread=None

    def start(self):
        self.running=True
        self.ao.start_stream()
        self.thread=threading.Thread(target=self.__run,daemon=True)
        self.thread.start()

    def __run(self):
        container=av.open(self.reader,"r",format=self.format,buffer_size=1024)
        stream = container.streams.audio[0]
        assert isinstance(stream,av.AudioStream)
        stream.layout="mono"
        stream.bit_rate=32000
        for frame in container.decode(stream):
            pcm=frame.to_ndarray()
            pcm=np.clip(pcm*self.scale, -32768, 32767)
            self.ao.write(pcm.tobytes())
        container.close()
        self.ao.close()
        self.p.terminate()
    
    
    def close(self):
        self.running=False
        if self.thread:
            self.thread.join()
        self.ao.stop_stream()
        self.ao.close()
        self.p.terminate()
def g276_dec_ao_test():
    p = pyaudio.PyAudio()
    ao = p.open(format=pyaudio.paInt16, channels=1, rate=8000, output=True)

    class Reader:
        def __init__(self, filename):
            self.file = open(filename, "rb")
            
        def read(self, n):
            print(n)
            return self.file.read(n)
        
        def close(self):
            self.file.close()
            
    # 播放 G.726 文件
    with av.open(Reader("test.g726"), format="g726", buffer_size=1024) as container:
        stream = container.streams.audio[0]
        stream.layout = "mono"
        stream.rate = 8000
        # 确保码率参数正确
        if hasattr(stream, 'bit_rate'):
            stream.bit_rate = 32000
        
        for frame in container.decode(stream):
            print(frame.layout, frame.format)
            pcm = frame.to_ndarray()
            pcm=np.clip(pcm, -32768, 32767)
            ao.write(pcm.tobytes())
    
    ao.close()
    p.terminate()


def ai_enc_test():
    p = pyaudio.PyAudio()
    ai = p.open(format=pyaudio.paInt16, channels=1, rate=8000, input=True)

    class Writer:
        def __init__(self,filename):
            self.file=open(filename,"wb")

        def write(self,data):
            print(len(data))
            self.file.write(data)

        def close(self):
            self.file.close()

    with av.open(Writer("test.g726"), "w", format="g726") as container:
        stream = container.add_stream("g726", rate=8000)
        stream.layout = "mono"
        stream.bit_rate = 32000  # 16kbps
        
        # 计算正确的时间戳
        pts = 0
        
        for i in range(50):
            pcm = ai.read(1024)
            
            pcm = np.frombuffer(pcm, dtype=np.int16)
        

            bytes_cnt = len(pcm) 

            frame = av.AudioFrame(samples=bytes_cnt).from_ndarray(pcm.reshape(1, -1),format="s16",layout="mono")
            frame.sample_rate = 8000
            frame.pts = pts
            pts += bytes_cnt               # 按字节递增
                                    
            for packet in stream.encode(frame):
                container.mux(packet)
    
    ai.close()
    p.terminate()


# # 测试编码
# print("开始编码...")
# ai_enc_test()
# print("编码完成")

# # 测试播放
# print("开始播放...")
# g276_dec_ao_test()
# print("播放完成")


import time
recoder=AudioRecorder()
player=AudioPlayer(recoder)
recoder.start()
player.start()

time.sleep(60)
recoder.close()
player.close()







