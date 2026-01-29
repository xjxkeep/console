"""
应用程序版本信息
"""

# 版本号
VERSION = "1.0.0"

# 应用名称
APP_NAME = "Andless Console"

# 完整标题
def get_window_title() -> str:
    return f"{APP_NAME} v{VERSION}"
