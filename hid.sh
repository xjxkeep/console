#!/bin/bash
# 一键配置HID Gadget并发送测试数据


# ----------------------
# 可配置参数
# ----------------------
VENDOR_ID="2207"         # 默认Linux Foundation VID
PRODUCT_ID="0019"        # 默认HID Gadget PID
REPORT_LENGTH=8         # 报告长度（需与描述符匹配）
UDC_NAME="$(ls /sys/class/udc/)"   # 替换为你的UDC名称（通过ls /sys/class/udc获取）
TEST_DATA="\x01\x02\x03\x04\x05\x06\x07\x08"  # 测试数据

# ----------------------
# 设备配置函数
# ----------------------
setup_hid_gadget() {
    # 创建Gadget目录
    # echo "创建Gadget配置..."
    # mkdir -p /sys/kernel/config/usb_gadget/my_hid
    cd /sys/kernel/config/usb_gadget/rockchip || exit 1

    # 设置基础描述符
    echo "0x${VENDOR_ID}" |  tee idVendor >/dev/null
    echo "0x${PRODUCT_ID}" |  tee idProduct >/dev/null
    echo "0x0100" |  tee bcdDevice >/dev/null
    echo "0x0200" |  tee bcdUSB >/dev/null

    # 字符串描述符
     mkdir -p strings/0x409
    echo "SN123456789" |  tee strings/0x409/serialnumber >/dev/null
    echo "endless" |  tee strings/0x409/manufacturer >/dev/null
    echo "HID Data Device" |  tee strings/0x409/product >/dev/null

    # 配置HID功能
    echo "配置HID功能..."
    mkdir -p functions/hid.usb0
    echo 0 |  tee functions/hid.usb0/protocol >/dev/null
    echo 0 |  tee functions/hid.usb0/subclass >/dev/null
    echo $REPORT_LENGTH |  tee functions/hid.usb0/report_length >/dev/null

    # 自定义报告描述符（8字节输入报告）
    echo "写入报告描述符..."
     echo "0600FF0901A1010902150026FF00750895088102C0" | xxd -r -p | tee functions/hid.usb0/report_desc >/dev/null

    # 绑定配置
     mkdir -p configs/b.1
     ln -s functions/hid.usb0 configs/b.1/

    # 清理残留配置
    echo "正在清理旧配置..."
    echo "" |  tee UDC >/dev/null 2>&1

    # 激活设备
    echo "激活设备 (UDC: $UDC_NAME)..."
    echo $UDC_NAME |  tee UDC >/dev/null 2>&1

    # 验证设备节点
    if [[ -e /dev/hidg0 ]]; then
         # chmod 666 /dev/hidg0
        echo "设备配置成功！"
    else
        echo "错误：设备节点未创建，请检查内核日志 (dmesg)"
        exit 1
    fi
}

# ----------------------
# 数据发送函数
# ----------------------
send_test_data() {
    echo "开始发送数据..."
    while true; do
        if !  printf "$TEST_DATA" > /dev/hidg0 2>/dev/null; then
            echo "写入失败，设备可能断开连接"
            return 1
        fi
        echo "数据已发送 → $(date '+%T')"
        sleep 1
    done
}

# ----------------------
# 主程序
# ----------------------
case "$1" in
    setup)
        setup_hid_gadget
        ;;
    send)
        send_test_data
        ;;
    *)
        echo "用法: $0 {setup|send}"
        echo "  setup : 配置HID Gadget"
        echo "  send  : 发送数据"
        exit 1
        ;;
esac