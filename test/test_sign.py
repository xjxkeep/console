#!/usr/bin/env python3
"""
测试签名逻辑
"""

import hashlib
import base64
import json
import time
from pkg.api import API,Device

def test_sign_generation():
    """测试签名生成"""
    # 创建API实例
    api = API({
        "base_url": "http://localhost:8000",
        "user_agent": "Python-Client/1.0"
    })
    
    # 测试参数
    timestamp = int(time.time())
    path = "/device/123"
    payload = '{"name":"test","mac":"00:11:22:33:44:55"}'
    
    # 生成签名
    sign = api.generate_sign(timestamp, path, payload)
    
    print(f"Timestamp: {timestamp}")
    print(f"Path: {path}")
    print(f"Payload: {payload}")
    print(f"User-Agent: {api.user_agent}")
    print(f"Sign: {sign}")
    
    # 验证签名逻辑
    sign_str = f"{timestamp}|{path}|{payload}|{api.user_agent}"
    print(f"\nSign string: {sign_str}")
    
    # 手动计算签名进行验证
    hash_obj = hashlib.sha256(sign_str.encode('utf-8'))
    hash_bytes = hash_obj.digest()
    expected_sign = base64.b64encode(hash_bytes).decode('utf-8')
    
    print(f"Expected sign: {expected_sign}")
    print(f"Sign match: {sign == expected_sign}")
    
    return sign == expected_sign

def test_api_methods():
    """测试API方法"""
    api = API({
        "base_url": "http://localhost:8888",
        "user_agent": "Python-Client/1.0",
        "token": "123"
    })
    
    print("\n=== 测试API方法 ===")
    
    # 测试创建设备
    try:
        device = api.update_device("ceshi","sdf","1.0","123")
        print(f"create device: {device}")
    except Exception as e:
        print(f"Create device error: {e}")
    
    # 测试获取设备信息
    try:
        device = api.get_device_info(device.device_id)
        print(f"Device info: {device}")
    except Exception as e:
        print(f"Get device error: {e}")

if __name__ == "__main__":
    print("=== 签名测试 ===")
    test_sign_generation()
    test_api_methods() 