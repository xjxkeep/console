#!/usr/bin/env python3
"""
测试数据缓冲和JSON解析功能
"""

import json
import time
from pkg.model import HIDResponse

def test_json_parsing():
    """测试JSON解析功能"""
    
    # 模拟HID响应数据
    test_responses = [
        '{"type": "response", "cmd": "test1", "request_id": "123", "args": {}, "returns": {"result": "success"}}',
        '{"type": "response", "cmd": "test2", "request_id": "456", "args": {}, "returns": {"data": [1,2,3]}}',
        '{"type": "response", "cmd": "test3", "request_id": "789", "args": {}, "returns": {"message": "hello world"}}'
    ]
    
    # 测试完整JSON解析
    print("=== 测试完整JSON解析 ===")
    for i, json_str in enumerate(test_responses):
        try:
            response_dict = json.loads(json_str)
            response = HIDResponse(**response_dict)
            print(f"响应 {i+1}: {response}")
        except Exception as e:
            print(f"解析失败 {i+1}: {e}")
    
    print("\n=== 测试分割的JSON数据 ===")
    
    # 模拟分割的JSON数据
    split_data = [
        b'{"type": "response", "cmd": "split1", "request_id": "abc", "args": {}, "returns": {"status": "ok"}}',
        b'{"type": "response", "cmd": "split2", "request_id": "def", "args": {}, "returns": {"value": 42}}',
        b'{"type": "response", "cmd": "split3", "request_id": "ghi", "args": {}, "returns": {"message": "test"}}'
    ]
    
    # 模拟数据被分割的情况
    buffer = bytearray()
    
    for i, data in enumerate(split_data):
        print(f"\n添加数据块 {i+1}: {data[:20]}...")
        buffer.extend(data)
        
        # 模拟解析过程
        try:
            buffer_str = buffer.decode('utf-8', errors='ignore')
            print(f"缓冲区内容: {buffer_str}")
            
            # 尝试找到完整的JSON对象
            json_start = 0
            brace_count = 0
            in_string = False
            escape_next = False
            processed_length = 0
            
            for j, char in enumerate(buffer_str):
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
                            json_start = j
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            # 找到一个完整的JSON对象
                            json_str = buffer_str[json_start:j+1]
                            try:
                                response_dict = json.loads(json_str)
                                response = HIDResponse(**response_dict)
                                print(f"解析成功: {response}")
                                processed_length = j + 1
                            except json.JSONDecodeError as e:
                                print(f"JSON解析失败: {e}")
                                break
                            except Exception as e:
                                print(f"响应创建失败: {e}")
                                processed_length = j + 1
            
            # 移除已处理的数据
            if processed_length > 0:
                buffer = buffer[processed_length:]
                print(f"移除已处理数据，剩余: {len(buffer)} 字节")
            
        except Exception as e:
            print(f"缓冲区处理失败: {e}")

def test_incomplete_json():
    """测试不完整JSON的处理"""
    print("\n=== 测试不完整JSON处理 ===")
    
    # 模拟不完整的JSON数据
    incomplete_data = [
        b'{"type": "response", "cmd": "incomplete", "request_id": "xyz", "args": {}, "returns": {"status": "pending"',
        b'}}'
    ]
    
    buffer = bytearray()
    
    for i, data in enumerate(incomplete_data):
        print(f"\n添加不完整数据块 {i+1}: {data}")
        buffer.extend(data)
        
        try:
            buffer_str = buffer.decode('utf-8', errors='ignore')
            print(f"缓冲区内容: {buffer_str}")
            
            # 尝试解析
            try:
                response_dict = json.loads(buffer_str)
                response = HIDResponse(**response_dict)
                print(f"解析成功: {response}")
                buffer.clear()
            except json.JSONDecodeError as e:
                print(f"JSON不完整，等待更多数据: {e}")
                # 保持数据在缓冲区中
            except Exception as e:
                print(f"其他错误: {e}")
                
        except Exception as e:
            print(f"缓冲区处理失败: {e}")

if __name__ == "__main__":
    test_json_parsing()
    test_incomplete_json()
