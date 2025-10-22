import asyncio
from asyncio import Queue
from collections import deque
import logging
import os
import ssl
import time
from typing import List, cast

from PyQt5.QtCore import QMetaObject, QObject, QThread, Qt, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QApplication
from aioquic.asyncio.client import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import ConnectionTerminated, DatagramFrameReceived, QuicEvent
from google.protobuf.message import Message
import numpy as np

from pkg.audio import AudioPlayer, AudioRecorder
from pkg.codec import H264Decoder, H264Encoder
from pkg.fec import FECCodec
from pkg.metric import *
from pkg.model import Setting
from pkg.crc import calculate_uint16_crc8
from protocol.highway_pb2 import (
    Audio,
    Control,
    Device,
    DeviceParam,
    File,
    Register,
    Video,
)



class HighwayClientProtocol(QuicConnectionProtocol,QObject):
    quic_connection_lost = pyqtSignal()
    datagram_data_received = pyqtSignal()
    def __init__(self, *args, **kwargs) -> None:
        QuicConnectionProtocol.__init__(self, *args, **kwargs)
        QObject.__init__(self)
        self.codec=FECCodec(block_size=1024,timeout_seconds=5.0,max_buffer_size=1000)
        self.codec.data_decoded.connect(self.datagram_data_received.emit)   
    def quic_event_received(self, event: QuicEvent) -> None:
        if isinstance(event, ConnectionTerminated):
            self.quic_connection_lost.emit()
        elif isinstance(event, DatagramFrameReceived):
            logging.debug("datagram frame received len",len(event.data))
            self.codec.add_package(event.data)
        return super().quic_event_received(event)
    
    def send_datagram(self,data:bytes):
        for packet in self.codec.encode(data):
            self._quic.send_datagram_frame(packet)
            
        self.transmit()

    def receive_datagram(self):
        if len(self.codec.data_buffer)>0:
            data=self.codec.data_buffer.popleft()
            return data



