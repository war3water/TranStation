# src/capture/text_selection/linux.py
# 注意: 需要 `python-xlib` 库。
from datetime import datetime
from typing import Dict, Any

def get_selected_text_linux() -> Dict[str, Any] | None:
    """
    在 Linux (X11) 上通过读取 PRIMARY 选择区来获取选中文本。
    """
    try:
        from Xlib import X, display
        from Xlib.error import XError

        d = display.Display()
        owner = d.get_selection_owner(d.intern_atom("PRIMARY"))
        if owner == X.NONE:
            return None

        # 请求选择区内容
        owner.convert_selection(
            d.intern_atom("PRIMARY"),
            d.intern_atom("UTF8_STRING"),
            d.intern_atom("XSEL_DATA"),
            X.CurrentTime,
        )
        
        # 等待事件
        timeout = 0.1 # 100ms timeout
        start_time = datetime.now()
        event = None
        while (datetime.now() - start_time).total_seconds() < timeout:
             if d.pending_events() > 0:
                 event = d.next_event()
                 if event.type == X.SelectionNotify:
                     break
        
        if event and event.property != X.NONE:
            prop = owner.get_property(
                d.intern_atom("XSEL_DATA"),
                X.AnyPropertyType,
                0,
                # Python-xlib的限制，需要获取足够大的长度
                2**20, # 约1MB
            )
            if prop and prop.format == 8: # 8-bit string
                selected_text = prop.value.decode('utf-8')
                return {
                    "type": "text",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "data": selected_text,
                    "metadata": {
                        "source_app_name": "Unknown",
                        "source_window_title": "Unknown" # 在X11下获取窗口标题较复杂
                    }
                }
    except (ImportError, XError, Exception):
        # 如果 Xlib 不可用或出错，则静默失败
        return None
    return None
