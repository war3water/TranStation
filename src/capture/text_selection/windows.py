# src/capture/text_selection/windows.py
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import comtypes.client
import comtypes
import ctypes
from ctypes import wintypes
# 关键修复：导入COM初始化所需的常量
from comtypes import BSTR, COINIT_APARTMENTTHREADED

# IAccessible 接口定义，当前版本中未使用，但保留用于未来可能的扩展
# 为MSAA定义必要的常量和接口
oleacc = ctypes.windll.oleacc
VT_I4 = 3
CHILDID_SELF = 0

class IAccessible(comtypes.IUnknown):
    _iid_ = comtypes.GUID('{618736E0-3C3D-11CF-810C-00AA00389B71}')
    _methods_ = [
        comtypes.STDMETHOD(comtypes.HRESULT, "GetIDsOfNames", (ctypes.POINTER(comtypes.GUID), wintypes.LPOLESTR, ctypes.c_uint, wintypes.LCID, ctypes.POINTER(comtypes.automation.DISPID))),
        comtypes.STDMETHOD(comtypes.HRESULT, "Invoke", (comtypes.automation.DISPID, ctypes.POINTER(comtypes.GUID), wintypes.LCID, wintypes.WORD, ctypes.POINTER(comtypes.automation.DISPPARAMS), ctypes.POINTER(comtypes.automation.VARIANT), ctypes.POINTER(comtypes.automation.EXCEPINFO), ctypes.POINTER(ctypes.c_uint))),
        comtypes.STDMETHOD(ctypes.c_int, "get_accParent", (ctypes.POINTER(ctypes.POINTER(comtypes.automation.IDispatch)),)),
        comtypes.STDMETHOD(ctypes.c_int, "get_accChildCount", (ctypes.POINTER(ctypes.c_long),)),
        comtypes.STDMETHOD(ctypes.c_int, "get_accChild", (comtypes.automation.VARIANT, ctypes.POINTER(ctypes.POINTER(comtypes.automation.IDispatch)))),
        comtypes.STDMETHOD(ctypes.c_int, "get_accName", (comtypes.automation.VARIANT, ctypes.POINTER(BSTR))),
        comtypes.STDMETHOD(ctypes.c_int, "get_accValue", (comtypes.automation.VARIANT, ctypes.POINTER(BSTR))),
        comtypes.STDMETHOD(ctypes.c_int, "get_accDescription", (comtypes.automation.VARIANT, ctypes.POINTER(BSTR))),
        comtypes.STDMETHOD(ctypes.c_int, "get_accRole", (comtypes.automation.VARIANT, ctypes.POINTER(comtypes.automation.VARIANT))),
        comtypes.STDMETHOD(ctypes.c_int, "get_accState", (comtypes.automation.VARIANT, ctypes.POINTER(comtypes.automation.VARIANT))),
        comtypes.STDMETHOD(ctypes.c_int, "get_accHelp", (comtypes.automation.VARIANT, ctypes.POINTER(BSTR))),
        comtypes.STDMETHOD(ctypes.c_int, "get_accHelpTopic", (ctypes.POINTER(BSTR), comtypes.automation.VARIANT, ctypes.POINTER(ctypes.c_long))),
        comtypes.STDMETHOD(ctypes.c_int, "get_accKeyboardShortcut", (comtypes.automation.VARIANT, ctypes.POINTER(BSTR))),
        comtypes.STDMETHOD(ctypes.c_int, "get_accFocus", (ctypes.POINTER(comtypes.automation.VARIANT),)),
        comtypes.STDMETHOD(ctypes.c_int, "get_accSelection", (ctypes.POINTER(comtypes.automation.VARIANT),)),
        comtypes.STDMETHOD(ctypes.c_int, "get_accDefaultAction", (comtypes.automation.VARIANT, ctypes.POINTER(BSTR))),
        comtypes.STDMETHOD(ctypes.c_int, "accSelect", (ctypes.c_long, comtypes.automation.VARIANT)),
        comtypes.STDMETHOD(ctypes.c_int, "accLocation", (ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_long), ctypes.POINTER(ctypes.c_long), comtypes.automation.VARIANT)),
        comtypes.STDMETHOD(ctypes.c_int, "accNavigate", (ctypes.c_long, comtypes.automation.VARIANT, ctypes.POINTER(comtypes.automation.VARIANT))),
        comtypes.STDMETHOD(ctypes.c_int, "accHitTest", (ctypes.c_long, ctypes.c_long, ctypes.POINTER(comtypes.automation.VARIANT))),
        comtypes.STDMETHOD(ctypes.c_int, "accDoDefaultAction", (comtypes.automation.VARIANT,)),
        comtypes.STDMETHOD(ctypes.c_int, "put_accName", (comtypes.automation.VARIANT, BSTR)),
        comtypes.STDMETHOD(ctypes.c_int, "put_accValue", (comtypes.automation.VARIANT, BSTR)),
    ]

