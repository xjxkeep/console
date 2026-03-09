"""
P2P UDP 打洞模块

基于 STUN + 信令服务器 + 对称 NAT 打洞策略，获取可与对端直连的 UDP socket。
消费者（如 pkg/quic.py）使用打洞得到的 (socket, peer_addr) 建立 QUIC 连接。

匹配 Go highway/pkg/p2p/ 实现：
- SignalingClient: 方法级信令交互
- LAN 地址发现
- 二进制 punch 包格式 (0x07 marker)
- 优先级排序 (IPv6 优先)
- 超时、随机延迟、keepalive

调用关系:
  HighwayQuicClient.start()
       |
       +-- [p2p 模式] --> P2PHolePuncher.run() --> (sock, (ip, port))
       |                         |
       |                         +--> signaling join → STUN → build addr list
       |                              → send result → wait peer → parse addr list
       |                              → hole punch → leave
       +-- [非 p2p]  --> connect(host, port)
"""

import ipaddress
import json
import logging
import os
import random
import select
import socket
import struct
import threading
import time
from typing import Callable

# ============================================================
# 配置
# ============================================================
STUN_SERVERS = [
    ("stun2.api.andless.tech", 33478),
]

DEFAULT_SIGNALING_HOST = "signaling.api.andless.tech"
DEFAULT_SIGNALING_PORT = 30001

STUN_TIMEOUT = 1
PORT_SWEEP_RANGE = 32
NUM_PUNCH_SOCKETS = 64
RECV_BUFFER = 1500

# 打洞超时与延迟（匹配 Go）
PUNCH_TIMEOUT = 10               # 打洞总超时(秒)
PUNCH_INITIAL_DELAY_MAX_MS = 500  # 随机初始延迟上限(毫秒)
PUNCH_MICRO_DELAY_INTERVAL = 50   # 每隔多少包插入一次微延迟
PUNCH_MICRO_DELAY_MIN_MS = 1      # 微延迟下限(毫秒)
PUNCH_MICRO_DELAY_MAX_MS = 5      # 微延迟上限(毫秒)
PUNCH_ROUND_DELAY_MIN_MS = 10     # 轮间延迟下限(毫秒)
PUNCH_ROUND_DELAY_MAX_MS = 50     # 轮间延迟上限(毫秒)
PUNCH_KEEPALIVE_COUNT = 20        # 成功后发送的 keepalive 包数
PUNCH_KEEPALIVE_INTERVAL = 0.2    # keepalive 间隔(秒)

# 信令超时
SIGNALING_WAIT_START_STUN_TIMEOUT = 180  # 等待 start_stun 超时(秒)
SIGNALING_WAIT_PEER_TIMEOUT = 60         # 等待 peer_found 超时(秒)

# 打洞包标记 (匹配 Go PUNCH_MARKER = 0x07)
PUNCH_MARKER = 0x07

# QUIC socket 缓冲区 (匹配 Go prepareConnForQUIC: 7MB)
QUIC_SOCKET_BUF_SIZE = 7 * 1024 * 1024

# STUN 协议常量 (RFC 5389)
STUN_MAGIC_COOKIE = 0x2112A442
STUN_BINDING_REQUEST = 0x0001
STUN_BINDING_RESPONSE = 0x0101
STUN_ATTR_MAPPED_ADDRESS = 0x0001
STUN_ATTR_XOR_MAPPED_ADDRESS = 0x0020


# ---------------------------------------------------------------------------
# 双栈 socket 工具 (匹配 Go net.ListenUDP("udp", ...))
# ---------------------------------------------------------------------------


def _create_dual_stack_udp(bind_port: int = 0) -> socket.socket:
    """创建双栈 UDP socket (匹配 Go net.ListenUDP("udp", ...))。
    AF_INET6 + IPV6_V6ONLY=0 使一个 socket 同时支持 IPv4 和 IPv6。
    """
    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    sock.bind(("::", bind_port))
    return sock


