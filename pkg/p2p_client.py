import socket
import struct
import os
import threading
import time
import json
import select

# ============================================================
# 配置区
# ============================================================
STUN_SERVERS = [
    ("stun.l.google.com", 19302),
]

# 信令服务器地址（改成你的公网服务器IP和端口）
SIGNALING_HOST = "signaling.api.andless.tech"
SIGNALING_PORT = 30002

LOCAL_BIND_PORT = 0  # 0=随机端口，可改为固定值如 8888
MESSAGE = b"Hello World! (UDP Hole Punch Test from Xjx's PC)"
RECV_BUFFER = 1024
STUN_TIMEOUT = 3  # STUN超时秒数

# ============================================================
# 对称NAT打洞策略配置
# ============================================================
PORT_SWEEP_RANGE = 32        # 端口扫描半径: peer_port ± 32 (小范围避免触发扫描检测)
NUM_PUNCH_SOCKETS = 64       # 额外socket数量(生日攻击，多socket更安全不易被限制)

# ============================================================
# STUN协议常量（RFC 5389）
# ============================================================
STUN_MAGIC_COOKIE = 0x2112A442
STUN_BINDING_REQUEST = 0x0001
STUN_BINDING_RESPONSE = 0x0101
STUN_ATTR_MAPPED_ADDRESS = 0x0001
STUN_ATTR_XOR_MAPPED_ADDRESS = 0x0020

def build_stun_request() -> tuple[bytes, bytes]:
    """
    构造STUN Binding Request
    返回：(完整请求包, 12字节transaction_id)
    """
    msg_type = STUN_BINDING_REQUEST
    msg_length = 0  # 无属性
    magic_cookie = STUN_MAGIC_COOKIE
    transaction_id = os.urandom(12)  # 96位随机ID

    header = struct.pack(
        ">HHI",       # 大端：2+2+4 字节
        msg_type,
        msg_length,
        magic_cookie
    ) + transaction_id

    return header, transaction_id

def parse_stun_response(data: bytes, expected_txn_id: bytes) -> tuple[str, int] | None:
    """
    解析STUN Binding Response，提取公网IP和端口
    返回：(ip, port) 或 None
    """
    if len(data) < 20:
        return None

    msg_type, msg_length, magic_cookie = struct.unpack(">HHI", data[:8])
    txn_id = data[8:20]

    # 验证响应
    if msg_type != STUN_BINDING_RESPONSE:
        return None
    if txn_id != expected_txn_id:
        return None

    # 解析属性
    offset = 20
    while offset < 20 + msg_length:
        if offset + 4 > len(data):
            break
        attr_type, attr_length = struct.unpack(">HH", data[offset:offset+4])
        attr_value = data[offset+4:offset+4+attr_length]

        # XOR-MAPPED-ADDRESS (优先) 或 MAPPED-ADDRESS
        if attr_type == STUN_ATTR_XOR_MAPPED_ADDRESS and attr_length >= 8:
            family = attr_value[1]
            if family == 0x01:  # IPv4
                xor_port = struct.unpack(">H", attr_value[2:4])[0]
                xor_ip = struct.unpack(">I", attr_value[4:8])[0]
                port = xor_port ^ (STUN_MAGIC_COOKIE >> 16)
                ip_int = xor_ip ^ STUN_MAGIC_COOKIE
                ip = socket.inet_ntoa(struct.pack(">I", ip_int))
                return (ip, port)

        elif attr_type == STUN_ATTR_MAPPED_ADDRESS and attr_length >= 8:
            family = attr_value[1]
            if family == 0x01:  # IPv4
                port = struct.unpack(">H", attr_value[2:4])[0]
                ip = socket.inet_ntoa(attr_value[4:8])
                return (ip, port)

        # 4字节对齐
        offset += 4 + attr_length + (4 - attr_length % 4) % 4

    return None

def get_public_addr_via_stun(sock: socket.socket) -> tuple[str, int] | None:
    """
    通过STUN服务器获取公网IP和端口
    """
    sock.settimeout(STUN_TIMEOUT)

    for stun_host, stun_port in STUN_SERVERS:
        print(f"\n尝试连接STUN服务器: {stun_host}:{stun_port}")
        try:
            request, txn_id = build_stun_request()
            sock.sendto(request, (stun_host, stun_port))

            response, _ = sock.recvfrom(1024)
            result = parse_stun_response(response, txn_id)

            if result:
                print(f"[OK] STUN探测成功!")
                print(f"[*] 你的公网地址: {result[0]}:{result[1]}")
                return result
            else:
                print(f"[X] STUN响应解析失败")
        except socket.timeout:
            print(f"[X] STUN连接超时")
        except Exception as e:
            print(f"[X] STUN连接失败: {e}")

    print("\n[X] 所有STUN服务器均无法使用")
    return None

