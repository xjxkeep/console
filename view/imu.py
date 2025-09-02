import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QDoubleSpinBox)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from OpenGL.GL import *
from OpenGL.GLU import *
from PyQt5.QtOpenGL import QGLWidget

class IMUVisualizer(QGLWidget):
    """IMU姿态可视化控件"""
    def __init__(self, parent=None):
        super(IMUVisualizer, self).__init__(parent)
        # 设置固定大小为200x200
        self.setFixedSize(400, 400)
        # self.setMinimumSize(200, 200)
        
        # 设置高DPI支持
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        
        # 设置像素完美渲染
        self.setAttribute(Qt.WA_PaintOnScreen, True)
        
        # 初始姿态角 (欧拉角：滚转角、俯仰角、偏航角)
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0
        
        # 初始化定时器用于更新显示
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateGL)
        self.timer.start(16)  # 60Hz更新频率，提高动画流畅度

    def initializeGL(self):
        """初始化OpenGL"""
        glClearColor(0.1, 0.1, 0.1, 1)  # 背景色
        glEnable(GL_DEPTH_TEST)  # 启用深度测试
        glEnable(GL_LIGHTING)    # 启用光照
        glEnable(GL_LIGHT0)      # 启用光源0
        glEnable(GL_COLOR_MATERIAL)  # 启用颜色材质
        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        
        # 启用多重采样抗锯齿 (MSAA)
        glEnable(GL_MULTISAMPLE)
        
        # 启用线条抗锯齿
        glEnable(GL_LINE_SMOOTH)  # 线条抗锯齿
        glEnable(GL_POLYGON_SMOOTH)  # 多边形抗锯齿
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)  # 最高质量线条
        glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)  # 最高质量多边形
        
        # 启用点抗锯齿
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        
        # 设置混合函数，改善抗锯齿效果
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # 设置光源
        light_pos = [1.0, 1.0, 1.0, 0.0]  # 方向光
        light_ambient = [0.2, 0.2, 0.2, 1.0]
        light_diffuse = [0.8, 0.8, 0.8, 1.0]
        glLightfv(GL_LIGHT0, GL_POSITION, light_pos)
        glLightfv(GL_LIGHT0, GL_AMBIENT, light_ambient)
        glLightfv(GL_LIGHT0, GL_DIFFUSE, light_diffuse)

    def resizeGL(self, width, height):
        """窗口大小改变时调整视口"""
        # 确保视口大小与窗口大小完全匹配
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        # 对于400x400的固定窗口，使用正交投影
        if width == height:  # 正方形窗口
            # 使用正交投影，缩小投影范围让模型更大更紧凑
            glOrtho(-0.6, 0.6, -0.6, 0.6, 0.1, 100.0)
        else:
            # 非正方形窗口使用透视投影
            aspect = width / height if height > 0 else 1.0
            gluPerspective(60, aspect, 0.1, 100.0)

    def paintGL(self):
        """绘制场景"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # 对于400x400窗口，调整相机位置
        if self.width() == 400 and self.height() == 400:
            # 使用正交投影时的相机设置
            gluLookAt(0, 0, 3,  # 相机距离更近，让模型更大
                      0, 0, 0,  # 目标点
                      0, 1, 0)  # 上方向
        else:
            # 透视投影时的相机设置
            gluLookAt(0, 0, 8,  # 相机位置
                      0, 0, 0,  # 目标点
                      0, 1, 0)  # 上方向
        
        # 根据姿态角旋转
        glRotatef(self.yaw, 0, 1, 0)    # 偏航角 (Y轴)
        glRotatef(self.pitch, 1, 0, 0)  # 俯仰角 (X轴)
        glRotatef(self.roll, 0, 0, 1)   # 滚转角 (Z轴)
        
        # 绘制IMU坐标系和模型
        self.draw_imu_model()

    def draw_imu_model(self):
        """绘制IMU模型"""
        # 绘制背景网格，减少空白区域
        self.draw_background_grid()
        
        # 绘制坐标轴 - 调整长度适应新的紧凑投影范围
        glLineWidth(4.0)  # 增加线宽，提高清晰度
        
        # X轴 - 红色
        glColor3f(1, 0, 0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(0.5, 0, 0)  # 调整轴长度适应新的投影范围
        glEnd()
        
        # Y轴 - 绿色
        glColor3f(0, 1, 0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0.5, 0)  # 调整轴长度适应新的投影范围
        glEnd()
        
        # Z轴 - 蓝色
        glColor3f(0, 0, 1)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 0.5)  # 调整轴长度适应新的投影范围
        glEnd()
        
        # 绘制坐标轴端点装饰，减少空白区域
        self.draw_axis_decorations()
        
        # 绘制IMU立方体模型 - 调整大小适应新的紧凑投影范围
        glColor3f(0.5, 0.5, 1.0)  # 蓝色调
        self.draw_cube(0.4)  # 调整立方体大小，更好地填充空间

    def draw_background_grid(self):
        """绘制背景网格，减少空白区域"""
        glColor3f(0.15, 0.15, 0.15)  # 稍微调亮网格颜色，减少锯齿感
        glLineWidth(1.5)  # 稍微增加网格线宽，减少锯齿
        
        # 绘制XY平面的网格线
        glBegin(GL_LINES)
        for i in range(-6, 7):  # 增加网格密度
            # X方向网格线
            glVertex3f(i * 0.1, -0.6, 0)
            glVertex3f(i * 0.1, 0.6, 0)
            # Y方向网格线
            glVertex3f(-0.6, i * 0.1, 0)
            glVertex3f(0.6, i * 0.1, 0)
        glEnd()
        
        # 绘制XZ平面的网格线
        glBegin(GL_LINES)
        for i in range(-6, 7):  # 增加网格密度
            # X方向网格线
            glVertex3f(i * 0.1, 0, -0.6)
            glVertex3f(i * 0.1, 0, 0.6)
            # Z方向网格线
            glVertex3f(-0.6, 0, i * 0.1)
            glVertex3f(0.6, 0, i * 0.1)
        glEnd()
        
        # 绘制YZ平面的网格线（添加第三个平面）
        glBegin(GL_LINES)
        for i in range(-6, 7):
            # Y方向网格线
            glVertex3f(0, i * 0.1, -0.6)
            glVertex3f(0, i * 0.1, 0.6)
            # Z方向网格线
            glVertex3f(0, -0.6, i * 0.1)
            glVertex3f(0, 0.6, i * 0.1)
        glEnd()

    def draw_cube(self, size):
        """绘制立方体"""
        half = size / 2.0
        vertices = [
            [-half, -half, -half], [half, -half, -half],
            [half, half, -half], [-half, half, -half],
            [-half, -half, half], [half, -half, half],
            [half, half, half], [-half, half, half]
        ]
        
        # 面的索引
        faces = [
            [0, 1, 2, 3],  # 前面
            [4, 5, 6, 7],  # 后面
            [0, 1, 5, 4],  # 下面
            [2, 3, 7, 6],  # 上面
            [1, 2, 6, 5],  # 右面
            [0, 3, 7, 4]   # 左面
        ]
        
        # 法向量，改善光照效果
        normals = [
            [0, 0, -1],  # 前面
            [0, 0, 1],   # 后面
            [0, -1, 0],  # 下面
            [0, 1, 0],   # 上面
            [1, 0, 0],   # 右面
            [-1, 0, 0]   # 左面
        ]
        
        glBegin(GL_QUADS)
        for i, face in enumerate(faces):
            glNormal3fv(normals[i])  # 设置法向量
            for vertex in face:
                glVertex3fv(vertices[vertex])
        glEnd()
        
        # 绘制边框，使用更粗的线条减少锯齿
        glColor3f(0, 0, 0)
        glLineWidth(3.0)  # 增加边框线宽，在紧凑布局下更清晰
        glBegin(GL_LINES)
        # 前面
        glVertex3fv(vertices[0])
        glVertex3fv(vertices[1])
        glVertex3fv(vertices[1])
        glVertex3fv(vertices[2])
        glVertex3fv(vertices[2])
        glVertex3fv(vertices[3])
        glVertex3fv(vertices[3])
        glVertex3fv(vertices[0])
        
        # 后面
        glVertex3fv(vertices[4])
        glVertex3fv(vertices[5])
        glVertex3fv(vertices[5])
        glVertex3fv(vertices[6])
        glVertex3fv(vertices[6])
        glVertex3fv(vertices[7])
        glVertex3fv(vertices[7])
        glVertex3fv(vertices[4])
        
        # 连接前后
        glVertex3fv(vertices[0])
        glVertex3fv(vertices[4])
        glVertex3fv(vertices[1])
        glVertex3fv(vertices[5])
        glVertex3fv(vertices[2])
        glVertex3fv(vertices[6])
        glVertex3fv(vertices[3])
        glVertex3fv(vertices[7])
        glEnd()

    def draw_axis_decorations(self):
        """绘制坐标轴端点装饰，减少空白区域"""
        # X轴端点装饰（红色小球）
        glColor3f(1, 0, 0)
        self.draw_sphere(0.5, 0, 0, 0.03)
        
        # Y轴端点装饰（绿色小球）
        glColor3f(0, 1, 0)
        self.draw_sphere(0, 0.5, 0, 0.03)
        
        # Z轴端点装饰（蓝色小球）
        glColor3f(0, 0, 1)
        self.draw_sphere(0, 0, 0.5, 0.03)
        
        # 原点装饰（白色小球）
        glColor3f(1, 1, 1)
        self.draw_sphere(0, 0, 0, 0.02)

    def draw_sphere(self, x, y, z, radius):
        """绘制小球体"""
        glPushMatrix()
        glTranslatef(x, y, z)
        
        # 使用更高分辨率的四边形近似绘制球体，减少锯齿
        slices = 16  # 增加切片数
        stacks = 16  # 增加堆叠数
        
        for i in range(stacks):
            lat0 = np.pi * (-0.5 + float(i) / stacks)
            z0 = np.sin(lat0)
            zr0 = np.cos(lat0)
            
            lat1 = np.pi * (-0.5 + float(i + 1) / stacks)
            z1 = np.sin(lat1)
            zr1 = np.cos(lat1)
            
            glBegin(GL_QUAD_STRIP)
            for j in range(slices + 1):
                lng = 2 * np.pi * float(j) / slices
                x = np.cos(lng)
                y = np.sin(lng)
                
                glNormal3f(x * zr0, y * zr0, z0)
                glVertex3f(x * zr0 * radius, y * zr0 * radius, z0 * radius)
                glNormal3f(x * zr1, y * zr1, z1)
                glVertex3f(x * zr1 * radius, y * zr1 * radius, z1 * radius)
            glEnd()
        
        glPopMatrix()

    def update_orientation_from_sensors(self, accel, gyro, dt=0.05):
        """
        从加速度计和陀螺仪数据更新姿态角
        accel: 三轴加速度 [ax, ay, az]
        gyro: 三轴角速度 [gx, gy, gz] (单位：度/秒)
        dt: 时间间隔 (秒)
        """
        # 从加速度计算俯仰角和滚转角
        ax, ay, az = accel
        
        # 计算俯仰角 (pitch) 和滚转角 (roll)
        pitch_acc = np.arctan2(ax, np.sqrt(ay**2 + az**2)) * 180 / np.pi
        roll_acc = np.arctan2(-ay, az) * 180 / np.pi
        
        # 从陀螺仪积分获取角度变化
        gx, gy, gz = gyro
        self.roll += gx * dt
        self.pitch += gy * dt
        self.yaw += gz * dt
        
        # 互补滤波：融合加速度计和陀螺仪数据
        alpha = 0.96  # 权重因子
        self.roll = alpha * self.roll + (1 - alpha) * roll_acc
        self.pitch = alpha * self.pitch + (1 - alpha) * pitch_acc
        
        # 限制角度范围在-180到180之间
        self.roll = (self.roll + 180) % 360 - 180
        self.pitch = (self.pitch + 180) % 360 - 180
        self.yaw = (self.yaw + 180) % 360 - 180


class IMUWidget(QWidget):
    """IMU可视化主窗口"""
    def __init__(self):
        super(IMUWidget, self).__init__()
        # 移除窗口标题和几何设置，适合作为嵌入控件
        # self.setWindowTitle("IMU姿态可视化")
        # self.setGeometry(100, 100, 800, 600)
        
        # 设置固定大小，适合放在右下角
        self.setFixedSize(400, 400)
        
        # 创建IMU可视化控件
        self.imu_visualizer = IMUVisualizer()
        self.accel_inputs = {}
        self.gyro_inputs = {}
        # 创建输入控件
        # self.create_input_controls()
        
        # 设置布局 - 简化布局，只显示IMU可视化控件
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.imu_visualizer)
        main_layout.setContentsMargins(0, 0, 0, 0)  # 移除边距
        
        self.setLayout(main_layout)
        
        # 启动定时器更新姿态
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_imu)
        self.update_timer.start(16)  # 60Hz更新，提高动画流畅度

    def create_input_controls(self):
        """创建加速度和角速度输入控件"""
        # 加速度输入组
        self.accel_group = QWidget()
        accel_layout = QVBoxLayout(self.accel_group)
        accel_label = QLabel("加速度 (m/s²)")
        accel_label.setFont(QFont("Arial", 12, QFont.Bold))
        accel_layout.addWidget(accel_label)
        
        
        for axis in ['X', 'Y', 'Z']:
            hbox = QHBoxLayout()
            lbl = QLabel(f"加速度 {axis}:")
            spin = QDoubleSpinBox()
            spin.setRange(-20, 20)
            spin.setDecimals(2)
            spin.setSingleStep(0.1)
            if axis == 'Z':
                spin.setValue(9.81)  # 初始设置为重力加速度
            self.accel_inputs[axis] = spin
            hbox.addWidget(lbl)
            hbox.addWidget(spin)
            accel_layout.addLayout(hbox)
        
        # 角速度输入组
        self.gyro_group = QWidget()
        gyro_layout = QVBoxLayout(self.gyro_group)
        gyro_label = QLabel("角速度 (°/s)")
        gyro_label.setFont(QFont("Arial", 12, QFont.Bold))
        gyro_layout.addWidget(gyro_label)
        
        self.gyro_inputs = {}
        for axis in ['X', 'Y', 'Z']:
            hbox = QHBoxLayout()
            lbl = QLabel(f"角速度 {axis}:")
            spin = QDoubleSpinBox()
            spin.setRange(-180, 180)
            spin.setDecimals(2)
            spin.setSingleStep(1)
            self.gyro_inputs[axis] = spin
            hbox.addWidget(lbl)
            hbox.addWidget(spin)
            gyro_layout.addLayout(hbox)


    def update_imu_data(self,data:dict):
        """更新IMU数据"""
        self.imu_visualizer.update_orientation_from_sensors(data['accel'], data['gyro'])

    def update_imu(self):
        """更新IMU姿态"""
        # 获取输入的加速度和角速度值
        accel = [
            self.accel_inputs.get('X',0),
            self.accel_inputs.get('Y',0),
            self.accel_inputs.get('Z',0)
        ]
        
        gyro = [
            self.gyro_inputs.get('X',0),
            self.gyro_inputs.get('Y',0),
            self.gyro_inputs.get('Z',0)
        ]
        
        # 更新IMU姿态
        self.imu_visualizer.update_orientation_from_sensors(accel, gyro)


if __name__ == "__main__":
    # 确保中文显示正常
    import matplotlib
    matplotlib.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
    
    app = QApplication(sys.argv)
    window = IMUWidget()
    window.show()
    sys.exit(app.exec_())
