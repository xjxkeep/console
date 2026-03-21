"""
应用程序版本信息
"""

import json
import os
import logging

# 默认值
VERSION = "0.0.1"
APP_NAME = "Andless Console"
CHANNEL = "dev"
COMMIT = ""
BUILD_TIME = ""

# 从 CI 生成的 version.json 加载版本信息
_version_file = os.path.join(os.path.dirname(__file__), "..", "assets", "version.json")
if os.path.exists(_version_file):
    try:
        with open(_version_file, encoding="utf-8") as _f:
            _info = json.load(_f)
            VERSION = _info.get("version") or VERSION
            CHANNEL = _info.get("channel", "dev")
            COMMIT = _info.get("commit", "")
            BUILD_TIME = _info.get("build_time", "")
    except Exception as _e:
        logging.warning(f"Failed to load version.json: {_e}")


def get_window_title() -> str:
    if CHANNEL == "dev" and COMMIT:
        return f"{APP_NAME} v{VERSION}-dev ({COMMIT[:7]})"
    return f"{APP_NAME} v{VERSION}"
