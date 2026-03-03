"""
P2P UDP 打洞模块

基于 STUN + 信令服务器 + 对称 NAT 打洞策略，获取可与对端直连的 UDP socket。
消费者（如 pkg/quic.py）使用打洞得到的 (socket, peer_addr) 建立 QUIC 连接。

调用关系:
  index.py / MainWindow
       |
       v
  HighwayQuicClient.start()
       |
       +-- [p2p 模式] --> P2PHolePuncher.run() --> (sock, peer_addr)
       |                         |
       |                         +--> 信令 join --> STUN --> 交换地址 --> 打洞
       |
       +-- [非 p2p]  --> connect(host, port)  # 原逻辑
       |
       v
  使用 (host, port) = peer_addr 建立 QUIC，并需将 sock 作为传输层

设计说明:
- aioquic.connect() 内部创建新 socket，无法直接复用打洞 socket。
- 集成时需使用 aioquic 低层 QuicConnection API，将 sock 作为 datagram 传输，
  或通过 local_port 等方案（需评估 NAT 映射保持性）。
"""

import json
import logging
import os
import select
import socket
import struct
import threading
import time
from typing import Callable

# ============================================================
# 配置（可从 Setting 注入）
# ============================================================
STUN_SERVERS = [
    ("stun2.api.andless.tech", 33478),
]

DEFAULT_SIGNALING_HOST = "signaling.api.andless.tech"
DEFAULT_SIGNALING_PORT = 30002

STUN_TIMEOUT = 3
PORT_SWEEP_RANGE = 32
NUM_PUNCH_SOCKETS = 64
RECV_BUFFER = 1024

# STUN 协议常量 (RFC 5389)
STUN_MAGIC_COOKIE = 0x2112A442
STUN_BINDING_REQUEST = 0x0001
STUN_BINDING_RESPONSE = 0x0101
STUN_ATTR_MAPPED_ADDRESS = 0x0001
STUN_ATTR_XOR_MAPPED_ADDRESS = 0x0020


# ---------------------------------------------------------------------------
# STUN 协议
# ---------------------------------------------------------------------------


def _build_stun_request() -> tuple[bytes, bytes]:
    """构造 STUN Binding Request。返回 (完整请求包, transaction_id)。"""
    msg_type = STUN_BINDING_REQUEST
    msg_length = 0
    magic_cookie = STUN_MAGIC_COOKIE
    transaction_id = os.urandom(12)
    header = struct.pack(">HHI", msg_type, msg_length, magic_cookie) + transaction_id
    return header, transaction_id


def _parse_stun_response(data: bytes, expected_txn_id: bytes) -> tuple[str, int] | None:
    """解析 STUN Binding Response，提取公网 IP 和端口。返回 (ip, port) 或 None。"""
    if len(data) < 20:
        return None
    msg_type, msg_length, _ = struct.unpack(">HHI", data[:8])
    txn_id = data[8:20]
    if msg_type != STUN_BINDING_RESPONSE or txn_id != expected_txn_id:
        return None
    offset = 20
    while offset < 20 + msg_length:
        if offset + 4 > len(data):
            break
        attr_type, attr_length = struct.unpack(">HH", data[offset : offset + 4])
        attr_value = data[offset + 4 : offset + 4 + attr_length]
        if attr_type == STUN_ATTR_XOR_MAPPED_ADDRESS and attr_length >= 8:
            family = attr_value[1]
            if family == 0x01:
                xor_port = struct.unpack(">H", attr_value[2:4])[0]
                xor_ip = struct.unpack(">I", attr_value[4:8])[0]
                port = xor_port ^ (STUN_MAGIC_COOKIE >> 16)
                ip_int = xor_ip ^ STUN_MAGIC_COOKIE
                return (socket.inet_ntoa(struct.pack(">I", ip_int)), port)
        elif attr_type == STUN_ATTR_MAPPED_ADDRESS and attr_length >= 8:
            family = attr_value[1]
            if family == 0x01:
                port = struct.unpack(">H", attr_value[2:4])[0]
                return (socket.inet_ntoa(attr_value[4:8]), port)
        offset += 4 + attr_length + (4 - attr_length % 4) % 4
    return None


