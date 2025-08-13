#!/usr/bin/env python3
"""
测试帧解析功能
"""

import json
import time

from pkg.model import HIDBody

def test_frame_parsing():
    """测试帧解析功能"""
    
    # 模拟HID数据（包含填充字节0）
    test_data = [
        # 第一个完整帧
        b'{"type": "response", "cmd": "test1", "request_id": "123", "args": {}, "returns": {"result": "success"}}',
        # 第二个完整帧（被分割）
        b'{"type": "response", "cmd": "test2", "request_id": "456", "args": {}, "returns": {"data": [1,2,3]}}',
        # 第三个完整帧
        b'{"type": "response", "cmd": "test3", "request_id": "789", "args": {}, "returns": {"message": "hello"}}'
    ]
    
    # 模拟包含填充字节的数据
    def add_padding(data, padding_ratio=0.3):
        """添加填充字节"""
        result = bytearray()
        for byte in data:
            result.append(byte)
            # 随机添加填充字节
            if time.time() % 1 < padding_ratio:
                result.append(0)
        return bytes(result)
    
    print("=== 测试帧解析功能 ===")
    
    # 模拟缓冲区
    buffer = bytearray()
    
    for i, data in enumerate(test_data):
        print(f"\n--- 处理数据块 {i+1} ---")
        
        # 添加填充字节
        padded_data = add_padding(data)
        print(f"原始数据: {data[:50]}...")
        print(f"添加填充后: {padded_data[:50]}...")
        
        # 添加到缓冲区
        buffer.extend(padded_data)
        print(f"缓冲区大小: {len(buffer)} 字节")
        
        # 模拟解析过程
        parse_frames(buffer)
    
    print(f"\n最终缓冲区大小: {len(buffer)} 字节")

def parse_frames(buffer):
    """模拟帧解析过程"""
    if not buffer:
        return
    
    # 过滤掉值为0的字节（HID填充字节）
    filtered_buffer = bytearray()
    for byte in buffer:
        if byte != 0:
            filtered_buffer.append(byte)
    
    if not filtered_buffer:
        # 如果过滤后没有数据，清空原缓冲区
        buffer.clear()
        print("过滤后无数据，清空缓冲区")
        return
    
    try:
        # 转换为字符串
        buffer_str = filtered_buffer.decode('utf-8', errors='ignore')
        print(f"过滤后字符串: {buffer_str}")
        
        # 查找完整的JSON对象
        json_start = 0
        brace_count = 0
        in_string = False
        escape_next = False
        processed_length = 0
        found_frames = []
        
        for i, char in enumerate(buffer_str):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    if brace_count == 0:
                        json_start = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # 找到一个完整的JSON对象
                        json_str = buffer_str[json_start:i+1]
                        try:
                            # 解析JSON并创建HIDBody
                            response_dict = json.loads(json_str)
                            hid_body = HIDBody(**response_dict)
                            
                            found_frames.append(hid_body)
                            print(f"解析成功: {hid_body}")
                            
                            # 更新已处理的数据长度
                            processed_length = i + 1
                            
                        except json.JSONDecodeError as e:
                            print(f"JSON解析失败: {e}, 数据: {json_str}")
                            # 如果解析失败，可能是数据不完整，继续等待更多数据
                            break
                        except Exception as e:
                            print(f"HIDBody创建失败: {e}")
                            processed_length = i + 1
        
        # 移除已处理的数据
        if processed_length > 0:
            # 计算原始缓冲区中对应的字节位置
            original_processed = 0
            filtered_index = 0
            
            for i, byte in enumerate(buffer):
                if byte != 0:  # 非填充字节
                    if filtered_index >= processed_length:
                        break
                    filtered_index += 1
                original_processed = i + 1
            
            # 移除已处理的原始数据
            buffer[:] = buffer[original_processed:]
            
            if found_frames:
                print(f"解析到 {len(found_frames)} 个完整帧")
                print(f"移除已处理数据，剩余: {len(buffer)} 字节")
        
    except Exception as e:
        print(f"帧解析失败: {e}")
        # 如果出现严重错误，清空缓冲区
        buffer.clear()

def test_incomplete_frame():
    """测试不完整帧的处理"""
    print("\n=== 测试不完整帧处理 ===")
    
    # 模拟不完整的帧数据
    incomplete_data = [
        b'{"type": "response", "cmd": "incomplete", "request_id": "xyz", "args": {}, "returns": {"status": "pending"',
        b'}}'
    ]
    
    buffer = bytearray()
    
    for i, data in enumerate(incomplete_data):
        print(f"\n--- 处理不完整数据块 {i+1} ---")
        print(f"数据: {data}")
        
        # 添加填充字节
        padded_data = add_padding(data)
        buffer.extend(padded_data)
        
        print(f"缓冲区大小: {len(buffer)} 字节")
        parse_frames(buffer)
    
    print(f"最终缓冲区大小: {len(buffer)} 字节")

def add_padding(data, padding_ratio=0.3):
    """添加填充字节"""
    result = bytearray()
    for byte in data:
        result.append(byte)
        # 随机添加填充字节
        if time.time() % 1 < padding_ratio:
            result.append(0)
    return bytes(result)

if __name__ == "__main__":
    test_frame_parsing()
    test_incomplete_frame()
