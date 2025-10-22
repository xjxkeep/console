from collections import OrderedDict, defaultdict, deque
import logging
from queue import Queue
import struct
import time

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from google.protobuf.message import DecodeError
from zfec.easyfec import Decoder, Encoder
from pkg.crc import calculate_crc8

'''
符号丢包率
块丢包率
丢帧率
传输延迟

'''
class Packet:
    """
    健壮的 FEC 编解码器
    头部格式（8字节）：
    - data_id: 4字节，数据包ID
    - block_index: 1字节，块序号
    - K: 1字节，原始数据块数
    - M: 1字节，冗余块数
    - crc: 1字节，CRC校验码
    """
    HEADER_FORMAT = '!IBBBB'  # 大端序: uint32(data_id), uint8(block_index), uint8(K), uint8(M), uint8(crc)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 自动计算大小
    def __init__(self, data_id, K, block_index, M,payload,crc=None) -> None:
        self.data_id = data_id
        self.K = K
        self.block_index = block_index
        self.M = M
        self.payload = payload
        self.pts = int(time.time() * 1000)  # 接收时间戳
        if crc:
            self.crc = crc
        else:
            self.crc = calculate_crc8(payload)
        self.last_updated = time.time()  # 最后更新时间

        
    def __str__(self):
        return f"Packet(data_id={self.data_id}, block_index={self.block_index}, K={self.K}, M={self.M}, crc={self.crc}, payload_len={len(self.payload)})"
    
    def is_expired(self, timeout_seconds):
        """检查数据包是否已过期"""
        return time.time() - self.last_updated > timeout_seconds


    @staticmethod
    def from_raw(raw: bytes):
        data_id, block_index, K,  M,crc = struct.unpack(
            Packet.HEADER_FORMAT,
            raw[:Packet.HEADER_SIZE]
        )
        payload = raw[Packet.HEADER_SIZE:]
        calculated_crc = calculate_crc8(payload)
        if crc != calculated_crc:
            raise ValueError(f"data_id {data_id} block_id {block_index} crc mismatch, expected {crc}, got {calculated_crc}")
        packet= Packet(data_id, K, block_index,  M, payload,crc)
        logging.debug(f"receive packet {packet}")
        return packet
    def raw(self):
        return struct.pack(self.HEADER_FORMAT, self.data_id,self.block_index, self.K, self.M, self.crc) + self.payload

  

class FECCodec(QObject):
     
    # 信号定义
    data_decoded = pyqtSignal()  # 数据解码成功
    
    def __init__(self, block_size=1200, timeout_seconds=5.0, max_buffer_size=1000):
        """
        初始化 FEC 编解码器
        
        Args:
            block_size: 数据块大小
            timeout_seconds: 数据包超时时间（秒）
            max_buffer_size: 最大缓冲区大小（防止内存泄漏）
        """
        super().__init__()
        
        # 配置参数
        self.block_size = block_size
        self.timeout_seconds = timeout_seconds
        self.max_buffer_size = max_buffer_size
        
        # 数据管理
        self.data_id_counter = 0
        
        self.packet_map=defaultdict(list)
        
        self.data_buffer= deque()
     
        self.running=True
        
        self.block_count=0
        self.block_loss_count=0
        self.block_break_count=0
        
        self.frame_count=0
        self.frame_loss_count=0
        self.frame_latest_id=0
        
        
     

    
    def encode(self, data: bytes):
        """
        编码数据为 FEC 数据包
        
        Args:
            data: 原始数据
            
        Returns:
            list: 编码后的数据包列表
        """
        
        if len(data) == 0:
            raise ValueError("输入数据不能为空")
        
        try:
            # 生成唯一的数据ID
            data_id = self.data_id_counter
            self.data_id_counter = (self.data_id_counter + 1) % (2**32)
            
            # 计算 FEC 参数
            K = max(1, (len(data) + self.block_size - 1) // self.block_size)  # 向上取整
            M = 2  # 冗余块数
            
            # 创建编码器
            encoder = Encoder(K, K + M)
            encoded_data = encoder.encode(data)
            
            packets = []
            for i, data in enumerate(encoded_data):
                # 封装头部
                packet = Packet(data_id, K, i, M, data)
                packets.append(packet.raw())
            
                logging.debug(f"Encoded data_id={data_id} block_index={i} : {len(data)} bytes -> {len(packets)} packets (K={K}, M={M})")
            return packets
            
        except Exception as e:
            logging.error(f"编码失败: {e}")
            raise
    
    def add_package(self, data: bytes):
        """
        添加接收到的数据包
        
        Args:
            data: 接收到的数据包（包含头部）
        """
        # 解析数据包
        try:
            self.block_count+=1
            packet = Packet.from_raw(data)
        except Exception as e:
            logging.error(f"add package error {e}")
            self.block_break_count+=1
            return
        
        self.packet_map[packet.data_id].append(packet)
        # TODO 如果没有达到K个包 尽量还原数据给解码器  添加超时机制 避免内存泄漏
        if len(self.packet_map[packet.data_id]) == packet.K:
            packets=self.packet_map[packet.data_id]
            decoder = Decoder(packet.K, packet.K + packet.M)
            blocks=[p.payload for p in packets]
            shard_idx=[p.block_index for p in packets]
            logging.debug(f"decoding data_id {packet.data_id} block_indexs {shard_idx}")
            decoded_data = decoder.decode(blocks, shard_idx,0)
            self.data_buffer.append(decoded_data)
            self.data_decoded.emit()
            self.frame_count+=1
            
            
            self.frame_latest_id=packet.data_id
            # 删除所有小于data_id的map数据
            keys_to_delete = [k for k in self.packet_map.keys() if k < packet.data_id]
            for k in keys_to_delete:
                del self.packet_map[k]

        
    # def collect_metrics(self):
    #     while self.running:
            
            
            
    def read_data(self):
        try:
            return self.data_buffer.popleft()
        except Exception as e:
            logging.error(f"data buffer is empty {e}")
            return None
  
    def close(self):
        self.running=False
        self.data_buffer.clear()
        self.packet_map.clear()
   
    
   

    
   
    
    
  