def _to_v6_mapped(ip: str, port: int) -> tuple[str, int]:
    """将 IPv4 地址转换为 IPv4-mapped IPv6 格式，用于双栈 socket sendto。
    IPv6 地址原样返回。
    """
    try:
        addr_obj = ipaddress.ip_address(ip)
        if isinstance(addr_obj, ipaddress.IPv4Address):
            return (f"::ffff:{ip}", port)
    except ValueError:
        pass
    return (ip, port)


def _resolve_stun_target(host: str, port: int) -> tuple[str, int]:
    """解析 STUN 服务器地址，返回双栈 socket 可用的地址。"""
    try:
        ipaddress.ip_address(host)
        return _to_v6_mapped(host, port)
    except ValueError:
        pass
    # 主机名 → DNS 解析
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_DGRAM)
        for family, _, _, _, sockaddr in infos:
            if family == socket.AF_INET6:
                return (sockaddr[0], sockaddr[1])
            elif family == socket.AF_INET:
                return (f"::ffff:{sockaddr[0]}", sockaddr[1])
    except socket.gaierror:
        pass
    return (host, port)


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
            elif family == 0x02 and attr_length >= 20:
                # IPv6 XOR-MAPPED-ADDRESS
                xor_port = struct.unpack(">H", attr_value[2:4])[0]
                port = xor_port ^ (STUN_MAGIC_COOKIE >> 16)
                xor_ip = attr_value[4:20]
                xor_key = struct.pack(">I", STUN_MAGIC_COOKIE) + expected_txn_id
                ip_bytes = bytes(a ^ b for a, b in zip(xor_ip, xor_key))
                return (socket.inet_ntop(socket.AF_INET6, ip_bytes), port)
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
            target = _resolve_stun_target(stun_host, stun_port) if sock.family == socket.AF_INET6 else (stun_host, stun_port)
            sock.sendto(request, target)
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
# LAN 地址发现 (匹配 Go lan.go)
# ---------------------------------------------------------------------------


def is_private_ipv4(ip: str) -> bool:
    """检查 IPv4 地址是否为 RFC 1918 私有地址。"""
    try:
        addr = ipaddress.IPv4Address(ip)
        return addr.is_private and not addr.is_loopback
    except (ipaddress.AddressValueError, ValueError):
        return False


def get_local_addrs() -> list[tuple[str, int]]:
    """
    获取本机非回环 IP 地址列表。返回 [(ip, AF_family), ...]，IPv6 优先。

    不依赖 netifaces/psutil，使用 socket.getaddrinfo() 回退方案。
    """
    addrs: list[tuple[str, int]] = []
    seen: set[str] = set()

    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            family = info[0]
            ip = info[4][0]
            # 去除 IPv6 zone id (如 %eth0)
            if isinstance(ip, str) and "%" in ip:
                ip = ip.split("%")[0]
            if ip in seen:
                continue
            try:
                addr_obj = ipaddress.ip_address(ip)
                if addr_obj.is_loopback:
                    continue
                # 过滤 link-local IPv6 (匹配 Go: 只保留 GUA 和 ULA)
                if isinstance(addr_obj, ipaddress.IPv6Address) and addr_obj.is_link_local:
                    continue
                seen.add(ip)
                addrs.append((ip, family))
            except ValueError:
                continue
    except (socket.gaierror, OSError):
        pass

    # 也尝试通过连接外部获取地址 (不实际发包)
    for target, af in [("8.8.8.8", socket.AF_INET), ("2001:4860:4860::8888", socket.AF_INET6)]:
        try:
            s = socket.socket(af, socket.SOCK_DGRAM)
            s.settimeout(0)
            s.connect((target, 80))
            ip = s.getsockname()[0]
            s.close()
            if ip not in seen:
                try:
                    addr_obj = ipaddress.ip_address(ip)
                    if not addr_obj.is_loopback:
                        seen.add(ip)
                        addrs.append((ip, af))
                except ValueError:
                    pass
        except (OSError, socket.error):
            pass

    # IPv6 排前面
    addrs.sort(key=lambda x: (0 if x[1] == socket.AF_INET6 else 1))
    return addrs


