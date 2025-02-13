import asyncio
import logging
import ssl
import struct
from typing import Dict, Optional, cast

from aioquic.asyncio.client import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent, StreamDataReceived
from aioquic.quic.logger import QuicFileLogger
from PyQt5.QtCore import QObject,pyqtSignal
from google.protobuf.message import Message
from protocol.highway_pb2 import Register,Device,Control,Video
import time
import threading
from asyncio import Queue

logger = logging.getLogger("client")


class HighwayClientProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


class HighwayQuicClient(QObject):
    # TODO 流写入失败 重试
    receive_video = pyqtSignal(Video)
    connected = pyqtSignal()  # 新增连接状态信号
    connection_error = pyqtSignal(str)  # 新增错误信号
    upload_speed = pyqtSignal(float)
    download_speed = pyqtSignal(float)
    
    def __init__(self, device:Device, host:str, port:int, ca_certs:str, insecure:bool,source_device_id:int=1) -> None:
        super().__init__()
        self.device = device
        self.host = host
        self.port = port
        self.ca_certs = ca_certs
        self.client = None
        self.reader = None
        self.writer = None
        self.loop = None
        self.running = False
        self.upload_bytes = 0
        self.download_bytes = 0
        self.source_device_id=source_device_id
        self.control_stream_queue=Queue()
        # QUIC configuration
        self.configuration = QuicConfiguration(alpn_protocols=["HLD"], is_client=True)
        if self.ca_certs:
            self.configuration.load_verify_locations(self.ca_certs)
        if insecure:
            self.configuration.verify_mode = ssl.CERT_NONE

    def send_message(self,writer:asyncio.StreamWriter,message:Message):
        message = message.SerializeToString()
        message = struct.pack("<L", len(message)) + message
        self.upload_bytes += len(message)
        writer.write(message)

    async def receive_message(self,reader:asyncio.StreamReader):
        length = await reader.readexactly(4)
        length = struct.unpack("<L",length)[0]
        message = await reader.readexactly(length)
        self.download_bytes += len(message)
        return message

    def start(self):
        """Start the client in a new thread"""
        if self.running:
            return
            
        self.running = True
        self.loop = asyncio.new_event_loop()
        
        # Start event loop in new thread
        self.thread = threading.Thread(
            target=self._run_event_loop,
            daemon=True
        )
        self.thread.start()

    def close(self):
        """Stop the client and cleanup resources"""
        if not self.running:
            return
            
        self.running = False
        
        # Stop the event loop
        if self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        
        # Wait for the thread to finish
        self.thread.join()
        
        # Close the loop if it's not already closed
        if not self.loop.is_closed():
            self.loop.close()

    async def __update_speed(self):
        while self.running:
            self.upload_speed.emit(self.upload_bytes)
            self.download_speed.emit(self.download_bytes)
            self.upload_bytes = 0
            self.download_bytes = 0
            await asyncio.sleep(1)
    
    def _run_event_loop(self):
        """Run the event loop in a separate thread"""
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.run())
            self.loop.run_forever()
        except Exception as e:
            self.connection_error.emit(str(e))
        finally:
            self.loop.close()

    async def run(self):
        """Establish QUIC connection"""
        try:
            print("connect quic client")
            async with connect(
                self.host,
                self.port,
                configuration=self.configuration,
                create_protocol=HighwayClientProtocol,
            ) as client:
            
                self.client = cast(HighwayClientProtocol, client)
                self.connected.emit()
                self.loop.create_task(self.__update_speed())
                await self.establish_video_stream()
                await self.establish_control_stream()
                 # Keep connection alive
                while self.running:
                    await asyncio.sleep(1)
        except Exception as e:
            self.connection_error.emit(str(e))
            raise

    async def establish_video_stream(self):
        """Establish video stream after connection"""
        self.video_reader, self.video_writer = await self.client.create_stream(False)
        
        # Register video stream
        register_msg = Register(
            device=Device(
                id=self.device.id,
                message_type=Device.MessageType.VIDEO
            ),
            subscribe_device=Device(
                id=self.source_device_id,
                message_type=Device.MessageType.VIDEO
            )
        )
        print("send register message")
        self.send_message(writer=self.video_writer,message=register_msg)

        # Start message reading task
        self.loop.create_task(self.send_test(writer=self.video_writer))
        self.loop.create_task(self._read_video_stream(reader=self.video_reader))
    
    def send_control_message(self, values: list[int]):
        # TODO 发送速率小于生产速率会产生堆积 导致延迟
        if self.loop and self.running:
            future = asyncio.run_coroutine_threadsafe(
                self.control_stream_queue.put(Control(values=values)), 
                self.loop
            )
            future.result()  # 等待操作完成
    
    async def establish_control_stream(self):
        self.control_reader,self.control_writer=await self.client.create_stream(False)
        # Register control stream
        register_msg = Register(
            device=Device(
                id=self.device.id,
                message_type=Device.MessageType.CONTROL
            )
        )
        self.send_message(writer=self.control_writer,message=register_msg)
        self.loop.create_task(self.__send_control_message(writer=self.control_writer))
    
    async def __send_control_message(self,writer:asyncio.StreamWriter):
        while self.running:
            message=await self.control_stream_queue.get()
            self.send_message(writer=writer,message=message)
            
   
    async def send_test(self,writer:asyncio.StreamWriter):
        with open(r"output.h264","rb") as f:
            while self.running:
                data=f.read(5000)
                if data:
                    self.send_message(writer=writer,message=Video(raw=data,timestamp=int(time.time()*1000)%1000))
                else:break
                await asyncio.sleep(0.05)
                
    async def _read_video_stream(self,reader:asyncio.StreamReader):
        """Background task to read incoming messages"""
        try:
            while self.running:
                message = await self.receive_message(reader)
                video = Video.FromString(message)
                self.receive_video.emit(video)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.connection_error.emit(f"Read error: {str(e)}")


        





