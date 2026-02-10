import asyncio
from asyncio import Queue
from collections import deque
import logging
import os
import ssl
import time
from typing import List, cast

from PyQt5.QtCore import QMetaObject, QObject, QThread, Qt, pyqtSignal, pyqtSlot, QTimer
from PyQt5.QtWidgets import QApplication
from aioquic.asyncio.client import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import ConnectionTerminated, DatagramFrameReceived, QuicEvent
from google.protobuf.message import Message
import numpy as np

from pkg.audio import AudioPlayer, AudioRecorder
from pkg.codec import VideoDecoder, H264Encoder
from pkg.fec import FECCodec
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
    VideoFeedback,
    ClockSynchronizationParam,
)
import threading


class HighwayClientProtocol(QuicConnectionProtocol,QObject):
    quic_connection_lost = pyqtSignal()
    datagram_data_received = pyqtSignal()
    def __init__(self, *args, **kwargs) -> None:
        QuicConnectionProtocol.__init__(self, *args, **kwargs)
        QObject.__init__(self)
        self.codec=FECCodec(block_size=1024,timeout_seconds=5.0,max_buffer_size=1000)
        self.codec.data_decoded.connect(self.datagram_data_received.emit)
        self._connection_lost = False   
    def quic_event_received(self, event: QuicEvent) -> None:
        if isinstance(event, ConnectionTerminated):
            self._connection_lost = True
            self.quic_connection_lost.emit()
        elif isinstance(event, DatagramFrameReceived):
            logging.debug(f"datagram frame received len {len(event.data)}")
            self.codec.add_package(event.data)
        return super().quic_event_received(event)
    
    def send_datagram(self,data:bytes):
        try:
            # 检查连接是否仍然有效
            if self._connection_lost or self._quic is None:
                logging.warning("QUIC连接已断开，无法发送数据报")
                return False
                
            for packet in self.codec.encode(data):
                self._quic.send_datagram_frame(packet)
                
            self._loop.call_soon_threadsafe(self.transmit)
            return True
        except Exception as e:
            logging.error(f"发送数据报时出错: {e}")
            self._connection_lost = True
            # 触发连接丢失信号
            self.quic_connection_lost.emit()
            return False

    def receive_datagram(self):
        data=self.codec.data_buffer.get()
        return data
    
    def connection_lost(self, exc):
        """重写连接丢失处理方法"""
        logging.info(f"传输层连接中断: {exc}")
        self._connection_lost = True
        self.quic_connection_lost.emit()
        return super().connection_lost(exc)



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
        self.ntp_reader = None
        self.ntp_writer = None
        self.feedback_reader = None 
        self.feedback_writer = None
        self.control_reader = None
        self.control_writer = None
        self.file_reader = None
        self.file_writer = None
        self.imu_reader = None
        self.imu_writer = None
        self.datagram_reader = None
        self.datagram_writer = None
        self.video_reader = None
        self.video_writer = None
        self.loop = None  # 初始化loop属性
        self.running = False
        self.receive_video_count=0
        self.upload_bytes = 0
        self.download_bytes = 0
        
        self.send_frame_count=0
        
        self.clock_offset=0
        self.control_stream_queue: Queue = Queue()
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
            idle_timeout=30
        )

        if self.setting.insecure:
            self.configuration.verify_mode = ssl.CERT_NONE
        self.video_stream_failed.connect(self.reconnect_video_stream)
        self.control_stream_failed.connect(self.reconnect_control_stream)
        
        
        # 视频解码
        self.h264_decoder_thread=QThread()
        self.h264_decoder_worker=VideoDecoder(format="h264")
        self.h264_decoder_worker.frame_decoded.connect(self.receive_video.emit)
        self.h264_decoder_worker.moveToThread(self.h264_decoder_thread)
        self.h264_decoder_thread.started.connect(self.h264_decoder_worker.frame_decode_task)
        self.h264_decoder_thread.finished.connect(self.h264_decoder_worker.deleteLater)

        self.h265_decoder_thread=QThread()
        self.h265_decoder_worker=VideoDecoder(format="h265")
        self.h265_decoder_worker.frame_decoded.connect(self.receive_video.emit)
        self.h265_decoder_worker.moveToThread(self.h265_decoder_thread)
        self.h265_decoder_thread.started.connect(self.h265_decoder_worker.frame_decode_task)
        self.h265_decoder_thread.finished.connect(self.h265_decoder_worker.deleteLater)
        
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
        self.upload_bytes+=len(data)
        
    async def receive_message(self,reader:asyncio.StreamReader):
         # 创建4字节的header缓冲区
        header = bytearray(4)
        remain_size=3
        # 读取直到找到0xff起始位
        while True:
            b = await reader.readexactly(1)
            self.download_bytes+=1
            if b[0] == 0xff:
                header[0] = b[0]
                # 读取剩余3个字节
                remain_size=3
                while True:
                    remaining = await reader.readexactly(remain_size)
                    header[4-remain_size:] = remaining
                    self.download_bytes+=remain_size
                    
                    # 获取长度并验证CRC
                    length = (header[2]&0xff | (header[3]&0xff)<<8)
                    check_crc = calculate_uint16_crc8(length)
                    
                    # CRC匹配则退出循环
                    if check_crc == header[1]:
                        # 读取消息体
                        data = await reader.readexactly(length)
                        self.download_bytes+=length
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
        """Start the client in a separate thread"""
        if self.running:
            return
        self.running = True
        
        # 创建新的事件循环
        self.loop = asyncio.new_event_loop()
        
        # 在单独线程中运行事件循环
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self._run_async_loop)
        self._thread.finished.connect(self.deleteLater)
        self._thread.start()
    
    def _run_async_loop(self):
        """在单独线程中运行异步事件循环"""
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.run())
        except Exception as e:
            logging.error(f"异步事件循环错误: {e}")
            self.connection_error.emit(str(e))
        finally:
            self.loop.close()

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
        
        # 关闭视频编码器
        if self.video_encoder_thread.isRunning():
            self.video_encoder_thread.quit()
            self.video_encoder_worker.close()
            self.video_encoder_worker.frame_encoded.disconnect()
            self.video_encoder_thread.wait()
        logging.info("video encoder closed")

        # 关闭视频解码器
        if self.h264_decoder_thread.isRunning():
            self.h264_decoder_thread.quit()
            self.h264_decoder_worker.frame_decoded.disconnect()
            self.h264_decoder_worker.close()
            self.h264_decoder_thread.wait()
        logging.info("h264 video decoder closed")
        if self.h265_decoder_thread.isRunning():
            self.h265_decoder_thread.quit()
            self.h265_decoder_worker.frame_decoded.disconnect()
            self.h265_decoder_worker.close()
            self.h265_decoder_thread.wait()
        logging.info("h265 video decoder closed")
        # 关闭音频编码器
        if self.audio_encoder_thread.isRunning():
            self.audio_encoder_thread.quit()
            self.audio_encoder_worker.close()
            self.audio_encoder_thread.wait()
        logging.info("audio encoder closed")
       
        # 关闭音频播放器
        if self.audio_player_thread.isRunning():
            self.audio_player_thread.quit()
            self.audio_player_worker.close()
            self.audio_player_thread.wait()
        logging.info("audio player closed")
         # 关闭客户端连接
        if self.client:
            try:
                self.client.close()
                # 使用asyncqt的run_until_complete
                self.loop.create_task(self.client.wait_closed())
                logging.info("client closed")
            except Exception as e:
                logging.error(f"关闭客户端时出错: {e}")
                # 强制关闭
                if hasattr(self.client, '_quic'):
                    self.client._quic.close()
        # 停止线程和事件循环
        if hasattr(self, '_thread') and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()
        if self.loop and self.loop.is_running():
            self.loop.stop()
        logging.info("event loop stopped")

    async def __update_speed(self):
        while self.running:
            logging.info(f"Network stats - Upload: {self.upload_bytes} bytes, Download: {self.download_bytes} bytes")
            self.upload_speed.emit(self.upload_bytes)
            self.download_speed.emit(self.download_bytes)
            self.upload_bytes = 0
            self.download_bytes = 0
            await asyncio.sleep(1.0)
    

    def connection_lost(self):
        logging.info("connection lost")
        self.running=False
        self.client=None
        self.connection_error.emit("quic lost")
        
        # 清理所有任务
        self.clear_tasks()

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
                    self.create_task(self.establish_feedback_stream())
                    self.create_task(self.establish_ntp_stream())
                    
                    # self.create_task(self.establish_audio_stream())
                    # self.audio_encoder_thread.start()
                    # self.audio_player_thread.start()
                    # Keep connection alive
                    while self.running:
                        try:
                            # 优化: 移除 ping()，依赖 idle_timeout/datagrams/streams keep-alive
                            # 频繁 ping 在高负载下可能导致不必要的开销
                            await asyncio.sleep(1.0)
                            
                                
                        except Exception as e:
                            logging.info(f"Keep-alive check error: {e}")
                            break
                    
                        
            except Exception as e:
                logging.error(f"connect error: {e}")
                if self.client:
                    self.client.close()
                    await self.client.wait_closed()
                self.clear_tasks()
                
                logging.info("tasks cleared!")


    def create_task(self, task):
        """创建异步任务"""
        if self.loop:
            self.tasks.append(self.loop.create_task(task))
        else:
            logging.warning("事件循环未初始化，无法创建任务")
    
    def _ensure_loop(self):
        """确保事件循环已初始化"""
        if self.loop is None:
            logging.warning("事件循环未初始化，尝试创建新的事件循环")
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    async def _establish_generic_stream(self, stream_name, message_type, read_task_func=None, need_subscribe=True, subscribe_id=None):
        """通用的流建立方法，减少重复代码
        
        Args:
            stream_name: 流名称
            message_type: 消息类型
            read_task_func: 读取任务函数
            need_subscribe: 是否需要订阅设备
        """
        # 创建流
        reader_attr = f"{stream_name}_reader"
        writer_attr = f"{stream_name}_writer"
        setattr(self, reader_attr, None)
        setattr(self, writer_attr, None)
        
        try:
            reader, writer = await self.client.create_stream(False)
            setattr(self, reader_attr, reader)
            setattr(self, writer_attr, writer)
            
            # 创建注册消息
            register_kwargs = {
                'device': Device(
                    id=int(self.setting.device_id),
                    message_type=message_type
                )
            }
            
            # 如果需要订阅，添加订阅设备
            if need_subscribe:
                
                subscribe_id=subscribe_id if subscribe_id else int(self.setting.subscribe_id)
                register_kwargs['subscribe_device'] = Device(
                    id=subscribe_id,
                    message_type=message_type
                )
            
            register_msg = Register(**register_kwargs)
            
            # 发送注册消息
            logging.info(f"send {stream_name} register message {register_msg}")
            await self.send_message(writer=writer, message=register_msg)
            
            # 如果提供了读取任务函数，创建任务
            if read_task_func:
                self.create_task(read_task_func(reader))
                
            return reader, writer
            
        except Exception as e:
            logging.error(f"Failed to establish {stream_name} stream: {e}")
            raise

    async def establish_imu_stream(self):
        await self._establish_generic_stream(
            stream_name="imu",
            message_type=Device.MessageType.DEVICEPARAM,
            read_task_func=self.__read_device_param_stream
        )

    async def __read_device_param_stream(self,reader:asyncio.StreamReader):
        while self.running:
            try:
                message = await asyncio.wait_for(self.receive_message(reader), timeout=1.0)
                device_param = DeviceParam.FromString(message)
                # logging.debug(f"receive device param message {device_param}")
                self.device_param_ready.emit(device_param)
            except asyncio.TimeoutError:
                # 超时是正常的，继续循环检查running状态
                continue
            except Exception as e:
                logging.error(f"读取设备参数流错误: {e}")
                break

    async def establish_file_stream(self):
        await self._establish_generic_stream(
            stream_name="file",
            message_type=Device.MessageType.FILE
        )
    
    def send_file(self,filePath):
        if self.running and self.file_writer:
            self._ensure_loop()
            if self.loop:
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
        reader, writer = await self._establish_generic_stream(
            stream_name="audio",
            message_type=Device.MessageType.AUDIO
        )
        
        # 保留音频流特有的额外日志
        logging.info(f"Audio stream created - Reader: {id(reader)}, Writer: {id(writer)}")
        logging.info(f"Audio stream sent successfully, writer state: {writer.is_closing()}")
        
        # 音频流需要创建两个任务：读取和发送
        self.create_task(self.__read_audio_stream(reader=reader))
        self.create_task(self.__send_audio_stream(writer=writer))
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
                    logging.error(f"读取音频流错误: {e}")
                    break
                if audio.raw:
                    self.audio_player_worker.write(audio.raw)
        except asyncio.CancelledError:
            logging.error("__read_audio_stream canceled")
        except Exception as e:
            logging.error(f"__read_audio_stream error: {e}")
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
            logging.error("__send_audio_stream canceled")
        except Exception as e:
            logging.error(f"__send_audio_stream error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            logging.info("__send_audio_stream task ended")
    
    async def establish_video_stream(self):
        """Establish video stream after connection"""
        await self._establish_generic_stream(
            stream_name="video",
            message_type=Device.MessageType.VIDEO
        )
        
        # 视频流需要启动H264解码器线程
        self.h264_decoder_thread.start()
        self.h265_decoder_thread.start()
        self.create_task(self.__read_video_stream(reader=self.video_reader))
    
    
    async def establish_datagram_stream(self):
        await self._establish_generic_stream(
            stream_name="datagram",
            message_type=Device.MessageType.DATAGRAM
        )
        

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
        if self.running and self.client:
            self._ensure_loop()
            if self.loop:
                # logging.info("send control message:",values)
                future = asyncio.run_coroutine_threadsafe(
                    self.control_stream_queue.put(Control(channels=values)), 
                    self.loop
                )
                future.result()  # 等待操作完成
    


    async def establish_ntp_stream(self):
        if self.setting.subscribe_id == self.setting.device_id:
            return
        
        self.ntp_reader, self.ntp_writer = await self._establish_generic_stream(
            stream_name="ntp",
            message_type=Device.MessageType.CLOCKSYNCHRONIZATIONPARAM
        )
        
        # NTP流需要创建两个任务：发送和读取
        self.create_task(self.__send_ntp_message(writer=self.ntp_writer))
        self.create_task(self.__read_ntp_stream(reader=self.ntp_reader))

    async def __send_ntp_message(self,writer:asyncio.StreamWriter):
        while self.running:
            try:
                ntp_param = ClockSynchronizationParam(req_tx_ms=int(time.time()*1000))
                await self.send_message(writer=writer,message=ntp_param)
                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"发送NTP消息错误: {e}")
                break

    async def __read_ntp_stream(self,reader:asyncio.StreamReader):
        while self.running:
            try:
                message = await asyncio.wait_for(self.receive_message(reader), timeout=1.0)
                ntp_param = ClockSynchronizationParam.FromString(message)
                self.clock_offset=round(((ntp_param.req_rx_ms-ntp_param.req_tx_ms)+(ntp_param.resp_tx_ms-int(time.time()*1000)))/2)
                # logging.debug(f"receive ntp param message {ntp_param} clock_offset {self.clock_offset}")
                await self.send_message(writer=self.ntp_writer,message=ntp_param,flush=False)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logging.error(f"读取NTP参数流错误: {e}")
                break

    async def establish_feedback_stream(self):
        self.feedback_reader,self.feedback_writer = await self._establish_generic_stream(
            stream_name="feedback",
            message_type=Device.MessageType.VIDEO_FEEDBACK,
            # need_subscribe=True,
            # subscribe_id=int(self.setting.device_id)
        )
        self.create_task(self.__send_feedback_message(writer=self.feedback_writer))
        # self.create_task(self.__read_feedback_stream(reader=self.feedback_reader))


        
    async def __read_feedback_stream(self,reader:asyncio.StreamReader):
        while self.running:
            try:
                message = await asyncio.wait_for(self.receive_message(reader), timeout=1.0)
                feedback = VideoFeedback.FromString(message)
                logging.info(f"receive feedback message {feedback}")
            except Exception as e:
                logging.error(f"读取反馈消息错误: {e}")
                break

    async def __send_feedback_message(self,writer:asyncio.StreamWriter):
        while self.running:
            try:
                await self.send_message(writer=writer, message=VideoFeedback(received_frame_index=self.receive_video_count), flush=False)
                await asyncio.sleep(0.2)
                logging.debug(f"send feedback message {self.receive_video_count}")
            except Exception as e:
                logging.error(f"发送反馈消息错误: {e}")
                break
    

    

    
    async def establish_control_stream(self):
        reader, writer = await self._establish_generic_stream(
            stream_name="control",
            message_type=Device.MessageType.CONTROL,
            need_subscribe=False
        )
        
        # 保留控制流特有的额外日志
        logging.info(f"Control stream register sent successfully, writer state: {writer.is_closing()}")
        
        # 控制流需要创建发送任务
        self.create_task(self.__send_control_message(writer=writer))
    
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
                    logging.error(f"发送控制消息错误: {e}")
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
        if self.running and self.video_writer:
            self._ensure_loop()
            if self.loop:
                video=Video(raw=data,timestamp=int(time.time()*1000),slice_count=1,slice_id=1)
                if data.startswith(b"\x00\x00\x00\x01"):
                    video.nalu_type=data[4]&0x1f
                    # logging.info("send nal (v1):",video.nalu_type,Video.NaluType.Name(video.nalu_type))
                elif data.startswith(b"\x00\x00\x01"):
                    video.nalu_type=data[3]&0x1f
                    # logging.info("send nal (v2):",video.nalu_type,Video.NaluType.Name(video.nalu_type))
                else:
                    logging.debug(f"illegal nalu length: {len(data)}")
                
                future = asyncio.run_coroutine_threadsafe(
                    self.send_message(writer=self.video_writer, message=video),
                    self.loop
                )
                future.result()  # Wait for completion
   

    def send_video_test_datagram(self):
        data = self.video_encoder_worker.read_frame()
        if self.running and self.client:
            self._ensure_loop()
            if self.loop:
                self.send_frame_count+=1
                video=Video(raw=data,timestamp=int(time.time()*1000),slice_count=1,slice_id=1,frame_id=self.send_frame_count)
                if data.startswith(b"\x00\x00\x00\x01"):
                    video.nalu_type=data[4]&0x1f
                    # logging.info("send nal (v1):",video.nalu_type,Video.NaluType.Name(video.nalu_type))
                elif data.startswith(b"\x00\x00\x01"):
                    video.nalu_type=data[3]&0x1f
                    # logging.info("send nal (v2):",video.nalu_type,Video.NaluType.Name(video.nalu_type))
                else:
                    logging.debug(f"illegal nalu length: {len(data)}")
                data=self.package_message(video)
                # self.loop.call_soon_threadsafe(self.client.send_datagram, data)
                # logging.info("send datagram frame id ",video.frame_id," size ",len(data))
                self.upload_bytes+=len(data)
                success = self.client.send_datagram(data)
                if not success:
                    logging.warning("发送视频数据报失败，连接可能已断开")
            
    
    def video_test_without_send(self):
        data=self.video_encoder_worker.read_frame()
        if data is None:
            return
        # logging.info("receive video data ",len(data),"decoder buffer size:",self.video_encoder_worker.buffer.size())
        self.h264_decoder_worker.write(data)
   
    
    async def __metric_collect(self):
        while self.running:
            await asyncio.sleep(1.0)
            if self.latency_count>0:
                self.latency.emit(self.latency_sum//self.latency_count+self.clock_offset)
                self.latency_sum=0
                self.latency_count=0
    
    
    
    
    def __parse_datagram(self):
        data=self.client.receive_datagram()
        if data is None:
            return
        self.download_bytes+=len(data)
        header=data[:4]
        length = (header[2]&0xff | (header[3]&0xff)<<8)
        data=data[4:4+length]
        
        self.__parse_video_data(data)
        
        
        
    def __parse_video_data(self,data:bytes):
        
        try:
            video = Video.FromString(data)
            if video.code_type == Video.CodeType.H265:
                self.h265_decoder_worker.write(video.raw)
            else:
                self.h264_decoder_worker.write(video.raw)
            self.receive_video_count=video.frame_id

            # FIXME 如果传输的数据不是一个完整的NALU的话 会花屏
            if video.slice_id == video.slice_count:
                logging.debug("send eof nal")
                self.h264_decoder_worker.write(b"\x00\x00\x00\x01\x09\x00")
            self.latency_sum+=int(time.time()*1000)-video.timestamp
            # logging.info("parse datagram frame id ",video.frame_id," latency ",int(time.time()*1000)-video.timestamp,"size",len(video.raw))
            self.latency_count+=1
        except Exception as e:
            logging.error(f"__parse_video_data error {e}")
        
    
    async def __read_video_stream(self,reader:asyncio.StreamReader):
        """Background task to read incoming messages"""
        try:
            while self.running:
                try:
                    message = await asyncio.wait_for(self.receive_message(reader), timeout=1.0)
                    await self.__parse_video_data(message)
                except asyncio.TimeoutError:
                    # 超时是正常的，继续循环检查running状态
                    continue
                except Exception as e:
                    logging.error(f"读取视频流错误: {e}")
                    break

        except asyncio.CancelledError as e:
            logging.error(f"_read_video_stream {e.with_traceback(e.__traceback__)}")
        except Exception as e:
            logging.error(f"read video stream error {e.with_traceback()}")
            self.video_stream_failed.emit(f"Read error: {str(e)}")

        finally:
            logging.info("_read_video_stream quit")




