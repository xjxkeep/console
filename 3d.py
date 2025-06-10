import sys
import numpy as np
from PyQt5.QtWidgets import QApplication, QMainWindow, QOpenGLWidget
from PyQt5.QtCore import Qt
from OpenGL.GL import *
from OpenGL.GLU import *
from stl import mesh

class GLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super(GLWidget, self).__init__(parent)
        self.angle_x = 0.0
        self.angle_y = 0.0
        self.angle_z = 0.0
        self.mesh_data = None

    def initializeGL(self):
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)

    def resizeGL(self, width, height):
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, width / height, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluLookAt(0, 0, 5, 0, 0, 0, 0, 1, 0)

        glRotatef(self.angle_x, 1, 0, 0)
        glRotatef(self.angle_y, 0, 1, 0)
        glRotatef(self.angle_z, 0, 0, 1)

        if self.mesh_data:
            self.draw_mesh()
        self.update()

    def draw_mesh(self):
        glBegin(GL_TRIANGLES)
        for face in self.mesh_data.vectors:
            for vertex in face:
                glVertex3fv(vertex)
        glEnd()

    def load_stl(self, filename):
        self.mesh_data = mesh.Mesh.from_file(filename)
        self.update()

    def update_angles(self, angle_x, angle_y, angle_z):
        self.angle_x = angle_x
        self.angle_y = angle_y
        self.angle_z = angle_z
        self.update()

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("陀螺仪上位机")
        self.resize(800, 600)
        self.gl_widget = GLWidget(self)
        self.setCentralWidget(self.gl_widget)

        # 加载 STL 模型
        self.gl_widget.load_stl("example.stl")  # 替换为你的 STL 文件路径

        # 模拟陀螺仪数据更新
        # self.timer = self.startTimer(100)  # 每100ms更新一次

    def timerEvent(self, event):
        # 模拟角度变化
        import random
        angle_x = random.uniform(-90, 90)
        angle_y = random.uniform(-90, 90)
        angle_z = random.uniform(-90, 90)
        self.gl_widget.update_angles(angle_x, angle_y, angle_z)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())