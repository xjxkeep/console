import av
import numpy as np
import pyaudio
import threading
from pkg.codec import AsyncRingBuffer,BufferStream
import time
from contextlib import contextmanager
import asyncio
@contextmanager
def measure_time(name):
    start_time = time.time()
    yield
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"{name} using {round(execution_time*1000):.4f} ms")


# TODO 异步性能优化
class AsyncAudioEncoder:
    def __init__(self, format="g726", output=None, rate=8000, channels=1):
        self.format = format
        self.channels = channels
        self.rate = rate
        self.chunk = 160
        self.pts = 0  # 初始化PTS
        self.p = pyaudio.PyAudio()
        self.output = output
        self.outf = None
        self.out_buffer = AsyncRingBuffer()
        self.container = None
        self.out_stream = None
       
        self.running = True
        self.fps = 0
        
        # 在单独的线程中运行事件循环
        self.loop = None
        self.encode_thread = None
        self._start_async_loop()
        
        threading.Thread(target=self.__fps, daemon=True).start()

    def _start_async_loop(self):
        """在单独线程中启动事件循环"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.encode_task = self.loop.create_task(self.__encode_frames())
            try:
                self.loop.run_forever()
            except Exception as e:
                print(f"Async loop error: {e}")
            finally:
                self.loop.close()
        
        self.encode_thread = threading.Thread(target=run_loop, daemon=True)
        self.encode_thread.start()
        


    def __fps(self):
        while True:
            print(f"audio encode fps:{self.fps}")
            self.fps=0
            time.sleep(1)
        
    def close(self):
        self.running = False
        if self.loop and not self.loop.is_closed():
            # 停止事件循环
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        if self.encode_thread:
            self.encode_thread.join(timeout=1.0)
        
        self.out_buffer.close()

    async def write(self, data):
        if len(data)==0:
            return 0
        # 这个方法用于av.open的回调
        await self.out_buffer.write(data)
        return len(data)

    
    async def read_frame(self):
        data=await self.out_buffer.read_single()
        return data
                

    async def __encode_frames(self):
        self.audio_stream = self.p.open(format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.chunk)
        self.audio_stream.start_stream()
        
        # 创建容器和输出流
        self.container = av.open(self,mode="w",format=self.format,buffer_size=1024)
        self.out_stream = self.container.add_stream(self.format, rate=self.rate)
        self.out_stream.layout = 'mono'
        self.out_stream.sample_rate=self.rate
        
        # 如果是G.726格式，设置比特率
        if self.format == "g726":
            self.out_stream.bit_rate = 32000  # G.726通常使用32kbps
        else:
            self.out_stream.bit_rate = 16000
            
        if self.output:
            self.outf=open(self.output,"wb")

        print(f"start encode format:{self.format} rate:{self.rate} channels:{self.channels}")
        while self.running:
            try:
                data = self.audio_stream.read(self.chunk, exception_on_overflow=False)  # 防止溢出
                audio_data = np.frombuffer(data,dtype=np.int16)
                
                # 创建音频帧
                frame = av.AudioFrame.from_ndarray(np.expand_dims(audio_data, axis=0), format="s16",layout='mono')
                frame.sample_rate = self.rate
                frame.pts = self.pts
                self.pts += self.chunk
                
                # 编码帧
                for packet in self.out_stream.encode(frame):
                    # print("encode packet",packet.size)  # 减少打印输出
                    # 写入容器
                    self.fps+=1
                    await self.out_buffer.write(bytes(packet))
                    
            except Exception as e:
                print(f"Encoding error: {e}")
            
        
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.p.terminate()
        if self.outf:
            self.outf.close()



class AsyncAudioPlayer:
    def __init__(self, format="mp3") -> None:
        self.format = format
        self.running = True
        self.rate = 8000
        self.stream = AsyncRingBuffer()
        self.pcm_buffer = AsyncRingBuffer()
        self.fps = 0
        self.play_sign = threading.Lock()
        self.play_sign.acquire()
        
        # 在单独的线程中运行事件循环
        self.loop = None
        self.decode_thread = None
        self._start_async_loop()
        
        threading.Thread(target=self.__fps, daemon=True).start()
        threading.Thread(target=self.__play, daemon=True).start()

    def _start_async_loop(self):
        """在单独线程中启动事件循环"""
        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.decode_task = self.loop.create_task(self.__decode_frames())
            try:
                self.loop.run_forever()
            except Exception as e:
                print(f"Async loop error: {e}")
            finally:
                self.loop.close()
        
        self.decode_thread = threading.Thread(target=run_loop, daemon=True)
        self.decode_thread.start()
        
        # 等待循环启动
        import time
        time.sleep(0.1)
    
    def __fps(self):
        while self.running:
            print("audio decode fps:", self.fps)
            self.fps = 0
            time.sleep(1)
    
    def close(self):
        self.running = False
        if self.loop and not self.loop.is_closed():
            # 停止事件循环
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        if self.decode_thread:
            self.decode_thread.join(timeout=1.0)
        
        self.stream.close()
        self.pcm_buffer.close()
        
    
    async def write(self, data):
        if len(data) == 0:
            return
        await self.stream.write(data)
        return len(data)
    
    
    
    def __play(self):
        self.play_sign.acquire()
        self.pa = pyaudio.PyAudio()
        self.audio_stream = self.pa.open(format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.rate,
                    output=True)
        self.audio_stream.start_stream()
        while self.running:
            # 使用同步方式读取以避免事件循环冲突
            data = self.pcm_buffer.read(1024)  # 使用同步读取
            if data:
                print("play", len(data))
                self.audio_stream.write(data)
            time.sleep(0.01)
        
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.pa.close()
            
    
    async def __decode_frames(self):
        try:
            # 等待有足够的数据来创建容器  
            self.container = av.open(self.stream, format=self.format, buffer_size=1024)
            stream = self.container.streams.audio[0]
            print("stream ", stream.bit_rate, stream.sample_rate, stream.layout)

            self.rate = self.container.streams.audio[0].rate
            self.channels = self.container.streams.audio[0].channels
            self.play_sign.release()
            print(f"Detected audio format: rate={self.rate}, channels={self.channels}")
            
            
            print(f"start decode rate:{self.rate} layout:{self.container.streams.audio[0].layout}")
            
            while self.running:
                try:
                    for frame in self.container.decode(stream):
                        if not self.running:
                            break
                        self.fps += 1
                        # print("frame:",frame.format.name,frame.layout,frame.sample_rate)  # 减少打印
                        # 转换音频格式到PCM
                        if frame.format.name == 'fltp':
                            pcm = frame.to_ndarray()  # shape: (channels, samples), dtype: float32
                            
                            # 缩放到 int16 范围并转换
                            pcm_int16 = (pcm * 32767).astype(np.int16)
                            
                            # 如果是多声道，转为 interleaved 格式
                            if pcm_int16.shape[0] > 1:
                                pcm_int16 = pcm_int16.T  # (channels, samples) -> (samples, channels)
                            await self.pcm_buffer.write(pcm_int16.tobytes())
                            
                        elif frame.format.name == 's16':
                            pcm_int16 = frame.to_ndarray() 
                            if pcm_int16.shape[0] > 1:
                                pcm_int16 = pcm_int16.T 
                            await self.pcm_buffer.write(pcm_int16.tobytes())

                            
                        elif frame.format.name == 's16p':
                            # 处理s16p格式（平面16位整数）
                            pcm = frame.to_ndarray()
                            if pcm.shape[0] > 1:
                                pcm = pcm.T  # 转为interleaved
                            await self.pcm_buffer.write(pcm.tobytes())
                        else:
                            print(f"Unsupported audio format: {frame.format.name}")
                            
                except av.error.EOFError:
                    print("End of audio stream")
                    break
                except Exception as e:
                    print(f"Decode frame error: {e}")
                    await asyncio.sleep(0.1)  # 短暂暂停避免忙等待
                    
        except Exception as e:
            print(f"Decode initialization error: {e}")
        finally:
            if hasattr(self, 'audio_stream'):
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            if hasattr(self, 'pa'):
                self.pa.terminate()
            if hasattr(self, 'container'):
                self.container.close()


class AudioEncoder:
    def __init__(self,format="g726",output=None,rate=8000,channels=1):
        super().__init__()
        self.format=format
        self.channels=channels
        self.rate=rate
        self.chunk=160
        self.pts = 0  # 初始化PTS
        self.p = pyaudio.PyAudio()
        self.output=output
        self.outf=None
        self.out_buffer=BufferStream()
        self.container = None
        self.out_stream = None
       
        self.encode_thread = threading.Thread(target=self.__encode_frames,daemon=True)
        self.running = True
        self.encode_thread.start()
        self.fps=0
        threading.Thread(target=self.__fps,daemon=True).start()

    def __fps(self):
        while True:
            print(f"audio encode fps:{self.fps}")
            self.fps=0
            time.sleep(1)
        
    def close(self):
        self.running = False
        self.encode_thread.join()
        # 刷新编码器缓冲
        if self.out_stream and self.container:
            for packet in self.out_stream.encode(None):
                self.container.mux(packet)
            self.container.close()

    def write(self, data):
        if len(data)==0:
            return 0
        # 这个方法用于av.open的回调
        self.out_buffer.write(data)
        return len(data)

    
    def read_frame(self):
        data=self.out_buffer.readSingle()
        return data
                
    def read(self,n):
        print("read called ",n)
        return None

    def __encode_frames(self):
        self.audio_stream = self.p.open(format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.chunk)
        self.audio_stream.start_stream()
        
        # 创建容器和输出流
        self.container = av.open(self,mode="w",format=self.format,buffer_size=1024)
        self.out_stream = self.container.add_stream(self.format, rate=self.rate)
        self.out_stream.layout = 'mono'
        self.out_stream.sample_rate=self.rate
        
        # 如果是G.726格式，设置比特率
        if self.format == "g726":
            self.out_stream.bit_rate = 32000  # G.726通常使用32kbps
        else:
            self.out_stream.bit_rate = 16000
            
        if self.output:
            self.outf=open(self.output,"wb")

        print(f"start encode format:{self.format} rate:{self.rate} channels:{self.channels}")
        while self.running:
            try:
                data = self.audio_stream.read(self.chunk, exception_on_overflow=False)  # 防止溢出
                audio_data = np.frombuffer(data,dtype=np.int16)
                
                # 创建音频帧
                frame = av.AudioFrame.from_ndarray(np.expand_dims(audio_data, axis=0), format="s16",layout='mono')
                frame.sample_rate = self.rate
                frame.pts = self.pts
                self.pts += self.chunk
                
                # 编码帧
                for packet in self.out_stream.encode(frame):
                    # print("encode packet",packet.size)  # 减少打印输出
                    # 写入容器
                    self.fps+=1
                    self.out_buffer.write(bytes(packet))
                    
            except Exception as e:
                print(f"Encoding error: {e}")
            
        
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.p.terminate()
        if self.outf:
            self.outf.close()



class AudioPlayer:
    def __init__(self,format="mp3") -> None:
        super().__init__()
        self.format=format
        self.running=True
        self.rate=8000
        self.stream=BufferStream()
        self.pcm_buffer=BufferStream()
        self.decode_thread = threading.Thread(target=self.__decode_frames,daemon=True)
        self.decode_thread.start()
        self.fps=0
        self.play_sign=threading.Lock()
        self.play_sign.acquire()
        self.running=True
        
        threading.Thread(target=self.__fps,daemon=True).start()
        threading.Thread(target=self.__play,daemon=True).start()
    
    def __fps(self):
        while self.running:
            print("audio decode fps:",self.fps)
            self.fps=0
            time.sleep(1)
    
    def close(self):
        self.running=False
        self.decode_thread.join()
        
    
    def write(self,data):
        if len(data)==0:
            return
        self.stream.write(data)
        return len(data)
    
    
    
    def __play(self):
        self.play_sign.acquire()
        self.pa=pyaudio.PyAudio()
        self.audio_stream=self.pa.open(format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.rate,
                    output=True)
        self.audio_stream.start_stream()
        while self.running:
            data=self.pcm_buffer.readSingle()
            self.audio_stream.write(data)
        
        self.audio_stream.stop_stream()
        self.audio_stream.close()
        self.pa.close()
            
    
    def __decode_frames(self):
        try:
            # 等待有足够的数据来创建容器  
            self.container=av.open(self.stream,format=self.format,buffer_size=1024)
            stream=self.container.streams.audio[0]
            print("stream ",stream.bit_rate,stream.sample_rate,stream.layout)

            self.rate=self.container.streams.audio[0].rate
            self.channels=self.container.streams.audio[0].channels
            self.play_sign.release()
            print(f"Detected audio format: rate={self.rate}, channels={self.channels}")
            
            
            print(f"start decode rate:{self.rate} layout:{self.container.streams.audio[0].layout}")
            
            while self.running:
                try:
                    for frame in self.container.decode(stream):
                        if not self.running:
                            break
                        self.fps+=1
                        # print("frame:",frame.format.name,frame.layout,frame.sample_rate)  # 减少打印
                        # 转换音频格式到PCM
                        if frame.format.name == 'fltp':
                            pcm = frame.to_ndarray()  # shape: (channels, samples), dtype: float32
                            
                            # 缩放到 int16 范围并转换
                            pcm_int16 = (pcm * 32767).astype(np.int16)
                            
                            # 如果是多声道，转为 interleaved 格式
                            if pcm_int16.shape[0] > 1:
                                pcm_int16 = pcm_int16.T  # (channels, samples) -> (samples, channels)
                            self.pcm_buffer.write(pcm_int16.tobytes())
                            
                        elif frame.format.name == 's16':
                            pcm_int16=frame.to_ndarray() 
                            if pcm_int16.shape[0] > 1:
                                pcm_int16 = pcm_int16.T 
                            self.pcm_buffer.write(pcm_int16.tobytes())

                            
                        elif frame.format.name == 's16p':
                            # 处理s16p格式（平面16位整数）
                            pcm = frame.to_ndarray()
                            if pcm.shape[0] > 1:
                                pcm = pcm.T  # 转为interleaved
                            self.pcm_buffer.write(pcm.tobytes())
                        else:
                            print(f"Unsupported audio format: {frame.format.name}")
                            
                except av.error.EOFError:
                    print("End of audio stream")
                    break
                except Exception as e:
                    print(f"Decode frame error: {e}")
                    time.sleep(0.1)  # 短暂暂停避免忙等待
                    
        except Exception as e:
            print(f"Decode initialization error: {e}")
        finally:
            if hasattr(self, 'audio_stream'):
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            if hasattr(self, 'pa'):
                self.pa.terminate()
            if hasattr(self, 'container'):
                self.container.close()




def test_decoder():
    import time
    
    player=AudioPlayer(format="aac")
    with open("Imagine.aac","rb") as f:
        while True:
            data=f.read(1024)
            if len(data)==0:
                break
            player.write(data)
    time.sleep(10)


def test_async_encoder_decoder():
    
    async def test():
        encoder=AsyncAudioEncoder(format="mp3")
        player=AsyncAudioPlayer(format="mp3")
        while True:
            print("read data")
            data=await encoder.read_frame()
            print("write data",len(data))
            await player.write(data)
            await asyncio.sleep(0.01)
    asyncio.run(test())

def test_encoder_decoder():
    encoder= AudioEncoder(format="mp3")
    # 给编码器一些时间来初始化
    time.sleep(1)
    
    player=AudioPlayer(format="mp3")
    # 给播放器一些时间来初始化
    time.sleep(1)
    
    print("Starting encoder-decoder test...")
    
    try:
        frame_count = 0
        while True:
            data=encoder.read_frame()
            if len(data)==0:
                print("No data available, waiting...")
                time.sleep(0.05)  # 等待50ms让编码器产生数据
                continue
                
            frame_count += 1
            # print(f"Processing frame {frame_count}, data length: {len(data)}")
            player.write(data)
            
    except KeyboardInterrupt:
        print("Test interrupted by user")
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        print("Closing encoder and player...")
        encoder.close()
        player.close()


if __name__=="__main__":
    # test_encoder()
    # analyze_mp3_pcm_format()
    # test_decoder()
    # test_encoder_decoder()  # 运行编码解码测试
    test_async_encoder_decoder()
    # test_end_to_end_latency()  # 端到端延迟测试
    # test_low_latency_comparison()  # 低延迟对比测试
    # test_buffer_behavior()  # 测试缓冲区行为
    # simple_audio_test()  # 先测试基本功能
    # test_echo()
    # test_encoder_latency()c
    
    # test_data_encode_decode()