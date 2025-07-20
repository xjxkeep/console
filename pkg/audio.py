import av
import pyaudio
import numpy as np
from pkg.buffer import RingBytesIO,BufferStream
import threading

class AudioRecorder:
    def __init__(self,scale=1,format="g726"):
        self.buffer=BufferStream()
        self.p=pyaudio.PyAudio()
        self.ai=self.p.open(format=pyaudio.paInt16, channels=1, rate=8000, input=True,start=False)
        self.running=False
        self.scale=1
        self.thread=None
        self.format=format

    def start(self):
        if self.running:
            return
        self.running=True
        self.ai.start_stream()
        self.thread=threading.Thread(target=self.__run,daemon=True)
        self.thread.start()

    def read(self,n):
        return self.buffer.read(n)

    async def read_async(self):
        return await self.buffer.read_single_async()

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
        if not self.running:
            return
        self.running=False
        self.buffer.close()
        self.ai.close()
        self.p.terminate()
        if self.thread:
            self.thread.join()

class AudioPlayer:
    def __init__(self,format="g726",scale=1):
        self.reader=BufferStream()
        self.p=pyaudio.PyAudio()
        self.ao=self.p.open(format=pyaudio.paInt16, channels=1, rate=8000, output=True,start=False)
        self.running=False
        self.format=format
        self.scale=scale
        self.thread=None

    def start(self):
        if self.running:
            return
        self.running=True
        self.ao.start_stream()
        self.thread=threading.Thread(target=self.__run,daemon=True)
        self.thread.start()

    def write(self,data):
        self.reader.write(data)


    def __run(self):
        container=av.open(self.reader,"r",format=self.format)
        stream = container.streams.audio[0]
        assert isinstance(stream,av.AudioStream)
        stream.layout="mono"
        stream.bit_rate=32000
        for frame in container.decode(stream):
            pcm=frame.to_ndarray()
            pcm=np.clip(pcm*self.scale, -32768, 32767)
            if self.running:
                self.ao.write(pcm.tobytes())
            else:
                break
        container.close()
        self.ao.close()
        self.p.terminate()
    
    def close(self):
        if not self.running:
            return
        self.running=False
        self.reader.close() 
        self.ao.close()
        self.p.terminate()
        if self.thread:
            self.thread.join()