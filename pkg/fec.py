from collections import defaultdict, OrderedDict
from google.protobuf.message import DecodeError
from reedsolo import RSCodec
from queue import Queue
import struct
import time
import threading
import logging
from zfec.easyfec import Encoder, Decoder
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


class Packet:
    """
    健壮的 FEC 编解码器
    头部格式（11字节）：
    - data_id: 4字节，数据包ID
    - K: 2字节，原始数据块数
    - block_index: 2字节，块序号
    - block_size: 2字节，原始块大小
    - M: 1字节，冗余块数
    """
    HEADER_FORMAT = '!IBBB'  # 大端序: uint32, uint8, uint8, uint8
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 自动计算大小
    def __init__(self, data_id, K, block_index, M, payload) -> None:
        self.data_id = data_id
        self.K = K
        self.block_index = block_index
        self.M = M
        self.payload = payload
        self.pts = int(time.time() * 1000)  # 接收时间戳
        
        self.last_updated = time.time()  # 最后更新时间
        
    def __str__(self):
        return f"Packet(data_id={self.data_id}, K={self.K}, block_index={self.block_index},  M={self.M}, payload_len={len(self.payload)})"
    
    def is_expired(self, timeout_seconds):
        """检查数据包是否已过期"""
        return time.time() - self.last_updated > timeout_seconds


    @staticmethod
    def from_raw(raw: bytes):
        data_id, block_index, K,  M = struct.unpack(
            Packet.HEADER_FORMAT,
            raw[:Packet.HEADER_SIZE]
        )
        return Packet(data_id, K, block_index,  M, raw[Packet.HEADER_SIZE:])

    def raw(self):
        return struct.pack(self.HEADER_FORMAT, self.data_id,self.block_index, self.K,   self.M) + self.payload

  

class FECCodec(QObject):
    
    
    """
    健壮的 FEC 编解码器
    头部格式（11字节）：
    - data_id: 4字节，数据包ID
    - K: 2字节，原始数据块数
    - block_index: 2字节，块序号
    - block_size: 2字节，原始块大小
    - M: 1字节，冗余块数
    """
    HEADER_FORMAT = '!IHHH B'  # 大端序: uint32, uint16, uint16, uint16, uint8
    HEADER_SIZE = 11  # 4+2+2+2+1 = 11字节
    
    # 信号定义
    data_decoded = pyqtSignal(bytes)  # 数据解码成功
    data_timeout = pyqtSignal(int)    # 数据包超时（data_id）
    partial_data = pyqtSignal(int, bytes, float)  # 部分数据恢复（data_id, data, recovery_rate）
    
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
            for i, block in enumerate(encoded_data):
                # 封装头部
                packet = Packet(data_id, K, i, M, block)
                packets.append(packet.raw())
            
            # print(f"Encoded data_id={data_id}: {len(data)} bytes -> {len(packets)} packets (K={K}, M={M})")
            return packets
            
        except Exception as e:
            print(f"编码失败: {e}")
            raise
    
    def add_package(self, data: bytes):
        """
        添加接收到的数据包
        
        Args:
            data: 接收到的数据包（包含头部）
        """
        # 解析数据包
        packet = Packet.from_raw(data)
        
        self.packet_map[packet.data_id].append(packet)
        if len(self.packet_map[packet.data_id]) >= packet.K:
            packets=self.packet_map[packet.data_id]
            decoder = Decoder(packet.K, packet.K + packet.M)
            blocks=[p.payload for p in packets]
            shard_idx=[p.block_index for p in packets]
            decoded_data = decoder.decode(blocks, shard_idx,0)
            
            self.data_decoded.emit(decoded_data)
            del self.packet_map[packet.data_id]
        
       
                
  
    
   
    
   

    
   
    
    
  


