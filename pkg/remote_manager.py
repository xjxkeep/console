"""
多进程远程调用框架

解决 pygame 和 PyQt5 都需要在主线程运行的冲突问题。
通过多进程架构，将 pygame 放在子进程主线程运行，
PyQt5 GUI 在主进程主线程运行。
"""

import logging
import multiprocessing
import time
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from multiprocessing import Process, Queue
from queue import Empty
from typing import Any, Dict, Optional

from PyQt5.QtCore import QObject, QTimer


@dataclass
class CallbackMessage:
    """跨进程回调消息"""
    signal_name: str
    args: tuple
    kwargs: dict

    def __init__(self, signal_name: str, *args, **kwargs):
        self.signal_name = signal_name
        self.args = args
        self.kwargs = kwargs


@dataclass
class CommandMessage:
    """命令消息"""
    request_id: int
    method: str
    args: tuple
    kwargs: dict


@dataclass
class ResultMessage:
    """结果消息"""
    request_id: int
    result: Any
    error: Optional[str] = None


class RemoteWorkerBase(ABC):
    """
    子进程工作类基类

    在子进程的主线程中运行，处理需要主线程的库（如 pygame）。
    通过回调队列将数据推送到主进程。
    """

    def __init__(self, callback_queue: Queue, command_queue: Queue, result_queue: Queue):
        """
        初始化 Worker

        Args:
            callback_queue: 用于向主进程发送回调的队列
            command_queue: 用于接收主进程命令的队列
            result_queue: 用于向主进程发送方法调用结果的队列
        """
        self.callback_queue = callback_queue
        self.command_queue = command_queue
        self.result_queue = result_queue
        self.running = True

    def _emit_callback(self, signal_name: str, *args, **kwargs):
        """
        发送回调消息到主进程

        Args:
            signal_name: 信号名称
            *args: 位置参数
            **kwargs: 关键字参数
        """
        try:
            msg = CallbackMessage(signal_name, *args, **kwargs)
            self.callback_queue.put_nowait(msg)
        except Exception as e:
            logging.error(f"Error emitting callback: {e}")

    def _process_commands(self):
        """处理来自主进程的命令"""
        try:
            while not self.command_queue.empty():
                cmd: CommandMessage = self.command_queue.get_nowait()
                if cmd is None:
                    continue

                if cmd.method == '_shutdown':
                    self.running = False
                    self.result_queue.put(ResultMessage(cmd.request_id, True))
                    return

                # 调用对应的方法
                if hasattr(self, cmd.method):
                    try:
                        method = getattr(self, cmd.method)
                        result = method(*cmd.args, **cmd.kwargs)
                        self.result_queue.put(ResultMessage(cmd.request_id, result))
                    except Exception as e:
                        logging.error(f"Error executing {cmd.method}: {e}")
                        self.result_queue.put(ResultMessage(cmd.request_id, None, str(e)))
                else:
                    logging.warning(f"Unknown method: {cmd.method}")
                    self.result_queue.put(ResultMessage(cmd.request_id, None, f"Unknown method: {cmd.method}"))
        except Empty:
            pass
        except Exception as e:
            logging.error(f"Error processing commands: {e}")

    @abstractmethod
    def run(self):
        """
        子进程主循环

        子类必须实现此方法，在其中:
        1. 初始化需要主线程的库
        2. 运行主循环，定期调用 _process_commands()
        3. 在循环中执行实际工作
        """
        pass

    def shutdown(self):
        """关闭 Worker"""
        self.running = False


