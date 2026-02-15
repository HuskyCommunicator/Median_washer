import time
import pyautogui
import json
try:
    import keyboard
except ImportError:
    keyboard = None

from .matcher import AffixMatcher
from .screen import ScreenReader
from . import win32_utils # 导入窗口工具

class GearWasher:
    def __init__(self, tesseract_cmd=None, debug_mode=False, ocr_scale_factor=2.5, background_mode=False):
        self.matcher = AffixMatcher()
        self.screen = ScreenReader(tesseract_cmd, debug_mode=debug_mode)
        self.debug_mode = debug_mode
        self.background_mode = background_mode
        self.ocr_scale_factor = ocr_scale_factor  # OCR图片放大倍数，原图字高20px左右，2.5倍放大到50px最佳
        
        # 默认配置
        self.gear_pos = None     # (x, y) 装备悬停位置 (可能是相对坐标)
        self.affix_region = None  # (x, y, w, h) 词缀识别区域 (如果是相对模式，xy为相对)
        self.window_title = None  # 绑定的窗口标题，如果不为None，则启用相对坐标模式
        self.wash_button_pos = None # (x, y) 洗炼按钮位置
        self.conditions = None
        self.max_attempts = 10000
        self.interval = 0.2 # 每次洗炼间隔(秒) - 默认加快速度
        
        # 中止信号标志位
        self.stop_requested = False
        if keyboard:
            try:
                # 注册全局热键，确保即使在 busy 时也能捕获按键
                keyboard.add_hotkey('home', self._on_stop_signal)
            except Exception as e:
                print(f"热键注册失败: {e}")

    def _on_stop_signal(self):
        """Home键的回调函数"""
        if not self.stop_requested:
            print("\n>>> 已捕获 HOME 键，正在通过信号停止... <<<")
            self.stop_requested = True

    def stop(self):
        self._on_stop_signal()

    def _wait_for_key(self):
        """等待按键确认坐标"""
        while True:
             if keyboard.is_pressed('space'):
                 # 防抖动
                 time.sleep(0.3)
                 return pyautogui.position()
             time.sleep(0.05)

    def _wait_for_limit(self):
        """等待空格键记录坐标"""
        import msvcrt
        print("请按【空格键】确认记录...", end="", flush=True)
        while True:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b' ':  # 空格键
                    print("\r" + " " * 30 + "\r", end="", flush=True)  # 清除提示
                    return pyautogui.position()
            time.sleep(0.05)

    def calibrate_ui(self):
        """
        [新的] 交互式获取坐标配置，返回字典
        此版本支持相对坐标：会先记录当前游戏窗口的位置
        """
        print("=== 界面坐标校准模式 ===")
        
        # 检查是否可以使用键盘触发
        if keyboard:
            print("说明：将鼠标移动到目标位置，然后按下 【Space 空格键】 确认记录。")
            wait_func = self._wait_for_key 
        else:
            print("警告：未安装 keyboard 库，将使用受限的空格键模式。")
            wait_func = self._wait_for_limit

        # 0. 绑定游戏窗口
        print("\n[0/3] 正在识别游戏窗口...")
        print("请【激活/点击】游戏窗口，确保它是当前活动窗口，然后按【Space 空格键】确认绑定。")
        wait_func() # 等待用户确认激活
        
        target_window = win32_utils.get_foreground_window_info()
        if not target_window:
            print("警告：无法获取活动窗口信息！将使用绝对坐标模式。")
            win_x, win_y = 0, 0
            win_title = None
        else:
            win_x, win_y = target_window['x'], target_window['y']
            win_title = target_window['title']
            print(f"已绑定窗口: [{win_title}] 位置: ({win_x}, {win_y})")
            print("接下来录制的所有坐标都将相对于此窗口左上角。")
        
        # 1. 设置装备悬停位置
        print("\n[1/3] 请将鼠标移动到【装备图标】上（用于触发属性浮窗）...")
        gx, gy = wait_func()
        # 转换为相对坐标
        gx_rel, gy_rel = gx - win_x, gy - win_y
        print(f"记录装备位置: 绝对{(gx, gy)} -> 相对{(gx_rel, gy_rel)}")

        # 2. 设置词缀识别区域
        print("\n[2/3] 即将设置词缀区域 (OCR范围)。")
        print("提示：请确保浮窗可见。")
        
        print("请将鼠标移动到【词缀文字区域】的【左上角】...")
        x1, y1 = wait_func()
        print(f"记录左上角: ({x1}, {y1})")
        
        print("\n请将鼠标移动到【词缀文字区域】的【右下角】...")
        x2, y2 = wait_func()
        print(f"记录右下角: ({x2}, {y2})")
        
        # 返回原始定义的两个对角点，方便存储和计算
        p1 = (x1 - win_x, y1 - win_y)
        p2 = (x2 - win_x, y2 - win_y)

        print("\n[3/3] 完成！鼠标将停留在装备位置，按Z键进行洗炼。")
        
        return {
            "gear_pos": (gx_rel, gy_rel),
            "affix_points": (p1, p2),
            "window_title": win_title
        }

    def setup_wizard(self):
        """
        (旧版兼容) 交互式设置向导
        """
        data = self.calibrate_ui()
        self.gear_pos = data['gear_pos']
        # 兼容旧逻辑：立即计算矩形
        p1, p2 = data['affix_points']
        x = min(p1[0], p2[0])
        y = min(p1[1], p2[1])
        w = abs(p2[0] - p1[0])
        h = abs(p2[1] - p1[1])
        self.affix_region = (x, y, w, h)

        # 4. 设置目标词缀
        print("\n[3/3] 设置目标词缀逻辑")

        # 4. 设置目标词缀
        print("\n[4/4] 设置目标词缀逻辑")
        raw_input = input("请输入目标词缀 (直接回车保持默认): ").strip()
        if raw_input:
            self.conditions = raw_input
        elif not self.conditions:
            self.conditions = "冰霜抗性"

        print(f"当前匹配条件: {self.conditions}")

        print("\n设置完成！")

    def _check_stop(self):
        """检查是否有停止信号"""
        # 1. 检查标志位 (由 hotkey 设置)
        if self.stop_requested:
            return True
            
        # 2. 直接检查按键状态 (作为备用)
        if keyboard and keyboard.is_pressed('home'):
            self.stop_requested = True # 确保标志位同步
            print("\n\n>>> 检测到 HOME 键 (直接)，正在停止... <<<")
            return True
            
        return False

    def _smart_sleep(self, duration):
        """
        智能等待：将长时间的 sleep 切割成小段，
        期间不断检查由 _check_stop 定义的中止条件。
        返回 True 表示被中止，False 表示等待完成。
        """
        start_time = time.time()
        while time.time() - start_time < duration:
            if self._check_stop():
                return True
            # 检测频率：每 0.05 秒检查一次
            time.sleep(0.05)
        return False

    def run(self):
        if not self.affix_region or not self.gear_pos:
            print("错误: 未配置区域，请先运行 setup_wizard()")
            return

        print(f"开始执行洗炼，最大尝试次数: {self.max_attempts}")
        if self.background_mode:
            print("模式: [后台运行] - 请确保游戏窗口不要最小化 (可以被遮挡)")
        else:
            print("模式: [前台运行] - 请在该窗口激活游戏/应用，不要移动鼠标")
            
        print("提示：按【HOME键】可随时终止运行")
        
        # 启动等待也可以被打断
        if self._smart_sleep(1.0): 
            print("启动被打断。")
            return

        # 查找窗口并计算
        offset_x, offset_y = 0, 0
        target_hwnd = None
        
        if self.window_title:
            print(f"尝试查找窗口: [{self.window_title}] ...")
            target_win = win32_utils.find_window_by_title(self.window_title)
            if target_win:
                offset_x, offset_y = target_win['x'], target_win['y']
                target_hwnd = target_win['hwnd']
                print(f"已定位窗口位置: ({offset_x}, {offset_y}) HWND: {target_hwnd}")
            else:
                print(f"错误: 找不到标题包含 [{self.window_title}] 的窗口！")
                if self.background_mode:
                    print("后台模式必须依赖窗口绑定，无法继续！")
                    return
                print("前台模式将尝试使用最后的绝对坐标 (可能不准确)...")
        else:
             if self.background_mode:
                print("错误: 后台模式必须在配置中绑定窗口标题！")
                return

        # 预计算前台模式需要的绝对坐标
        real_gear_pos = (self.gear_pos[0] + offset_x, self.gear_pos[1] + offset_y)
        real_affix_region = (self.affix_region[0] + offset_x, self.affix_region[1] + offset_y, self.affix_region[2], self.affix_region[3])

        for i in range(self.max_attempts):
            # --- 阶段性检查 1 ---
            if self._check_stop(): break

            # 调试日志仅每10次显示一次，避免刷屏 (还是全显吧，用户爱看不看)
            print(f"\n--- 第 {i+1} 次尝试 ---")
            
            # 1. 移动到装备位置，显示浮窗
            if self.background_mode:
                 # 后台模式：发送鼠标移动消息 (使用相对坐标)
                 win32_utils.send_mouse_move(target_hwnd, self.gear_pos[0], self.gear_pos[1])
            else:
                 # 前台模式：物理移动鼠标
                 pyautogui.moveTo(real_gear_pos[0], real_gear_pos[1], duration=0)
            
            # --- 阶段性检查 2 (移动后) ---
            if self._check_stop(): break

            # 等待浮窗显示
            if self._smart_sleep(0.1): break

            # 2. 识别当前属性
            if self._check_stop(): break
            
            try:
                if self.background_mode:
                    # 后台模式：传递 hwnd 和相对区域
                    text = self.screen.read_text(self.affix_region, scale_factor=self.ocr_scale_factor, hwnd=target_hwnd)
                else:
                    # 前台模式：使用绝对区域
                    text = self.screen.read_text(real_affix_region, scale_factor=self.ocr_scale_factor)
            except Exception as e:
                print(f"识别出错: {e}")
                text = ""

            clean_text = text.replace("\n", " | ")
            print(f"识别到的文本: {clean_text}")

            # --- 阶段性检查 3 (识别后) ---
            if self._check_stop(): break

            # 3. 判断是否满足条件
            if self.matcher.check(text, self.conditions):
                print(">>> 成功匹配到目标属性！停止洗炼。 <<<")
                
                # 尝试强制前台并置顶 (仅提醒)
                import ctypes
                try:
                    # 如果是后台模式，可能需要闪烁任务栏提醒
                    if self.background_mode:
                        ctypes.windll.user32.FlashWindow(ctypes.windll.kernel32.GetConsoleWindow(), 1)
                    else:
                        ctypes.windll.user32.SwitchToThisWindow(ctypes.windll.kernel32.GetConsoleWindow(), 1)
                except:
                    pass
                
                ctypes.windll.user32.MessageBoxW(0, f'洗炼完成！\n已匹配到目标属性:\n{self.conditions}', '装备洗炼助手', 0x40 | 0x1000)
                break
            
            # 4. 不满足，按Z键洗炼
            # 注意：在后台模式下，鼠标理论上只是发送了消息，不需要显式保持。
            # 但为了保险，可以再次确保鼠标位置(通常不需要)
            
            print("未匹配，按Z键洗炼...")
            if self.background_mode:
                 win32_utils.send_key_click(target_hwnd, 'z')
            else:
                if keyboard:
                    try:
                        keyboard.press_and_release('z')
                    except:
                        pyautogui.press('z')
                else:
                    pyautogui.press('z')
            
            # 5. 等待动画或刷新
            if self._smart_sleep(self.interval):
                print("\n\n>>> 用户手动停止脚本。 <<<")
                try:
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(0, '用户手动中止洗炼。', '脚本停止', 0x40 | 0x1000)
                except:
                    pass
                break

        else:
             print("已达到最大尝试次数，停止执行。")

if __name__ == "__main__":
    # 示例用法
    washer = GearWasher()
    
    # 你可以在这里硬编码配置，或者使用向导
    # washer.affix_region = (100, 100, 200, 300)
    # washer.wash_button_pos = (500, 500)
    # washer.conditions = {'OR': ['冰霜抗性', '火焰抗性']}
    
    # 启动向导
    washer.setup_wizard()
    
    # 确认执行
    confirm = input("是否开始执行？(y/n): ")
    if confirm.lower() == 'y':
        washer.run()
