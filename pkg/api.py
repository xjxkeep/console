import requests
import hashlib
import base64
import time
import json
from pkg.model import Device,DeviceResponse,Version,VersionResponse


class API:
    def __init__(self, setting: dict):
        self.base_url = setting.get("base_url", "http://139.224.218.82:30080")
        self.user_agent = setting.get("user_agent", "Python-Client/1.0")
        self.token = setting.get("token", "0")
        self.source_device_id = setting.get("source_device_id", "0")
        self.arch = setting.get("arch", "x86_64")
        
    def generate_sign(self, timestamp: int, path: str, payload: str = "") -> str:
        """
        生成签名
        :param timestamp: 时间戳
        :param path: 请求路径
        :param payload: 请求体内容（POST/PUT/PATCH请求）
        :return: base64编码的签名
        """
        # 拼接字符串：timestamp|path|payload|userAgent
        sign_str = f"{timestamp}|{path}|{payload}|{self.user_agent}"
        # 计算sha256
        hash_obj = hashlib.sha256(sign_str.encode('utf-8'))
        hash_bytes = hash_obj.digest()
        
        # 返回base64编码的签名
        return base64.b64encode(hash_bytes).decode('utf-8')

    def _make_request(self, method: str, path: str, data: dict = None) -> requests.Response:
        """
        发送带签名的HTTP请求
        """
        url = f"{self.base_url}{path}"
        timestamp = int(time.time())
        
        # 准备payload
        payload = ""
        if data and method in ["POST", "PUT", "PATCH"]:
            payload = json.dumps(data)
        
        # 生成签名
        sign = self.generate_sign(timestamp, path, payload)
        # 准备请求头
        headers = {
            "timestamp": str(timestamp),
            "User-Agent": self.user_agent,
            "sign": sign,
            "Content-Type": "application/json",
            "device-token": self.token
        }
        
        # 发送请求
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        return response

    def get_device_info(self) -> Device:
        path = f"/verify/findDevice?device_id={self.source_device_id}"
        response = self._make_request("GET", path)
        response.raise_for_status()
        response = DeviceResponse.model_validate_json(json_data=response.content)
        print("get_device_info response",response)
        device=response.data
        return device
    
    def create_device(self, name: str, mac: str, version: str, token: str) -> Device:
        path = "/verify/createDevice"
        data = {"name": name, "mac": mac, "version": version, "token": token}
        response = self._make_request("POST", path, data)
        response.raise_for_status()
        response = DeviceResponse.model_validate_json(json_data=response.content)
        return response.data
    
    def update_device(self, name:str, mac:str, version:str, token:str) -> Device:
        path = f"/verify/updateDevice"
        data = {"name": name, "mac": mac, "version": version, "token": token}
        response = self._make_request("PUT", path, data)
        response.raise_for_status()
        response = DeviceResponse.model_validate_json(json_data=response.content)
        return response.data
    
    def delete_device(self, device_id: str) -> bool:
        path = f"/verify/deleteDevice?device_id={device_id}"
        response = self._make_request("DELETE", path)
        response.raise_for_status()
        return True
    
    
    def check_version(self) -> Version:
        path = f"/verify/checkVersion?arch={self.arch}"
        response = self._make_request("GET", path)
        response.raise_for_status()
        response = VersionResponse.model_validate_json(json_data=response.content)
        return response.data