"""
P2P UDP 打洞测试工具 (交互式 CLI)

使用 pkg/p2p.py 提供的 SignalingClient、hole_punch 等功能。
"""

import socket
import threading
import time
import logging

from pkg.p2p import (
    STUN_SERVERS,
    DEFAULT_SIGNALING_HOST,
    DEFAULT_SIGNALING_PORT,
    NUM_PUNCH_SOCKETS,
    PORT_SWEEP_RANGE,
    SignalingClient,
    get_public_addr_via_stun,
    get_local_addrs,
    build_addr_list,
    parse_addr_list,
    hole_punch,
    is_punch_packet,
    random_punch_payload,
    build_punch_targets,
    _create_dual_stack_udp,
)


LOCAL_BIND_PORT = 0
RECV_BUFFER = 1500


def input_peer_addr() -> tuple[str, int] | None:
    """手动输入对方公网地址。"""
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


def get_peer_via_signaling_interactive(udp_sock: socket.socket) -> list[tuple[str, int]] | None:
    """
    通过信令服务器获取对方地址 (交互式 CLI)。
    返回对端地址列表，或 None。
    """
    room_id = input("\n请输入房间ID(双方输入相同ID即可配对): ").strip()
    if not room_id:
        room_id = "default"

    print("请选择角色:")
    print("  1. owner (设备端，先加入)")
    print("  2. subscriber (控制端，后加入)")
    role_choice = input("请输入选项 [1/2]: ").strip()
    role = "owner" if role_choice == "1" else "subscriber"

    print(f"[*] 连接信令服务器: {DEFAULT_SIGNALING_HOST}:{DEFAULT_SIGNALING_PORT}")

    sc = SignalingClient()
    try:
        sc.connect(DEFAULT_SIGNALING_HOST, DEFAULT_SIGNALING_PORT)
        print("[OK] 已连接信令服务器")
        print(f"[*] 房间ID: {room_id}, 角色: {role}")

        # 以指定角色加入 (owner 或 subscriber)
        sc._send({"type": "join", "room_id": room_id, "role": role})
        print("[*] 等待配对...")

        # owner 需要 ping 保活
        ping_stop = threading.Event()
        if role == "owner":
            def ping_loop():
                while not ping_stop.is_set():
                    try:
                        sc._send({"type": "ping"})
                    except OSError:
                        break
                    ping_stop.wait(10)

            ping_thread = threading.Thread(target=ping_loop, daemon=True)
            ping_thread.start()

        # 等待 joined
        msg = sc._receive_filtered(timeout=10)
        if msg and msg.get("type") == "joined":
            print(f"[OK] {msg.get('message', '已加入')}")
        else:
            print(f"[X] 加入失败: {msg}")
            return None

        # 等待 start_stun
        print("[*] 等待配对...")
        if not sc.wait_for_start_stun():
            print("[X] 等待 start_stun 超时")
            return None

        # STUN 探测
        print("\n[*] 开始 STUN 探测...")
        result = get_public_addr_via_stun(udp_sock)
        if not result:
            print("[X] STUN 探测失败")
            return None

        ext_ip, ext_port = result
        print(f"[OK] STUN 探测成功!")
        print(f"[*] 你的公网地址: {ext_ip}:{ext_port}")

        # 构建地址列表 (公网 + LAN)
        local_port = udp_sock.getsockname()[1]
        local_addrs = get_local_addrs()
        addr_list = build_addr_list((ext_ip, ext_port), local_addrs, local_port)

        print("\n" + "=" * 60)
        print(f"  地址列表: {addr_list}")
        print("=" * 60)

        # 发送 stun_result
        sc.send_stun_result(addr_list)
        print("[*] 已提交地址列表，等待对方...")

        # 等待 peer_found
        peer_addr_str = sc.wait_for_peer()
        if not peer_addr_str:
            print("[X] 等待对端超时")
            return None

        print(f"[OK] 配对成功! 对方地址: {peer_addr_str}")

        # 解析地址列表
        peer_addrs = parse_addr_list(peer_addr_str)
        if not peer_addrs:
            print(f"[X] 无法解析对端地址: {peer_addr_str}")
            return None

        print(f"[*] 对端地址列表: {peer_addrs}")
        return peer_addrs

    except ConnectionError as e:
        print(f"[X] 信令连接失败: {e}")
        return None
    except Exception as e:
        print(f"[X] 信令连接失败: {e}")
        return None
    finally:
        ping_stop.set() if role == "owner" else None
        sc.leave()
        sc.close()


def start_hole_punching(sock: socket.socket, peer_addrs: list[tuple[str, int]]):
    """
    打洞主函数 - 使用 p2p.py 的 hole_punch 函数。
    成功后进入保活循环。
    """
    targets = build_punch_targets(peer_addrs)

    print(f"\n[策略] 端口扫描 + 生日攻击")
    print(f"[配置] {NUM_PUNCH_SOCKETS + 1} 个socket × {len(targets)} 个目标")
    print(f"       = 每轮 {(NUM_PUNCH_SOCKETS + 1) * len(targets)} 种组合")
    print(f"[目标] {peer_addrs}")
    print(f"\n[*] 开始打洞... (Ctrl+C 退出)\n")

    stop_event = threading.Event()

    def on_success(s, addr):
        print(f"\n\n{'=' * 60}")
        print(f"  打洞成功!")
        print(f"  本地端口 {s.getsockname()[1]} <-> {addr[0]}:{addr[1]}")
        print(f"{'=' * 60}\n")

    try:
        result = hole_punch(
            sock, peer_addrs,
            stop_event=stop_event,
            on_success=on_success,
        )

        if not result:
            print("[X] 打洞失败")
            return

        conn_sock, conn_peer = result

        # 保活阶段
        print(f"[*] 连接已建立，发送保活 (Ctrl+C 退出)\n")
        count = 0
        while True:
            conn_sock.sendto(random_punch_payload(), conn_peer)
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


def main():
    print("=" * 60)
    print("  Python UDP 打洞测试工具")
    print("=" * 60)

    # 1. 创建并绑定UDP Socket (双栈，支持 IPv4 + IPv6)
    try:
        sock = _create_dual_stack_udp(LOCAL_BIND_PORT)
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
        # 信令模式
        peer_addrs = get_peer_via_signaling_interactive(sock)
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
        peer_addrs = [peer_addr] if peer_addr else None

    if not peer_addrs:
        sock.close()
        return

    # 3. 开始打洞
    start_hole_punching(sock, peer_addrs)


if __name__ == "__main__":
    main()