def generate_spiral_ports(center: int, radius: int) -> list[int]:
    """
    从中心端口向外螺旋生成端口列表
    顺序: center, center+1, center-1, center+2, center-2, ...
    优先探测离STUN端口最近的端口，命中概率最高
    """
    ports = [center]
    for d in range(1, radius + 1):
        if center + d <= 65535:
            ports.append(center + d)
        if center - d >= 1024:
            ports.append(center - d)
    return ports

def input_peer_addr() -> tuple[str, int] | None:
    """
    手动输入对方公网地址
    """
    while True:
        peer_str = input("\n请输入对方的公网地址(格式 IP:端口): ").strip()
        if not peer_str:
            continue
        try:
            ip, port = peer_str.rsplit(":", 1)
            port = int(port)
            if 1 <= port <= 65535:
                return (ip, port)
            print("[X] 端口无效，请输入1-65535之间的数字")
        except ValueError:
            print("[X] 格式错误，请按 IP:端口 格式输入")

def get_peer_via_signaling(udp_sock: socket.socket) -> tuple[str, int] | None:
    """
    通过信令服务器获取对方地址
    流程：
      1. 双方加入房间
      2. 服务器通知 start_stun
      3. 双方同时探测STUN
      4. 发送结果，服务器交换地址
    """
    room_id = input("\n请输入房间ID(双方输入相同ID即可配对): ").strip()
    if not room_id:
        room_id = "default"

    print(f"[*] 连接信令服务器: {SIGNALING_HOST}:{SIGNALING_PORT}")

    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.settimeout(180)  # 3分钟超时

    try:
        tcp_sock.connect((SIGNALING_HOST, SIGNALING_PORT))
        print(f"[OK] 已连接信令服务器")
        print(f"[*] 房间ID: {room_id}")

        # 发送加入请求（不带public_addr）
        request = json.dumps({
            "action": "join",
            "room_id": room_id
        }) + "\n"
        tcp_sock.sendall(request.encode())

        print("[*] 等待对方加入...")

        # 接收响应
        buffer = ""
        while True:
            data = tcp_sock.recv(1024).decode()
            if not data:
                print("[X] 服务器断开连接")
                break

            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue

                msg = json.loads(line)
                action = msg.get("action")

                if action == "waiting":
                    print(f"[*] {msg.get('message', '等待中...')}")
                    continue

                if action == "start_stun":
                    # 双方都到齐，开始STUN探测
                    print(f"[OK] {msg.get('message', '开始STUN探测')}")

                    result = get_public_addr_via_stun(udp_sock)
                    if not result:
                        tcp_sock.close()
                        return None

                    ext_ip, ext_port = result
                    public_addr = f"{ext_ip}:{ext_port}"

                    print("\n" + "=" * 60)
                    print(f"  你的公网地址: {public_addr}")
                    print("=" * 60)

                    # 发送STUN结果
                    result_msg = json.dumps({
                        "action": "stun_result",
                        "public_addr": public_addr
                    }) + "\n"
                    tcp_sock.sendall(result_msg.encode())
                    print("[*] 已提交公网地址，等待对方...")
                    continue

                if action == "peer_found":
                    peer_addr_str = msg.get("peer_addr")
                    print(f"[OK] 配对成功! 对方地址: {peer_addr_str}")
                    tcp_sock.close()

                    ip, port = peer_addr_str.rsplit(":", 1)
                    return (ip, int(port))

                if action == "error":
                    print(f"[X] 服务器错误: {msg.get('message')}")
                    break

    except socket.timeout:
        print("[X] 等待超时")
    except ConnectionRefusedError:
        print("[X] 无法连接信令服务器，请检查服务器是否运行")
    except Exception as e:
        print(f"[X] 信令服务器连接失败: {e}")
    finally:
        tcp_sock.close()

    return None

