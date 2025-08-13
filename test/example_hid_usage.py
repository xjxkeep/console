#!/usr/bin/env python3
"""
HID设备使用示例
展示如何使用新的双线程架构的HID类
"""

import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit, QLabel
from PyQt5.QtCore import QTimer
from pkg.hid_caller import HID

class HIDTestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HID设备测试")
        self.setGeometry(100, 100, 600, 400)
        
        # 创建HID实例（需要替换为实际的vendor_id和product_id）
        self.hid = HID(vendor_id=0x1234, product_id=0x5678)  # 示例ID
        
        # 连接信号
        self.hid.connected.connect(self.on_device_connected)
        self.hid.disconnected.connect(self.on_device_disconnected)
        self.hid.data_received.connect(self.on_data_received)
        
        self.setup_ui()
        

        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 状态标签
        self.status_label = QLabel("设备状态: 未连接")
        layout.addWidget(self.status_label)
        
        # 测试按钮
        self.test_button = QPushButton("发送测试请求")
        self.test_button.clicked.connect(self.send_test_request)
        self.test_button.setEnabled(False)
        layout.addWidget(self.test_button)
        
        # 长数据测试按钮
        self.long_test_button = QPushButton("发送长数据请求")
        self.long_test_button.clicked.connect(self.send_long_request)
        self.long_test_button.setEnabled(False)
        layout.addWidget(self.long_test_button)
        
        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
    def on_device_connected(self):
        """设备连接成功"""
        self.status_label.setText("设备状态: 已连接")
        self.test_button.setEnabled(True)
        self.long_test_button.setEnabled(True)
        self.log_message("HID设备已连接")
        
    def on_device_disconnected(self):
        """设备断开连接"""
        self.status_label.setText("设备状态: 未连接")
        self.test_button.setEnabled(False)
        self.long_test_button.setEnabled(False)
        self.log_message("HID设备已断开")
        
    def send_test_request(self):
        """发送测试请求"""
        try:
            self.log_message("发送测试请求...")
            
            # 调用HID函数（阻塞等待响应）
            response = self.hid.call_function(
                method="test_function",
                args={"param1": "value1", "param2": 123}
            )
            
            self.log_message(f"收到响应: {response}")
            
        except Exception as e:
            self.log_message(f"请求失败: {e}")
    
    def send_long_request(self):
        """发送长数据请求（测试分包功能）"""
        try:
            self.log_message("发送长数据请求...")
            
            # 创建一个包含大量数据的请求
            long_args = {
                "data": "x" * 200,  # 200个字符的数据
                "array": list(range(100)),  # 100个数字的数组
                "nested": {
                    "level1": {
                        "level2": {
                            "level3": "deep_nested_value"
                        }
                    }
                }
            }
            
            response = self.hid.call_function(
                method="long_data_test",
                args=long_args
            )
            
            self.log_message(f"收到长数据响应: {response}")
            
        except Exception as e:
            self.log_message(f"长数据请求失败: {e}")
            
    def on_data_received(self, hid_body: HIDBody):
        """接收到HID数据时的处理"""
        self.log_message(f"接收到数据: {hid_body}")
        
        # 根据数据类型进行不同处理
        if hid_body.type == "response":
            self.log_message(f"响应数据: {hid_body.returns}")
        elif hid_body.type == "notification":
            self.log_message(f"通知数据: {hid_body.args}")
            
    def log_message(self, message):
        """添加日志消息"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        if hasattr(self, 'hid'):
            self.hid.cleanup()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # 创建测试窗口
    window = HIDTestWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