class HighwayQuicClient(QObject):
    # TODO 流写入失败 重试
    receive_video = pyqtSignal()
    connected = pyqtSignal()  # 新增连接状态信号
    connection_error = pyqtSignal(str)  # 新增错误信号
    
    upload_speed = pyqtSignal(float)
    download_speed = pyqtSignal(float)
    latency = pyqtSignal(int)
    file_send_progress = pyqtSignal(str,int)
    
    video_stream_failed = pyqtSignal(str)
    control_stream_failed = pyqtSignal(str)
    input_wave_data = pyqtSignal(np.ndarray)

    device_param_ready = pyqtSignal(DeviceParam)
    
    
    def __init__(self, setting:Setting) -> None:
        super().__init__()
        self.setting=setting
        self.client = None
        self.reader = None
        self.writer = None
        self.loop = None
        self.running = False
        self.upload_bytes = 0
        self.download_bytes = 0
        self.main_thread=QThread()
        
        
        self.send_frame_count=0
        

        
        self.control_stream_queue=Queue()
        self.latency_sum=0
        self.frame_latency_sum=0
        self.frame_slice_count=0
        self.latency_count=0
        # QUIC configuration
        self.configuration = QuicConfiguration(
            alpn_protocols=["HLD"], 
            is_client=True,
            max_datagram_frame_size=65536,  # 启用 datagram 支持，设置最大大小
            max_datagram_size=1200,  # 单个 datagram 最大大小
        )

        if self.setting.insecure:
            self.configuration.verify_mode = ssl.CERT_NONE
        self.video_stream_failed.connect(self.reconnect_video_stream)
        self.control_stream_failed.connect(self.reconnect_control_stream)
        
        
        # 视频解码
        self.video_decoder_thread=QThread()
        self.video_decoder_worker=H264Decoder()
        self.video_decoder_worker.frame_decoded.connect(self.receive_video.emit)
        self.video_decoder_worker.moveToThread(self.video_decoder_thread)
        self.video_decoder_thread.started.connect(self.video_decoder_worker.frame_decode_task)
        self.video_decoder_thread.finished.connect(self.video_decoder_worker.deleteLater)
        
        # 视频编码
        self.video_test_mode=0 # 0: stream 1: datagram 2: without send
        self.video_encoder_thread=QThread()
        self.video_encoder_worker=H264Encoder()
        self.video_encoder_worker.frame_encoded.connect(self.send_video)
        self.video_encoder_worker.moveToThread(self.video_encoder_thread)
        self.video_encoder_thread.started.connect(self.video_encoder_worker.frame_encode_task)
        self.video_encoder_thread.finished.connect(self.video_encoder_worker.deleteLater)
        
        
        # 音频编码和播放
        self.audio_encoder_worker=AudioRecorder(format="g726")
        self.audio_player_worker=AudioPlayer(format="g726")
        self.audio_encoder_thread=QThread()
        self.audio_player_thread=QThread()
        self.audio_encoder_worker.moveToThread(self.audio_encoder_thread)
        self.audio_player_worker.moveToThread(self.audio_player_thread)
        self.audio_encoder_thread.started.connect(self.audio_encoder_worker.run_task)
        self.audio_player_thread.started.connect(self.audio_player_worker.run_task)
        self.audio_encoder_thread.finished.connect(self.audio_encoder_worker.deleteLater)
        self.audio_player_thread.finished.connect(self.audio_player_worker.deleteLater)
        

        
        self.tasks: List[asyncio.Task] = []
        
    
    # TODO 用map[format]decoder 切换更顺滑
    def change_video_format(self,format):
        if format!=self.video_decoder_worker.format:
            self.video_decoder_worker.frame_decoded.disconnect()
            self.video_decoder_worker.close()
            self.video_decoder_thread.quit()
            self.video_decoder_thread.started.disconnect()
            self.video_decoder_thread.wait() # TODO 耗时高的话就不wait了 应该也没问题
            
            self.video_decoder_thread=QThread()
            self.video_decoder_worker=H264Decoder(format=format)
            self.video_decoder_worker.moveToThread(self.video_decoder_thread)
            self.video_decoder_thread.started.connect(self.video_decoder_worker.frame_decode_task)
            self.video_decoder_thread.finished.connect(self.video_decoder_worker.deleteLater)
            self.video_decoder_worker.frame_decoded.connect(self.receive_video.emit)
            self.video_decoder_thread.start()
            
            

    def reconnect_video_stream(self):
        logging.info("reconnect video stream")
        if self.client:
            self.create_task(self.establish_video_stream())

    def reconnect_control_stream(self):
        logging.info("reconnect control stream")
        if self.client:
            self.create_task(self.establish_control_stream())


    def package_message(self,message:Message):
         # 序列化消息
        data = message.SerializeToString()
        
        # 构建header
        length = len(data)
        crc = calculate_uint16_crc8(length)
        header = bytes([
            0xff,
            crc,
            length & 0xFF,
            (length >> 8) & 0xFF
        ])
        return header + data

    async def send_message(self,writer:asyncio.StreamWriter,message:Message,flush=True):
        data=self.package_message(message)
        writer.write(data)
        if flush:
            await writer.drain()
        NETWORK_UPLOAD_BYTES.inc(float(len(data)))
        self.upload_bytes+=len(data)
        
    async def receive_message(self,reader:asyncio.StreamReader):
         # 创建4字节的header缓冲区
        header = bytearray(4)
        remain_size=3
        # 读取直到找到0xff起始位
        while True:
            b = await reader.readexactly(1)
            self.download_bytes+=1
            NETWORK_DOWNLOAD_BYTES.inc(float(1))
            if b[0] == 0xff:
                header[0] = b[0]
                # 读取剩余3个字节
                remain_size=3
                while True:
                    remaining = await reader.readexactly(remain_size)
                    header[4-remain_size:] = remaining
                    self.download_bytes+=remain_size
                    NETWORK_DOWNLOAD_BYTES.inc(float(remain_size))
                    
                    # 获取长度并验证CRC
                    length = (header[2]&0xff | (header[3]&0xff)<<8)
                    check_crc = calculate_uint16_crc8(length)
                    
                    # CRC匹配则退出循环
                    if check_crc == header[1]:
                        # 读取消息体
                        data = await reader.readexactly(length)
                        self.download_bytes+=length
                        NETWORK_DOWNLOAD_BYTES.inc(float(length))
                        return data
                    # [ff,a,ff,b]
                    # [ff,b]   i=2  
                    has_ff=False
                    for i in range(1, 4):
                        if header[i] == 0xff:
                            has_ff=True
                            # 移动数据
                            for j in range(0, 4-i):
                                header[j] = header[j+i]
                            remain_size=i
                            break
                    if not has_ff:
                        break
                        
    def start(self):
        """Start the client in a new thread"""
        if self.running:
            return
        self.running = True
        self.loop = asyncio.new_event_loop()
        self.moveToThread(self.main_thread)
        self.main_thread.started.connect(self._run_event_loop)
        self.main_thread.finished.connect(self.deleteLater)
        self.main_thread.start()

    def close(self):
        """Stop the client and cleanup resources"""
        if not self.running:
            return
        self.disconnect()
        self.running = False
        
        # 取消所有异步任务
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # 关闭客户端连接
        if self.client:
            try:
                self.client.close()
                # 使用超时避免无限等待
                future = asyncio.run_coroutine_threadsafe(self.client.wait_closed(), self.loop)
                future.result(timeout=2)  # 2秒超时
                logging.info("client closed")
            except Exception as e:
                logging.info(f"关闭客户端时出错: {e}")
                # 强制关闭
                if hasattr(self.client, '_quic'):
                    self.client._quic.close()
        
        logging.info("start closing video_encoder_thread")
        if self.video_encoder_thread.isRunning():
            self.video_encoder_thread.quit()
            self.video_encoder_worker.close()
            self.video_encoder_worker.frame_encoded.disconnect()
            self.video_encoder_thread.wait()
        logging.info("video encoder closed")


        
        if self.video_decoder_thread.isRunning():
            self.video_decoder_thread.quit()
            self.video_decoder_worker.frame_decoded.disconnect()
            self.video_decoder_worker.close()
            self.video_decoder_thread.wait()
        logging.info("video decoder closed")

        
        if self.audio_encoder_thread.isRunning():
            self.audio_encoder_thread.quit()
            self.audio_encoder_worker.close()
            self.audio_encoder_thread.wait()
        logging.info("audio encoder closed")
       
        
        if self.audio_player_thread.isRunning():
            self.audio_player_thread.quit()
            self.audio_player_worker.close()
            self.audio_player_thread.wait()
        logging.info("audio player closed")
        
        
        # # Stop the event loop
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        logging.info("loop stop")
        
        # Wait for the thread to finish with timeout (Windows11 fix)
        if self.main_thread.isRunning():
            self.main_thread.quit()
            # 使用超时避免Windows11上的无限阻塞
            if not self.main_thread.wait(3000):  # 3秒超时
                logging.info("警告: 主线程未能在3秒内退出，强制终止")
                self.main_thread.terminate()
                self.main_thread.wait(1000)  # 再等待1秒
        logging.info("main thread quit")
        
        
        
        

    async def __update_speed(self):
        while self.running:
            logging.info(f"Network stats - Upload: {self.upload_bytes} bytes, Download: {self.download_bytes} bytes")
            self.upload_speed.emit(self.upload_bytes)
            self.download_speed.emit(self.download_bytes)
            self.upload_bytes = 0
            self.download_bytes = 0
            await asyncio.sleep(1)
    
    @pyqtSlot()
    def _run_event_loop(self):
        """Run the event loop in a separate thread"""
        if not self.running:
            return
        logging.info("run event loop")
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.run())
            self.loop.run_forever()
        except Exception as e:
            self.connection_error.emit(str(e))
        finally:
            # 确保所有任务都被取消
            try:
                pending = asyncio.all_tasks(self.loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self.loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception as e:
                logging.info(f"清理任务时出错: {e}")
            finally:
                self.loop.close()
                logging.info("事件循环已关闭")

    def connection_lost(self):
        logging.info("connection lost")
        self.running=False
        self.client=None
        self.connection_error.emit("quic lost")

    def clear_tasks(self):
        for task in self.tasks:
            if not task.done():
                task.cancel()
        self.tasks=[]
       
        
    
    async def run(self):
        """Establish QUIC connection"""
       
        while self.running:
            try:
                
                logging.info(f"connecting quic server, running {self.running}")
                async with connect(
                    self.setting.host,
                    self.setting.port,
                    configuration=self.configuration,
                    create_protocol=HighwayClientProtocol,
                ) as client:
                    logging.info("connected quic server")
                    self.client = cast(HighwayClientProtocol, client)
                    self.client.datagram_data_received.connect(self.__parse_datagram)

                    
                    self.client.quic_connection_lost.connect(self.connection_lost)
                    self.connected.emit()
                    self.create_task(self.__update_speed())
                    self.create_task(self.__metric_collect())
                    self.create_task(self.establish_video_stream())
                    self.create_task(self.establish_control_stream())
                    self.create_task(self.establish_file_stream())
                    self.create_task(self.establish_imu_stream())
                    self.create_task(self.establish_datagram_stream())
                    
                    # self.create_task(self.establish_audio_stream())
                    # self.audio_encoder_thread.start()
                    # self.audio_player_thread.start()
                    # Keep connection alive
                    while self.running:
                        try:
                            # Check if client is still connected with shorter timeout
                            await asyncio.wait_for(client.ping(), timeout=0.5)
                            await asyncio.sleep(5)
                        except asyncio.TimeoutError:
                            logging.info("Ping timeout, connection may be lost")
                            break
                        except Exception as e:
                            logging.info(f"Ping error: {e}")
                            break
                    
                        
            except Exception as e:
                logging.info(f"connect error: {e}")
                if self.client:
                    self.client.close()
                    await self.client.wait_closed()
                self.clear_tasks()
                
                logging.info("tasks cleared!")


    def create_task(self,task):
        self.tasks.append(self.loop.create_task(task))

    async def establish_imu_stream(self):
        self.imu_reader,self.imu_writer=await self.client.create_stream(False)
        register_msg = Register(
            device=Device(
                id=int(self.setting.device_id),
                message_type=Device.MessageType.DEVICEPARAM
            ),
            subscribe_device=Device(
                id=int(self.setting.source_device_id),
                message_type=Device.MessageType.DEVICEPARAM
            )
        )
        logging.info(f"send imu register message {register_msg}")
        await self.send_message(writer=self.imu_writer,message=register_msg)
        self.create_task(self.__read_device_param_stream(reader=self.imu_reader))

    async def __read_device_param_stream(self,reader:asyncio.StreamReader):
        while self.running:
            try:
                message = await asyncio.wait_for(self.receive_message(reader), timeout=1.0)
                device_param = DeviceParam.FromString(message)
                logging.info(f"receive device param message {device_param}")
                self.device_param_ready.emit(device_param)
            except asyncio.TimeoutError:
                # 超时是正常的，继续循环检查running状态
                continue
            except Exception as e:
                logging.info(f"读取设备参数流错误: {e}")
                break

    async def establish_file_stream(self):
        self.file_reader,self.file_writer=await self.client.create_stream(False)
        register_msg = Register(
            device=Device(
                id=int(self.setting.device_id),
                message_type=Device.MessageType.FILE
            ),
            subscribe_device=Device(
                id=int(self.setting.source_device_id),
                message_type=Device.MessageType.FILE
            )
        )
        logging.info(f"send file register message {register_msg}")
        await self.send_message(writer=self.file_writer,message=register_msg)
    
    def send_file(self,filePath):
        if self.loop and self.running and self.file_writer:
            self.loop.create_task(self.__send_file(filePath))

    async def __send_file(self,filePath):
        with open(filePath, "rb") as f:
            fileName=os.path.basename(filePath)
            fileSize=os.stat(filePath).st_size
            await self.send_message(writer=self.file_writer,message=File(name=fileName,size=fileSize))
            sendSize=0
            while True:
                data=f.read(1024)
                if len(data)==0:
                    break
                self.file_writer.write(data)
                await self.file_writer.drain()
                sendSize+=len(data)
                self.file_send_progress.emit(fileName,round(sendSize*100/fileSize))


    async def establish_audio_stream(self):
        self.audio_reader, self.audio_writer = await self.client.create_stream(False)
        logging.info(f"Audio stream created - Reader: {id(self.audio_reader)}, Writer: {id(self.audio_writer)}")
        
        register_msg = Register(
            device=Device(
                id=int(self.setting.device_id),
                message_type=Device.MessageType.AUDIO,
                # device_type=Device.DeviceType.CONTROLLER
            ),
            subscribe_device=Device(
                id=int(self.setting.source_device_id),
                message_type=Device.MessageType.AUDIO,
                # device_type=Device.DeviceType.RECEIVER
            )
        )
        logging.info(f"Audio stream {register_msg} sent successfully, writer state: {self.audio_writer.is_closing()}")
        await self.send_message(writer=self.audio_writer,message=register_msg)
        
        self.create_task(self.__read_audio_stream(reader=self.audio_reader))
        self.create_task(self.__send_audio_stream(writer=self.audio_writer))
        logging.info(f"Audio stream tasks created, total tasks: {len(self.tasks)}")
    


    async def __read_audio_stream(self,reader:asyncio.StreamReader):
        try:
            while self.running:
                try:
                    message = await asyncio.wait_for(self.receive_message(reader), timeout=1.0)
                    audio=Audio.FromString(message)
                    self.input_wave_data.emit(np.frombuffer(audio.raw,dtype=np.int16))
                except asyncio.TimeoutError:
                    # 超时是正常的，继续循环检查running状态
                    continue
                except Exception as e:
                    logging.info(f"读取音频流错误: {e}")
                    break
                if audio.raw:
                    self.audio_player_worker.write(audio.raw)
        except asyncio.CancelledError:
            logging.info("__read_audio_stream canceled")
        except Exception as e:
            logging.info(f"__read_audio_stream error: {e}")
        finally:
            logging.info("__read_audio_stream quit")

    async def __send_audio_stream(self,writer:asyncio.StreamWriter):
        logging.info("__send_audio_stream task started")
        # 等待一下，确保establish函数完全完成
        await asyncio.sleep(0.1)    
        logging.info("__send_audio_stream starting to send data")
        try:
            while self.running:
                data=await self.audio_encoder_worker.read_async()
                if len(data) == 0:
                    await asyncio.sleep(0.01)  # 短暂等待避免忙等待
                    continue
                audio=Audio(raw=data)
                await self.send_message(writer=writer,message=audio,flush=False)
        except asyncio.CancelledError:
            logging.info("__send_audio_stream canceled")
        except Exception as e:
            logging.info(f"__send_audio_stream error: {e}")
            import traceback
            traceback.logging.info_exc()
        finally:
            logging.info("__send_audio_stream task ended")
    
    async def establish_video_stream(self):
        """Establish video stream after connection"""
        self.video_reader, self.video_writer = await self.client.create_stream(False)

        # Register video stream
        register_msg = Register(
            device=Device(
                id=int(self.setting.device_id),
                message_type=Device.MessageType.VIDEO
            ),
            subscribe_device=Device(
                id=int(self.setting.source_device_id),
                message_type=Device.MessageType.VIDEO
            )
        )
        logging.info(f"send video register message {register_msg}")
        await self.send_message(writer=self.video_writer,message=register_msg)

        self.video_decoder_thread.start()
  
        self.create_task(self.__read_video_stream(reader=self.video_reader))
    
    
    async def establish_datagram_stream(self):
        self.datagram_reader,self.datagram_writer=await self.client.create_stream(False)
        register_msg = Register(
            device=Device(
                id=int(self.setting.device_id),
                message_type=Device.MessageType.DATAGRAM
            ),
            subscribe_device=Device(
                id=int(self.setting.source_device_id),
                message_type=Device.MessageType.DATAGRAM
            )
        )
        logging.info(f"send datagram register message {register_msg}")
        await self.send_message(writer=self.datagram_writer,message=register_msg)
        

    def start_test_video_stream(self):
        logging.info("start send video with stream")
        self.video_test_mode=0
        self.video_encoder_thread.start()
    

    def start_test_video_datagram(self):
        logging.info("start send video with datagram")
        self.video_test_mode=1
        self.video_encoder_thread.start()

    def start_test_video_codec(self):
        logging.info("start send video with codec")
        self.video_test_mode=2
        self.video_encoder_thread.start()


    def send_control_message(self, values: list):
        # TODO 发送速率小于生产速率会产生堆积 导致延迟
        if self.loop and self.running and self.client:
            # logging.info("send control message:",values)
            future = asyncio.run_coroutine_threadsafe(
                self.control_stream_queue.put(Control(channels=values)), 
                self.loop
            )
            future.result()  # 等待操作完成
    
    
    
    async def establish_control_stream(self):
        self.control_reader,self.control_writer=await self.client.create_stream(False)
        # Register control stream
        register_msg = Register(
            device=Device(
                id=int(self.setting.device_id),
                message_type=Device.MessageType.CONTROL
            )
        )
        logging.info(f"send control register message {register_msg}")
        await self.send_message(writer=self.control_writer,message=register_msg)
        logging.info(f"Control stream register sent successfully, writer state: {self.control_writer.is_closing()}")
        self.create_task(self.__send_control_message(writer=self.control_writer))
    
    async def __send_control_message(self,writer:asyncio.StreamWriter):
        try:
            while self.running:
                try:
                    message = await asyncio.wait_for(self.control_stream_queue.get(), timeout=1.0)
                    # logging.info("send control message channels:",message.channels )
                    await self.send_message(writer=writer,message=message)
                except asyncio.TimeoutError:
                    # 超时是正常的，继续循环检查running状态
                    continue
                except Exception as e:
                    logging.info(f"发送控制消息错误: {e}")
                    break
        except Exception as e:
            self.control_stream_failed.emit(f"Send control message error: {str(e)}")
        finally:
            logging.info("__send_control_message quit")
    
    
    
    def send_video(self):
        if self.video_test_mode==1:
            self.send_video_test_datagram()
        elif self.video_test_mode==0:
            self.send_video_test_stream_data()
        elif self.video_test_mode==2:
            self.video_test_without_send()

    def send_video_test_stream_data(self):
        

        data = self.video_encoder_worker.read_frame()
        if self.loop and self.running:
            video=Video(raw=data,timestamp=int(time.time()*1000),slice_count=1,slice_id=1)
            if data.startswith(b"\x00\x00\x00\x01"):
                video.nalu_type=data[4]&0x1f
                # logging.info("send nal (v1):",video.nalu_type,Video.NaluType.Name(video.nalu_type))
            elif data.startswith(b"\x00\x00\x01"):
                video.nalu_type=data[3]&0x1f
                # logging.info("send nal (v2):",video.nalu_type,Video.NaluType.Name(video.nalu_type))
            else:
                logging.info(f"illegal nalu length: {len(data)}")
            
            future = asyncio.run_coroutine_threadsafe(
                self.send_message(writer=self.video_writer, message=video),
                self.loop
            )
            future.result()  # Wait for completion
   

    def send_video_test_datagram(self):
        data = self.video_encoder_worker.read_frame()
        if self.loop and self.running:
            self.send_frame_count+=1
            video=Video(raw=data,timestamp=int(time.time()*1000),slice_count=1,slice_id=1,frame_id=self.send_frame_count)
            if data.startswith(b"\x00\x00\x00\x01"):
                video.nalu_type=data[4]&0x1f
                # logging.info("send nal (v1):",video.nalu_type,Video.NaluType.Name(video.nalu_type))
            elif data.startswith(b"\x00\x00\x01"):
                video.nalu_type=data[3]&0x1f
                # logging.info("send nal (v2):",video.nalu_type,Video.NaluType.Name(video.nalu_type))
            else:
                logging.info(f"illegal nalu length: {len(data)}")
            data=self.package_message(video)
            # self.loop.call_soon_threadsafe(self.client.send_datagram, data)
            # logging.info("send datagram frame id ",video.frame_id," size ",len(data))
            self.client.send_datagram(data)
            
    
    def video_test_without_send(self):
        data=self.video_encoder_worker.read_frame()
        if data is None:
            return
        # logging.info("receive video data ",len(data),"decoder buffer size:",self.video_encoder_worker.buffer.size())
        self.video_decoder_worker.write(data)
   
    
    async def __metric_collect(self):
        while self.running:
            await asyncio.sleep(1)
            if self.latency_count>0:
                self.latency.emit(self.latency_sum//self.latency_count)
                self.latency_sum=0
                self.latency_count=0
    
    
    
    
    def __parse_datagram(self):
        data=self.client.receive_datagram()
        if data is None:
            return
        header=data[:4]
        length = (header[2]&0xff | (header[3]&0xff)<<8)
        data=data[4:4+length]
        self.__parse_video_data(data)
        
        
    def __parse_video_data(self,data:bytes):
        
        
        video = Video.FromString(data)
    
        self.video_decoder_worker.write(video.raw)
        # FIXME 如果传输的数据不是一个完整的NALU的话 会花屏
        # if video.slice_id == video.slice_count:
        #     # logging.info("send eof nal")
        #     self.video_decoder_worker.write(b"\x00\x00\x00\x01\x09\x00")
        self.latency_sum+=int(time.time()*1000)-video.timestamp
        # logging.info("parse datagram frame id ",video.frame_id," latency ",int(time.time()*1000)-video.timestamp,"size",len(video.raw))
        PROTOBUF_LATENCY.labels(type="video").observe(int(time.time()*1000)-video.timestamp)
        self.latency_count+=1
        
    
    async def __read_video_stream(self,reader:asyncio.StreamReader):
        """Background task to read incoming messages"""
        try:
            while self.running:
                try:
                    message = await asyncio.wait_for(self.receive_message(reader), timeout=1.0)
                    self.__parse_video_data(message)
                except asyncio.TimeoutError:
                    # 超时是正常的，继续循环检查running状态
                    continue
                except Exception as e:
                    logging.info(f"读取视频流错误: {e}")
                    break

        except asyncio.CancelledError as e:
            logging.info(f"_read_video_stream {e}")
        except Exception as e:
            logging.info(f"read video stream error {e}")
            self.video_stream_failed.emit(f"Read error: {str(e)}")

        finally:
            logging.info("_read_video_stream quit")




