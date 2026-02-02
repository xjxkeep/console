"""
JoyStick 多进程实现

通过多进程架构解决 pygame 必须在主线程运行的问题。
JoyStickWorker 在子进程主线程运行 pygame，
JoyStickProxy 在主进程中提供与原 JoyStick 相同的接口。
"""

import importlib
import logging
import time
import multiprocessing
from multiprocessing import Process, Queue
from queue import Empty
from typing import List, Dict, Any, Optional

from PyQt5.QtCore import QObject, QTimer, pyqtSignal


class JoyStickWorker:
    """
    JoyStick 子进程 Worker

    在子进程主线程中运行 pygame，读取手柄数据，
    通过回调队列将数据发送到主进程。
    """

    def __init__(self, callback_queue: Queue, command_queue: Queue, result_queue: Queue):
        self.callback_queue = callback_queue
        self.command_queue = command_queue
        self.result_queue = result_queue
        self.running = True
        self.joystick = None
        self.device_id = None
        self._pygame_initialized = False
        self._pygame = None
        self._update_interval = 0.05  # 50ms

    def _emit_callback(self, signal_name: str, *args):
        """发送回调消息到主进程"""
        try:
            self.callback_queue.put_nowait((signal_name, args))
        except Exception as e:
            print(f"Error emitting callback: {e}")

    def _lazy_init(self):
        """延迟初始化 pygame"""
        if self._pygame_initialized:
            return

        self._pygame = importlib.import_module('pygame')
        self._pygame.init()
        self._pygame.joystick.init()
        self._pygame_initialized = True
        print("pygame initialized in worker process")

    def get_device_list(self) -> List[Dict[str, Any]]:
        """获取所有已连接的手柄设备列表"""
        devices = []
        try:
            self._lazy_init()

            # 重新初始化 joystick 子系统以检测新设备
            self._pygame.joystick.quit()
            self._pygame.joystick.init()

            for i in range(self._pygame.joystick.get_count()):
                try:
                    joy = self._pygame.joystick.Joystick(i)
                    devices.append({
                        'id': i,
                        'name': joy.get_name()
                    })
                except Exception as e:
                    print(f"Error accessing joystick {i}: {e}")
        except Exception as e:
            print(f"Error getting device list: {e}")
        return devices

    def select_device(self, device_id: int) -> bool:
        """选择手柄设备"""
        if self.device_id == device_id:
            return True

        try:
            # 先关闭当前手柄
            if self.joystick:
                try:
                    self.joystick.quit()
                except Exception as e:
                    print(f"Error quitting joystick: {e}")
                self.joystick = None

            self._lazy_init()

            if device_id >= self._pygame.joystick.get_count():
                print(f"Device ID {device_id} out of range")
                return False

            self.joystick = self._pygame.joystick.Joystick(device_id)
            self.joystick.init()
            self.device_id = device_id
            print(f"Selected joystick device {device_id}: {self.joystick.get_name()}")
            return True

        except Exception as e:
            print(f"Error selecting device: {e}")
            return False

    def _update(self):
        """读取手柄数据并发送到主进程"""
        if not self.joystick or self.device_id is None:
            return

        try:
            self._pygame.event.pump()  # 更新事件状态

            values = []
            # 获取所有轴的值
            for axis in range(self.joystick.get_numaxes()):
                value = self.joystick.get_axis(axis)
                current_value = int(value * 50) + 50
                values.append(current_value)

            # 获取按钮状态
            for button in range(self.joystick.get_numbuttons()):
                value = self.joystick.get_button(button)
                values.append(value * 100)

            # 发送数据到主进程
            self._emit_callback('signal', values)

        except Exception as e:
            print(f"Error in joystick update: {e}")
            self._handle_joystick_error()

    def _handle_joystick_error(self):
        """处理手柄错误，尝试重新连接"""
        try:
            if self.joystick:
                try:
                    self.joystick.quit()
                except:
                    pass
                self.joystick = None

            # 尝试重新选择设备
            if self.device_id is not None:
                self.select_device(self.device_id)
        except Exception as e:
            print(f"Error handling joystick error: {e}")

    def _process_commands(self):
        """处理来自主进程的命令"""
        try:
            while not self.command_queue.empty():
                cmd = self.command_queue.get_nowait()
                if cmd is None:
                    continue

                req_id, method_name, args, kwargs = cmd

                if method_name == '_shutdown':
                    self.running = False
                    self.result_queue.put((req_id, True, None))
                    return

                # 调用对应的方法
                if hasattr(self, method_name):
                    try:
                        method = getattr(self, method_name)
                        result = method(*args, **kwargs)
                        self.result_queue.put((req_id, result, None))
                    except Exception as e:
                        print(f"Error executing {method_name}: {e}")
                        self.result_queue.put((req_id, None, str(e)))
                else:
                    print(f"Unknown method: {method_name}")
                    self.result_queue.put((req_id, None, f"Unknown method: {method_name}"))
        except Empty:
            pass
        except Exception as e:
            print(f"Error processing commands: {e}")

    def run(self):
        """子进程主循环"""
        print("JoyStickWorker started")

        while self.running:
            # 处理来自主进程的命令
            self._process_commands()

            if not self.running:
                break

            # 更新手柄数据
            self._update()

            # 控制更新频率
            time.sleep(self._update_interval)

        # 清理资源
        self._cleanup()
        print("JoyStickWorker stopped")

    def _cleanup(self):
        """清理 pygame 资源"""
        try:
            if self.joystick:
                try:
                    self.joystick.quit()
                except:
                    pass
                self.joystick = None

            if self._pygame_initialized and self._pygame:
                try:
                    self._pygame.quit()
                except:
                    pass
                self._pygame_initialized = False

            print("pygame cleaned up")
        except Exception as e:
            print(f"Error cleaning up pygame: {e}")