def build_addr_list(public_addr: tuple[str, int] | None, local_addrs: list[tuple[str, int]], local_port: int) -> str:
    """
    构建逗号分隔的地址列表字符串 (匹配 Go buildAddrList)。

    格式: "ip:port,ip:port,..." IPv6 地址使用 "[ip]:port" 格式。
    公网地址放第一个，后面是各 LAN 地址。
    """
    parts: list[str] = []

    if public_addr:
        ip, port = public_addr
        parts.append(_format_addr(ip, port))

    for ip, family in local_addrs:
        if is_private_ipv4(ip) or family == socket.AF_INET6:
            parts.append(_format_addr(ip, local_port))

    return ",".join(parts)


def _format_addr(ip: str, port: int) -> str:
    """格式化地址，IPv6 使用 [ip]:port 格式。"""
    try:
        addr = ipaddress.ip_address(ip)
        if isinstance(addr, ipaddress.IPv6Address):
            return f"[{ip}]:{port}"
    except ValueError:
        pass
    return f"{ip}:{port}"


def parse_addr_list(addr_str: str) -> list[tuple[str, int]]:
    """
    解析逗号分隔的地址列表字符串 (匹配 Go parseAddrList)。

    支持 IPv4 "ip:port" 和 IPv6 "[ip]:port" 格式。
    返回 [(ip, port), ...]。
    """
    result: list[tuple[str, int]] = []
    if not addr_str:
        return result

    for part in addr_str.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if part.startswith("["):
                # IPv6: [ip]:port
                bracket_end = part.index("]")
                ip = part[1:bracket_end]
                port_str = part[bracket_end + 2:]  # skip ]:
                result.append((ip, int(port_str)))
            else:
                # IPv4: ip:port
                ip, port_str = part.rsplit(":", 1)
                result.append((ip, int(port_str)))
        except (ValueError, IndexError):
            logging.warning(f"无法解析地址: {part}")
            continue

    return result


# ---------------------------------------------------------------------------
# 打洞包格式 (匹配 Go holepunch.go)
# ---------------------------------------------------------------------------


def random_punch_payload() -> bytes:
    """生成打洞包: 第一字节为 PUNCH_MARKER(0x07) + 32-128 字节随机数据。"""
    payload_len = random.randint(32, 128)
    return bytes([PUNCH_MARKER]) + os.urandom(payload_len)


def is_punch_packet(data: bytes) -> bool:
    """检查数据是否为打洞包 (第一字节为 PUNCH_MARKER)。"""
    return len(data) > 0 and data[0] == PUNCH_MARKER


# ---------------------------------------------------------------------------
# SignalingClient (匹配 Go SignalingClient)
# ---------------------------------------------------------------------------


