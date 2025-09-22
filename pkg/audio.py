import av
import pyaudio
import numpy as np
from pkg.buffer import RingBytesIO,BufferStream
from PyQt5.QtCore import QObject,pyqtSignal,pyqtSlot,QThread

class AudioRecorder(QObject):
    def __init__(self,scale=1,format="g726",frame_size=1024):
        super().__init__()
        self.buffer=BufferStream(maxSize=1)
        
        self.frame_size=frame_size
        self.running=False
        self.scale=1
        self.format=format

    def read(self,n):
        return self.buffer.read(n)

    async def read_async(self):
        return await self.buffer.read_single_async()

    @pyqtSlot()
    def run_task(self):
        self.running=True
        self.p=None
        self.ai=None
        try:
            self.p=pyaudio.PyAudio()
            self.ai=self.p.open(format=pyaudio.paInt16, channels=1, rate=8000, input=True,start=False)
            self.ai.start_stream()
            
            container=av.open(self.buffer,"w",format=self.format,buffer_size=self.frame_size)
            stream=container.add_stream(self.format,rate=8000)
            assert isinstance(stream,av.AudioStream)
            stream.layout="mono"
            stream.bit_rate=32000
            pts = 0
            while self.running:
                pcm=self.ai.read(self.frame_size,exception_on_overflow=False)
                pcm=np.frombuffer(pcm,dtype=np.int16)
                pcm=np.clip(pcm*self.scale, -32768, 32767)
                frame=av.AudioFrame(samples=len(pcm)).from_ndarray(pcm.reshape(1, -1),format="s16",layout="mono")
                frame.sample_rate=8000
                frame.pts=pts
                pts+=len(pcm)
                for packet in stream.encode(frame):
                    container.mux(packet)
            container.close()
        except Exception as e:
            print(f"AudioRecorder run_task error: {e}")
        finally:
            # 安全清理PyAudio资源
            try:
                if self.ai:
                    self.ai.stop_stream()
                    self.ai.close()
                    self.ai = None
            except Exception as e:
                print(f"Error closing audio input stream: {e}")
            try:
                if self.p:
                    self.p.terminate()
                    self.p = None
            except Exception as e:
                print(f"Error terminating PyAudio: {e}")

    @pyqtSlot()
    def close(self):

        if not self.running:
            print("AudioRecorder already closed or not running")
            return

        self.running=False
        self.buffer.close()



class AudioPlayer(QObject):
    def __init__(self,format="g726",scale=1,frame_size=1024):
        super().__init__()
        self.reader=BufferStream(maxSize=1)
        self.format=format
        self.scale=scale
        self.frame_size=frame_size
        self.running=False
   
   
    def write(self,data):
        self.reader.write(data)


    @pyqtSlot()
    def run_task(self):
        self.p=None
        self.ao=None
        try:
            self.p=pyaudio.PyAudio()
            self.ao=self.p.open(format=pyaudio.paInt16, channels=1, rate=8000, output=True,start=False)
            self.running=True
            self.ao.start_stream()
            container=av.open(self.reader,"r",format=self.format,buffer_size=self.frame_size)
            stream = container.streams.audio[0]
            assert isinstance(stream,av.AudioStream)
            stream.layout="mono"
            stream.bit_rate=32000
            for frame in container.decode(stream):
                pcm=frame.to_ndarray()
                pcm=np.clip(pcm*self.scale, -32768, 32767)
                if not self.running: break
                self.ao.write(pcm.tobytes())
            container.close()
        except Exception as e:
            print(f"AudioPlayer run_task error: {e}")
        finally:
            # 安全清理PyAudio资源
            try:
                if self.ao:
                    self.ao.stop_stream()
                    self.ao.close()
                    self.ao = None
            except Exception as e:
                print(f"Error closing audio output stream: {e}")
            try:
                if self.p:
                    self.p.terminate()
                    self.p = None
            except Exception as e:
                print(f"Error terminating PyAudio: {e}")
    
    @pyqtSlot()
    def close(self):
        if not self.running:
            print("AudioPlayer already closed or not running")
            return
        self.running=False
        self.reader.close()

        
