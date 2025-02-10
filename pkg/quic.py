import argparse
import asyncio
import logging
import pickle
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

logger = logging.getLogger("client")


class HighwayClientProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)


def send_message(writer:asyncio.StreamWriter,message:Message):
    message = message.SerializeToString()
    message = struct.pack("<L", len(message)) + message
    writer.write(message)

async def receive_message(reader:asyncio.StreamReader):
    length = await reader.readexactly(4)
    length = struct.unpack("<L",length)[0]
    message = await reader.readexactly(length)
    return message

class HighwayQuicClient(QObject):
    video_stream = pyqtSignal(bytes)
    connected = pyqtSignal()  # 新增连接状态信号
    connection_error = pyqtSignal(str)  # 新增错误信号
    
    def __init__(self, device:Device, host:str, port:int, ca_certs:str, insecure:bool) -> None:
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
        
        # QUIC configuration
        self.configuration = QuicConfiguration(alpn_protocols=["HLD"], is_client=True)
        if self.ca_certs:
            self.configuration.load_verify_locations(self.ca_certs)
        if insecure:
            self.configuration.verify_mode = ssl.CERT_NONE

    def start(self, source_device_id: int):
        """Start the client in a new thread"""
        if self.running:
            return
            
        self.running = True
        self.loop = asyncio.new_event_loop()
        
        # Start event loop in new thread
        thread = threading.Thread(
            target=self._run_event_loop,
            args=(source_device_id,),
            daemon=True
        )
        thread.start()

    def stop(self):
        """Stop the client and cleanup resources"""
        if not self.running:
            return
            
        self.running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self._cleanup)

    def _run_event_loop(self, source_device_id: int):
        """Run the event loop in a separate thread"""
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.connect(source_device_id))
            self.loop.run_forever()
        except Exception as e:
            self.connection_error.emit(str(e))
        finally:
            self.loop.close()

    async def connect(self, source_device_id: int):
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
                await self.establish_video_stream(source_device_id)
        except Exception as e:
            self.connection_error.emit(str(e))
            raise

    async def establish_video_stream(self, source_device_id: int):
        """Establish video stream after connection"""
        self.reader, self.writer = await self.client.create_stream(False)
        
        # Register video stream
        register_msg = Register(
            device=Device(
                id=self.device.id,
                message_type=Device.MessageType.VIDEO
            ),
            subscribe_device=Device(
                id=source_device_id,
                message_type=Device.MessageType.VIDEO
            )
        )
        print("send register message")
        send_message(self.writer, register_msg)

        # Start message reading task
        self.loop.create_task(self._read_messages())
        self.loop.create_task(self.send_test())
        
        # Keep connection alive
        while self.running:
            await asyncio.sleep(1)

    async def send_test(self):
        with open(r"/Users/xiongjinxin/workspace/endless/console/output.h264","rb") as f:
            while self.running:
                data=f.read(5000)
                if data:
                    send_message(self.writer,Video(raw=data))
                else:break
                await asyncio.sleep(0.01)
    async def _read_messages(self):
        """Background task to read incoming messages"""
        try:
            while self.running:
                message = await receive_message(self.reader)
                video = Video.FromString(message)
                self.video_stream.emit(video.raw)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.connection_error.emit(f"Read error: {str(e)}")

    def _cleanup(self):
        """Cleanup resources when stopping"""
        if self.writer:
            self.writer.close()
        if self.client:
            self.client.close()
        self.loop.stop()

def save_session_ticket(ticket):
    """
    Callback which is invoked by the TLS engine when a new session ticket
    is received.
    """
    logger.info("New session ticket received")
    if args.session_ticket:
        with open(args.session_ticket, "wb") as fp:
            pickle.dump(ticket, fp)




async def main(
    configuration: QuicConfiguration,
    host: str,
    port: int,
) -> None:
    logger.debug(f"Connecting to {host}:{port}")
    async with connect(
        host,
        port,
        configuration=configuration,
        session_ticket_handler=save_session_ticket,
        create_protocol=HighwayClientProtocol,
    ) as client:
        client = cast(HighwayClientProtocol, client)
        reader,writer=await client.create_stream(False)
        
        send_message(writer,Register(device=Device(id=1),subscribe_device=Device(id=1)))
        async def read_message():
            while True:
                message = await receive_message(reader)
                control = Control.FromString(message)
                print(control.ByteSize(),int(time.time()*1000)%10000-control.channels[0]," ms")
        asyncio.create_task(read_message())
        while True:
            await asyncio.sleep(1)
            send_message(writer,Control(channels=[int(time.time()*1000)%10000]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DNS over QUIC client")
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="The remote peer's host name or IP address",
    )
    parser.add_argument(
        "--port", type=int, default=853, help="The remote peer's port number"
    )
    parser.add_argument(
        "-k",
        "--insecure",
        action="store_true",
        help="do not validate server certificate",
    )
    parser.add_argument(
        "--ca-certs", type=str, help="load CA certificates from the specified file"
    )
    # parser.add_argument("--query-name", required=True, help="Domain to query")
    # parser.add_argument("--query-type", default="A", help="The DNS query type to send")
    parser.add_argument(
        "-q",
        "--quic-log",
        type=str,
        help="log QUIC events to QLOG files in the specified directory",
    )
    parser.add_argument(
        "-l",
        "--secrets-log",
        type=str,
        help="log secrets to a file, for use with Wireshark",
    )
    parser.add_argument(
        "-s",
        "--session-ticket",
        type=str,
        help="read and write session ticket from the specified file",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="increase logging verbosity"
    )

    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    configuration = QuicConfiguration(alpn_protocols=["HLD"], is_client=True)
    if args.ca_certs:
        configuration.load_verify_locations(args.ca_certs)
    if args.insecure:
        configuration.verify_mode = ssl.CERT_NONE
    if args.quic_log:
        configuration.quic_logger = QuicFileLogger(args.quic_log)
    if args.secrets_log:
        configuration.secrets_log_file = open(args.secrets_log, "a")
    if args.session_ticket:
        try:
            with open(args.session_ticket, "rb") as fp:
                configuration.session_ticket = pickle.load(fp)
        except FileNotFoundError:
            logger.debug(f"Unable to read {args.session_ticket}")
            pass
    else:
        logger.debug("No session ticket defined...")

    asyncio.run(
        main(
            configuration=configuration,
            host=args.host,
            port=args.port
        )
    )
