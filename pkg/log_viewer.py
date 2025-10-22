"""
日志查看器 - 提供实时日志查看功能
"""
import os
import time
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QGroupBox
from qfluentwidgets import PushButton, BodyLabel, ComboBox, InfoBar, InfoBarPosition


class LogViewer(QWidget):
    """日志查看器界面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_file_path = "app.log"
        self.last_position = 0
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        """设置界面"""
        layout = QVBoxLayout()
        
        # 日志文件信息
        info_group = QGroupBox("日志文件信息")
        info_layout = QVBoxLayout()
        
        self.file_size_label = BodyLabel("文件大小: 0 KB")
        self.last_update_label = BodyLabel("最后更新: 从未")
        info_layout.addWidget(self.file_size_label)
        info_layout.addWidget(self.last_update_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 日志显示区域
        log_group = QGroupBox("实时日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(300)
        log_layout.addWidget(self.log_text)
        
        # 控制按钮
        control_layout = QHBoxLayout()
        
        self.auto_scroll_button = PushButton("自动滚动: 开启")
        self.auto_scroll_button.clicked.connect(self.toggle_auto_scroll)
        self.auto_scroll_enabled = True
        control_layout.addWidget(self.auto_scroll_button)
        
        self.clear_display_button = PushButton("清空显示")
        self.clear_display_button.clicked.connect(self.clear_display)
        control_layout.addWidget(self.clear_display_button)
        
        self.refresh_button = PushButton("刷新")
        self.refresh_button.clicked.connect(self.refresh_log)
        control_layout.addWidget(self.refresh_button)
        
        log_layout.addLayout(control_layout)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        self.setLayout(layout)
    
    def setup_timer(self):
        """设置定时器"""
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_log_display)
        self.timer.start(1000)  # 每秒更新一次
    
    def toggle_auto_scroll(self):
        """切换自动滚动"""
        self.auto_scroll_enabled = not self.auto_scroll_enabled
        self.auto_scroll_button.setText(f"自动滚动: {'开启' if self.auto_scroll_enabled else '关闭'}")
    
    def clear_display(self):
        """清空显示"""
        self.log_text.clear()
        self.last_position = 0
    
    def refresh_log(self):
        """刷新日志"""
        self.last_position = 0
        self.update_log_display()
    
    def update_log_display(self):
        """更新日志显示"""
        try:
            if not os.path.exists(self.log_file_path):
                return
            
            # 更新文件信息
            file_size = os.path.getsize(self.log_file_path)
            self.file_size_label.setText(f"文件大小: {file_size / 1024:.1f} KB")
            self.last_update_label.setText(f"最后更新: {time.strftime('%H:%M:%S')}")
            
            # 读取新内容
            with open(self.log_file_path, 'r', encoding='utf-8') as f:
                f.seek(self.last_position)
                new_content = f.read()
                self.last_position = f.tell()
            
            if new_content:
                # 添加新内容到显示区域
                self.log_text.append(new_content)
                
                # 自动滚动到底部
                if self.auto_scroll_enabled:
                    scrollbar = self.log_text.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())
                
                # 限制显示行数，避免内存占用过多
                lines = self.log_text.toPlainText().split('\n')
                if len(lines) > 1000:
                    self.log_text.setPlainText('\n'.join(lines[-1000:]))
                    
        except Exception as e:
            print(f"更新日志显示时出错: {e}")
    
    def closeEvent(self, event):
        """关闭事件"""
        if hasattr(self, 'timer'):
            self.timer.stop()
        event.accept()
