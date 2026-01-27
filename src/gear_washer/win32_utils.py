import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG)
    ]

def get_foreground_window_info():
    """获取当前活动窗口的句柄、标题和位置(x, y, w, h)"""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None
        
    # 获取标题
    length = user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buff, length + 1)
    title = buff.value
    
    # 获取位置
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    
    return {
        "hwnd": hwnd,
        "title": title,
        "x": rect.left,
        "y": rect.top,
        "w": rect.right - rect.left,
        "h": rect.bottom - rect.top
    }

def find_window_by_title(title_part):
    """
    根据标题查找窗口（部分匹配）
    注意：FindWindowW 只能精确匹配类名或标题，这里我们需要遍历枚举
    """
    if not title_part:
        return None

    found_windows = []

    def enum_windows_proc(hwnd, lParam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            curr_title = buff.value
            
            # 只有可见窗口才算
            if user32.IsWindowVisible(hwnd) and title_part in curr_title:
                rect = RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                found_windows.append({
                    "hwnd": hwnd,
                    "title": curr_title,
                    "x": rect.left,
                    "y": rect.top,
                    "w": rect.right - rect.left,
                    "h": rect.bottom - rect.top
                })
        return True

    CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    user32.EnumWindows(CMPFUNC(enum_windows_proc), 0)
    
    # 优先返回完全匹配的，否则返回第一个部分匹配的
    for w in found_windows:
        if w['title'] == title_part:
            return w
    
    if found_windows:
        return found_windows[0]
        
    return None

def get_window_rect(hwnd):
    rect = RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return (rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
    return None
