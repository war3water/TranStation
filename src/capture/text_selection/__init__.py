# src/capture/text_selection/__init__.py
import sys
from typing import Dict, Any

def get_selected_text() -> Dict[str, Any] | None:
    """
    根据当前操作系统调用相应的函数来获取选中文本。
    """
    platform = sys.platform
    if platform == "win32":
        from . import windows
        return windows.get_selected_text_windows()
    elif platform == "darwin":
        from . import macos
        return macos.get_selected_text_macos()
    elif platform.startswith("linux"):
        from . import linux
        return linux.get_selected_text_linux()
    else:
        raise NotImplementedError(f"Unsupported platform: {platform}")