def get_public_addr_via_stun(
    sock: socket.socket,
    stop_event: threading.Event | None = None,
) -> tuple[str, int] | None:
    """通过 STUN 服务器获取公网 IP 和端口。若 stop_event 被 set 则提前退出。"""
    sock.settimeout(STUN_TIMEOUT)
    for stun_host, stun_port in STUN_SERVERS:
        if stop_event and stop_event.is_set():
            return None
        try:
            request, txn_id = _build_stun_request()
            sock.sendto(request, (stun_host, stun_port))
            response, _ = sock.recvfrom(1024)
            result = _parse_stun_response(response, txn_id)
            if result:
                logging.info(f"STUN 成功: {result[0]}:{result[1]}")
                return result
        except socket.timeout:
            logging.debug(f"STUN 超时: {stun_host}:{stun_port}")
        except Exception as e:
            logging.warning(f"STUN 失败 {stun_host}:{stun_port}: {e}")
    return None


# ---------------------------------------------------------------------------
# 信令 + 打洞
# ---------------------------------------------------------------------------


def _generate_spiral_ports(center: int, radius: int) -> list[int]:
    """从中心端口向外螺旋生成端口列表，优先探测靠近 STUN 端口的。"""
    ports = [center]
    for d in range(1, radius + 1):
        if center + d <= 65535:
            ports.append(center + d)
        if center - d >= 1024:
            ports.append(center - d)
    return ports


def get_peer_via_signaling(
    udp_sock: socket.socket,
    room_id: str,
    signaling_host: str = DEFAULT_SIGNALING_HOST,
    signaling_port: int = DEFAULT_SIGNALING_PORT,
    on_log: Callable[[str], None] | None = None,
    stop_event: threading.Event | None = None,
) -> tuple[str, int] | None:
    """
    通过信令服务器获取对端地址。

    流程: join -> start_stun -> STUN -> stun_result -> peer_found
    若 stop_event 被 set 则提前退出，返回 None。
    """
    log = on_log or logging.info
    stop = stop_event

    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.settimeout(1.0)  # 短超时以便定期检查 stop_event

    try:
        tcp_sock.connect((signaling_host, signaling_port))
        log(f"已连接信令服务器 {signaling_host}:{signaling_port}")

        request = json.dumps({"action": "join", "room_id": room_id}) + "\n"
        tcp_sock.sendall(request.encode())
        log(f"已加入房间: {room_id}")

        buffer = ""
        while True:
            if stop and stop.is_set():
                log("信令已取消")
                return None
            try:
                data = tcp_sock.recv(1024).decode()
            except socket.timeout:
                continue
            if not data:
                log("信令服务器断开连接")
                return None
            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                action = msg.get("action")

                if action == "waiting":
                    log(msg.get("message", "等待对方加入..."))
                    continue

                if action == "start_stun":
                    log("开始 STUN 探测")
                    result = get_public_addr_via_stun(udp_sock, stop_event=stop)
                    if not result:
                        return None
                    ext_ip, ext_port = result
                    public_addr = f"{ext_ip}:{ext_port}"

                    result_msg = json.dumps({"action": "stun_result", "public_addr": public_addr}) + "\n"
                    tcp_sock.sendall(result_msg.encode())
                    log("已提交公网地址，等待对端...")
                    continue

                if action == "peer_found":
                    peer_addr_str = msg.get("peer_addr")
                    log(f"配对成功，对端地址: {peer_addr_str}")
                    tcp_sock.close()
                    ip, port = peer_addr_str.rsplit(":", 1)
                    return (ip, int(port))

                if action == "error":
                    log(f"信令错误: {msg.get('message')}")
                    break

    except socket.timeout:
        log("信令等待超时")
    except ConnectionRefusedError:
        log(f"无法连接信令服务器 {signaling_host}:{signaling_port}")
    except Exception as e:
        logging.exception(f"信令连接失败: {e}")
    finally:
        try:
            tcp_sock.close()
        except OSError:
            pass
    return None


