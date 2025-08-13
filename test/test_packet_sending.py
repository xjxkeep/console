#!/usr/bin/env python3
"""
测试128字节分包发送功能
"""

import json
from pkg.model import HIDBody

def test_packet_serialization():
    """测试数据包序列化功能"""
    
    print("=== 测试数据包序列化 ===")
    
    # 测试用例1：短数据（不超过128字节）
    short_request = HIDBody(
        type="request",
        cmd="test_short",
        request_id="123",
        args={"param": "value"},
        returns={}
    )
    
    print("\n--- 测试短数据 ---")
    print(f"请求: {short_request}")
    
    # 模拟序列化过程
    json_str = short_request.model_dump_json()
    data = json_str.encode('utf-8')
    print(f"JSON长度: {len(data)} 字节")
    print(f"JSON内容: {json_str}")
    
    # 分包处理
    packet_size = 128
    packets = []
    
    for i in range(0, len(data), packet_size):
        packet = bytearray(data[i:i + packet_size])
        
        # 如果包大小不足128字节，用0填充
        while len(packet) < packet_size:
            packet.append(0)
        
        packets.append(bytes(packet))
    
    print(f"生成 {len(packets)} 个数据包")
    for i, packet in enumerate(packets):
        print(f"包 {i+1}: {len(packet)} 字节")
        print(f"  内容: {packet[:50]}...")
        print(f"  填充字节数: {packet.count(0)}")
    
    # 测试用例2：长数据（超过128字节）
    long_request = HIDBody(
        type="request",
        cmd="test_long",
        request_id="456",
        args={
            "param1": "very_long_value_that_exceeds_128_bytes",
            "param2": "another_long_parameter",
            "param3": "third_long_parameter",
            "param4": "fourth_long_parameter",
            "param5": "fifth_long_parameter",
            "param6": "sixth_long_parameter",
            "param7": "seventh_long_parameter",
            "param8": "eighth_long_parameter"
        },
        returns={}
    )
    
    print("\n--- 测试长数据 ---")
    print(f"请求: {long_request}")
    
    # 模拟序列化过程
    json_str = long_request.model_dump_json()
    data = json_str.encode('utf-8')
    print(f"JSON长度: {len(data)} 字节")
    print(f"JSON内容: {json_str[:100]}...")
    
    # 分包处理
    packets = []
    
    for i in range(0, len(data), packet_size):
        packet = bytearray(data[i:i + packet_size])
        
        # 如果包大小不足128字节，用0填充
        while len(packet) < packet_size:
            packet.append(0)
        
        packets.append(bytes(packet))
    
    print(f"生成 {len(packets)} 个数据包")
    for i, packet in enumerate(packets):
        print(f"包 {i+1}: {len(packet)} 字节")
        print(f"  内容: {packet[:50]}...")
        print(f"  填充字节数: {packet.count(0)}")
    
    # 验证数据完整性
    print("\n--- 验证数据完整性 ---")
    
    # 重建原始数据
    reconstructed_data = bytearray()
    for packet in packets:
        # 移除填充字节
        for byte in packet:
            if byte != 0:
                reconstructed_data.append(byte)
    
    reconstructed_json = reconstructed_data.decode('utf-8')
    print(f"重建的JSON: {reconstructed_json}")
    
    # 验证JSON是否有效
    try:
        parsed_data = json.loads(reconstructed_json)
        print("✓ 数据完整性验证通过")
    except json.JSONDecodeError as e:
        print(f"✗ 数据完整性验证失败: {e}")

def test_packet_reconstruction():
    """测试数据包重建功能"""
    print("\n=== 测试数据包重建 ===")
    
    # 模拟接收到的数据包
    original_json = '{"type": "response", "cmd": "test", "request_id": "789", "args": {"data": "very_long_response_data_that_requires_multiple_packets"}, "returns": {"status": "success"}}'
    original_data = original_json.encode('utf-8')
    
    print(f"原始数据长度: {len(original_data)} 字节")
    print(f"原始JSON: {original_json}")
    
    # 模拟分包
    packet_size = 128
    packets = []
    
    for i in range(0, len(original_data), packet_size):
        packet = bytearray(original_data[i:i + packet_size])
        
        # 填充到128字节
        while len(packet) < packet_size:
            packet.append(0)
        
        packets.append(bytes(packet))
    
    print(f"分包数量: {len(packets)}")
    
    # 模拟接收端重建数据
    received_buffer = bytearray()
    for packet in packets:
        # 过滤掉填充字节
        for byte in packet:
            if byte != 0:
                received_buffer.append(byte)
    
    # 重建JSON
    try:
        reconstructed_json = received_buffer.decode('utf-8')
        print(f"重建的JSON: {reconstructed_json}")
        
        # 验证JSON
        parsed_data = json.loads(reconstructed_json)
        print("✓ 数据重建成功")
        
        # 创建HIDBody对象
        hid_body = HIDBody(**parsed_data)
        print(f"✓ HIDBody创建成功: {hid_body}")
        
    except Exception as e:
        print(f"✗ 数据重建失败: {e}")

if __name__ == "__main__":
    test_packet_serialization()
    test_packet_reconstruction()