def _worker_main(callback_queue: Queue, command_queue: Queue, result_queue: Queue):
    """子进程入口函数（模块级函数，可被 pickle）"""
    try:
        worker = JoyStickWorker(callback_queue, command_queue, result_queue)
        worker.run()
    except Exception as e:
        print(f"Worker error: {e}")
        import traceback
        traceback.print_exc()


class JoyStickProxy(QObject):
    """
    JoyStick 主进程代理

    提供与原 JoyStick 类相同的接口，
    实际操作代理到子进程中的 JoyStickWorker。
    """

    # 与原 JoyStick 类相同的信号
    signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.running = True
        self._process: Optional[Process] = None
        self._callback_queue: Optional[Queue] = None
        self._command_queue: Optional[Queue] = None
        self._result_queue: Optional[Queue] = None
        self._poll_timer: Optional[QTimer] = None
        self._started = False
        self._request_id = 0

        # 自动启动
        self._start()

    def _start(self) -> bool:
        """启动子进程"""
        if self._started:
            return True

        try:
            # 创建队列
            self._callback_queue = multiprocessing.Queue()
            self._command_queue = multiprocessing.Queue()
            self._result_queue = multiprocessing.Queue()

            # 创建并启动子进程（使用模块级函数作为 target）
            self._process = Process(
                target=_worker_main,
                args=(self._callback_queue, self._command_queue, self._result_queue),
                daemon=True
            )
            self._process.start()

            # 等待子进程启动
            time.sleep(0.1)

            # 启动轮询定时器
            self._poll_timer = QTimer()
            self._poll_timer.timeout.connect(self._poll_callbacks)
            self._poll_timer.start(20)

            self._started = True
            logging.info("JoyStickProxy started")
            return True

        except Exception as e:
            logging.error(f"Failed to start JoyStickProxy: {e}")
            self._cleanup()
            return False

    def _cleanup(self):
        """清理资源"""
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None

        self._process = None
        self._callback_queue = None
        self._command_queue = None
        self._result_queue = None
        self._started = False

    def _poll_callbacks(self):
        """轮询回调队列，分发信号"""
        if not self._callback_queue:
            return

        for _ in range(10):
            try:
                signal_name, args = self._callback_queue.get_nowait()
                if signal_name == 'signal' and args:
                    self.signal.emit(args[0])
            except Empty:
                break
            except Exception as e:
                logging.error(f"Error polling callbacks: {e}")

    def _call_remote(self, method_name: str, *args, timeout: float = 5.0, **kwargs) -> Any:
        """调用子进程中的方法"""
        if not self._started or not self._command_queue or not self._result_queue:
            logging.warning("JoyStickProxy not started")
            return None

        try:
            self._request_id += 1
            req_id = self._request_id

            # 发送命令 (req_id, method_name, args, kwargs)
            self._command_queue.put((req_id, method_name, args, kwargs))

            # 直接轮询结果队列
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    result_req_id, result, error = self._result_queue.get(timeout=0.1)
                    if result_req_id == req_id:
                        if error:
                            logging.error(f"Remote method {method_name} error: {error}")
                            return None
                        return result
                except Empty:
                    continue

            logging.warning(f"Timeout waiting for {method_name} result")
            return None

        except Exception as e:
            logging.error(f"Error calling remote method {method_name}: {e}")
            return None

    def get_device_list(self) -> List[Dict[str, Any]]:
        """获取所有已连接的手柄设备列表"""
        result = self._call_remote('get_device_list', timeout=5.0)
        return result if result is not None else []

    def select_device(self, device_id: int) -> bool:
        """选择手柄设备"""
        result = self._call_remote('select_device', device_id, timeout=5.0)
        return result if result is not None else False

    def close(self):
        """关闭手柄组件"""
        logging.info("Closing JoyStickProxy...")
        self.running = False

        # 发送关闭命令
        try:
            if self._command_queue:
                self._request_id += 1
                self._command_queue.put((self._request_id, '_shutdown', (), {}))
        except:
            pass

        # 等待进程结束
        if self._process and self._process.is_alive():
            self._process.join(timeout=2.0)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join(timeout=1.0)

        self._cleanup()
        logging.info("JoyStickProxy closed")


def create_joystick() -> JoyStickProxy:
    """
    工厂函数：创建 JoyStick 实例

    返回 JoyStickProxy，提供与原 JoyStick 相同的接口。
    """
    return JoyStickProxy()
