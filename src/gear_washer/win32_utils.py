import ctypes
from ctypes import wintypes
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
gdi32 = ctypes.windll.gdi32

# Win32 Constants
SRCCOPY = 0x00CC0020
DIB_RGB_COLORS = 0
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
MK_LBUTTON = 0x0001

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

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD),
    ]

def MAKELPARAM(l, h):
    return (int(h) << 16) | (int(l) & 0xFFFF)

def background_screenshot(hwnd, x, y, width, height):
    """
    后台截图
    """
    try:
        from PIL import Image
    except ImportError:
        return None

    hwndDC = user32.GetWindowDC(hwnd)
    if not hwndDC:
        return None
    
    mfcDC = gdi32.CreateCompatibleDC(hwndDC)
    if not mfcDC:
        user32.ReleaseDC(hwnd, hwndDC)
        return None

    saveBitMap = gdi32.CreateCompatibleBitmap(hwndDC, width, height)
    if not saveBitMap:
        gdi32.DeleteDC(mfcDC)
        user32.ReleaseDC(hwnd, hwndDC)
        return None

    gdi32.SelectObject(mfcDC, saveBitMap)

    # BitBlt
    result = gdi32.BitBlt(mfcDC, 0, 0, width, height, hwndDC, int(x), int(y), SRCCOPY)
    
    image = None
    if result:
        bmpinfo = BITMAPINFOHEADER()
        bmpinfo.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmpinfo.biWidth = width
        bmpinfo.biHeight = -height
        bmpinfo.biPlanes = 1
        bmpinfo.biBitCount = 32
        bmpinfo.biCompression = 0
        
        buffer_len = width * height * 4
        buffer = ctypes.create_string_buffer(buffer_len)
        
        gdi32.GetDIBits(mfcDC, saveBitMap, 0, height, buffer, ctypes.byref(bmpinfo), DIB_RGB_COLORS)
        image = Image.frombuffer('RGB', (width, height), buffer, 'raw', 'BGRX', 0, 1)

    gdi32.DeleteObject(saveBitMap)
    gdi32.DeleteDC(mfcDC)
    user32.ReleaseDC(hwnd, hwndDC)
    
    return image

def send_mouse_move(hwnd, x, y):
    point = ctypes.wintypes.POINT(int(x), int(y))
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    # 假设传入的 x,y 是相对于窗口(包括边框)左上角的
    screen_x = rect.left + int(x)
    screen_y = rect.top + int(y)
    
    point_screen = ctypes.wintypes.POINT(screen_x, screen_y)
    user32.ScreenToClient(hwnd, ctypes.byref(point_screen))
    
    lparam = MAKELPARAM(point_screen.x, point_screen.y)
    user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)

def send_mouse_click(hwnd, x, y):
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    screen_x = rect.left + int(x)
    screen_y = rect.top + int(y)
    
    point_screen = ctypes.wintypes.POINT(screen_x, screen_y)
    user32.ScreenToClient(hwnd, ctypes.byref(point_screen))
    
    lparam = MAKELPARAM(point_screen.x, point_screen.y)
    
    user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
    time.sleep(0.05)
    user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, lparam)

def send_key_click(hwnd, key_str):
    vk_map = {
        'z': 0x5A,
        'space': 0x20,
        'enter': 0x0D
    }
    vk_code = vk_map.get(key_str.lower(), 0x5A)
    
    # 构造 lParam (scan code 等)
    scan_code = user32.MapVirtualKeyW(vk_code, 0)
    lparam_down = 0x00000001 | (scan_code << 16)
    # bit 30: previous key state, bit 31: transition state (0=press, 1=release)
    lparam_up = 0xC0000001 | (scan_code << 16)
    
    user32.PostMessageW(hwnd, WM_KEYDOWN, vk_code, lparam_down)
    time.sleep(0.05)
    user32.PostMessageW(hwnd, WM_KEYUP, vk_code, lparam_up)