def hole_punch(
    sock: socket.socket,
    peer_addr: tuple[str, int],
    stop_event: threading.Event | None = None,
    on_success: Callable[[socket.socket, tuple[str, int]], None] | None = None,
) -> tuple[socket.socket, tuple[str, int]] | None:
    """
    打洞主逻辑：端口扫描 + 生日攻击。

    发送消息格式为 "#对端ip:当前扫描端口#"，便于对方识别目标。
    成功时打印对端发来的消息（含连接 IP 和端口），并返回 (sock, peer_addr)。
    若 stop_event 被 set 则提前退出，返回 None。
    """
    peer_ip, peer_port = peer_addr
    stop = stop_event or threading.Event()
    success_event = threading.Event()
    conn_info: dict = {}  # sock, peer, recv_data

    # 生日攻击：多 socket
    extra_socks = []
    for _ in range(NUM_PUNCH_SOCKETS):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("", 0))
        extra_socks.append(s)
    all_socks = [sock] + extra_socks

    sweep_ports = _generate_spiral_ports(peer_port, PORT_SWEEP_RANGE)
    logging.info(f"打洞: {len(all_socks)} socket × {len(sweep_ports)} 端口 -> {peer_ip}:{peer_port}")

    def listener():
        while not stop.is_set():
            try:
                readable, _, _ = select.select(all_socks, [], [], 0.5)
            except (ValueError, OSError):
                if stop.is_set():
                    break
                time.sleep(0.1)
                continue
            for rs in readable:
                try:
                    data, addr = rs.recvfrom(RECV_BUFFER)
                    if not success_event.is_set():
                        conn_info["sock"] = rs
                        conn_info["peer"] = addr
                        conn_info["recv_data"] = data
                        peer_msg = data.decode("utf-8", errors="replace")
                        logging.info(f"打洞成功: 本地 {rs.getsockname()[1]} <-> {addr[0]}:{addr[1]}")
                        logging.info(f"对端消息(记录的连接IP和端口): {peer_msg}")
                        success_event.set()
                        if on_success:
                            on_success(rs, addr)
                except (OSError, ValueError):
                    continue

    listen_thread = threading.Thread(target=listener, daemon=True)
    listen_thread.start()

    try:
        while not success_event.is_set() and not stop.is_set():
            for port in sweep_ports:
                if success_event.is_set() or stop.is_set():
                    break
                msg = f"#{peer_ip}:{port}#".encode("utf-8")
                for s in all_socks:
                    try:
                        s.sendto(msg, (peer_ip, port))
                    except OSError:
                        pass
            time.sleep(0.1)

        if success_event.is_set() and conn_info:
            stop.set()
            time.sleep(0.2)
            conn_sock = conn_info["sock"]
            conn_peer = conn_info["peer"]
            for s in all_socks:
                if s is not conn_sock:
                    try:
                        s.close()
                    except OSError:
                        pass
            return (conn_sock, conn_peer)
    finally:
        stop.set()
        if not conn_info:
            for s in all_socks:
                try:
                    s.close()
                except OSError:
                    pass
    return None


# ---------------------------------------------------------------------------
# 对外接口：P2PHolePuncher
# ---------------------------------------------------------------------------


class P2PHolePuncher:
    """
    P2P 打洞封装类。

    使用方式:
        puncher = P2PHolePuncher(room_id="xxx", ...)
        result = puncher.run()  # 阻塞，返回 (sock, peer_addr) 或 None

    退出逻辑:
        调用 puncher.stop() 可中止正在进行的 run()（信令等待或打洞阶段）。
        若在另一线程运行 run()，主线程调用 stop() 即可触发退出。
    """

    def __init__(
        self,
        room_id: str = "default",
        signaling_host: str = DEFAULT_SIGNALING_HOST,
        signaling_port: int = DEFAULT_SIGNALING_PORT,
        local_bind_port: int = 0,
    ):
        self.room_id = room_id
        self.signaling_host = signaling_host
        self.signaling_port = signaling_port
        self.local_bind_port = local_bind_port
        self._stop_event = threading.Event()

    def stop(self) -> None:
        """请求中止打洞流程，run() 将在下一轮检查时退出。"""
        self._stop_event.set()

    def run(self) -> tuple[socket.socket, tuple[str, int]] | None:
        """
        执行完整流程：创建 UDP socket -> 信令配对 -> STUN -> 打洞。
        阻塞直到成功、失败或 stop() 被调用。成功返回 (sock, peer_addr)，否则返回 None。
        """
        self._stop_event.clear()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.bind(("", self.local_bind_port))
        except OSError as e:
            logging.error(f"UDP 绑定失败: {e}")
            return None

        if self._stop_event.is_set():
            sock.close()
            return None

        peer_addr = get_peer_via_signaling(
            sock,
            self.room_id,
            self.signaling_host,
            self.signaling_port,
            stop_event=self._stop_event,
        )
        if not peer_addr:
            sock.close()
            return None

        if self._stop_event.is_set():
            sock.close()
            return None

        result = hole_punch(sock, peer_addr, stop_event=self._stop_event)
        return result


def create_puncher_from_setting(setting) -> P2PHolePuncher:
    """
    从 Setting 对象创建 P2PHolePuncher。
    需要 setting 具备 room_id；signaling 暂用默认值，可后续扩展 setting 字段。
    """
    room_id = getattr(setting, "room_id", None) or "default"
    return P2PHolePuncher(room_id=room_id)