class RemoteProxyBase(QObject):
    """
    主进程代理类基类

    在主进程中运行，代理对子进程 Worker 的方法调用，
    并将子进程的回调转换为 Qt 信号。
    """

    def __init__(self, worker_class: type, poll_interval: int = 20):
        """
        初始化代理

        Args:
            worker_class: Worker 类（必须继承 RemoteWorkerBase）
            poll_interval: 轮询回调队列的间隔（毫秒）
        """
        super().__init__()
        self.worker_class = worker_class
        self.poll_interval = poll_interval

        self._process: Optional[Process] = None
        self._callback_queue: Optional[Queue] = None
        self._command_queue: Optional[Queue] = None
        self._result_queue: Optional[Queue] = None
        self._poll_timer: Optional[QTimer] = None
        self._started = False

        # 请求ID计数器和待处理结果
        self._request_id = 0
        self._request_id_lock = threading.Lock()
        self._pending_results: Dict[int, Any] = {}
        self._pending_events: Dict[int, threading.Event] = {}

    def start(self) -> bool:
        """
        启动子进程

        Returns:
            是否成功启动
        """
        if self._started:
            logging.warning("RemoteProxy already started")
            return True

        try:
            # 创建队列
            self._callback_queue = multiprocessing.Queue()
            self._command_queue = multiprocessing.Queue()
            self._result_queue = multiprocessing.Queue()

            # 创建并启动子进程
            self._process = Process(
                target=self._worker_entry,
                args=(self.worker_class, self._callback_queue, self._command_queue, self._result_queue),
                daemon=True
            )
            self._process.start()

            # 启动轮询定时器
            self._poll_timer = QTimer()
            self._poll_timer.timeout.connect(self._poll_all)
            self._poll_timer.start(self.poll_interval)

            self._started = True
            logging.info(f"RemoteProxy started with worker {self.worker_class.__name__}")
            return True

        except Exception as e:
            logging.error(f"Failed to start RemoteProxy: {e}")
            self._cleanup()
            return False

    @staticmethod
    def _worker_entry(worker_class: type, callback_queue: Queue, command_queue: Queue, result_queue: Queue):
        """子进程入口点"""
        try:
            worker = worker_class(callback_queue, command_queue, result_queue)
            worker.run()
        except Exception as e:
            logging.error(f"Worker error: {e}")

    def stop(self):
        """停止子进程"""
        if not self._started:
            return

        logging.info("Stopping RemoteProxy...")

        # 发送关闭命令
        try:
            if self._command_queue:
                with self._request_id_lock:
                    self._request_id += 1
                    req_id = self._request_id
                cmd = CommandMessage(req_id, '_shutdown', (), {})
                self._command_queue.put(cmd)
        except Exception as e:
            logging.error(f"Error sending shutdown command: {e}")

        # 等待进程结束
        if self._process and self._process.is_alive():
            self._process.join(timeout=2.0)
            if self._process.is_alive():
                logging.warning("Worker process did not exit gracefully, terminating...")
                self._process.terminate()
                self._process.join(timeout=1.0)

        self._cleanup()
        logging.info("RemoteProxy stopped")

    def _cleanup(self):
        """清理资源"""
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer = None

        # 唤醒所有等待中的请求
        for event in self._pending_events.values():
            event.set()
        self._pending_events.clear()
        self._pending_results.clear()

        self._process = None
        self._callback_queue = None
        self._command_queue = None
        self._result_queue = None
        self._started = False

    def _poll_all(self):
        """轮询所有队列"""
        self._poll_callbacks()
        self._poll_results()

    def _poll_callbacks(self):
        """轮询回调队列，分发信号"""
        if not self._callback_queue:
            return

        # 每次最多处理 10 条消息，避免阻塞 GUI
        for _ in range(10):
            try:
                msg: CallbackMessage = self._callback_queue.get_nowait()
                self._dispatch_callback(msg)
            except Empty:
                break
            except Exception as e:
                logging.error(f"Error polling callbacks: {e}")

    def _poll_results(self):
        """轮询结果队列"""
        if not self._result_queue:
            return

        for _ in range(10):
            try:
                result: ResultMessage = self._result_queue.get_nowait()
                req_id = result.request_id
                if req_id in self._pending_events:
                    self._pending_results[req_id] = result.result
                    self._pending_events[req_id].set()
            except Empty:
                break
            except Exception as e:
                logging.error(f"Error polling results: {e}")

    def _dispatch_callback(self, msg: CallbackMessage):
        """
        分发回调消息到对应的信号

        子类应该重写此方法来处理特定的信号。

        Args:
            msg: 回调消息
        """
        signal = getattr(self, msg.signal_name, None)
        if signal is not None and hasattr(signal, 'emit'):
            try:
                signal.emit(*msg.args)
            except Exception as e:
                logging.error(f"Error emitting signal {msg.signal_name}: {e}")
        else:
            logging.warning(f"Unknown signal: {msg.signal_name}")

    def _call_remote(self, method_name: str, *args, timeout: float = 5.0, **kwargs) -> Any:
        """
        调用子进程中的方法

        Args:
            method_name: 方法名
            *args: 位置参数
            timeout: 超时时间（秒）
            **kwargs: 关键字参数

        Returns:
            方法返回值，超时或出错返回 None
        """
        if not self._started or not self._command_queue or not self._result_queue:
            logging.warning("RemoteProxy not started")
            return None

        try:
            # 生成请求 ID
            with self._request_id_lock:
                self._request_id += 1
                req_id = self._request_id

            # 发送命令
            cmd = CommandMessage(req_id, method_name, args, kwargs)
            self._command_queue.put(cmd)

            # 直接轮询结果队列（避免依赖 QTimer 导致的死锁）
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    result: ResultMessage = self._result_queue.get(timeout=0.1)
                    if result.request_id == req_id:
                        return result.result
                    else:
                        # 存储其他请求的结果
                        self._pending_results[result.request_id] = result.result
                        if result.request_id in self._pending_events:
                            self._pending_events[result.request_id].set()
                except Empty:
                    continue

            logging.warning(f"Timeout waiting for {method_name} result")
            return None

        except Exception as e:
            logging.error(f"Error calling remote method {method_name}: {e}")
            return None

    def is_alive(self) -> bool:
        """检查子进程是否存活"""
        return self._process is not None and self._process.is_alive()