_uia_module = None

def _initialize_uia():
    """动态加载并缓存UIAutomationClient类型库。"""
    global _uia_module
    if _uia_module is None:
        try:
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen import UIAutomationClient
            _uia_module = UIAutomationClient
        except (ImportError, OSError) as e:
            logging.error(f"无法加载 UIAutomationCore.dll: {e}")
            _uia_module = None
    return _uia_module

def _find_text_selection_recursive(uia_element, uia_interface, tree_walker):
    """
    递归遍历UI元素树，查找支持文本模式并有内容的选区。
    """
    if not uia_element:
        return None
    
    try:
        # 检查当前元素是否支持文本模式 (TextPattern)
        text_pattern_unknown = uia_element.GetCurrentPattern(10014) # TextPattern ID
        if text_pattern_unknown:
            text_pattern = text_pattern_unknown.QueryInterface(uia_interface.IUIAutomationTextPattern)
            if text_pattern:
                selection = text_pattern.GetSelection()
                if selection and selection.Length > 0:
                    texts = [selection.GetElement(i).GetText(-1).strip() for i in range(selection.Length)]
                    full_text = "\n".join(filter(None, texts))
                    if full_text:
                        return full_text, uia_element
    except comtypes.COMError:
        pass

    if tree_walker:
        try:
            child = tree_walker.GetFirstChildElement(uia_element)
            while child:
                result = _find_text_selection_recursive(child, uia_interface, tree_walker)
                if result:
                    return result
                child = tree_walker.GetNextSiblingElement(child)
        except comtypes.COMError:
            pass
        
    return None


def get_selected_text_windows() -> Optional[Dict[str, Any]]:
    """
    在 Windows 上通过 UI Automation (UIA) 的 TextPattern 精准获取选中的文本。
    此版本已修复COM初始化问题，并增加了详细的调试日志。
    """
    UIAutomationClient = _initialize_uia()
    if not UIAutomationClient:
        return None

    # 关键修复: 为当前工作线程以单线程单元(STA)模式初始化COM
    # 这是在非GUI主线程中稳定操作UI元素的必要条件
    comtypes.CoInitializeEx(COINIT_APARTMENTTHREADED)
    
    try:
        uia = comtypes.client.CreateObject(UIAutomationClient.CUIAutomation, interface=UIAutomationClient.IUIAutomation)
        try:
            focused_element = uia.GetFocusedElement()
        except comtypes.COMError as e:
            if e.hresult == -2147220991:
                logging.debug("UIA无法获取焦点元素（例如桌面），此为正常情况。")
                return None
            else:
                raise
        
        if focused_element:
            tree_walker = uia.RawViewWalker
            result = _find_text_selection_recursive(focused_element, UIAutomationClient, tree_walker)
            
            if result:
                full_text, element = result
                logging.info(f"成功捕获文本: '{full_text[:70].strip().replace('\n', ' ')}...'")
                try:
                    window_title = element.CurrentName
                    app_name = element.CurrentClassName
                except Exception:
                    window_title, app_name = "Unknown", "Unknown"
                
                return {
                    "type": "text", 
                    "timestamp": datetime.utcnow().isoformat() + "Z", 
                    "data": full_text,
                    "metadata": {
                        "source_app_name": app_name,
                        "source_window_title": window_title,
                        "method": "UIA_TextPattern_Precise"
                    }
                }
    except Exception as e:
        # 关键修复: 打开 exc_info=True 以便看到完整的错误堆栈
        logging.error(f"捕获划词内容时发生未知错误: {e}", exc_info=True)
    finally:
        # 确保COM库在此线程中被正确释放
        comtypes.CoUninitialize()
    
    return None
