#!/usr/bin/env python3
"""
API使用示例
"""

from pkg.api import API

def main():
    # 创建API实例
    api = API({
        "base_url": "http://localhost:8000",
        "user_agent": "Python-Client/1.0"
    })
    
    print("=== API使用示例 ===")
    
    # 示例1：创建设备
    print("\n1. 创建设备")
    try:
        device = api.create_device("我的设备", "AA:BB:CC:DD:EE:FF")
        print(f"设备创建成功: {device}")
    except Exception as e:
        print(f"创建设备失败: {e}")
    
    # 示例2：获取设备信息
    print("\n2. 获取设备信息")
    try:
        device = api.get_device_info("123")
        print(f"设备信息: {device}")
    except Exception as e:
        print(f"获取设备信息失败: {e}")
    
    # 示例3：更新设备
    print("\n3. 更新设备")
    try:
        device = api.update_device("123", "更新后的设备名", "11:22:33:44:55:66")
        print(f"设备更新成功: {device}")
    except Exception as e:
        print(f"更新设备失败: {e}")
    
    # 示例4：删除设备
    print("\n4. 删除设备")
    try:
        result = api.delete_device("123")
        print(f"设备删除成功: {result}")
    except Exception as e:
        print(f"删除设备失败: {e}")

if __name__ == "__main__":
    main() 