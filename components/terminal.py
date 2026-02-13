"""
终端组件 - PTY 远程终端
参考: highway/cmd/quic_pty/receiver/main.go

数据流 (receiver/client 端):
- 接收: stream -> stdout (Pty{Data: <shell output>})
- 发送: stdin -> stream (Pty{Data: <input>, WindowWidth: <w>, WindowHeight: <h>})

关键行为:
1. 连接建立后立即发送当前窗口大小
2. 每次发送输入时都附带当前窗口大小
"""
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import (
    QColor, QPalette, QTextCursor, QTextCharFormat, QFont, QFontMetrics
)
from PyQt5.QtWidgets import (
    QVBoxLayout, QTextEdit, QFrame
)
from qfluentwidgets import FluentIcon, GroupHeaderCardWidget, ComboBox
import logging
from protocol.highway_pb2 import Pty


# ANSI 颜色代码映射
ANSI_COLORS = {
    '30': QColor(0, 0, 0),       # 黑色
    '31': QColor(205, 49, 49),   # 红色
    '32': QColor(13, 188, 121),  # 绿色
    '33': QColor(229, 229, 16),  # 黄色
    '34': QColor(36, 113, 163),  # 蓝色
    '35': QColor(188, 63, 188),  # 品红
    '36': QColor(17, 168, 205),  # 青色
    '37': QColor(238, 238, 238), # 白色
    '90': QColor(102, 102, 102),  # 亮黑（灰）
    '91': QColor(241, 76, 76),   # 亮红
    '92': QColor(42, 161, 152),  # 亮绿
    '93': QColor(242, 204, 96),  # 亮黄
    '94': QColor(42, 145, 190),  # 亮蓝
    '95': QColor(211, 54, 130),  # 亮品红
    '96': QColor(42, 161, 152),  # 亮青
    '97': QColor(255, 255, 255), # 亮白
}

# ANSI 背景色代码映射
ANSI_BG_COLORS = {
    '40': QColor(0, 0, 0),       # 黑色背景
    '41': QColor(205, 49, 49),   # 红色背景
    '42': QColor(13, 188, 121),  # 绿色背景
    '43': QColor(229, 229, 16),  # 黄色背景
    '44': QColor(36, 113, 163),  # 蓝色背景
    '45': QColor(188, 63, 188),  # 品红背景
    '46': QColor(17, 168, 205),  # 青色背景
    '47': QColor(238, 238, 238), # 白色背景
    '100': QColor(102, 102, 102), # 亮黑背景
    '101': QColor(241, 76, 76),  # 亮红背景
    '102': QColor(42, 161, 152), # 亮绿背景
    '103': QColor(242, 204, 96), # 亮黄背景
    '104': QColor(42, 145, 190), # 亮蓝背景
    '105': QColor(211, 54, 130), # 亮品红背景
    '106': QColor(42, 161, 152), # 亮青背景
    '107': QColor(255, 255, 255), # 亮白背景
}