class SignalingClient:
    """
    信令客户端，方法级交互 (匹配 Go SignalingClient)。

    使用流程:
        sc = SignalingClient()
        sc.connect(host, port)
        sc.join_as_subscriber(room_id)
        sc.wait_for_start_stun(stop_event)
        sc.send_stun_result(addr_list_str)
        peer_addr_str = sc.wait_for_peer(stop_event)
        sc.leave()
        sc.close()
    """

    def __init__(self):
        self._sock: socket.socket | None = None
        self._buffer = ""

    def connect(self, host: str, port: int) -> None:
        """连接信令服务器。"""
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(10)
        self._sock.connect((host, port))
        logging.info(f"已连接信令服务器 {host}:{port}")

    def close(self) -> None:
        """关闭连接。"""
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def join_as_subscriber(self, room_id: str) -> None:
        """以 subscriber 角色加入房间，等待 joined 确认。"""
        self._send({"type": "join", "room_id": room_id, "role": "subscriber"})
        logging.info(f"已发送 join: room={room_id}, role=subscriber")

        # 等待 joined 确认
        msg = self._receive_filtered(timeout=10)
        if msg and msg.get("type") == "joined":
            logging.info(f"已加入房间: {msg.get('message', '')}")
        elif msg and msg.get("type") == "error":
            raise ConnectionError(f"信令错误: {msg.get('message')}")
        else:
            raise ConnectionError(f"加入房间失败，收到: {msg}")

    def wait_for_start_stun(self, stop_event: threading.Event | None = None) -> bool:
        """
        阻塞等待 start_stun 消息 (最多 180 秒)。
        返回 True 表示收到 start_stun，False 表示超时或取消。
        """
        deadline = time.monotonic() + SIGNALING_WAIT_START_STUN_TIMEOUT
        while True:
            if stop_event and stop_event.is_set():
                return False
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logging.warning("等待 start_stun 超时")
                return False
            msg = self._receive_filtered(timeout=min(remaining, 1.0))
            if msg is None:
                continue
            msg_type = msg.get("type")
            if msg_type == "start_stun":
                logging.info(f"收到 start_stun: {msg.get('message', '')}")
                return True
            if msg_type == "error":
                logging.error(f"信令错误: {msg.get('message')}")
                return False

    def send_stun_result(self, addr_list: str) -> None:
        """发送 STUN 结果 (逗号分隔的地址列表)。"""
        self._send({"type": "stun_result", "public_addr": addr_list})
        logging.info(f"已发送 stun_result: {addr_list}")

    def wait_for_peer(self, stop_event: threading.Event | None = None) -> str | None:
        """
        阻塞等待 peer_found 消息 (最多 60 秒)。
        返回对端地址字符串，或 None (超时/取消)。
        """
        deadline = time.monotonic() + SIGNALING_WAIT_PEER_TIMEOUT
        while True:
            if stop_event and stop_event.is_set():
                return None
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logging.warning("等待 peer_found 超时")
                return None
            msg = self._receive_filtered(timeout=min(remaining, 1.0))
            if msg is None:
                continue
            msg_type = msg.get("type")
            if msg_type == "peer_found":
                peer_addr = msg.get("peer_addr", "")
                logging.info(f"配对成功，对端地址: {peer_addr}")
                return peer_addr
            if msg_type == "error":
                logging.error(f"信令错误: {msg.get('message')}")
                return None

    def leave(self) -> None:
        """发送 leave 消息。"""
        try:
            self._send({"type": "leave"})
        except OSError:
            pass

    def _send(self, msg: dict) -> None:
        """发送 JSON 消息 (换行分隔)。"""
        if not self._sock:
            raise ConnectionError("信令未连接")
        data = json.dumps(msg) + "\n"
        self._sock.sendall(data.encode())

    def _receive(self, timeout: float = 1.0) -> dict | None:
        """
        接收一条 JSON 消息。
        返回解析后的 dict，或 None (超时/无数据)。
        """
        if not self._sock:
            return None

        # 先检查缓冲区中是否有完整消息
        if "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if line:
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    pass

        self._sock.settimeout(timeout)
        try:
            data = self._sock.recv(4096).decode()
        except socket.timeout:
            return None
        except OSError:
            return None

        if not data:
            raise ConnectionError("信令服务器断开连接")

        self._buffer += data
        if "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if line:
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    pass
        return None

    def _receive_filtered(self, timeout: float = 1.0) -> dict | None:
        """接收消息，自动跳过 pong。"""
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            msg = self._receive(timeout=min(remaining, timeout))
            if msg is None:
                return None
            if msg.get("type") == "pong":
                continue
            return msg


# ---------------------------------------------------------------------------
# 打洞策略 (匹配 Go holepunch.go)
# ---------------------------------------------------------------------------


