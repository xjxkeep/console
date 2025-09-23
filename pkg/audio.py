import av
import sounddevice as sd
import numpy as np
from pkg.buffer import BufferStream
from PyQt5.QtCore import QObject,pyqtSignal,pyqtSlot,QThread
import sys
import time
from queue import Queue
# g726 8000
class AudioRecorder(QObject):
    frame_encoded = pyqtSignal()
    def __init__(self,scale=1,format="g726",frame_size=1024,samplerate=8000):
        super().__init__()
        self.buffer=BufferStream(maxSize=10)
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
        frame=av.AudioFrame.from_ndarray(pcm.reshape(1, -1),layout="mono")
        frame.sample_rate=self.samplerate
        frame.pts=self.pts
        self.pts+=len(pcm)
        print("callback frame",frame)
        self.fifo.put(frame)

    @pyqtSlot()
    def run_task(self):
        self.running=True

        self.sound_device_id = sd.default.device[0]
        container=av.open(self.buffer,"w",format=self.format,buffer_size=self.frame_size)
        stream=container.add_stream(self.format,rate=self.samplerate)
        assert isinstance(stream,av.AudioStream)
        stream.layout="mono"
        stream.bit_rate=32000
        
        try:
            with sd.InputStream(
                device=self.sound_device_id,
                samplerate=self.samplerate,
                blocksize=self.frame_size,
                channels=1,
                dtype="int16",
                callback=self.audio_callback
            ):
                while self.running:
                    frame=self.fifo.get()
                    if frame is None:
                        break
                   
                    for packet in stream.encode(frame):
                        print("encode packet",packet)
                        container.mux(packet)
                        self.frame_encoded.emit()
            self.fifo.put(None)
            container.close()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"AudioRecorder run_task error: {e}")


    def close(self):
        self.running=False
        self.fifo.put(None)
        self.buffer.close()



class AudioPlayer(QObject):
    def __init__(self,format="g726",scale=1,frame_size=1024,samplerate=8000):
        super().__init__()
        self.reader=BufferStream(maxSize=10)
        self.format=format
        self.scale=scale
        self.frame_size=frame_size
        self.running=False
        self.samplerate=samplerate
        self.fifo=Queue()
   
    def write(self,data):
        print("write",len(data))
        self.reader.write(data)

    def audio_callback(self,outdata,frames,time_info,status):
        data=self.fifo.get()
        print("audio_callback get outdata",data.shape)
        if data is None:
            outdata[:]=0
            return False
        else:
            outdata[:]=data
            return self.running

    @pyqtSlot()
    def run_task(self):
        self.running=True
        self.sound_device_id = sd.default.device[1]
        container=av.open(self.reader,"r",format=self.format,buffer_size=self.frame_size)
        stream = container.streams.audio[0]
        assert isinstance(stream,av.AudioStream)
        stream.layout="mono"
        stream.bit_rate=32000
        
        try:
            with sd.OutputStream(
                device=self.sound_device_id,
                samplerate=self.samplerate,
                blocksize=self.frame_size,
                channels=1,
                dtype="int16",
                callback=self.audio_callback
            ):
                while self.running:
                    for frame in container.decode(stream):
                        print("decode frame",frame)
                        pcm=frame.to_ndarray()
                        pcm=np.clip(pcm*self.scale, -32768, 32767)
                        if not self.running: break
                        self.fifo.put(pcm.T)
         
            container.close()
        except Exception as e:
            print(f"AudioPlayer run_task error: {e}")
      
    
    @pyqtSlot()
    def close(self):
        self.running=False
        self.fifo.put(None)
        self.reader.close()

        
