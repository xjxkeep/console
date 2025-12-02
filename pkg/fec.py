from collections import OrderedDict, defaultdict, deque
import logging
from queue import Queue
import struct
import time

from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from google.protobuf.message import DecodeError
from zfec.easyfec import Decoder, Encoder
from pkg.crc import calculate_crc8
import threading
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
    data_decoded = pyqtSignal()

    def __init__(self, block_size=1200, timeout_seconds=5.0, max_buffer_size=1000):
        super().__init__()
        
        self.block_size = block_size
        self.timeout_seconds = timeout_seconds
        self.max_buffer_size = max_buffer_size
        
        self.data_id_counter = 0
        
        # 优化: 使用字典存储接收到的包。键是 data_id
        # 值为一个包含 (payload, block_index) 的列表
        self.received_blocks = defaultdict(list)
        # 优化: 记录已成功解码的 data_id，避免重复解码
        self.decoded_ids = set() 
        
        self.data_buffer = Queue()
        self._lock = threading.Lock()
        self.running = True
        
        # 统计信息
        self.block_total_received = 0
        self.block_crc_errors = 0
        self.frame_decoded_count = 0
        self.frame_latest_id = -1 # 使用 -1 表示未收到
        self.frame_lost_count = 0 # 统计因超时而被清理的帧数量
        
        # 优化: QTimer 用于定时清理过期数据包，防止内存泄漏
        self.cleanup_timer = QTimer(self)
        self.cleanup_timer.timeout.connect(self._cleanup_expired_blocks)
        self.cleanup_timer.start(1000) # 每隔 1 秒清理一次

    def close(self):
        self.running = False
        self.cleanup_timer.stop()
        self.data_buffer.put(None)
        with self._lock:
            self.received_blocks.clear()
            self.decoded_ids.clear()
        logging.info("FECCodec closed.")

    # 保持 encode 接口不变，因为 zfec 的编码逻辑是直接计算 K 和 M 的
    def encode(self, data: bytes):
        # ... (encode 方法保持不变) ...
        if len(data) == 0:
            raise ValueError("输入数据不能为空")
        
        try:
            data_id = self.data_id_counter
            self.data_id_counter = (self.data_id_counter + 1) % (2**32)
            
            K = max(1, (len(data) + self.block_size - 1) // self.block_size)
            M = 2
            
            encoder = Encoder(K, K + M)
            encoded_data = encoder.encode(data)
            
            packets = []
            for i, data_chunk in enumerate(encoded_data):
                packet = Packet(data_id, K, i, M, data_chunk)
                packets.append(packet.raw())
            
            logging.debug(f"Encoded data_id={data_id} K={K}, M={M}")
            return packets
            
        except Exception as e:
            logging.error(f"编码失败: {e}")
            raise

    def add_package(self, data: bytes):
        """
        添加接收到的数据包。
        - 立即尝试 FEC 解码 (只需 K 个包，不一定必须是原始包)。
        - 在成功解码后清理旧的块。
        """
        with self._lock:
            try:
                self.block_total_received += 1
                packet = Packet.from_raw(data)
            except ValueError as e:
                logging.warning(f"CRC 或头部错误: {e}")
                self.block_crc_errors += 1
                return
            
            data_id = packet.data_id
            K = packet.K
            M = packet.M
            
            # 1. 检查是否已经解码
            if data_id in self.decoded_ids or data_id < self.frame_latest_id:
                logging.debug(f"Block {data_id} already decoded or too old, ignoring.")
                return

            # 2. 检查是否已存在，避免重复添加（可能因为网络重传）
            is_new = True
            for _, index, _ in self.received_blocks[data_id]:
                if index == packet.block_index:
                    is_new = False
                    break
            
            if is_new:
                # 存储数据: (payload, block_index, timestamp)
                self.received_blocks[data_id].append((packet.payload, packet.block_index, packet.last_updated))
            
            current_count = len(self.received_blocks[data_id])
            
            # 3. 尝试解码: 收到 K 个包就尝试解码 (不需要等到 K 个原始包)
            if current_count >= K:
                
                # 避免重复解码
                if data_id in self.decoded_ids:
                    return

                try:
                    # 准备解码数据
                    # [ (payload, block_index, timestamp), ... ]
                    blocks_info = self.received_blocks[data_id]
                    blocks = [info[0] for info in blocks_info]
                    shard_indices = [info[1] for info in blocks_info]
                    
                    # 验证参数有效性，防止崩溃
                    if K <= 0 or K > 255 or M < 0 or M > 255:
                        logging.error(f"Invalid FEC parameters: K={K}, M={M} for data_id {data_id}")
                        return
                    
                    if len(blocks) < K:
                        logging.warning(f"Not enough blocks for decoding: got {len(blocks)}, need {K}")
                        return
                    
                    if len(blocks) != len(shard_indices):
                        logging.error(f"Blocks and indices count mismatch: {len(blocks)} != {len(shard_indices)}")
                        return
                    
                    # 验证索引范围
                    for idx in shard_indices:
                        if idx < 0 or idx >= (K + M):
                            logging.error(f"Invalid shard index: {idx}, must be in [0, {K+M-1}]")
                            return
                    
                    decoder = Decoder(K, K + M)
                    
                    # zfec.decode 的正确调用方式: decode(blocks, indices, padlen)
                    # padlen 是填充长度，由于解码时不知道原始数据长度，使用 0
                    # 如果原始数据有填充，解码后的数据末尾会有填充字节，但通常不影响使用
                    decoded_data = decoder.decode(blocks, shard_indices, 0)
                    
                    # 4. 解码成功处理
                    self.data_buffer.put(decoded_data)
                    self.data_decoded.emit()
                    self.frame_decoded_count += 1
                    self.decoded_ids.add(data_id)
                    
                    # 5. 更新最新 ID 并清理过期/已解码的块
                    if data_id > self.frame_latest_id:
                        self.frame_latest_id = data_id
                        self._delete_old_blocks_locked(data_id)
                        
                    logging.debug(f"Successfully decoded data_id {data_id} (K={K})")
                    
                except Exception as e:
                    # 解码失败通常是由于数据损坏或 K 个包不一致（极少数情况）
                    # 继续等待更多冗余包 (M-K 个)
                    logging.warning(f"FEC decoding failed for data_id {data_id}: {e}")
                    # 如果缓冲区没有满，不删除，继续等待
                    pass
        
    def _delete_old_blocks_locked(self, latest_id):
        """
        在锁保护下删除已解码或过期的数据块。
        """
        keys_to_delete = [k for k in self.received_blocks.keys() if k < latest_id]
        
        # 限制缓冲区大小
        if len(self.received_blocks) > self.max_buffer_size:
             # 找出最小的 ID 进行清理，直到达到 max_buffer_size
             oldest_ids = sorted(self.received_blocks.keys())[:-self.max_buffer_size]
             keys_to_delete.extend(oldest_ids)
             
        for k in set(keys_to_delete):
            if k not in self.decoded_ids:
                 # 统计因超时或清理而丢失的帧
                 self.frame_lost_count += 1 
                 logging.warning(f"Frame data_id {k} dropped due to being too old or buffer overflow.")
            del self.received_blocks[k]
            self.decoded_ids.discard(k) # 如果是已解码的，也删除记录

    def _cleanup_expired_blocks(self):
        """
        QTimer 触发的超时清理函数。
        """
        if not self.running:
            return

        expired_ids = []
        now = time.time()
        
        with self._lock:
            for data_id, blocks in list(self.received_blocks.items()):
                # 检查块中是否有任何包已过期
                if blocks and (now - blocks[0][2]) > self.timeout_seconds:
                    expired_ids.append(data_id)

            for data_id in expired_ids:
                if data_id not in self.decoded_ids:
                    # 统计因超时而被丢弃的帧
                    self.frame_lost_count += 1
                    logging.warning(f"Frame data_id {data_id} timed out and was dropped (not decoded).")
                del self.received_blocks[data_id]
                self.decoded_ids.discard(data_id)
        
    def read_data(self):
        # 保持接口不变
        return self.data_buffer.get()
   

    
   
    
    
  


