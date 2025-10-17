# utils/platform_utils.py
import sys

def get_platform() -> str:
    """
    返回当前操作系统的规范名称。
    """
    return sys.platform

def is_windows() -> bool:
    return get_platform() == "win32"

def is_macos() -> bool:
    return get_platform() == "darwin"

def is_linux() -> bool:
    return get_platform().startswith("linux")