def _generate_spiral_ports(center: int, radius: int) -> list[int]:
    """从中心端口向外螺旋生成端口列表。"""
    ports = [center]
    for d in range(1, radius + 1):
        if center + d <= 65535:
            ports.append(center + d)
        if center - d >= 1024:
            ports.append(center - d)
    return ports


def build_punch_targets(
    peer_addrs: list[tuple[str, int]],
    sweep_range: int = PORT_SWEEP_RANGE,
) -> list[tuple[str, int]]:
    """
    构建打洞目标列表 (匹配 Go buildPunchTargets)。

    规则:
    - 第一个地址: 螺旋端口扫描 (对称 NAT)
    - IPv6 地址: 只使用精确端口
    - LAN (私有 IPv4) 地址: 只使用精确端口
    - 其他公网 IPv4: 螺旋端口扫描
    """
    targets: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()

    for i, (ip, port) in enumerate(peer_addrs):
        is_ipv6 = ":" in ip and not ip.startswith("[")
        is_lan = is_private_ipv4(ip)

        if is_ipv6 or is_lan:
            # IPv6 和 LAN 地址：精确端口
            t = (ip, port)
            if t not in seen:
                seen.add(t)
                targets.append(t)
        elif i == 0:
            # 第一个公网地址：螺旋扫描
            for p in _generate_spiral_ports(port, sweep_range):
                t = (ip, p)
                if t not in seen:
                    seen.add(t)
                    targets.append(t)
        else:
            # 其他公网地址：也做螺旋扫描但范围可以小一些
            for p in _generate_spiral_ports(port, sweep_range):
                t = (ip, p)
                if t not in seen:
                    seen.add(t)
                    targets.append(t)

    return targets


