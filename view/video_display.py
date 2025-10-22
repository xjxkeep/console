import logging

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QVBoxLayout,
    QWidget,
)
class VideoDisplayWidget(QWidget):
    """基于QGraphicsView + QGraphicsPixmapItem的高性能视频显示组件
    保持与QLabel.setPixmap()接口兼容
    """
    
    def __init__(self, text="无信号，等待客户端连接...", parent=None):
        super().__init__(parent)
        self.setup_ui(text)
        
    def setup_ui(self, text):
        """初始化UI"""
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        # 创建GraphicsView和Scene
        self.graphics_view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)
        
        # 创建PixmapItem
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        
        # 设置视图属性 - 优化性能
        self.graphics_view.setRenderHint(QPainter.Antialiasing, True)
        self.graphics_view.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphics_view.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.graphics_view.setAlignment(Qt.AlignCenter)
        
        # 设置样式
        self.graphics_view.setStyleSheet("background-color: rgb(0,0,0);")
        
        # 初始文本显示
        self.setText(text)
        
        self.layout().addWidget(self.graphics_view)
        
    def setPixmap(self, pixmap: QPixmap):
        """设置图像 - 与QLabel.setPixmap()兼容的接口"""
        try:
            if pixmap and not pixmap.isNull():
                # 设置图像
                self.pixmap_item.setPixmap(pixmap)
                
                # 调整场景大小以适应图像
                self.scene.setSceneRect(self.pixmap_item.boundingRect())
                
                # 自动调整视图以适应图像
                self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
                
                # 清除文本显示
                self.clearText()
            else:
                self.setText("无效图像")
                
        except Exception as e:
            logging.info(f"Error setting pixmap: {str(e)}")
            self.setText("图像显示错误")
    
    def setText(self, text: str):
        """设置文本 - 与QLabel.setText()兼容的接口"""
        try:
            # 清除图像
            self.pixmap_item.setPixmap(QPixmap())
            
            # 创建文本项
            from PyQt5.QtWidgets import QGraphicsTextItem
            from PyQt5.QtGui import QFont
            
            # 移除之前的文本项
            for item in self.scene.items():
                if isinstance(item, QGraphicsTextItem):
                    self.scene.removeItem(item)
            
            # 添加新文本项
            text_item = QGraphicsTextItem(text)
            font = QFont()
            font.setPointSize(14)
            text_item.setFont(font)
            text_item.setDefaultTextColor(Qt.white)
            
            # 居中显示文本
            text_rect = text_item.boundingRect()
            text_item.setPos(-text_rect.width()/2, -text_rect.height()/2)
            
            self.scene.addItem(text_item)
            self.scene.setSceneRect(text_item.boundingRect())
            
        except Exception as e:
            logging.info(f"Error setting text: {str(e)}")
    
    def clearText(self):
        """清除文本显示"""
        for item in self.scene.items():
            if isinstance(item, QGraphicsTextItem):
                self.scene.removeItem(item)
    
    def pixmap(self) -> QPixmap:
        """获取当前图像 - 与QLabel.pixmap()兼容的接口"""
        return self.pixmap_item.pixmap()
    
    def text(self) -> str:
        """获取当前文本 - 与QLabel.text()兼容的接口"""
        for item in self.scene.items():
            if isinstance(item, QGraphicsTextItem):
                return item.toPlainText()
        return ""
    
    def clear(self):
        """清除所有内容 - 与QLabel.clear()兼容的接口"""
        self.pixmap_item.setPixmap(QPixmap())
        self.clearText()
        self.setText("无信号，等待客户端连接...")
    
    def setAlignment(self, alignment):
        """设置对齐方式 - 与QLabel.setAlignment()兼容的接口"""
        self.graphics_view.setAlignment(alignment)
    
    def setSizePolicy(self, policy):
        """设置大小策略 - 与QLabel.setSizePolicy()兼容的接口"""
        self.graphics_view.setSizePolicy(policy)
    
    def setStyleSheet(self, style):
        """设置样式表 - 与QLabel.setStyleSheet()兼容的接口"""
        self.graphics_view.setStyleSheet(style)
    
    def resizeEvent(self, event):
        """窗口大小改变时自动调整视图"""
        super().resizeEvent(event)
        if self.pixmap_item.pixmap() and not self.pixmap_item.pixmap().isNull():
            self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
    
    def showEvent(self, event):
        """显示事件 - 确保视图正确显示"""
        super().showEvent(event)
        if self.pixmap_item.pixmap() and not self.pixmap_item.pixmap().isNull():
            self.graphics_view.fitInView(self.pixmap_item, Qt.KeepAspectRatio) 