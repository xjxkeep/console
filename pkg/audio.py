import av
import sounddevice as sd
import numpy as np
from pkg.buffer import RingBytesIO,BufferStream
from PyQt5.QtCore import QObject,pyqtSignal,pyqtSlot,QThread
import sys
import time
from queue import Queue
class AudioRecorder(QObject):
    def __init__(self,scale=1,format="g726",frame_size=1024,samplerate=44100):
        super().__init__()
        self.buffer=BufferStream(maxSize=1)
        self.samplerate=samplerate
        self.frame_size=frame_size
        self.running=False
        self.scale=1
        self.format=format
        self.fifo=Queue()
        self.pts=0

    def read(self,n):
        return self.buffer.read(n)

    async def read_async(self):
        return await self.buffer.read_single_async()

    def audio_callback(self,indata,frames,time_info,status):
        if status:
            print(status,file=sys.stderr)
        pcm=np.frombuffer(indata,dtype=np.int16)
        pcm=np.clip(pcm*self.scale, -32768, 32767)
        frame=av.AudioFrame(samples=len(pcm)).from_ndarray(pcm.reshape(1, -1),format="s16",layout="mono")
        frame.sample_rate=self.samplerate
        frame.pts=self.pts
        self.pts+=len(pcm)
        self.fifo.put(frame)

    @pyqtSlot()
    def run_task(self):
        self.running=True
        self.p=None
        self.ai=None
        self.sound_device_id = sd.default.device[0]
        container=av.open(self.buffer,"w",format=self.format,buffer_size=self.frame_size)
        stream=container.add_stream(self.format,rate=self.samplerate)
        assert isinstance(stream,av.AudioStream)
        stream.layout="mono"
        stream.bit_rate=self.samplerate*16*1
        
        try:
            with sd.InputStream(
                device=self.sound_device_id,
                samplerate=self.samplerate,
                blocksize=self.frame_size,
                channels=1,
                dtype=np.int16,
                callback=self.audio_callback
            ):
                while self.running:
                    frame=self.fifo.get()
                    if frame is None:
                        break
                    for packet in stream.encode(frame):
                        container.mux(packet)
            self.fifo.put(None)
            container.close()
        except Exception as e:
            print(f"AudioRecorder run_task error: {e}")


    def close(self):
        self.running=False
        self.fifo.put(None)
        self.buffer.close()



class AudioPlayer(QObject):
    def __init__(self,format="g726",scale=1,frame_size=1024,samplerate=44100):
        super().__init__()
        self.reader=BufferStream(maxSize=1)
        self.format=format
        self.scale=scale
        self.frame_size=frame_size
        self.running=False
        self.samplerate=samplerate
        self.fifo=Queue()
   
    def write(self,data):
        self.reader.write(data)

    def audio_callback(self,outdata,frames,time_info,status):
        data=self.fifo.get()
        if data is None:
            outdata[:]=0
            return False
        else:
            outdata[:]=data
            return True

    @pyqtSlot()
    def run_task(self):
        self.sound_device_id = sd.default.device[1]
        container=av.open(self.reader,"r",format=self.format,buffer_size=self.frame_size)
        stream = container.streams.audio[0]
        assert isinstance(stream,av.AudioStream)
        stream.layout="mono"
        stream.bit_rate=self.samplerate*16*1
        
        try:
            with sd.OutputStream(
                device=self.sound_device_id,
                samplerate=self.samplerate,
                blocksize=self.frame_size,
                channels=1,
                dtype=np.int16,
                callback=self.audio_callback
            ):
                while self.running:
                    for frame in container.decode(stream):
                        pcm=frame.to_ndarray()
                        pcm=np.clip(pcm*self.scale, -32768, 32767)
                        if not self.running: break
                        self.fifo.put(pcm)
         
            container.close()
        except Exception as e:
            print(f"AudioPlayer run_task error: {e}")
      
    
    @pyqtSlot()
    def close(self):
        self.running=False
        self.fifo.put(None)
        self.reader.close()

        