def shuffle_targets_with_priority(targets: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """
    按优先级排序目标列表 (匹配 Go shuffleTargetsWithPriority)。
    IPv6 目标始终排在最前面。
    """
    ipv6_targets = []
    other_targets = []
    for t in targets:
        ip = t[0]
        if ":" in ip:
            ipv6_targets.append(t)
        else:
            other_targets.append(t)
    return ipv6_targets + other_targets


def hole_punch(
    sock: socket.socket,
    peer_addrs: list[tuple[str, int]],
    stop_event: threading.Event | None = None,
    on_success: Callable[[socket.socket, tuple[str, int]], None] | None = None,
) -> tuple[socket.socket, tuple[str, int]] | None:
    """
    打洞主逻辑 (匹配 Go holepunch.go)。

    改进:
    - 二进制打洞包 (0x07 marker + 随机 payload)
    - 30 秒超时
    - 随机初始延迟 0-500ms
    - 微延迟: 每 50-150 包插入 1-5ms 延迟
    - 轮间延迟: 10-50ms (随机)
    - 成功后 keepalive: 20 个 punch 包 @200ms 间隔
    """
    stop = stop_event or threading.Event()
    success_event = threading.Event()
    conn_info: dict = {}

    # 构建目标列表
    targets = build_punch_targets(peer_addrs)
    targets = shuffle_targets_with_priority(targets)

    if not targets:
        logging.error("打洞目标列表为空")
        return None

    # 生日攻击：多 socket (双栈，匹配 Go)
    extra_socks = []
    for _ in range(NUM_PUNCH_SOCKETS):
        try:
            s = _create_dual_stack_udp()
            extra_socks.append(s)
        except OSError:
            break
    all_socks = [sock] + extra_socks

    logging.info(
        f"打洞: {len(all_socks)} socket × {len(targets)} 目标, "
        f"超时 {PUNCH_TIMEOUT}s"
    )
    logging.info(f"targets: {targets}")

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
                    if is_punch_packet(data) and not success_event.is_set():
                        conn_info["sock"] = rs
                        conn_info["peer"] = addr
                        conn_info["recv_data"] = data
                        logging.info(
                            f"打洞成功: 本地 {rs.getsockname()[1]} <-> {addr[0]}:{addr[1]}"
                        )
                        success_event.set()
                        if on_success:
                            on_success(rs, addr)
                except (OSError, ValueError):
                    continue

    listen_thread = threading.Thread(target=listener, daemon=True)
    listen_thread.start()

    try:
        # 随机初始延迟 (匹配 Go)
        initial_delay = random.randint(0, PUNCH_INITIAL_DELAY_MAX_MS) / 1000.0
        time.sleep(initial_delay)

        deadline = time.monotonic() + PUNCH_TIMEOUT
        pkt_count = 0

        while not success_event.is_set() and not stop.is_set():
            if time.monotonic() >= deadline:
                logging.warning("打洞超时")
                break

            for target in targets:
                if success_event.is_set() or stop.is_set():
                    break
                payload = random_punch_payload()
                for s in all_socks:
                    try:
                        s.sendto(payload, _to_v6_mapped(*target))
                        pkt_count += 1
                    except OSError:
                        pass
                # 微延迟: 每 50-150 包
                if pkt_count % PUNCH_MICRO_DELAY_INTERVAL == 0:
                    time.sleep(
                        random.randint(PUNCH_MICRO_DELAY_MIN_MS, PUNCH_MICRO_DELAY_MAX_MS) / 1000.0
                    )

            # 轮间延迟
            if not success_event.is_set() and not stop.is_set():
                time.sleep(
                    random.randint(PUNCH_ROUND_DELAY_MIN_MS, PUNCH_ROUND_DELAY_MAX_MS) / 1000.0
                )

        if success_event.is_set() and conn_info:
            conn_sock = conn_info["sock"]
            conn_peer = conn_info["peer"]

            # Keepalive: 发送 20 个 punch 包 (匹配 Go)
            for _ in range(PUNCH_KEEPALIVE_COUNT):
                try:
                    conn_sock.sendto(random_punch_payload(), conn_peer)
                except OSError:
                    break
                time.sleep(PUNCH_KEEPALIVE_INTERVAL)

            stop.set()
            time.sleep(0.2)

            # 关闭多余 socket
            for s in all_socks:
                if s is not conn_sock:
                    try:
                        s.close()
                    except OSError:
                        pass
            return (conn_sock, (conn_peer[0], conn_peer[1]))
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
# 兼容旧接口: get_peer_via_signaling (供 p2p_client.py 等使用)
# ---------------------------------------------------------------------------


def get_peer_via_signaling(
    udp_sock: socket.socket,
    room_id: str,
    role: str = "subscriber",
    signaling_host: str = DEFAULT_SIGNALING_HOST,
    signaling_port: int = DEFAULT_SIGNALING_PORT,
    on_log: Callable[[str], None] | None = None,
    stop_event: threading.Event | None = None,
) -> tuple[str, int] | None:
    """
    兼容旧接口。内部使用 SignalingClient。
    返回 (ip, port) 或 None。
    """
    log = on_log or logging.info

    sc = SignalingClient()
    try:
        sc.connect(signaling_host, signaling_port)
        log(f"已连接信令服务器 {signaling_host}:{signaling_port}")

        sc.join_as_subscriber(room_id)
        log(f"已加入房间: {room_id} (角色: subscriber)")

        if not sc.wait_for_start_stun(stop_event):
            return None
        log("开始 STUN 探测")

        result = get_public_addr_via_stun(udp_sock, stop_event=stop_event)
        if not result:
            return None
        ext_ip, ext_port = result

        local_port = udp_sock.getsockname()[1]
        local_addrs = get_local_addrs()
        addr_list = build_addr_list((ext_ip, ext_port), local_addrs, local_port)

        sc.send_stun_result(addr_list)
        log("已提交地址列表，等待对端...")

        peer_addr_str = sc.wait_for_peer(stop_event)
        if not peer_addr_str:
            return None

        addrs = parse_addr_list(peer_addr_str)
        if addrs:
            return addrs[0]
        return None

    except ConnectionError as e:
        log(f"信令连接失败: {e}")
        return None
    except Exception as e:
        logging.exception(f"信令连接失败: {e}")
        return None
    finally:
        sc.leave()
        sc.close()


# ---------------------------------------------------------------------------
# 对外接口：P2PHolePuncher
# ---------------------------------------------------------------------------


def _prepare_conn_for_quic(sock: socket.socket) -> None:
    """设置 socket 缓冲区大小以适配 QUIC (匹配 Go prepareConnForQUIC)。"""
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, QUIC_SOCKET_BUF_SIZE)
    except OSError:
        pass
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, QUIC_SOCKET_BUF_SIZE)
    except OSError:
        pass