class TerminalTextEdit(QTextEdit):
    """PTY 远程终端文本编辑器

    对外接口:
        write(data: bytes): 接收远程 PTY 输出并显示
        data_to_send: (data: bytes, width: int, height: int) - 发送数据到远程 PTY
    """

    data_to_send = pyqtSignal(Pty)  # width, height, data

    def __init__(self, parent=None):
        super().__init__(parent)

        # 字体设置 - 使用等宽字体
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        self.setFont(font)

        # 字体度量，用于计算字符列数
        self._font_metrics = QFontMetrics(font)
        self._char_width = self._font_metrics.width('M')
        self._char_height = self._font_metrics.height()

        # 默认窗口大小 (字符数)
        self._window_cols = 80
        self._window_rows = 24

        # 设置背景色和前景色
        palette = self.palette()
        palette.setColor(QPalette.Base, QColor(28, 28, 28))
        palette.setColor(QPalette.Text, QColor(238, 238, 238))
        self.setPalette(palette)

        # 其他设置
        self.setFrameStyle(QFrame.NoFrame)
        self.setAcceptRichText(True)
        # 允许键盘事件但不允许直接编辑文本
        self.setTextInteractionFlags(
            Qt.TextSelectableByMouse |
            Qt.TextSelectableByKeyboard |
            Qt.TextEditable
        )
        # 确保能获取键盘焦点
        self.setFocusPolicy(Qt.StrongFocus)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def sizeHint(self):
        """返回推荐大小"""
        return QSize(
            self._char_width * self._window_cols,
            self._char_height * self._window_rows
        )

    def resizeEvent(self, event):
        """窗口大小改变时计算新的字符行列数"""
        super().resizeEvent(event)

        # 计算新的字符列数和行数
        new_cols = max(80, event.size().width() // self._char_width)
        new_rows = max(24, event.size().height() // self._char_height)

        if new_cols != self._window_cols or new_rows != self._window_rows:
            self._window_cols = new_cols
            self._window_rows = new_rows
            # 窗口大小改变时，发送空数据和新的窗口尺寸
            pty = Pty(window_width=new_cols, window_height=new_rows, data=b'')
            self.data_to_send.emit(pty)

    def get_window_size(self):
        """获取当前窗口大小 (cols, rows)"""
        return self._window_cols, self._window_rows

    def write(self, data: bytes):
        """接收远程 PTY 输出并显示

        Args:
            data: 来自远程 PTY 的数据 (bytes)
        """
        try:
            # 解码数据
            text = data.decode('utf-8', errors='replace')
            self._append_ansi_text(text)
        except:
            # 解码失败，尝试其他编码
            try:
                text = data.decode('latin-1', errors='replace')
                self._append_ansi_text(text)
            except:
                pass

    def _append_ansi_text(self, text: str):
        """追加带 ANSI 转义码的文本"""
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End)

        current_format = QTextCharFormat()
        current_format.setForeground(QColor(238, 238, 238))
        current_format.setBackground(QColor(28, 28, 28))
        bold = False
        italic = False
        underline = False

        pos = 0
        while pos < len(text):
            # 检查是否有 ANSI 转义序列
            if text[pos] == '\x1b' and pos + 1 < len(text) and text[pos + 1] == '[':
                # 找到转义序列结束位置
                end_pos = pos + 2
                while end_pos < len(text) and text[end_pos] not in 'mKHJABCDGhlsx':
                    end_pos += 1

                if end_pos < len(text):
                    end_pos += 1  # 包含结束字符
                    esc_seq = text[pos:end_pos]

                    # 处理转义序列
                    if esc_seq[-1] == 'm':
                        # 颜色/样式序列
                        params = esc_seq[2:-1]
                        if params == '' or params == '0':
                            current_format.setForeground(QColor(238, 238, 238))
                            current_format.setBackground(QColor(28, 28, 28))
                            bold = False
                            italic = False
                            underline = False
                        else:
                            codes = params.split(';')
                            for code in codes:
                                if code == '1':
                                    bold = True
                                elif code == '3':
                                    italic = True
                                elif code == '4':
                                    underline = True
                                elif code == '22':
                                    bold = False
                                elif code == '23':
                                    italic = False
                                elif code == '24':
                                    underline = False
                                elif code in ANSI_COLORS:
                                    current_format.setForeground(ANSI_COLORS[code])
                                elif code in ANSI_BG_COLORS:
                                    current_format.setBackground(ANSI_BG_COLORS[code])
                                # 处理 RGB 颜色 (ESC[38;2;r;g;bm / ESC[48;2;r;g;bm)
                                elif code == '38' and len(codes) >= 5 and codes[1] == '2':
                                    r = int(codes[2]) if len(codes) > 2 else 0
                                    g = int(codes[3]) if len(codes) > 3 else 0
                                    b = int(codes[4]) if len(codes) > 4 else 0
                                    current_format.setForeground(QColor(r, g, b))
                                elif code == '48' and len(codes) >= 5 and codes[1] == '2':
                                    r = int(codes[2]) if len(codes) > 2 else 0
                                    g = int(codes[3]) if len(codes) > 3 else 0
                                    b = int(codes[4]) if len(codes) > 4 else 0
                                    current_format.setBackground(QColor(r, g, b))

                        # 应用样式
                        font = self.font()
                        if bold:
                            font.setBold(True)
                        if italic:
                            font.setItalic(True)
                        current_format.setFont(font)
                        if underline:
                            current_format.setUnderlineStyle(QTextCharFormat.SingleUnderline)
                        else:
                            current_format.setUnderlineStyle(QTextCharFormat.NoUnderline)

                    elif esc_seq[-1] == 'K':
                        # 清除行 (ESC[K - 清除到行尾)
                        pass

                    elif esc_seq[-1] == 'H':
                        # 光标定位 (ESC[row;colH) - 简化处理
                        pass

                    pos = end_pos
                else:
                    pos += 1
            else:
                # 普通文本
                next_ansi = text.find('\x1b[', pos)
                if next_ansi == -1:
                    next_ansi = len(text)

                # 处理控制字符
                chunk = text[pos:next_ansi]
                display_chunk = chunk.replace('\r\n', '\n').replace('\r', '\n')
                cursor.insertText(display_chunk, current_format)
                pos = next_ansi

        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def focusInEvent(self, event):
        """获得焦点时"""
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        """失去焦点时"""
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        """处理键盘输入 - 发送到远程 PTY，每次都附带窗口大小"""
        # 获取按键和修饰符
        logging.info(f"keyPressEvent: {event}")
        key = event.key()
        modifiers = event.modifiers()
        text = event.text()

        # 处理特殊按键
        data = b''

        if key == Qt.Key_Return or key == Qt.Key_Enter:
            # Enter 键发送 CR (\r)
            data = b'\r'
        elif key == Qt.Key_Backspace:
            # Backspace 键发送 DEL (0x7F)
            data = b'\x7f'
        elif key == Qt.Key_Tab:
            # Tab 键
            data = b'\t'
        elif key == Qt.Key_Up:
            data = b'\x1b[A'  # ANSI 上箭头
        elif key == Qt.Key_Down:
            data = b'\x1b[B'  # ANSI 下箭头
        elif key == Qt.Key_Left:
            data = b'\x1b[D'  # ANSI 左箭头
        elif key == Qt.Key_Right:
            data = b'\x1b[C'  # ANSI 右箭头
        elif key == Qt.Key_Home:
            data = b'\x1b[H'  # Home
        elif key == Qt.Key_End:
            data = b'\x1b[F'  # End
        elif key == Qt.Key_PageUp:
            data = b'\x1b[5~'  # PageUp
        elif key == Qt.Key_PageDown:
            data = b'\x1b[6~'  # PageDown
        elif key == Qt.Key_Delete:
            data = b'\x1b[3~'  # Delete
        elif key == Qt.Key_Escape:
            data = b'\x1b'  # ESC
        elif key == Qt.Key_C and modifiers & Qt.ControlModifier:
            # Ctrl+C 发送 ETX (0x03) - 中断信号
            data = b'\x03'
        elif key == Qt.Key_D and modifiers & Qt.ControlModifier:
            # Ctrl+D 发送 EOT (0x04) - EOF
            data = b'\x04'
        elif key == Qt.Key_L and modifiers & Qt.ControlModifier:
            # Ctrl+L 发送 FF (0x0C) - 清屏
            data = b'\x0c'
        elif key == Qt.Key_Z and modifiers & Qt.ControlModifier:
            # Ctrl+Z 发送 SUB (0x1A) - 挂起
            data = b'\x1a'
        elif modifiers & Qt.ControlModifier:
            # 其他 Ctrl 组合键 (Ctrl+A = 1, Ctrl+B = 2, ...)
            if Qt.Key_A <= key <= Qt.Key_Z:
                ctrl_code = key - Qt.Key_A + 1
                data = bytes([ctrl_code])
        elif text:
            # 普通字符
            data = text.encode('utf-8', errors='ignore')

        # 发送数据到远程 PTY，每次都附带当前窗口大小
        if data:
            pty = Pty(window_width=self._window_cols, window_height=self._window_rows, data=data)
            self.data_to_send.emit(pty)

        # 阻止默认的文本编辑行为
        event.accept()

    def mousePressEvent(self, event):
        """鼠标事件 - 允许复制选中文本"""
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        """右键菜单 - 复制和清屏"""
        from PyQt5.QtWidgets import QMenu
        from qfluentwidgets import Action

        menu = QMenu(self)

        # 复制
        copy_action = Action(FluentIcon.COPY, '复制', self)
        copy_action.triggered.connect(self.copy)
        copy_action.setEnabled(self.textCursor().hasSelection())
        menu.addAction(copy_action)

        menu.addSeparator()

        # 清屏
        clear_action = Action(FluentIcon.DELETE, '清屏', self)
        clear_action.triggered.connect(self.clear)
        menu.addAction(clear_action)

        menu.exec_(event.globalPos())

    def clear(self):
        """清空终端"""
        self.clear()


class TerminalPanel(GroupHeaderCardWidget):
    """终端面板组件

    对外接口:
        write(data: bytes): 接收远程 PTY 输出并显示
        send_to_pty: (data: bytes, width: int, height: int) - 发送到 PTY
        param_changed: (dict) - 参数改变
    """

    send_to_pty = pyqtSignal(Pty)  # pty
    param_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """初始化UI"""
        self.setTitle("终端")

        # 主布局
        self.vBoxLayout = QVBoxLayout()
        self.vBoxLayout.setContentsMargins(0, 0, 0, 0)
        self.vBoxLayout.setSpacing(0)
        self.vBoxLayout.setAlignment(Qt.AlignTop)

        # 终端编辑器
        self.terminal = TerminalTextEdit(self)
        # 连接终端输入信号到面板信号
        self.terminal.data_to_send.connect(self.send_to_pty)
        self.vBoxLayout.addWidget(self.terminal)

        # 头部布局（已有）
        self.headerLayout.addStretch()

        # 字体大小选择
        self.font_size_combo = ComboBox()
        self.font_size_combo.addItems(["10pt", "12pt", "14pt", "16pt"])
        self.font_size_combo.setCurrentIndex(0)
        self.font_size_combo.currentIndexChanged.connect(self._on_font_size_changed)
        self.headerLayout.addWidget(self.font_size_combo)

        # 清屏按钮
        from qfluentwidgets import TransparentToolButton
        self.clear_btn = TransparentToolButton(
            FluentIcon.DELETE.icon(),
            self
        )
        self.clear_btn.clicked.connect(self.terminal.clear)
        self.headerLayout.addWidget(self.clear_btn)

        # 设置布局
        self.viewLayout.addLayout(self.vBoxLayout)

    def write(self, data: bytes):
        """接收远程 PTY 输出并显示

        Args:
            data: 来自远程 PTY 的数据
        """
        self.terminal.write(data)

    def get_window_size(self):
        """获取当前窗口大小 (cols, rows)"""
        return self.terminal.get_window_size()

    def send_window_size(self):
        """发送当前窗口大小 (无数据)"""
        cols, rows = self.terminal.get_window_size()
        pty = Pty(window_width=cols, window_height=rows, data=b'')
        self.send_to_pty.emit(pty)

    def clear(self):
        """清空终端"""
        self.terminal.clear()

    def _on_font_size_changed(self, index: int):
        """字体大小改变"""
        font_sizes = [10, 12, 14, 16]
        font = self.terminal.font()
        font.setPointSize(font_sizes[index])
        self.terminal.setFont(font)

        # 更新字符度量
        fm = QFontMetrics(font)
        self.terminal._char_width = fm.width('M')
        self.terminal._char_height = fm.height()

        self.param_changed.emit({"font_size": font_sizes[index]})