def start_hole_punching(sock: socket.socket, peer_addr: tuple[str, int]):
    """
    打洞主函数 - 端口扫描 + 生日攻击策略

    对称NAT下，双方向对方STUN端口发包时，各自NAT会分配新的外部端口，
    导致双方都无法命中对方的实际端口。

    策略:
    1. 端口扫描: 不只发往对方STUN报告的端口，而是扫描其附近 ±N 个端口。
       因为对方NAT分配的新端口大概率在STUN端口附近。
    2. 生日攻击: 本地创建多个socket，每个socket在NAT上产生不同的外部端口。
       对方扫描时更容易命中我方某个端口。
       M个socket × N个目标端口 = M×N 种组合，大幅提高成功概率。
    """
    peer_ip, peer_port = peer_addr
    stop_event = threading.Event()
    success_event = threading.Event()
    conn_info = {}  # 存储成功连接信息: {sock, peer}

    # --- 创建额外socket (生日攻击) ---
    extra_socks = []
    for _ in range(NUM_PUNCH_SOCKETS):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("", 0))
        extra_socks.append(s)
    all_socks = [sock] + extra_socks

    # --- 生成扫描端口列表 (螺旋序，中心向外) ---
    sweep_ports = generate_spiral_ports(peer_port, PORT_SWEEP_RANGE)
    port_min, port_max = min(sweep_ports), max(sweep_ports)

    print(f"\n[策略] 端口扫描 + 生日攻击")
    print(f"[配置] {len(all_socks)} 个socket × {len(sweep_ports)} 个端口")
    print(f"       = 每轮 {len(all_socks) * len(sweep_ports)} 种组合")
    print(f"[范围] 扫描端口: {port_min} ~ {port_max}")
    print(f"[目标] {peer_ip}:{peer_port}")
    print(f"\n[*] 开始打洞... (Ctrl+C 退出)\n")

    # --- 监听线程: 用select同时监听所有socket ---
    def listener():
        while not stop_event.is_set():
            try:
                readable, _, _ = select.select(all_socks, [], [], 0.5)
            except (ValueError, OSError):
                if stop_event.is_set():
                    break
                time.sleep(0.1)
                continue

            for rs in readable:
                try:
                    data, addr = rs.recvfrom(RECV_BUFFER)
                    if not success_event.is_set():
                        local_p = rs.getsockname()[1]
                        conn_info['sock'] = rs
                        conn_info['peer'] = addr
                        print(f"\n\n{'=' * 60}")
                        print(f"  打洞成功!")
                        print(f"  本地端口 {local_p} <-> {addr[0]}:{addr[1]}")
                        print(f"  消息: {data.decode('utf-8', errors='ignore')}")
                        print(f"{'=' * 60}\n")
                        success_event.set()
                    else:
                        print(f"\n[收到] {data.decode('utf-8', errors='ignore')}")
                except (OSError, ValueError):
                    continue

    listen_thread = threading.Thread(target=listener, daemon=True)
    listen_thread.start()

    try:
        # ====== Phase 1: 扫描打洞 ======
        round_num = 0
        total_sent = 0

        while not success_event.is_set():
            round_num += 1
            round_sent = 0

            for port in sweep_ports:
                if success_event.is_set():
                    break
                for s in all_socks:
                    try:
                        s.sendto(MESSAGE, (peer_ip, port))
                        round_sent += 1
                    except OSError:
                        pass
                # 每100包暂停2ms，避免NAT限速丢包
                if round_sent % 100 == 0:
                    time.sleep(0.002)

            total_sent += round_sent
            print(
                f"\r[扫描] 第{round_num}轮 | "
                f"本轮 {round_sent} 包 | "
                f"累计 {total_sent} 包",
                end="", flush=True
            )
            time.sleep(0.1)

        # ====== Phase 2: 连接保持 ======
        if conn_info:
            # 停止扫描监听，关闭多余socket
            stop_event.set()
            time.sleep(0.3)

            conn_sock = conn_info['sock']
            conn_peer = conn_info['peer']

            for s in all_socks:
                if s is not conn_sock:
                    try:
                        s.close()
                    except OSError:
                        pass

            # 启动单socket保活监听
            stop_keep = threading.Event()

            def keep_listener():
                conn_sock.settimeout(1)
                while not stop_keep.is_set():
                    try:
                        data, addr = conn_sock.recvfrom(RECV_BUFFER)
                        print(f"\n[收到] {data.decode('utf-8', errors='ignore')}")
                    except socket.timeout:
                        continue
                    except OSError:
                        break

            kl_thread = threading.Thread(target=keep_listener, daemon=True)
            kl_thread.start()

            print(f"[*] 连接已建立，发送保活 (Ctrl+C 退出)\n")
            count = 0
            while True:
                conn_sock.sendto(MESSAGE, conn_peer)
                count += 1
                print(
                    f"\r[保活] 第{count}次 -> {conn_peer[0]}:{conn_peer[1]}",
                    end="", flush=True
                )
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n[*] 已退出")
    finally:
        stop_event.set()
        for s in all_socks:
            try:
                s.close()
            except OSError:
                pass

def main():
    print("=" * 60)
    print("  Python UDP 打洞测试工具")
    print("=" * 60)

    # 1. 创建并绑定UDP Socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("", LOCAL_BIND_PORT))
    except OSError as e:
        print(f"[X] 端口绑定失败: {e}")
        return

    local_port = sock.getsockname()[1]
    print(f"[OK] 本地UDP端口已绑定: {local_port}")

    # 2. 选择配对方式
    print("\n请选择配对方式:")
    print("  1. 通过信令服务器自动配对 (推荐)")
    print("  2. 手动输入对方地址")

    choice = input("\n请输入选项 [1/2]: ").strip()

    if choice == "1":
        # 信令模式：连接房间后再探测STUN
        peer_addr = get_peer_via_signaling(sock)
    else:
        # 手动模式：先探测STUN显示地址
        result = get_public_addr_via_stun(sock)
        if not result:
            sock.close()
            return
        ext_ip, ext_port = result
        print("\n" + "=" * 60)
        print(f"  你的公网地址: {ext_ip}:{ext_port}")
        print("=" * 60)
        peer_addr = input_peer_addr()

    if not peer_addr:
        sock.close()
        return

    # 3. 开始打洞
    start_hole_punching(sock, peer_addr)

if __name__ == "__main__":
    main()