class P2PHolePuncher:
    """
    P2P 打洞封装类 (subscriber-only，匹配 Go RunSubscriberHolePunch)。

    使用方式:
        puncher = P2PHolePuncher(room_id="xxx", ...)
        result = puncher.run()  # 阻塞，返回 (sock, peer_addr) 或 None

    流程:
        signaling join → STUN → build addr list → send result
        → wait peer → parse addr list → hole punch → leave
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
        """请求中止打洞流程。"""
        self._stop_event.set()

    def run(self) -> tuple[socket.socket, tuple[str, int]] | None:
        """
        执行完整流程 (匹配 Go RunSubscriberHolePunch)。
        阻塞直到成功、失败或 stop() 被调用。
        成功返回 (sock, peer_addr)，否则返回 None。
        """
        self._stop_event.clear()

        try:
            sock = _create_dual_stack_udp(self.local_bind_port)
        except OSError as e:
            logging.error(f"UDP 绑定失败: {e}")
            return None

        local_port = sock.getsockname()[1]
        logging.info(f"UDP 已绑定端口: {local_port}")

        sc = SignalingClient()
        try:
            if self._stop_event.is_set():
                sock.close()
                return None

            # 1. 连接信令
            sc.connect(self.signaling_host, self.signaling_port)

            # 2. 加入房间
            sc.join_as_subscriber(self.room_id)

            # 3. 等待 start_stun
            if not sc.wait_for_start_stun(self._stop_event):
                sock.close()
                return None

            # 4. STUN 探测
            public_addr = get_public_addr_via_stun(sock, stop_event=self._stop_event)
            if not public_addr:
                logging.error("STUN 探测失败")
                sock.close()
                return None

            # 5. 构建地址列表
            local_addrs = get_local_addrs()
            addr_list = build_addr_list(public_addr, local_addrs, local_port)
            logging.info(f"地址列表: {addr_list}")

            # 6. 发送 stun_result
            sc.send_stun_result(addr_list)

            # 7. 等待对端地址
            peer_addr_str = sc.wait_for_peer(self._stop_event)
            if not peer_addr_str:
                sock.close()
                return None

            # 8. 解析对端地址列表
            peer_addrs = parse_addr_list(peer_addr_str)
            if not peer_addrs:
                logging.error(f"无法解析对端地址: {peer_addr_str}")
                sock.close()
                return None
            logging.info(f"对端地址列表: {peer_addrs}")

            # 9. 打洞
            result = hole_punch(sock, peer_addrs, stop_event=self._stop_event)
            if not result:
                sock.close()
                return None

            # 10. 设置 QUIC 缓冲区
            _prepare_conn_for_quic(result[0])

            return result

        except ConnectionError as e:
            logging.error(f"P2P 失败: {e}")
            sock.close()
            return None
        except Exception as e:
            logging.exception(f"P2P 失败: {e}")
            sock.close()
            return None
        finally:
            # 11. 离开房间
            sc.leave()
            sc.close()


def create_puncher_from_setting(setting) -> P2PHolePuncher:
    """
    从 Setting 对象创建 P2PHolePuncher。
    需要 setting 具备 room_id；signaling 暂用默认值，可后续扩展 setting 字段。
    """
    room_id = getattr(setting, "room_id", None) or "default"
    return P2PHolePuncher(room_id=room_id)
